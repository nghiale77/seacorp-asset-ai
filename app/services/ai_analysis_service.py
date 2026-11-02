"""Bước 2 — AI phân tích nhu cầu tài sản.

Nguyên tắc bắt buộc (lấy từ tài liệu, mục Bước 2 và AN TOÀN THÔNG TIN VÀ QUẢN
TRỊ AI): trích xuất 4 nhóm thông tin (đơn vị đề xuất / tài sản / nhu cầu sử
dụng / hiệu quả); phân loại Đầy đủ / Thiếu thông tin / Không rõ mục đích /
Trùng yêu cầu; KHÔNG tự suy diễn thông số kỹ thuật, giá trị đầu tư hay hiệu
quả kinh tế khi chưa có dữ liệu — khi thiếu cơ sở phải trả "Chưa đủ cơ sở
đánh giá", không đoán. Nếu chưa cấu hình ANTHROPIC_API_KEY, hệ thống fallback
sang chế độ yêu cầu nhập liệu/phân loại thủ công.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.timeutils import utcnow
from app.models.request import AssetRequest
from app.services.duplicate_detection import find_possible_duplicate

NOT_ENOUGH_BASIS = "Chưa đủ cơ sở đánh giá"

EXTRACTION_TOOL = {
    "name": "extract_asset_request",
    "description": "Trích xuất thông tin có cấu trúc từ nội dung yêu cầu tài sản.",
    "input_schema": {
        "type": "object",
        "properties": {
            "unit_info": {"type": "string", "description": "Thông tin đơn vị đề xuất: pháp nhân, phòng ban, người đề xuất, người phụ trách, địa điểm sử dụng — chỉ ghi lại những gì có trong văn bản."},
            "asset_info": {"type": "string", "description": "Thông tin tài sản: tên, nhóm, thông số kỹ thuật, số lượng, công suất, giá trị dự kiến, thời gian cần — chỉ ghi lại những gì có trong văn bản."},
            "usage_need": {"type": "string", "description": "Mục đích sử dụng, lý do phát sinh nhu cầu, khả năng tận dụng tài sản hiện có, tác động nếu không đáp ứng."},
            "efficiency_info": {"type": "string", "description": "Sản lượng/công suất dự kiến, doanh thu hoặc giá trị tiết kiệm dự kiến, chi phí vận hành — CHỈ nếu có nêu rõ trong văn bản."},
            "asset_group": {"type": ["string", "null"], "description": "Nhóm/loại tài sản cụ thể được yêu cầu, ví dụ 'Xe tải', 'Máy nông nghiệp'. Null nếu không rõ."},
            "requested_quantity": {"type": ["number", "null"], "description": "Số lượng tài sản cần, null nếu không nêu."},
            "requested_capacity": {"type": ["number", "null"], "description": "Công suất/tải trọng cần, null nếu không nêu."},
            "requested_location_province": {"type": ["string", "null"], "description": "Tỉnh/thành nơi sử dụng, null nếu không nêu."},
            "needed_by_date": {"type": ["string", "null"], "description": "Ngày cần có tài sản, định dạng YYYY-MM-DD, null nếu không nêu rõ."},
            "completeness": {
                "type": "string",
                "enum": ["Đầy đủ", "Thiếu thông tin", "Không rõ mục đích"],
                "description": "Đầy đủ = có đủ đơn vị, tài sản, mục đích, số lượng/công suất. Thiếu thông tin = thiếu một hoặc nhiều trường định lượng/định danh then chốt. Không rõ mục đích = có mô tả tài sản nhưng không nêu lý do/mục đích sử dụng.",
            },
            "confidence_note": {"type": "string", "description": "Ghi chú mức độ tin cậy; nêu rõ các trường còn thiếu/chưa chắc chắn. Nếu thiếu dữ liệu để đánh giá hiệu quả/giá trị, phải ghi 'Chưa đủ cơ sở đánh giá' cho phần đó, không suy diễn."},
        },
        "required": ["unit_info", "asset_info", "usage_need", "efficiency_info", "completeness", "confidence_note"],
    },
}

SYSTEM_PROMPT = (
    "Bạn là trợ lý phân tích yêu cầu tài sản cho Phòng Quản lý Tài sản & Đầu tư SeaCorp. "
    "CHỈ trích xuất thông tin thực sự có trong nội dung được cung cấp. "
    "TUYỆT ĐỐI KHÔNG suy diễn, KHÔNG bổ sung số liệu, thông số kỹ thuật, giá trị đầu tư hoặc "
    "hiệu quả kinh tế không được nêu rõ trong văn bản. Trường nào không có dữ liệu thì để trống/null "
    "hoặc ghi 'Chưa đủ cơ sở đánh giá', không được đoán hoặc ước lượng tùy ý. "
    "Luôn gọi tool extract_asset_request với kết quả trích xuất."
)


@dataclass
class ExtractedFields:
    unit_info: str
    asset_info: str
    usage_need: str
    efficiency_info: str
    completeness: str
    confidence_note: str
    asset_group: str | None = None
    requested_quantity: float | None = None
    requested_capacity: float | None = None
    requested_location_province: str | None = None
    needed_by_date: str | None = None
    source: str = "claude_api"


def _extract_via_claude(content: str) -> ExtractedFields:
    import anthropic

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.ai_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "extract_asset_request"},
        messages=[{"role": "user", "content": f"Nội dung yêu cầu tài sản:\n\n{content}"}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    data = tool_use.input
    return ExtractedFields(
        unit_info=data.get("unit_info", ""),
        asset_info=data.get("asset_info", ""),
        usage_need=data.get("usage_need", ""),
        efficiency_info=data.get("efficiency_info") or NOT_ENOUGH_BASIS,
        completeness=data.get("completeness", "Thiếu thông tin"),
        confidence_note=data.get("confidence_note", ""),
        asset_group=data.get("asset_group"),
        requested_quantity=data.get("requested_quantity"),
        requested_capacity=data.get("requested_capacity"),
        requested_location_province=data.get("requested_location_province"),
        needed_by_date=data.get("needed_by_date"),
        source="claude_api",
    )


def _extract_fallback_manual(content: str) -> ExtractedFields:
    """Không có ANTHROPIC_API_KEY hoặc gọi API lỗi — không suy diễn, yêu cầu
    chuyên viên QLTS&ĐT nhập liệu/phân loại thủ công."""
    return ExtractedFields(
        unit_info=NOT_ENOUGH_BASIS,
        asset_info=content,
        usage_need=NOT_ENOUGH_BASIS,
        efficiency_info=NOT_ENOUGH_BASIS,
        completeness="Thiếu thông tin",
        confidence_note=(
            f"{NOT_ENOUGH_BASIS}: AI chưa được cấu hình (thiếu ANTHROPIC_API_KEY) hoặc không gọi được. "
            "Chuyên viên Phòng QLTS&ĐT cần đọc nội dung gốc và nhập liệu/phân loại thủ công."
        ),
        source="manual_fallback",
    )


def run_ai_analysis(db: Session, request_id: str) -> AssetRequest:
    request = db.get(AssetRequest, request_id)
    if request is None:
        raise ValueError(f"Không tìm thấy yêu cầu {request_id}")

    duplicate = find_possible_duplicate(
        db, request.sender_email, request.original_content, request.received_at,
        exclude_request_id=request.request_id,
    )
    if duplicate is not None:
        request.suspected_duplicate = True
        request.duplicate_of_request_id = duplicate.request_id
        request.ai_completeness = "Trùng yêu cầu"
        request.ai_confidence_note = (
            f"Nghi trùng với hồ sơ {duplicate.request_id} (cùng người gửi, nội dung tương tự trong "
            f"vòng {duplicate.received_at:%d/%m/%Y}) — cần Phòng QLTS&ĐT xác nhận trước khi xử lý tiếp."
        )
        request.updated_at = utcnow()
        db.flush()
        return request

    settings = get_settings()
    if settings.ai_enabled:
        try:
            extracted = _extract_via_claude(request.original_content)
        except Exception as exc:  # không để lỗi AI làm gãy luồng tiếp nhận
            extracted = _extract_fallback_manual(request.original_content)
            extracted.confidence_note += f" (Lỗi gọi Claude API: {exc})"
    else:
        extracted = _extract_fallback_manual(request.original_content)

    request.proposed_unit_info = extracted.unit_info
    request.proposed_asset_info = extracted.asset_info
    request.proposed_usage_need = extracted.usage_need
    request.proposed_efficiency_info = extracted.efficiency_info
    request.ai_completeness = extracted.completeness
    request.ai_confidence_note = extracted.confidence_note

    if extracted.asset_group and not request.asset_group:
        request.asset_group = extracted.asset_group
    if extracted.requested_quantity is not None and request.requested_quantity is None:
        request.requested_quantity = extracted.requested_quantity
    if extracted.requested_capacity is not None and request.requested_capacity is None:
        request.requested_capacity = extracted.requested_capacity
    if extracted.requested_location_province and not request.requested_location_province:
        request.requested_location_province = extracted.requested_location_province
    if extracted.needed_by_date and not request.needed_by_date:
        try:
            import datetime as dt
            request.needed_by_date = dt.date.fromisoformat(extracted.needed_by_date)
        except ValueError:
            pass

    request.updated_at = utcnow()
    db.flush()
    return request
