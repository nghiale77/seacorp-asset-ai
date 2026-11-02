"""Bước 3 — đối chiếu dữ liệu tài sản toàn hệ thống. "Chức năng quan trọng
nhất của ứng dụng" theo tài liệu nghiệp vụ.

Thiết kế: chấm điểm 7 tiêu chí trên thang 100 (trọng số đọc từ
`system_settings`, cấu hình được theo nhóm tài sản), áp ngưỡng tham khảo
85/70. Kết quả LUÔN ở trạng thái "đề xuất / chờ xác nhận" — hàm ở đây không
bao giờ tự kết luận một tài sản đủ điều kiện điều chuyển; việc xác nhận cuối
thuộc về đơn vị quản lý/kỹ thuật/kế toán qua workflow_service.

Khi dữ liệu nguồn thiếu (ví dụ chưa có công suất còn dư, chưa có chi phí sửa
chữa...), hàm chấm một mức trung bình bảo toàn kèm ghi rõ trong rationale là
"chưa đủ dữ liệu, cần xác minh" — không suy diễn số liệu không có.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.rbac import PermissionDenied, UserContext
from app.core.timeutils import utcnow
from app.models.asset import Asset, AssetCondition, AssetValuation
from app.models.audit import SystemSetting
from app.models.matching import AssetMatchingResult
from app.models.request import AssetRequest

DEFAULT_WEIGHTS = {
    "function": 25, "technical_spec": 20, "capacity": 15, "condition": 15,
    "time_readiness": 10, "cost": 10, "location": 5,
}
DEFAULT_THRESHOLDS = {"high_fit": 85, "needs_review": 70}

# Tình trạng tài sản coi là "có thể xem xét điều chuyển ngay"; các trạng thái
# đã thanh lý/không còn phù hợp bị loại khỏi tập ứng viên.
EXCLUDED_ASSET_STATUSES = {"Đề xuất thanh lý", "Không còn phù hợp với nhu cầu khai thác"}


@dataclass
class ScoreBreakdown:
    function: float = 0.0
    technical_spec: float = 0.0
    capacity: float = 0.0
    condition: float = 0.0
    time_readiness: float = 0.0
    cost: float = 0.0
    location: float = 0.0
    notes: list[str] = field(default_factory=list)

    def total(self) -> float:
        return round(
            self.function + self.technical_spec + self.capacity + self.condition
            + self.time_readiness + self.cost + self.location, 2
        )


def get_scoring_weights(db: Session, asset_class: str | None) -> dict:
    row = db.get(SystemSetting, "asset_matching.scoring_weights")
    if not row:
        return dict(DEFAULT_WEIGHTS)
    table = json.loads(row.value)
    return table.get(asset_class, table.get("DEFAULT", DEFAULT_WEIGHTS))


def get_thresholds(db: Session) -> dict:
    row = db.get(SystemSetting, "asset_matching.thresholds")
    if not row:
        return dict(DEFAULT_THRESHOLDS)
    return json.loads(row.value)


def classify_band(score: float, thresholds: dict) -> str:
    if score >= thresholds.get("high_fit", DEFAULT_THRESHOLDS["high_fit"]):
        return "HIGH"
    if score >= thresholds.get("needs_review", DEFAULT_THRESHOLDS["needs_review"]):
        return "NEEDS_REVIEW"
    return "LOW_PRIORITY"


def find_candidate_assets(db: Session, request: AssetRequest) -> list[Asset]:
    query = db.query(Asset).filter(~Asset.asset_status.in_(EXCLUDED_ASSET_STATUSES))
    if request.asset_group:
        query = query.filter(
            or_(
                Asset.asset_subclass == request.asset_group,
                Asset.asset_type == request.asset_group,
                Asset.asset_class == request.asset_group,
            )
        )
    return query.all()


def _score_function(asset: Asset, request: AssetRequest, notes: list[str]) -> float:
    if not request.asset_group:
        notes.append("Chưa xác định nhóm tài sản cần — không chấm được công năng, tạm tính 0.")
        return 0.0
    if asset.asset_subclass == request.asset_group or asset.asset_type == request.asset_group:
        return 1.0  # hệ số đầy đủ, nhân với trọng số bên ngoài
    if asset.asset_class == request.asset_group:
        return 0.5
    return 0.0


def _score_technical_spec(asset: Asset, notes: list[str]) -> float:
    if asset.technical_specification:
        return 1.0
    notes.append("Chưa có thông số kỹ thuật ghi nhận cho tài sản — cần bộ phận kỹ thuật xác minh.")
    return 0.5


def _score_capacity(asset: Asset, request: AssetRequest, notes: list[str]) -> float:
    if request.requested_capacity is None:
        notes.append("Yêu cầu chưa nêu công suất cần — chấm công suất ở mức trung bình, cần làm rõ thêm.")
        return 0.5
    design = float(asset.capacity_design) if asset.capacity_design is not None else None
    utilized = float(asset.capacity_utilized) if asset.capacity_utilized is not None else 0.0
    if design is None:
        notes.append("Tài sản chưa có dữ liệu công suất thiết kế — chưa đủ cơ sở đánh giá công suất.")
        return 0.5
    available = max(design - utilized, 0.0)
    needed = float(request.requested_capacity)
    if needed <= 0:
        return 0.5
    if available >= needed:
        return 1.0
    if available >= 0.6 * needed:
        notes.append(f"Công suất còn dư ({available:g}) thấp hơn nhu cầu ({needed:g}) nhưng gần đáp ứng.")
        return 0.6
    notes.append(f"Công suất còn dư ({available:g}) không đủ so với nhu cầu ({needed:g}).")
    return 0.2


def _score_condition(asset: Asset, condition: AssetCondition | None, notes: list[str]) -> float:
    if condition is None:
        if asset.asset_status in ("Đang khai thác đủ công suất", "Đang khai thác nhưng còn công suất dư"):
            return 0.8
        notes.append("Chưa có biên bản đánh giá tình trạng kỹ thuật — cần bộ phận kỹ thuật kiểm tra.")
        return 0.5
    if condition.can_be_transferred is True:
        return 1.0
    if condition.maintenance_required:
        notes.append(
            f"Tài sản cần sửa chữa trước khi điều chuyển (ước tính {condition.estimated_repair_cost or 'chưa rõ'} "
            f"đồng, {condition.estimated_downtime_days or '?'} ngày)."
        )
        return 0.3
    return 0.6


def _score_time_readiness(asset: Asset, request: AssetRequest, notes: list[str]) -> float:
    if asset.asset_status == "Đang nhàn rỗi":
        return 1.0
    if asset.asset_status == "Đang khai thác nhưng còn công suất dư":
        return 0.8
    if asset.asset_status == "Đang sửa chữa/bảo trì":
        notes.append("Tài sản đang sửa chữa — thời gian sẵn sàng phụ thuộc tiến độ sửa chữa.")
        return 0.3
    if request.needed_by_date and asset.next_verification_due and asset.next_verification_due > request.needed_by_date:
        return 0.5
    return 0.5


def _score_cost(asset: Asset, condition: AssetCondition | None, valuation: AssetValuation | None,
                 notes: list[str]) -> float:
    repair_cost = float(condition.estimated_repair_cost) if condition and condition.estimated_repair_cost else 0.0
    replacement_cost = float(valuation.replacement_cost) if valuation and valuation.replacement_cost else None
    if repair_cost <= 0:
        return 1.0
    if replacement_cost and replacement_cost > 0:
        ratio = repair_cost / replacement_cost
        if ratio <= 0.1:
            return 0.9
        if ratio <= 0.3:
            return 0.6
        notes.append("Chi phí sửa chữa/điều chuyển ước tính khá cao so với chi phí thay thế.")
        return 0.3
    notes.append("Chưa có chi phí thay thế tham chiếu để so sánh chi phí sửa chữa — cần Kế toán/Kỹ thuật bổ sung.")
    return 0.5


def _score_location(asset: Asset, request: AssetRequest, notes: list[str]) -> float:
    if not request.requested_location_province:
        notes.append("Yêu cầu chưa nêu địa điểm sử dụng — chấm vị trí ở mức trung bình.")
        return 0.5
    if asset.province_city and asset.province_city == request.requested_location_province:
        return 1.0
    if asset.country == "Việt Nam":
        return 0.5
    return 0.3


def score_asset_against_request(
    db: Session, asset: Asset, request: AssetRequest, weights: dict,
) -> ScoreBreakdown:
    condition = (
        db.query(AssetCondition)
        .filter(AssetCondition.asset_id == asset.asset_id)
        .order_by(AssetCondition.inspection_date.desc())
        .first()
    )
    valuation = (
        db.query(AssetValuation)
        .filter(AssetValuation.asset_id == asset.asset_id)
        .order_by(AssetValuation.valuation_date.desc())
        .first()
    )

    notes: list[str] = []
    breakdown = ScoreBreakdown(notes=notes)
    breakdown.function = round(_score_function(asset, request, notes) * weights["function"], 2)
    breakdown.technical_spec = round(_score_technical_spec(asset, notes) * weights["technical_spec"], 2)
    breakdown.capacity = round(_score_capacity(asset, request, notes) * weights["capacity"], 2)
    breakdown.condition = round(_score_condition(asset, condition, notes) * weights["condition"], 2)
    breakdown.time_readiness = round(_score_time_readiness(asset, request, notes) * weights["time_readiness"], 2)
    breakdown.cost = round(_score_cost(asset, condition, valuation, notes) * weights["cost"], 2)
    breakdown.location = round(_score_location(asset, request, notes) * weights["location"], 2)
    return breakdown


def run_matching(db: Session, request_id: str) -> list[AssetMatchingResult]:
    """Chạy đối chiếu cho một yêu cầu; xóa kết quả cũ (nếu có) và ghi kết quả mới.
    Luôn trả về confirmed_status=PENDING_CONFIRMATION — không tự kết luận."""
    request = db.get(AssetRequest, request_id)
    if request is None:
        raise ValueError(f"Không tìm thấy yêu cầu {request_id}")

    db.query(AssetMatchingResult).filter(AssetMatchingResult.request_id == request_id).delete()

    candidates = find_candidate_assets(db, request)
    thresholds = get_thresholds(db)
    results: list[AssetMatchingResult] = []
    now = utcnow()

    for asset in candidates:
        weights = get_scoring_weights(db, asset.asset_class)
        breakdown = score_asset_against_request(db, asset, request, weights)
        total = breakdown.total()
        band = classify_band(total, thresholds)
        result = AssetMatchingResult(
            request_id=request_id, asset_id=asset.asset_id,
            score_function=breakdown.function, score_technical_spec=breakdown.technical_spec,
            score_capacity=breakdown.capacity, score_condition=breakdown.condition,
            score_time_readiness=breakdown.time_readiness, score_cost=breakdown.cost,
            score_location=breakdown.location, score_total=total,
            suitability_band=band,
            rationale="; ".join(breakdown.notes) if breakdown.notes else "Đủ dữ liệu để chấm điểm.",
            evaluated_at=now, evaluated_by="system_matching_engine",
            confirmed_status="PENDING_CONFIRMATION",
        )
        db.add(result)
        results.append(result)

    db.flush()
    results.sort(key=lambda r: r.score_total, reverse=True)
    return results


# Vai trò được phép xác nhận/từ chối một kết quả đối chiếu — đơn vị đang quản
# lý tài sản (Asset Custodian) là bên có quyền từ chối bàn giao (kịch bản
# "đơn vị sở hữu tài sản từ chối điều chuyển"); kỹ thuật/QLTS&ĐT cũng xác nhận được.
CONFIRMATION_ROLES = {"ASSET_CUSTODIAN", "TECHNICAL_REVIEWER", "ASSET_MGMT_ADMIN"}


def confirm_matching_result(
    db: Session, result_id: int, ctx: UserContext, accepted: bool, comments: str | None = None,
) -> AssetMatchingResult:
    """Đơn vị quản lý/kỹ thuật/QLTS&ĐT xác nhận hoặc TỪ CHỐI một kết quả đối
    chiếu. Từ chối (ví dụ đơn vị sở hữu không đồng ý bàn giao) bắt buộc phải
    nêu lý do — không được tự động suy ra lý do."""
    result = db.get(AssetMatchingResult, result_id)
    if result is None:
        raise ValueError(f"Không tìm thấy kết quả đối chiếu #{result_id}")

    if not any(ctx.has_role(r) for r in CONFIRMATION_ROLES):
        raise PermissionDenied(
            f"Người dùng '{ctx.user_id}' không có thẩm quyền xác nhận/từ chối kết quả đối chiếu "
            f"(yêu cầu vai trò: {sorted(CONFIRMATION_ROLES)})."
        )
    if not accepted and not (comments and comments.strip()):
        raise ValueError(
            "Từ chối điều chuyển (ví dụ đơn vị đang sở hữu/quản lý tài sản không đồng ý bàn giao) "
            "phải nêu rõ lý do."
        )

    result.confirmed_status = "CONFIRMED_SUITABLE" if accepted else "REJECTED_BY_REVIEWER"
    result.confirmed_by = ctx.user_id
    result.confirmed_at = utcnow()
    if comments:
        result.rationale = f"{result.rationale} | Xác nhận: {comments}" if result.rationale else comments

    db.flush()
    return result
