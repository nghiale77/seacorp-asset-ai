"""Interface pluggable cho kênh tiếp nhận (intake) và kênh gửi (outbound).
Giai đoạn 1 chỉ có ManualIntakeProvider + LoggingOutboundChannel hoạt động
thật; outlook/gmail/teams là stub cho Giai đoạn 2 khi có thông tin xác thực."""
from __future__ import annotations

from abc import ABC, abstractmethod


class IntegrationNotConfigured(Exception):
    """Kênh tích hợp chưa có thông tin xác thực/chưa triển khai ở Giai đoạn 1."""


class OutboundChannel(ABC):
    """Kênh gửi thông báo ra ngoài (email/Teams). send() phải raise khi thất bại,
    không được âm thầm coi là thành công."""

    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None:
        raise NotImplementedError


class IntakeProvider(ABC):
    """Kênh tiếp nhận yêu cầu tài sản (email/Teams/form nội bộ)."""

    @abstractmethod
    def fetch_new_messages(self) -> list[dict]:
        """Trả về danh sách message thô: {sender_name, sender_email, content,
        received_at, attachments: [...]}. Giai đoạn 1 dùng ManualIntakeProvider
        (submit trực tiếp qua form), không cần fetch định kỳ."""
        raise NotImplementedError
