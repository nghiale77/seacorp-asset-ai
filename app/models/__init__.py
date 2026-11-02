"""Import toàn bộ model để Base.metadata nhận diện (dùng cho create_all/Alembic)."""
from app.models.org import Company, Department, Employee  # noqa: F401
from app.models.asset import (  # noqa: F401
    Asset,
    AssetLocation,
    AssetValuation,
    AssetCondition,
    AssetResponsibility,
    AssetComponent,
    AssetIntangibleRight,
    AssetBioRecord,
    AssetMovement,
    Lookup,
)
from app.models.request import AssetRequest, RequestDocument  # noqa: F401
from app.models.matching import AssetMatchingResult  # noqa: F401
from app.models.proposal import TransferProposal, ProcurementProposal  # noqa: F401
from app.models.workflow import WorkflowTask, ApprovalHistory, WORKFLOW_STATES  # noqa: F401
from app.models.notification import EmailMessage, Notification  # noqa: F401
from app.models.audit import AuditLog, SystemSetting  # noqa: F401
from app.models.auth import UserAccount, UserRoleAssignment, ROLES  # noqa: F401
