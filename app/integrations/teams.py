"""Stub Giai đoạn 2 — tích hợp Microsoft Teams (webhook/bot). Chưa triển khai
thật vì chưa có TEAMS_WEBHOOK_URL trong môi trường hiện tại."""
from __future__ import annotations

from app.core.config import get_settings
from app.integrations.base import IntakeProvider, IntegrationNotConfigured, OutboundChannel


class TeamsIntakeProvider(IntakeProvider):
    def fetch_new_messages(self) -> list[dict]:
        raise IntegrationNotConfigured("Tích hợp tiếp nhận qua Teams thuộc Giai đoạn 2.")


class TeamsOutboundChannel(OutboundChannel):
    def send(self, to: str, subject: str, body: str) -> None:
        settings = get_settings()
        if not settings.teams_webhook_url:
            raise IntegrationNotConfigured(
                "Chưa cấu hình TEAMS_WEBHOOK_URL — gửi thông báo qua Teams thuộc Giai đoạn 2."
            )
        raise NotImplementedError("Gửi webhook Teams thật sẽ triển khai ở Giai đoạn 2.")
