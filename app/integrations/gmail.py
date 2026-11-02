"""Stub Giai đoạn 2 — tích hợp Gmail API. Chưa triển khai thật vì chưa có
GMAIL_CREDENTIALS_JSON trong môi trường hiện tại."""
from __future__ import annotations

from app.core.config import get_settings
from app.integrations.base import IntakeProvider, IntegrationNotConfigured, OutboundChannel


class GmailIntakeProvider(IntakeProvider):
    def fetch_new_messages(self) -> list[dict]:
        settings = get_settings()
        if not settings.gmail_credentials_json:
            raise IntegrationNotConfigured(
                "Chưa cấu hình GMAIL_CREDENTIALS_JSON — tích hợp Gmail thuộc Giai đoạn 2."
            )
        raise NotImplementedError("Kết nối Gmail API thật sẽ triển khai ở Giai đoạn 2.")


class GmailOutboundChannel(OutboundChannel):
    def send(self, to: str, subject: str, body: str) -> None:
        raise IntegrationNotConfigured("Gửi email qua Gmail chưa được cấu hình trong Giai đoạn 1 MVP.")
