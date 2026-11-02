"""Cơ sở dữ liệu tài sản tập trung — 10 phân hệ, kế thừa trực tiếp field list
đã thiết kế trong SEACORP_Cau_truc_Du_lieu_Tai_san_Tap_trung.xlsx (xem
E:\\_SC_ASSETS). Không thiết kế lại từ đầu, chỉ ánh xạ sang ORM.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Asset(Base):
    """01_ASSET_MASTER — hồ sơ định danh và phân loại tài sản, trung tâm liên kết dữ liệu."""

    __tablename__ = "assets"

    asset_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset_name: Mapped[str] = mapped_column(String(300), nullable=False)
    asset_name_en: Mapped[str | None] = mapped_column(String(300))
    asset_class: Mapped[str] = mapped_column(String(30), nullable=False)  # TANGIBLE/BIOLOGICAL/INTANGIBLE/CIP
    asset_subclass: Mapped[str | None] = mapped_column(String(50))
    asset_type: Mapped[str | None] = mapped_column(String(100))
    parent_asset_id: Mapped[str | None] = mapped_column(String(50))

    legal_entity_owner: Mapped[str | None] = mapped_column(String(100))
    owning_unit: Mapped[str | None] = mapped_column(String(100))
    managing_unit: Mapped[str | None] = mapped_column(String(100))
    using_operating_unit: Mapped[str | None] = mapped_column(String(100))
    custodian_employee_id: Mapped[str | None] = mapped_column(String(30))

    asset_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Chưa xác định tình trạng")
    lifecycle_status: Mapped[str | None] = mapped_column(String(50))
    acquisition_method: Mapped[str | None] = mapped_column(String(50))
    acquisition_date: Mapped[dt.date | None] = mapped_column(Date)
    in_service_date: Mapped[dt.date | None] = mapped_column(Date)
    useful_life_months: Mapped[int | None] = mapped_column(Integer)
    depreciation_method: Mapped[str | None] = mapped_column(String(50))
    accounting_asset_code: Mapped[str | None] = mapped_column(String(50))
    gl_account: Mapped[str | None] = mapped_column(String(30))
    cost_center: Mapped[str | None] = mapped_column(String(30))
    project_code: Mapped[str | None] = mapped_column(String(30))

    quantity: Mapped[float | None] = mapped_column(Numeric(18, 3))
    unit_of_measure: Mapped[str | None] = mapped_column(String(30))
    manufacturer: Mapped[str | None] = mapped_column(String(150))
    model: Mapped[str | None] = mapped_column(String(150))
    serial_number_vin_imo_lot: Mapped[str | None] = mapped_column(String(150))
    technical_specification: Mapped[str | None] = mapped_column(Text)

    capacity_design: Mapped[float | None] = mapped_column(Numeric(18, 3))
    capacity_current: Mapped[float | None] = mapped_column(Numeric(18, 3))
    capacity_utilized: Mapped[float | None] = mapped_column(Numeric(18, 3))
    utilization_rate: Mapped[float | None] = mapped_column(Numeric(6, 4))

    country: Mapped[str | None] = mapped_column(String(100))
    province_city: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    ward_commune: Mapped[str | None] = mapped_column(String(100))
    address_description: Mapped[str | None] = mapped_column(String(300))
    latitude_wgs84: Mapped[float | None] = mapped_column(Numeric(10, 6))
    longitude_wgs84: Mapped[float | None] = mapped_column(Numeric(10, 6))
    gps_accuracy_m: Mapped[float | None] = mapped_column(Numeric(10, 2))
    coordinate_captured_at: Mapped[dt.date | None] = mapped_column(Date)
    coordinate_method: Mapped[str | None] = mapped_column(String(50))

    land_parcel_certificate_no: Mapped[str | None] = mapped_column(String(100))
    ownership_document_ref: Mapped[str | None] = mapped_column(String(100))
    insurance_policy_ref: Mapped[str | None] = mapped_column(String(100))
    warranty_expiry: Mapped[dt.date | None] = mapped_column(Date)
    last_physical_verification: Mapped[dt.date | None] = mapped_column(Date)
    next_verification_due: Mapped[dt.date | None] = mapped_column(Date)

    data_owner: Mapped[str | None] = mapped_column(String(100))
    last_updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    updated_by: Mapped[str | None] = mapped_column(String(100))
    verification_status: Mapped[str | None] = mapped_column(String(50), default="Chưa xác minh")
    evidence_link: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)


class AssetLocation(Base):
    """02_LOCATION — vị trí, tọa độ, ranh giới theo thời gian."""

    __tablename__ = "asset_locations"

    location_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    location_type: Mapped[str | None] = mapped_column(String(50))
    location_name: Mapped[str | None] = mapped_column(String(200))
    legal_entity: Mapped[str | None] = mapped_column(String(100))
    site_farm_vessel_facility: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300))
    province_city: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    ward_commune: Mapped[str | None] = mapped_column(String(100))
    latitude_wgs84: Mapped[float | None] = mapped_column(Numeric(10, 6))
    longitude_wgs84: Mapped[float | None] = mapped_column(Numeric(10, 6))
    gps_accuracy_m: Mapped[float | None] = mapped_column(Numeric(10, 2))
    coordinate_captured_at: Mapped[dt.date | None] = mapped_column(Date)
    coordinate_method: Mapped[str | None] = mapped_column(String(50))
    geojson_polygon_link: Mapped[str | None] = mapped_column(String(300))
    land_plot_block_row: Mapped[str | None] = mapped_column(String(100))
    berth_port_route: Mapped[str | None] = mapped_column(String(150))
    valid_from: Mapped[dt.date | None] = mapped_column(Date)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)
    current_location_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    verified_by: Mapped[str | None] = mapped_column(String(100))
    evidence_link: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)


class AssetValuation(Base):
    """03_VALUATION — lịch sử định giá, không ghi đè; mỗi lần định giá một dòng."""

    __tablename__ = "asset_valuations"

    valuation_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    valuation_type: Mapped[str | None] = mapped_column(String(50))
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2))
    currency: Mapped[str | None] = mapped_column(String(10), default="VND")
    valuation_date: Mapped[dt.date | None] = mapped_column(Date)
    valuation_basis: Mapped[str | None] = mapped_column(String(100))
    methodology: Mapped[str | None] = mapped_column(String(150))
    valuer_organization: Mapped[str | None] = mapped_column(String(150))
    valuer_name: Mapped[str | None] = mapped_column(String(150))
    report_certificate_no: Mapped[str | None] = mapped_column(String(100))
    accounting_gross_cost: Mapped[float | None] = mapped_column(Numeric(20, 2))
    accumulated_depreciation_amortization: Mapped[float | None] = mapped_column(Numeric(20, 2))
    impairment_allowance: Mapped[float | None] = mapped_column(Numeric(20, 2))
    net_book_value: Mapped[float | None] = mapped_column(Numeric(20, 2))
    market_value: Mapped[float | None] = mapped_column(Numeric(20, 2))
    replacement_cost: Mapped[float | None] = mapped_column(Numeric(20, 2))
    recoverable_amount: Mapped[float | None] = mapped_column(Numeric(20, 2))
    disposal_cost_estimate: Mapped[float | None] = mapped_column(Numeric(20, 2))
    valuation_approval_status: Mapped[str | None] = mapped_column(String(50))
    approved_by: Mapped[str | None] = mapped_column(String(100))
    evidence_link: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)


class AssetCondition(Base):
    """04_CONDITION — tình trạng kỹ thuật, do bộ phận kỹ thuật/bảo trì xác nhận."""

    __tablename__ = "asset_conditions"

    inspection_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    inspection_date: Mapped[dt.date | None] = mapped_column(Date)
    condition_category: Mapped[str | None] = mapped_column(String(50))
    operating_status: Mapped[str | None] = mapped_column(String(50))
    physical_condition: Mapped[str | None] = mapped_column(String(50))
    technical_rating_1_5: Mapped[int | None] = mapped_column(Integer)
    safety_status: Mapped[str | None] = mapped_column(String(50))
    environmental_status: Mapped[str | None] = mapped_column(String(50))
    defects_observed: Mapped[str | None] = mapped_column(Text)
    maintenance_required: Mapped[bool | None] = mapped_column(Boolean)
    estimated_repair_cost: Mapped[float | None] = mapped_column(Numeric(20, 2))
    estimated_downtime_days: Mapped[int | None] = mapped_column(Integer)
    can_be_transferred: Mapped[bool | None] = mapped_column(Boolean)
    transfer_readiness_date: Mapped[dt.date | None] = mapped_column(Date)
    inspector_employee_id: Mapped[str | None] = mapped_column(String(30))
    technical_reviewer: Mapped[str | None] = mapped_column(String(100))
    next_inspection_date: Mapped[dt.date | None] = mapped_column(Date)
    photo_link: Mapped[str | None] = mapped_column(String(300))
    inspection_report_link: Mapped[str | None] = mapped_column(String(300))
    verification_status: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)


class AssetResponsibility(Base):
    """05_RESPONSIBILITY — phân định trách nhiệm quản lý, theo thời kỳ bàn giao."""

    __tablename__ = "asset_responsibility"

    responsibility_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    legal_entity_owner: Mapped[str | None] = mapped_column(String(100))
    asset_owner_representative: Mapped[str | None] = mapped_column(String(100))
    managing_unit: Mapped[str | None] = mapped_column(String(100))
    managing_unit_head: Mapped[str | None] = mapped_column(String(100))
    using_operating_unit: Mapped[str | None] = mapped_column(String(100))
    using_unit_head: Mapped[str | None] = mapped_column(String(100))
    direct_custodian_employee_id: Mapped[str | None] = mapped_column(String(30))
    direct_custodian_name: Mapped[str | None] = mapped_column(String(100))
    handover_record_no: Mapped[str | None] = mapped_column(String(100))
    responsibility_start_date: Mapped[dt.date | None] = mapped_column(Date)
    responsibility_end_date: Mapped[dt.date | None] = mapped_column(Date)
    scope_of_responsibility: Mapped[str | None] = mapped_column(Text)
    operating_obligations: Mapped[str | None] = mapped_column(Text)
    maintenance_obligations: Mapped[str | None] = mapped_column(Text)
    reporting_frequency: Mapped[str | None] = mapped_column(String(50))
    acknowledgement_status: Mapped[str | None] = mapped_column(String(50))
    acknowledged_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    approved_by: Mapped[str | None] = mapped_column(String(100))
    evidence_link: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)


class AssetComponent(Base):
    """06_COMPONENTS — cấu phần/hạng mục có thể quản lý hoặc thay thế riêng."""

    __tablename__ = "asset_components"

    component_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    parent_asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    component_name: Mapped[str | None] = mapped_column(String(200))
    component_type: Mapped[str | None] = mapped_column(String(100))
    component_asset_id: Mapped[str | None] = mapped_column(String(50))
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 3))
    unit: Mapped[str | None] = mapped_column(String(30))
    technical_description: Mapped[str | None] = mapped_column(Text)
    component_location: Mapped[str | None] = mapped_column(String(200))
    accounting_separate_asset_flag: Mapped[bool | None] = mapped_column(Boolean)
    useful_life_months: Mapped[int | None] = mapped_column(Integer)
    replacement_date: Mapped[dt.date | None] = mapped_column(Date)
    condition_status: Mapped[str | None] = mapped_column(String(50))
    evidence_link: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)


class AssetIntangibleRight(Base):
    """07_INTANGIBLE_RIGHTS — quyền tài sản vô hình (patent/bản quyền/nhãn hiệu/R&D)."""

    __tablename__ = "asset_intangible_rights"

    right_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    intangible_type: Mapped[str | None] = mapped_column(String(50))
    title_or_project_name: Mapped[str | None] = mapped_column(String(300))
    creator_applicant_owner: Mapped[str | None] = mapped_column(String(200))
    registered_legal_entity: Mapped[str | None] = mapped_column(String(100))
    registration_application_no: Mapped[str | None] = mapped_column(String(100))
    patent_certificate_no: Mapped[str | None] = mapped_column(String(100))
    copyright_contract_no: Mapped[str | None] = mapped_column(String(100))
    jurisdiction_territory: Mapped[str | None] = mapped_column(String(100))
    filing_date: Mapped[dt.date | None] = mapped_column(Date)
    grant_date: Mapped[dt.date | None] = mapped_column(Date)
    effective_date: Mapped[dt.date | None] = mapped_column(Date)
    expiry_date: Mapped[dt.date | None] = mapped_column(Date)
    renewal_deadline: Mapped[dt.date | None] = mapped_column(Date)
    exclusive_nonexclusive: Mapped[str | None] = mapped_column(String(50))
    licensed_use_scope: Mapped[str | None] = mapped_column(Text)
    restrictions_encumbrances: Mapped[str | None] = mapped_column(Text)
    legal_status: Mapped[str | None] = mapped_column(String(50))
    r_and_d_project_code: Mapped[str | None] = mapped_column(String(50))
    research_milestones: Mapped[str | None] = mapped_column(Text)
    commercialization_status: Mapped[str | None] = mapped_column(String(50))
    revenue_or_benefit_model: Mapped[str | None] = mapped_column(Text)
    legal_document_link: Mapped[str | None] = mapped_column(String(300))
    technical_dossier_link: Mapped[str | None] = mapped_column(String(300))
    responsible_department: Mapped[str | None] = mapped_column(String(100))
    responsible_person: Mapped[str | None] = mapped_column(String(100))
    last_legal_review_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class AssetBioRecord(Base):
    """08_BIO_ASSETS — cây trồng/vật nuôi, theo chu kỳ sản xuất."""

    __tablename__ = "asset_bio_records"

    bio_record_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    bio_category: Mapped[str | None] = mapped_column(String(50))
    species_variety_breed: Mapped[str | None] = mapped_column(String(150))
    farm_site: Mapped[str | None] = mapped_column(String(150))
    plot_block_or_herd_flock: Mapped[str | None] = mapped_column(String(100))
    area_ha_or_headcount: Mapped[float | None] = mapped_column(Numeric(18, 3))
    planting_or_birth_date: Mapped[dt.date | None] = mapped_column(Date)
    age_or_growth_stage: Mapped[str | None] = mapped_column(String(100))
    quantity_opening: Mapped[float | None] = mapped_column(Numeric(18, 3))
    additions: Mapped[float | None] = mapped_column(Numeric(18, 3))
    harvest_sales_deaths: Mapped[float | None] = mapped_column(Numeric(18, 3))
    quantity_closing: Mapped[float | None] = mapped_column(Numeric(18, 3))
    unit: Mapped[str | None] = mapped_column(String(30))
    production_cycle: Mapped[str | None] = mapped_column(String(100))
    expected_output: Mapped[float | None] = mapped_column(Numeric(18, 3))
    actual_output: Mapped[float | None] = mapped_column(Numeric(18, 3))
    yield_per_ha_or_animal: Mapped[float | None] = mapped_column(Numeric(18, 3))
    biological_condition: Mapped[str | None] = mapped_column(String(50))
    disease_pest_status: Mapped[str | None] = mapped_column(String(100))
    harvest_or_maturity_date: Mapped[dt.date | None] = mapped_column(Date)
    cultivation_rearing_cost: Mapped[float | None] = mapped_column(Numeric(20, 2))
    biological_asset_value: Mapped[float | None] = mapped_column(Numeric(20, 2))
    measurement_basis: Mapped[str | None] = mapped_column(String(150))
    valuation_date: Mapped[dt.date | None] = mapped_column(Date)
    agronomy_vet_responsible: Mapped[str | None] = mapped_column(String(100))
    evidence_link: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)


class AssetMovement(Base):
    """09_MOVEMENT — lịch sử điều chuyển; nguồn dữ liệu chính cho đối chiếu điều chuyển."""

    __tablename__ = "asset_movements"

    movement_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    movement_type: Mapped[str | None] = mapped_column(String(50))
    from_legal_entity: Mapped[str | None] = mapped_column(String(100))
    from_unit: Mapped[str | None] = mapped_column(String(100))
    from_location: Mapped[str | None] = mapped_column(String(200))
    to_legal_entity: Mapped[str | None] = mapped_column(String(100))
    to_unit: Mapped[str | None] = mapped_column(String(100))
    to_location: Mapped[str | None] = mapped_column(String(200))
    movement_request_no: Mapped[str | None] = mapped_column(String(50), index=True)
    approval_reference: Mapped[str | None] = mapped_column(String(100))
    effective_date: Mapped[dt.date | None] = mapped_column(Date)
    handover_date: Mapped[dt.date | None] = mapped_column(Date)
    gps_latitude: Mapped[float | None] = mapped_column(Numeric(10, 6))
    gps_longitude: Mapped[float | None] = mapped_column(Numeric(10, 6))
    condition_before: Mapped[str | None] = mapped_column(String(50))
    condition_after: Mapped[str | None] = mapped_column(String(50))
    custodian_before: Mapped[str | None] = mapped_column(String(100))
    custodian_after: Mapped[str | None] = mapped_column(String(100))
    accounting_treatment_reference: Mapped[str | None] = mapped_column(String(150))
    handover_record_link: Mapped[str | None] = mapped_column(String(300))
    updated_by: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)


class Lookup(Base):
    """10_LOOKUPS — danh mục chuẩn dùng chung (Asset_Class, Asset_Status, ...)."""

    __tablename__ = "lookups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lookup_group: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    lookup_code: Mapped[str] = mapped_column(String(50), nullable=False)
    lookup_name_vi: Mapped[str | None] = mapped_column(String(200))
    lookup_name_en: Mapped[str | None] = mapped_column(String(200))
    definition_or_usage: Mapped[str | None] = mapped_column(Text)
    active_flag: Mapped[bool] = mapped_column(Boolean, default=True)
