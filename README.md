# SEACORP AI Asset Request & Allocation Management System — Giai đoạn 1 (MVP)

Hệ thống quản lý quy trình nghiệp vụ (không phải chatbot) giúp Phòng Quản lý
Tài sản & Đầu tư SeaCorp tiếp nhận yêu cầu tài sản từ các đơn vị, dùng AI
phân tích nhu cầu, đối chiếu với dữ liệu tài sản toàn hệ thống, và điều phối
sang quy trình điều chuyển nội bộ hoặc đề xuất mua sắm mới.

Xây dựng theo prompt `SC_PROMPT_CLAUDE_QUAN_LY_TAI_SAN.docx` và kế thừa trực
tiếp field list đã thiết kế trong `E:\_SC_ASSETS\SEACORP_Cau_truc_Du_lieu_Tai_san_Tap_trung.xlsx`
+ quy trình `SEACORP_Quy_trinh_Quan_ly_Tai_san_va_Bieu_mau_so_hoa_Du_thao.docx`.
Xem kế hoạch triển khai gốc tại `C:\Users\Admin\.claude\plans\whimsical-doodling-harbor.md`.

## Kiến trúc

- **Backend/services:** Python 3.12+, SQLAlchemy 2.0 ORM, Alembic migrations.
- **Database:** PostgreSQL (production, schema `seacorp_asset`, qua Docker Compose) hoặc
  SQLite (dev/test cục bộ — mặc định, không cần cài gì thêm).
- **Frontend:** Streamlit — 6 trang theo đúng 5 bước nghiệp vụ + dashboard.
- **AI:** Claude API (Anthropic SDK), tùy chọn qua `ANTHROPIC_API_KEY`; fallback thủ công nếu chưa cấu hình.
- **Email/Teams:** interface pluggable (`app/integrations/`) — Giai đoạn 1 dùng
  `manual_intake` (nhập nội dung qua form) + `LoggingOutboundChannel` ("gửi" =
  ghi nhận SENT, hiển thị trên UI); Outlook/Gmail/Teams là stub cho Giai đoạn 2.

```
app/
  core/        config, security (bcrypt), RBAC, timeutils
  database/    SQLAlchemy engine/session (Base dùng chung)
  models/      26 bảng ORM (org, asset x10 phân hệ, request, matching, proposal, workflow, notification, audit, auth)
  services/    numbering, duplicate_detection, ai_analysis_service, asset_matching_service,
               workflow_service, notification_service, reporting_service
  integrations/ manual_intake (hoạt động), outlook/gmail/teams (stub Giai đoạn 2), logging_channel
frontend/      Streamlit app.py (đăng nhập) + pages/ 1..6
migrations/    Alembic — chạy được trên cả SQLite và Postgres
scripts/       seed_demo_data.py
tests/         41 test (pytest), bao gồm 10 kịch bản tối thiểu theo tài liệu
```

### Mô hình dữ liệu

`assets` + 9 bảng phân hệ (`asset_locations/valuations/conditions/responsibility/
components/intangible_rights/bio_records/movements`, `lookups`) ánh xạ trực
tiếp field list đã có trong file Excel cấu trúc dữ liệu tài sản tập trung —
không thiết kế lại từ đầu. Nhóm bảng nghiệp vụ mới: `asset_requests`,
`request_documents`, `asset_matching_results`, `transfer_proposals`,
`procurement_proposals`, `workflow_tasks`, `approval_history`,
`email_messages`, `notifications`, `audit_logs`, `system_settings`
(trọng số chấm điểm + ngưỡng, cấu hình được), `user_accounts`/`user_role_assignments` (RBAC).

### Luồng nghiệp vụ (5 bước, đúng tài liệu)

1. **Tiếp nhận** (`app/integrations/manual_intake.py`) — sinh mã `ASR-YYYYMM-XXXXX`,
   chống trùng (`duplicate_detection.py`, chỉ GẮN CỜ, không tự gộp).
