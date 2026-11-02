"""FastAPI — expose một số nghiệp vụ lõi qua HTTP cho tích hợp Giai đoạn 2+
(Teams/React...). Giai đoạn 1, Streamlit frontend gọi thẳng service layer,
KHÔNG qua HTTP — service này chỉ cần chạy ổn định (health check) và sẵn sàng
mở rộng, không phải đường dẫn chính của MVP.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.request import AssetRequest
from app.services.reporting_service import get_dashboard_summary

app = FastAPI(title="SeaCorp Asset AI API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/dashboard/summary")
def dashboard_summary(company_code: str | None = None, db: Session = Depends(get_db)) -> dict:
    return get_dashboard_summary(db, company_code=company_code)


@app.get("/api/requests/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db)) -> dict:
    request = db.get(AssetRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy yêu cầu {request_id}")
    return {
        "request_id": request.request_id,
        "sender_name": request.sender_name,
        "company_code": request.company_code,
        "status": request.status,
        "asset_group": request.asset_group,
        "created_at": request.created_at.isoformat(),
    }
