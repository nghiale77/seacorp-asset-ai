"""Stub Giai đoạn 2 — tích hợp Microsoft Outlook/365 qua Microsoft Graph API.
Chưa triển khai thật vì môi trường hiện tại chưa có MS_GRAPH_CLIENT_ID/
MS_GRAPH_CLIENT_SECRET/MS_GRAPH_TENANT_ID. Khi SeaCorp cấp quyền, hiện thực
hai phương thức theo đúng interface IntakeProvider/OutboundChannel."""
from __future__ import annotations

from app.core.config import get_settings
from app.integrations.base import IntakeProvider, IntegrationNotConfigured, OutboundChannel


class OutlookIntakeProvider(IntakeProvider):
    def fetch_new_messages(self) -> list[dict]:
        settings = get_settings()
        if not (settings.ms_graph_client_id and settings.ms_graph_client_secret and settings.ms_graph_tenant_id):
            raise IntegrationNotConfigured(
                "Chưa cấu hình MS_GRAPH_CLIENT_ID/MS_GRAPH_CLIENT_SECRET/MS_GRAPH_TENANT_ID — "
                "tích hợp Outlook/Microsoft 365 thuộc Giai đoạn 2."
            )
        raise NotImplementedError("Kết nối Microsoft Graph API thật sẽ triển khai ở Giai đoạn 2.")


class OutlookOutboundChannel(OutboundChannel):
    def send(self, to: str, subject: str, body: str) -> None:
        raise IntegrationNotConfigured(
            "Gửi email qua Outlook/Microsoft Graph chưa được cấu hình trong Giai đoạn 1 MVP."
        )
