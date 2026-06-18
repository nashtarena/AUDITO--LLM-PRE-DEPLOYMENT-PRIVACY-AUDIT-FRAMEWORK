from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.session import get_db
from models.user import User
from models.project import Project
from models.audit import Audit, AuditResult, AuditStatus
from api.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_projects = db.query(Project).filter(Project.owner_id == current_user.id).all()
    project_ids = [str(p.id) for p in user_projects]

    total_audits = db.query(Audit).filter(Audit.project_id.in_(project_ids)).count()
    completed_audits = db.query(Audit).filter(
        Audit.project_id.in_(project_ids),
        Audit.status == AuditStatus.completed,
    ).count()

    # Average risk score
    avg_risk = db.query(func.avg(AuditResult.risk_score)).join(Audit).filter(
        Audit.project_id.in_(project_ids)
    ).scalar() or 0.0

    # Risk level distribution
    risk_counts = {}
    results = db.query(AuditResult).join(Audit).filter(
        Audit.project_id.in_(project_ids)
    ).all()

    for r in results:
        level = r.risk_level.value if r.risk_level else "Unknown"
        risk_counts[level] = risk_counts.get(level, 0) + 1

    # Recent audits (last 10)
    recent_audits = (
        db.query(Audit)
        .filter(Audit.project_id.in_(project_ids))
        .order_by(Audit.created_at.desc())
        .limit(10)
        .all()
    )

    recent = []
    for audit in recent_audits:
        project = next((p for p in user_projects if str(p.id) == str(audit.project_id)), None)
        entry = {
            "audit_id": str(audit.id),
            "project_name": project.name if project else "Unknown",
            "model_name": project.model_name if project else "Unknown",
            "status": audit.status.value,
            "created_at": audit.created_at.isoformat(),
            "risk_score": audit.result.risk_score if audit.result else None,
            "risk_level": audit.result.risk_level.value if (audit.result and audit.result.risk_level) else None,
        }
        recent.append(entry)

    return {
        "total_projects": len(user_projects),
        "total_audits": total_audits,
        "completed_audits": completed_audits,
        "average_risk_score": round(float(avg_risk), 1),
        "risk_distribution": risk_counts,
        "recent_audits": recent,
    }
