from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from database.session import get_db
from models.user import User
from models.audit import Audit, AuditStatus
from models.report import Report
from models.project import Project
from api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/{audit_id}/generate")
def generate_report(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    audit = db.query(Audit).join(Project).filter(
        Audit.id == audit_id,
        Project.owner_id == current_user.id,
    ).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    if audit.status != AuditStatus.completed:
        raise HTTPException(status_code=400, detail="Audit not completed yet")
    if not audit.result:
        raise HTTPException(status_code=400, detail="No audit results found")

    project = db.query(Project).filter(Project.id == audit.project_id).first()
    result = audit.result

    from reports.generator import generate_report as gen_pdf
    pdf_path = gen_pdf({
        "audit_id": str(audit.id),
        "project_name": project.name,
        "model_name": project.model_name,
        "risk_score": result.risk_score,
        "risk_level": result.risk_level.value if result.risk_level else "Unknown",
        "exact_match_score": result.exact_match_score,
        "matched_records": result.matched_records,
        "ngram_overlap_score": result.ngram_overlap_score,
        "semantic_similarity_score": result.semantic_similarity_score,
        "membership_probability": result.membership_probability,
        "canary_exposure_score": result.canary_exposure_score,
        "sensitive_data_detected": result.sensitive_data_detected,
        "total_sensitive_findings": len(result.sensitive_findings or []),
        "top_matches": result.top_matches,
        "sensitive_findings": result.sensitive_findings,
    })

    # Save report record
    if not audit.report:
        report = Report(audit_id=audit_id, file_path=pdf_path)
        db.add(report)
        db.commit()

    return {"message": "Report generated", "download_url": f"/api/reports/{audit_id}/download"}


@router.get("/{audit_id}/download")
def download_report(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(Report).join(Audit).join(Project).filter(
        Report.audit_id == audit_id,
        Project.owner_id == current_user.id,
    ).first()
    if not report or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report not found. Generate it first.")

    return FileResponse(
        report.file_path,
        media_type="application/pdf",
        filename=os.path.basename(report.file_path),
    )
