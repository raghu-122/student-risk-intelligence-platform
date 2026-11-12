from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.api.dependencies.auth import require_roles
from app.models.user import User
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.risk_assessment import RiskAssessment
from app.models.intervention import Intervention
from app.models.support_case import SupportCase
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin", tags=["Administration"])

ADMIN_ROLES = ("PLATFORM_ADMINISTRATOR",)


@router.get("/users")
def list_users(db: Session = Depends(get_db), _=Depends(require_roles(*ADMIN_ROLES))):
    users = db.query(User).all()
    return [{"user_id": u.user_id, "username": u.username, "email": u.email,
             "role": u.role, "is_active": u.is_active} for u in users]


@router.get("/audit-logs")
def list_audit_logs(
    page: int = 1, page_size: int = 50,
    db: Session = Depends(get_db), _=Depends(require_roles(*ADMIN_ROLES)),
):
    q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "items": [{
        "log_id": l.log_id, "entity_type": l.entity_type, "entity_id": l.entity_id,
        "action": l.action, "performed_by": l.performed_by, "timestamp": l.timestamp,
    } for l in items]}


@router.get("/system-stats")
def system_stats(db: Session = Depends(get_db), _=Depends(require_roles(*ADMIN_ROLES))):
    return {
        "students": db.query(func.count(Student.student_id)).scalar(),
        "enrollments": db.query(func.count(Enrollment.enrollment_id)).scalar(),
        "risk_assessments": db.query(func.count(RiskAssessment.risk_id)).scalar(),
        "interventions": db.query(func.count(Intervention.intervention_id)).scalar(),
        "support_cases": db.query(func.count(SupportCase.case_id)).scalar(),
        "users": db.query(func.count(User.user_id)).scalar(),
        "audit_logs": db.query(func.count(AuditLog.log_id)).scalar(),
    }

