"""Kênh gửi mặc định cho Giai đoạn 1 MVP: không có Outlook/Gmail/Teams thật
để giao hàng, nên 'gửi' nghĩa là ghi nhận đã gửi (status=SENT) để hiển thị
trên UI — không giả vờ đã gửi ra ngoài hệ thống."""
from __future__ import annotations

from app.integrations.base import OutboundChannel


class LoggingOutboundChannel(OutboundChannel):
    def send(self, to: str, subject: str, body: str) -> None:
        if not to:
            raise ValueError("Thiếu địa chỉ người nhận — không thể ghi nhận gửi.")
        # Giai đoạn 1: không gọi API bên ngoài; notification_service chịu
        # trách nhiệm cập nhật status=SENT/sent_at sau khi gọi send() thành công.
        return None


class FailingOutboundChannel(OutboundChannel):
    """Dùng để mô phỏng lỗi kết nối trong kiểm thử (kịch bản 10)."""

    def __init__(self, error_message: str = "Mô phỏng lỗi kết nối khi gửi."):
        self.error_message = error_message

    def send(self, to: str, subject: str, body: str) -> None:
        raise ConnectionError(self.error_message)