2. **AI phân tích** (`ai_analysis_service.py`) — trích xuất 4 nhóm thông tin,
   phân loại Đầy đủ/Thiếu thông tin/Không rõ mục đích/Trùng yêu cầu; không
   suy diễn khi thiếu dữ liệu (trả "Chưa đủ cơ sở đánh giá"); fallback thủ
   công nếu chưa cấu hình `ANTHROPIC_API_KEY`.
3. **Đối chiếu tài sản** (`asset_matching_service.py`) — chấm điểm 100 theo 7
   tiêu chí (trọng số/ngưỡng cấu hình qua `system_settings`); kết quả luôn
   "chờ xác nhận" (`confirm_matching_result`), không tự kết luận đủ điều kiện
   điều chuyển.
4. **Đề xuất & Phê duyệt** (`workflow_service.py`, `proposal.py` models) — state
   machine `NEW → ... → CLOSED` (mục VIII tài liệu), RBAC theo 9 vai trò,
   không tự động đóng hồ sơ khi chưa có xác nhận.
5. **Thông báo** (`notification_service.py`) — 5 mẫu, luôn ở trạng thái
   `PENDING_APPROVAL`, M3/M4 (kết luận điều chuyển/đầu tư) bắt buộc vai trò
   `APPROVER` duyệt; "gửi" trùng hoặc lỗi kết nối được xử lý rõ ràng (không
   âm thầm coi là thành công).

### RBAC — 9 vai trò

`SYSTEM_ADMIN, ASSET_MGMT_ADMIN, REQUESTING_UNIT, ASSET_CUSTODIAN,
TECHNICAL_REVIEWER, ACCOUNTANT, PROCUREMENT, APPROVER, MANAGEMENT_VIEWER`
(`app/models/auth.py`, `app/core/rbac.py`). Vai trò không có phạm vi global
(`GLOBAL_SCOPE_ROLES`) chỉ xem được dữ liệu của `company_code` được gán.

## Chạy thử (dev, SQLite — không cần Docker/Postgres)

```bash
cd 06_SOURCE_CODE
python -m venv .venv
.venv/Scripts/activate        # Windows; `source .venv/bin/activate` trên Linux/macOS
pip install -r requirements.txt
copy .env.example .env        # để trống DATABASE_URL -> dùng SQLite tại gốc project
python -m alembic upgrade head
python scripts/seed_demo_data.py
streamlit run frontend/app.py
```

Tài khoản demo (mật khẩu `Demo@123`, chỉ dùng cục bộ — đổi ngay khi triển khai thật):
`qlts01` (ASSET_MGMT_ADMIN), `req_danny01`/`req_farm01` (REQUESTING_UNIT),
`cust_seagull01` (ASSET_CUSTODIAN), `tech01` (TECHNICAL_REVIEWER),
`acct01` (ACCOUNTANT), `proc01` (PROCUREMENT), `approver01` (APPROVER),
`mgmt01` (MANAGEMENT_VIEWER), `admin01` (SYSTEM_ADMIN).

Dữ liệu demo: 4 công ty (SeaCorp, Seagull Marine, Seafarm, DannyGreen
Logistics) + các farm/đội tàu, 12 tài sản mẫu (tàu, xe tải/xe nâng — có cả
tài sản nhàn rỗi, tài sản đủ công suất, tài sản cần sửa chữa — cây lâu năm,
vật nuôi, công trình, bằng sáng chế), 3 yêu cầu demo.

## Chạy thật (Postgres, Docker)

```bash
cd 06_SOURCE_CODE
cp .env.example .env
# Sửa .env: DATABASE_URL=postgresql+psycopg://seacorp_asset_app:<password>@db:5432/seacorp_asset
#           SECRET_KEY=<giá trị ngẫu nhiên thật>, ANTHROPIC_API_KEY=<nếu có>
docker compose up -d --build
docker compose exec api python -m alembic upgrade head
docker compose exec api python scripts/seed_demo_data.py   # tùy chọn — chỉ cho môi trường demo/UAT
```

