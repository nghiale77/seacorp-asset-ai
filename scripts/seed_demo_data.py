"""Nạp dữ liệu demo: danh mục lookups (từ SEACORP_Cau_truc_Du_lieu_Tai_san_Tap_trung.xlsx),
pháp nhân/đơn vị/nhân sự mẫu, tài sản mẫu cho 4 công ty, tài khoản RBAC demo,
trọng số chấm điểm và vài yêu cầu tài sản mẫu để khám phá UI.

Chạy: python scripts/seed_demo_data.py
An toàn để chạy lại nhiều lần (idempotent theo khóa chính).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định cp1252, không in được tiếng Việt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openpyxl  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.core.timeutils import utcnow  # noqa: E402,F811
from app.database.session import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.models.asset import (  # noqa: E402
    Asset, AssetBioRecord, AssetCondition, AssetLocation, AssetValuation, Lookup,
)
from app.models.auth import ROLES, UserAccount, UserRoleAssignment  # noqa: E402
from app.models.audit import SystemSetting  # noqa: E402
from app.models.org import Company, Department, Employee  # noqa: E402
from app.models.request import AssetRequest  # noqa: E402

SOURCE_XLSX = Path(r"E:\_SC_ASSETS\SEACORP_Cau_truc_Du_lieu_Tai_san_Tap_trung.xlsx")
DEMO_PASSWORD = "Demo@123"  # chỉ dùng cho tài khoản demo cục bộ — đổi ngay khi triển khai thật


def upsert(db, model, pk_field: str, pk_value, **fields):
    obj = db.get(model, pk_value)
    if obj is None:
        obj = model(**{pk_field: pk_value}, **fields)
        db.add(obj)
    else:
        for k, v in fields.items():
            setattr(obj, k, v)
    return obj


def seed_lookups(db) -> None:
    if not SOURCE_XLSX.exists():
        print(f"[seed] Không thấy {SOURCE_XLSX}, bỏ qua nạp lookups từ Excel.")
        return
    wb = openpyxl.load_workbook(SOURCE_XLSX, data_only=True)
    ws = wb["10_LOOKUPS"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    existing = {(l.lookup_group, l.lookup_code) for l in db.query(Lookup).all()}
    added = 0
    for row in rows:
        if not row or row[0] is None:
            continue
        group, code, name_vi, name_en, definition, active_flag = row
        if (group, code) in existing:
            continue
        db.add(Lookup(
            lookup_group=group, lookup_code=code, lookup_name_vi=name_vi,
            lookup_name_en=name_en, definition_or_usage=definition,
            active_flag=bool(active_flag),
        ))
        added += 1
    print(f"[seed] Lookups: +{added} dòng mới từ {SOURCE_XLSX.name}")


def seed_org(db) -> None:
    companies = [
        ("SEACORP", "Tập đoàn SeaCorp", "Holding/Tập đoàn", "Đa ngành"),
        ("SEAGULL_MARINE", "Seagull Marine", "Công ty thành viên", "Vận tải biển"),
        ("SEAFARM", "Seafarm", "Công ty thành viên", "Nông nghiệp"),
        ("DANNYGREEN", "DannyGreen Logistics", "Công ty thành viên", "Kho vận/Logistics"),
    ]
    for code, name, legal_type, industry in companies:
        upsert(db, Company, "company_code", code, company_name=name,
               legal_entity_type=legal_type, industry=industry, active_flag=True)

    departments = [
        ("QLTS_DT", "Phòng Quản lý Tài sản & Đầu tư", "SEACORP", "Quản lý tài sản"),
        ("KE_TOAN_SC", "Phòng Kế toán", "SEACORP", "Kế toán"),
        ("KY_THUAT_SC", "Bộ phận Kỹ thuật", "SEACORP", "Kỹ thuật"),
        ("MUA_SAM_SC", "Bộ phận Mua sắm", "SEACORP", "Mua sắm"),
        ("DOI_TAU_SEAGULL", "Đội tàu & Phương tiện", "SEAGULL_MARINE", "Vận hành"),
        ("FARM_DAKNONG", "Farm Đắk Nông", "SEAFARM", "Sản xuất nông nghiệp"),
        ("FARM_LAMDONG", "Farm Lâm Đồng", "SEAFARM", "Sản xuất nông nghiệp"),
        ("KHO_VAN_DANNYGREEN", "Kho vận Bình Dương", "DANNYGREEN", "Kho vận"),
    ]
    for code, name, company, dtype in departments:
        upsert(db, Department, "department_code", code, department_name=name,
               company_code=company, department_type=dtype, active_flag=True)

    employees = [
        ("admin01", "Nguyễn Văn Admin", "SEACORP", "QLTS_DT", "Quản trị hệ thống"),
        ("qlts01", "Trần Thị Quản Lý Tài Sản", "SEACORP", "QLTS_DT", "Trưởng phòng QLTS&ĐT"),
        ("req_danny01", "Lê Văn Kho Vận", "DANNYGREEN", "KHO_VAN_DANNYGREEN", "Trưởng kho"),
        ("req_farm01", "Phạm Thị Nông Trại", "SEAFARM", "FARM_DAKNONG", "Quản lý farm"),
        ("cust_seagull01", "Hoàng Văn Đội Tàu", "SEAGULL_MARINE", "DOI_TAU_SEAGULL", "Phụ trách đội xe/tàu"),
        ("tech01", "Đỗ Thị Kỹ Thuật", "SEACORP", "KY_THUAT_SC", "Chuyên viên kỹ thuật"),
        ("acct01", "Vũ Văn Kế Toán", "SEACORP", "KE_TOAN_SC", "Kế toán tài sản"),
        ("proc01", "Bùi Thị Mua Sắm", "SEACORP", "MUA_SAM_SC", "Chuyên viên mua sắm"),
        ("approver01", "Người được ủy quyền phê duyệt", "SEACORP", "QLTS_DT", "Phụ trách Khối ĐT&TC-KT"),
        ("mgmt01", "Ban Tổng Giám Đốc", "SEACORP", "QLTS_DT", "Lãnh đạo xem báo cáo"),
    ]
    for emp_id, name, company, dept, title in employees:
        upsert(db, Employee, "employee_id", emp_id, full_name=name, company_code=company,
               department_code=dept, title=title, email=f"{emp_id}@seacorp.local", active_flag=True)


ROLE_ASSIGNMENTS = [
    # (user_id, role_code, scope_company_code or None for global)
    ("admin01", "SYSTEM_ADMIN", None),
    ("qlts01", "ASSET_MGMT_ADMIN", None),
    ("req_danny01", "REQUESTING_UNIT", "DANNYGREEN"),
    ("req_farm01", "REQUESTING_UNIT", "SEAFARM"),
    ("cust_seagull01", "ASSET_CUSTODIAN", "SEAGULL_MARINE"),
    ("tech01", "TECHNICAL_REVIEWER", None),
    ("acct01", "ACCOUNTANT", None),
    ("proc01", "PROCUREMENT", None),
    ("approver01", "APPROVER", None),
    ("mgmt01", "MANAGEMENT_VIEWER", None),
]


def seed_users(db) -> None:
    for user_id, role_code, scope in ROLE_ASSIGNMENTS:
        emp = db.get(Employee, user_id)
        upsert(
            db, UserAccount, "user_id", user_id,
            full_name=emp.full_name if emp else user_id,
            email=f"{user_id}@seacorp.local",
            hashed_password=hash_password(DEMO_PASSWORD),
            company_code=emp.company_code if emp else None,
            department_code=emp.department_code if emp else None,
            active_flag=True,
            created_at=utcnow(),
        )
        existing = (
            db.query(UserRoleAssignment)
            .filter_by(user_id=user_id, role_code=role_code, scope_company_code=scope)
            .first()
        )
        if not existing:
            db.add(UserRoleAssignment(user_id=user_id, role_code=role_code, scope_company_code=scope))
    assert set(r for _, r, _ in ROLE_ASSIGNMENTS) == set(ROLES), "Thiếu demo user cho một vai trò RBAC"


def _asset(db, asset_id, **fields):
    fields.setdefault("last_updated_at", utcnow())
    fields.setdefault("updated_by", "seed_demo_data")
    fields.setdefault("verification_status", "Chưa xác minh")
    return upsert(db, Asset, "asset_id", asset_id, **fields)


def seed_assets(db) -> None:
    # ----- Seagull Marine: tàu + phương tiện cảng -----
    _asset(db, "SC-MAR-SHIP-2026-00001",
           asset_name="Tàu dầu sản phẩm mẫu", asset_class="TANGIBLE", asset_subclass="VESSEL",
           asset_type="Tàu biển", legal_entity_owner="SEAGULL_MARINE", owning_unit="SEAGULL_MARINE",
           managing_unit="DOI_TAU_SEAGULL", using_operating_unit="DOI_TAU_SEAGULL",
           custodian_employee_id="cust_seagull01", asset_status="Đang khai thác đủ công suất",
           lifecycle_status="Đang khai thác", quantity=1, unit_of_measure="Chiếc",
           capacity_design=25000, capacity_current=22000, capacity_utilized=18000, utilization_rate=0.82,
           country="Việt Nam")

    _asset(db, "SC-MAR-TRUCK-2026-00001",
           asset_name="Xe tải cảng 5 tấn", asset_class="TANGIBLE", asset_subclass="VEHICLE",
           asset_type="Xe tải", legal_entity_owner="SEAGULL_MARINE", owning_unit="SEAGULL_MARINE",
           managing_unit="DOI_TAU_SEAGULL", using_operating_unit="DOI_TAU_SEAGULL",
           custodian_employee_id="cust_seagull01", asset_status="Đang nhàn rỗi",
           lifecycle_status="Nhàn rỗi", quantity=1, unit_of_measure="Chiếc",
           capacity_design=5, capacity_current=5, capacity_utilized=0, utilization_rate=0.0,
           country="Việt Nam", province_city="Bà Rịa - Vũng Tàu",
           notes="Tài sản nhàn rỗi minh họa — dùng cho kịch bản đối chiếu thành công.")

    _asset(db, "SC-MAR-FORKLIFT-2026-00001",
           asset_name="Xe nâng cảng 3 tấn", asset_class="TANGIBLE", asset_subclass="EQUIPMENT",
           asset_type="Xe nâng", legal_entity_owner="SEAGULL_MARINE", owning_unit="SEAGULL_MARINE",
           managing_unit="DOI_TAU_SEAGULL", using_operating_unit="DOI_TAU_SEAGULL",
           custodian_employee_id="cust_seagull01", asset_status="Đang sửa chữa/bảo trì",
           lifecycle_status="Đang sửa chữa", quantity=1, unit_of_measure="Chiếc",
           capacity_design=3, capacity_current=2, capacity_utilized=0, utilization_rate=0.0,
           country="Việt Nam",
           notes="Cần sửa chữa trước khi điều chuyển — dùng cho kịch bản 'có tài sản nhưng cần sửa chữa'.")
    db.add(AssetCondition(
        inspection_id="INS-0001", asset_id="SC-MAR-FORKLIFT-2026-00001", inspection_date=utcnow().date(),
        condition_category="C", operating_status="Tạm ngừng", physical_condition="Trung bình",
        technical_rating_1_5=3, maintenance_required=True, estimated_repair_cost=15_000_000,
        estimated_downtime_days=10, can_be_transferred=False, technical_reviewer="tech01",
        verification_status="Đã xác minh", notes="Hỏng bơm thủy lực, cần thay thế.",
    ))

    # ----- DannyGreen Logistics -----
    _asset(db, "SC-DGL-TRUCK-2026-00001",
           asset_name="Xe tải 10 tấn", asset_class="TANGIBLE", asset_subclass="VEHICLE",
           asset_type="Xe tải", legal_entity_owner="DANNYGREEN", owning_unit="DANNYGREEN",
           managing_unit="KHO_VAN_DANNYGREEN", using_operating_unit="KHO_VAN_DANNYGREEN",
           custodian_employee_id="req_danny01", asset_status="Đang khai thác đủ công suất",
           lifecycle_status="Đang khai thác", quantity=1, unit_of_measure="Chiếc",
           capacity_design=10, capacity_current=10, capacity_utilized=9.5, utilization_rate=0.95,
           country="Việt Nam", province_city="Bình Dương",
           notes="Không còn công suất dư — dùng cho kịch bản 'công suất không đủ'.")

    _asset(db, "SC-DGL-WAREHOUSE-2026-00001",
           asset_name="Kho bãi Bình Dương", asset_class="TANGIBLE", asset_subclass="BUILDING",
           asset_type="Công trình kho bãi", legal_entity_owner="DANNYGREEN", owning_unit="DANNYGREEN",
           managing_unit="KHO_VAN_DANNYGREEN", using_operating_unit="KHO_VAN_DANNYGREEN",
           asset_status="Đang khai thác đủ công suất", lifecycle_status="Đang khai thác",
           quantity=1, unit_of_measure="Công trình", country="Việt Nam", province_city="Bình Dương")

    # ----- Seafarm -----
    _asset(db, "SC-SEAFARM-BIO-2026-00001",
           asset_name="Vườn sầu riêng lô A", asset_class="BIOLOGICAL", asset_subclass="PERENNIAL_CROP",
           asset_type="Cây lâu năm", legal_entity_owner="SEAFARM", owning_unit="SEAFARM",
           managing_unit="FARM_DAKNONG", using_operating_unit="FARM_DAKNONG",
           custodian_employee_id="req_farm01", asset_status="Đang khai thác đủ công suất",
           lifecycle_status="Đang khai thác", acquisition_date=dt.date(2022, 6, 1), quantity=1,
           unit_of_measure="Lô", country="Việt Nam", province_city="Đắk Nông")

    _asset(db, "SC-SF-MACH-2026-00001",
           asset_name="Máy kéo nông nghiệp", asset_class="TANGIBLE", asset_subclass="MACHINERY",
           asset_type="Máy nông nghiệp", legal_entity_owner="SEAFARM", owning_unit="SEAFARM",
           managing_unit="FARM_DAKNONG", using_operating_unit="FARM_DAKNONG",
           custodian_employee_id="req_farm01", asset_status="Đang khai thác nhưng còn công suất dư",
           lifecycle_status="Đang khai thác", quantity=1, unit_of_measure="Chiếc",
           capacity_design=100, capacity_current=100, capacity_utilized=40, utilization_rate=0.40,
           country="Việt Nam", province_city="Đắk Nông",
           notes="Còn công suất dư đáng kể — ứng viên điều chuyển/tận dụng.")

    _asset(db, "SC-SF-IRRIG-2026-00001",
           asset_name="Hệ thống tưới 50ha", asset_class="TANGIBLE", asset_subclass="INFRASTRUCTURE",
           asset_type="Công trình tưới", legal_entity_owner="SEAFARM", owning_unit="SEAFARM",
           managing_unit="FARM_DAKNONG", using_operating_unit="FARM_DAKNONG",
           asset_status="Đang khai thác đủ công suất", lifecycle_status="Đang khai thác",
           quantity=1, unit_of_measure="Công trình", country="Việt Nam", province_city="Đắk Nông")

    _asset(db, "SC-SF-CATTLE-2026-00001",
           asset_name="Đàn bò sữa Lâm Đồng", asset_class="BIOLOGICAL", asset_subclass="LIVESTOCK",
           asset_type="Vật nuôi", legal_entity_owner="SEAFARM", owning_unit="SEAFARM",
           managing_unit="FARM_LAMDONG", using_operating_unit="FARM_LAMDONG",
           asset_status="Đang khai thác đủ công suất", lifecycle_status="Đang khai thác",
           quantity=120, unit_of_measure="Con", country="Việt Nam", province_city="Lâm Đồng")

    # ----- SeaCorp (holding) -----
    _asset(db, "SC-SC-OFFICE-2026-00001",
           asset_name="Văn phòng SeaCorp Tower", asset_class="TANGIBLE", asset_subclass="BUILDING",
           asset_type="Công trình văn phòng", legal_entity_owner="SEACORP", owning_unit="SEACORP",
           managing_unit="QLTS_DT", using_operating_unit="QLTS_DT",
           asset_status="Đang khai thác đủ công suất", lifecycle_status="Đang khai thác",
           quantity=1, unit_of_measure="Công trình", country="Việt Nam", province_city="TP.HCM")

    _asset(db, "SC-SC-IT-2026-00001",
           asset_name="Hệ thống máy chủ văn phòng", asset_class="TANGIBLE", asset_subclass="IT_EQUIPMENT",
           asset_type="Thiết bị CNTT", legal_entity_owner="SEACORP", owning_unit="SEACORP",
           managing_unit="QLTS_DT", using_operating_unit="QLTS_DT",
           asset_status="Đang khai thác đủ công suất", lifecycle_status="Đang khai thác",
           quantity=1, unit_of_measure="Hệ thống", country="Việt Nam")

    _asset(db, "SC-SC-INT-2026-00001",
           asset_name="Giải pháp công nghệ xử lý sau thu hoạch", asset_class="INTANGIBLE",
           asset_subclass="PATENT", asset_type="Bằng sáng chế", legal_entity_owner="SEACORP",
           owning_unit="SEACORP", managing_unit="QLTS_DT", using_operating_unit="QLTS_DT",
           asset_status="Đang khai thác đủ công suất", lifecycle_status="Đang khai thác",
           quantity=1, unit_of_measure="Quyền", country="Việt Nam")


def seed_system_settings(db) -> None:
    scoring_weights = {
        "DEFAULT": {
            "function": 25, "technical_spec": 20, "capacity": 15, "condition": 15,
            "time_readiness": 10, "cost": 10, "location": 5,
        }
    }
    thresholds = {"high_fit": 85, "needs_review": 70}

    upsert(db, SystemSetting, "setting_key", "asset_matching.scoring_weights",
           value=json.dumps(scoring_weights, ensure_ascii=False),
           description="Trọng số 7 tiêu chí chấm điểm phù hợp tài sản (thang 100), theo nhóm tài sản.",
           updated_by="seed_demo_data", updated_at=utcnow())
    upsert(db, SystemSetting, "setting_key", "asset_matching.thresholds",
           value=json.dumps(thresholds, ensure_ascii=False),
           description="Ngưỡng tham khảo: >=high_fit là phù hợp cao; >=needs_review là cần đánh giá kỹ thuật bổ sung.",
           updated_by="seed_demo_data", updated_at=utcnow())


def seed_demo_requests(db) -> None:
    from app.services.numbering import generate_request_id

    if db.get(AssetRequest, "ASR-202611-00001") is not None:
        print("[seed] Yêu cầu demo đã tồn tại, bỏ qua.")
        return

    now = utcnow()
    req1_id = generate_request_id(db, now)
    db.add(AssetRequest(
        request_id=req1_id, sender_name="Lê Văn Kho Vận", sender_email="req_danny01@seacorp.local",
        company_code="DANNYGREEN", department_code="KHO_VAN_DANNYGREEN", received_at=now,
        channel="manual_intake", asset_group="Xe tải",
        original_content=(
            "Kính đề nghị Phòng QLTS&ĐT xem xét cấp 1 xe tải cảng khoảng 5 tấn phục vụ "
            "trung chuyển hàng tại kho Bình Dương, cần đưa vào sử dụng trong tháng tới. "
            "Người chịu trách nhiệm: Lê Văn Kho Vận."
        ),
        requested_quantity=1, requested_capacity=5, requested_location_province="Bình Dương",
        needed_by_date=now.date() + dt.timedelta(days=30),
        status="NEW", created_at=now,
    ))
    db.flush()

    req2_id = generate_request_id(db, now)
    db.add(AssetRequest(
        request_id=req2_id, sender_name="Phạm Thị Nông Trại", sender_email="req_farm01@seacorp.local",
        company_code="SEAFARM", department_code="FARM_DAKNONG", received_at=now,
        channel="manual_intake",
        original_content="Farm cần thêm thiết bị để làm việc, mong Phòng hỗ trợ sớm.",
        status="NEED_MORE_INFORMATION", ai_completeness="Thiếu thông tin",
        ai_confidence_note="Chưa đủ cơ sở đánh giá: thiếu nhóm tài sản, số lượng, công suất, thời điểm cần.",
        created_at=now,
    ))
    db.flush()

    req3_id = generate_request_id(db, now)
    db.add(AssetRequest(
        request_id=req3_id, sender_name="Lê Văn Kho Vận", sender_email="req_danny01@seacorp.local",
        company_code="DANNYGREEN", department_code="KHO_VAN_DANNYGREEN", received_at=now,
        channel="manual_intake", asset_group="VEHICLE",
        original_content="Bổ sung thêm cho yêu cầu xe tải cảng 5 tấn đã gửi hôm trước, vẫn cần gấp.",
        status="NEW", suspected_duplicate=True, duplicate_of_request_id=req1_id,
        created_at=now,
    ))
    print(f"[seed] Tạo yêu cầu demo: {req1_id} (đầy đủ), {req2_id} (thiếu thông tin), {req3_id} (nghi trùng với {req1_id})")


def main() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed_lookups(db)
        seed_org(db)
        seed_users(db)
        seed_assets(db)
        seed_system_settings(db)
        db.commit()
        seed_demo_requests(db)
        db.commit()
        print("[seed] Hoàn tất nạp dữ liệu demo.")
        print(f"[seed] Đăng nhập demo: user_id như 'qlts01', mật khẩu '{DEMO_PASSWORD}' (chỉ dùng cục bộ).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
