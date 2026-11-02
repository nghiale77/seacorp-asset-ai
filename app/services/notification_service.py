"""Bước 5 — phản hồi email/tin nhắn bằng 5 mẫu có sẵn trong tài liệu.

Nguyên tắc bắt buộc: AI chỉ SOẠN nội dung; thông báo hành chính (M1/M2/M5) cần
chuyên viên QLTS&ĐT duyệt, còn thông báo liên quan kết luận điều chuyển/đầu tư
(M3/M4) phải qua người có thẩm quyền (APPROVER) duyệt nội dung trước khi gửi.
Không có đường tắt nào gửi thẳng mà bỏ qua bước duyệt.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.rbac import PermissionDenied, UserContext
from app.core.timeutils import utcnow
from app.integrations.base import OutboundChannel
from app.integrations.logging_channel import LoggingOutboundChannel
from app.models.notification import EmailMessage
from app.models.request import AssetRequest

TEMPLATES: dict[str, dict] = {
    "M1": {
        "subject": "SeaCorp đã tiếp nhận yêu cầu tài sản — Mã hồ sơ {request_id}",
        "body": (
            "SeaCorp đã tiếp nhận yêu cầu đề xuất tài sản của Quý Đơn vị. Hồ sơ đã được ghi nhận "
            "với mã số {request_id}. Phòng Quản lý Tài sản & Đầu tư sẽ tiến hành kiểm tra nhu cầu "
            "và đối chiếu dữ liệu tài sản hiện có trên toàn hệ thống trước khi xác định phương án xử lý."
        ),
        "required_context": [],
    },
    "M2": {
        "subject": "Đề nghị bổ sung thông tin — Mã hồ sơ {request_id}",
        "body": (
            "Để có cơ sở đánh giá nhu cầu và phương án sử dụng tài sản, đề nghị Quý Đơn vị bổ sung "
            "các thông tin còn thiếu: {missing_fields}. Hồ sơ {request_id} sẽ được tiếp tục xử lý "
            "sau khi nhận đủ thông tin."
        ),
        "required_context": ["missing_fields"],
    },
    "M3": {
        "subject": "Có tài sản phù hợp — Mã hồ sơ {request_id}",
        "body": (
            "Qua kiểm tra dữ liệu tài sản toàn hệ thống, hiện có tài sản {asset_name} ({asset_id}) "
            "tại đơn vị {asset_unit} có khả năng đáp ứng nhu cầu đề xuất của hồ sơ {request_id}. "
            "Hồ sơ đang được chuyển đến các bộ phận liên quan để xác minh tình trạng kỹ thuật, "
            "khả năng bàn giao và phương án điều chuyển."
        ),
        "required_context": ["asset_name", "asset_id", "asset_unit"],
    },
    "M4": {
        "subject": "Chưa có tài sản phù hợp — Mã hồ sơ {request_id}",
        "body": (
            "Qua rà soát dữ liệu tài sản hiện có, chưa tìm thấy tài sản đáp ứng đầy đủ nhu cầu của "
            "Quý Đơn vị (hồ sơ {request_id}). Hồ sơ sẽ được chuyển sang bước thẩm định phương án "
            "đầu tư, trong đó xem xét phương án mua mới, thuê tài sản và các giải pháp thay thế."
        ),
        "required_context": [],
    },
    "M5": {
        "subject": "Hồ sơ đang chờ xác nhận — Mã hồ sơ {request_id}",
        "body": (
            "Hồ sơ {request_id} hiện đang chờ xác nhận từ đơn vị quản lý tài sản/bộ phận chuyên môn. "
            "Hệ thống sẽ cập nhật trạng thái và thông báo khi có kết quả xử lý tiếp theo."
        ),
        "required_context": [],
    },
}

# M1/M2/M5 là thông báo hành chính; M3/M4 liên quan kết luận điều chuyển/đầu tư
# nên bắt buộc người có thẩm quyền (APPROVER) duyệt, theo đúng tài liệu.
TEMPLATE_APPROVAL_ROLES: dict[str, set[str]] = {
    "M1": {"ASSET_MGMT_ADMIN"},
    "M2": {"ASSET_MGMT_ADMIN"},
    "M3": {"APPROVER"},
    "M4": {"APPROVER"},
    "M5": {"ASSET_MGMT_ADMIN"},
}


def draft_notification(
    db: Session, request_id: str, template_code: str, created_by: str,
    recipient: str | None = None, **context,
) -> EmailMessage:
    if template_code not in TEMPLATES:
        raise ValueError(f"Mẫu thông báo không hợp lệ: {template_code}. Chỉ chấp nhận {list(TEMPLATES)}.")

    request = db.get(AssetRequest, request_id)
    if request is None:
        raise ValueError(f"Không tìm thấy yêu cầu {request_id}")

    template = TEMPLATES[template_code]
    missing = [k for k in template["required_context"] if k not in context]
    if missing:
        raise ValueError(f"Mẫu {template_code} thiếu context bắt buộc: {missing}")

    fmt_context = {"request_id": request_id, **context}
    subject = template["subject"].format(**fmt_context)
    body = template["body"].format(**fmt_context)

    message = EmailMessage(
        request_id=request_id, template_code=template_code,
        recipient=recipient or request.sender_email, subject=subject, body=body,
        status="PENDING_APPROVAL", created_by=created_by, created_at=utcnow(),
    )
    db.add(message)
    db.flush()
    return message


def approve_notification(
    db: Session, email_id: int, ctx: UserContext, approve: bool, comments: str | None = None,
) -> EmailMessage:
    message = db.get(EmailMessage, email_id)
    if message is None:
        raise ValueError(f"Không tìm thấy thông báo #{email_id}")
    if message.status != "PENDING_APPROVAL":
        raise ValueError(f"Thông báo #{email_id} đang ở trạng thái '{message.status}', không ở trạng thái chờ duyệt.")

    required_roles = TEMPLATE_APPROVAL_ROLES.get(message.template_code, {"ASSET_MGMT_ADMIN"})
    if not any(ctx.has_role(r) for r in required_roles):
        raise PermissionDenied(
            f"Người dùng '{ctx.user_id}' không có thẩm quyền duyệt thông báo mẫu {message.template_code} "
            f"(yêu cầu vai trò: {sorted(required_roles)})."
        )

    now = utcnow()
    message.approved_by = ctx.user_id
    message.approved_at = now
    if approve:
        message.status = "APPROVED"
    else:
        message.status = "REJECTED"
        message.error_message = comments
    db.flush()
    return message


def send_notification(
    db: Session, email_id: int, channel: OutboundChannel | None = None,
) -> EmailMessage:
    channel = channel or LoggingOutboundChannel()
    message = db.get(EmailMessage, email_id)
    if message is None:
        raise ValueError(f"Không tìm thấy thông báo #{email_id}")

    if message.status == "SENT":
        raise ValueError(f"Thông báo #{email_id} đã được gửi trước đó — tránh gửi trùng.")
    if message.status not in ("APPROVED", "FAILED"):
        # FAILED vẫn được phép gửi lại (đã qua duyệt, chỉ là lần trước lỗi kết nối).
        raise ValueError(f"Thông báo #{email_id} chưa được duyệt (trạng thái hiện tại: '{message.status}').")

    try:
        channel.send(to=message.recipient, subject=message.subject, body=message.body)
    except Exception as exc:
        message.status = "FAILED"
        message.error_message = str(exc)
        db.flush()
        return message

    message.status = "SENT"
    message.sent_at = utcnow()
    message.error_message = None
    db.flush()
    return message