API: `http://localhost:8000` · Frontend: `http://localhost:8501`.

**Trước khi triển khai lên máy chủ SeaCorp thật:** đổi `SECRET_KEY`, đặt
`POSTGRES_PASSWORD`/`SECRET_KEY` qua biến môi trường của hệ thống (không
commit vào `.env`), và xem mục "Những điểm cần SeaCorp chốt" trong tài liệu
quy trình (ma trận phân quyền chính thức, thông tin xác thực Outlook/Gmail/
Teams, khóa Claude API chính thức) trước khi bật Giai đoạn 2.

## Kiểm thử

```bash
python -m pytest tests/ -v
```

41 test, bao gồm đủ 10 kịch bản tối thiểu theo tài liệu:

| # | Kịch bản | Test |
|---|---|---|
| 1 | Đầy đủ thông tin + có tài sản nhàn rỗi phù hợp | `test_matching_engine.py::test_scenario1_full_match_idle_asset_scores_high` |
| 2 | Có tài sản nhưng công suất không đủ | `test_matching_engine.py::test_scenario2_insufficient_capacity_scores_lower` |
| 3 | Có tài sản nhưng cần sửa chữa | `test_matching_engine.py::test_scenario3_needs_repair_scores_lower_on_condition_and_cost` |
| 4 | Không có tài sản phù hợp → chuyển mua mới | `test_matching_engine.py::test_scenario4_no_matching_asset_returns_empty_and_no_rows_persisted` |
| 5 | Yêu cầu thiếu thông tin | `test_ai_analysis_service.py::test_scenario5_missing_info_falls_back_without_api_key` |
| 6 | Yêu cầu trùng lặp | `test_ai_analysis_service.py::test_scenario6_duplicate_short_circuits_ai_call`, `test_manual_intake.py::test_scenario6_*`, `test_duplicate_detection.py` |
| 7 | Đơn vị sở hữu tài sản từ chối điều chuyển | `test_matching_engine.py::test_scenario7_owner_refuses_transfer_requires_reason` |
| 8 | Hồ sơ vượt thời hạn xử lý | `test_workflow_states.py::test_scenario8_overdue_task_is_flagged_not_autoclosed` |
| 9 | Người không có thẩm quyền cố phê duyệt | `test_workflow_states.py::test_scenario9_unauthorized_user_cannot_approve` |
| 10 | Email gửi trùng hoặc lỗi kết nối | `test_notification_service.py::test_scenario10_*` |

Kết quả lần chạy gần nhất: **41 passed**. Frontend đã được kiểm thử trực tiếp
qua trình duyệt (đăng nhập → tiếp nhận → AI phân tích (fallback) → đối chiếu
tài sản → lập đề xuất điều chuyển → chuyển trạng thái → soạn/duyệt/gửi thông
báo → dashboard) trên dữ liệu demo thật, không chỉ unit test.

## Giới hạn đã biết của Giai đoạn 1 (có chủ đích, xem kế hoạch gốc)

- Chưa nối Outlook/Gmail/Teams thật (`app/integrations/outlook.py` v.v. là
  stub, raise `IntegrationNotConfigured` rõ ràng) — Giai đoạn 2 khi có thông
  tin xác thực.
- AI phân tích dùng Claude API thật nếu có `ANTHROPIC_API_KEY`; nếu không,
  toàn bộ phân loại do chuyên viên QLTS&ĐT quyết định qua UI (không suy diễn).
- Không tích hợp kế toán/ERP thật (Giai đoạn 3).
- Dữ liệu demo là minh họa — cần thay bằng dữ liệu tài sản thật đã kiểm kê/xác minh trước khi vận hành chính thức.
