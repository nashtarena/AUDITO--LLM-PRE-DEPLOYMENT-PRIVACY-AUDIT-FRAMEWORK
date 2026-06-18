from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database.session import get_db
from models.user import User
from models.project import Project
from models.dataset import Dataset
from models.audit import Audit, AuditResult, AuditStatus
from api.deps import get_current_user, require_researcher

from uuid import UUID

router = APIRouter(prefix="/audits", tags=["audits"])


class AuditCreate(BaseModel):
    project_id: UUID
    reference_dataset_id: str
    generated_dataset_id: str


class AuditResultResponse(BaseModel):
    exact_match_score: float
    matched_records: int
    ngram_overlap_score: float
    semantic_similarity_score: float
    top_matches: Optional[list]
    membership_probability: float
    canary_exposure_score: float
    canary_hits: Optional[list]
    sensitive_data_detected: bool
    sensitive_findings: Optional[list]
    risk_score: float
    risk_level: str

    class Config:
        from_attributes = True


class AuditResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    progress: int
    created_at: datetime
    completed_at: Optional[datetime]
    result: Optional[AuditResultResponse]

    class Config:
        from_attributes = True


@router.post("", response_model=AuditResponse, status_code=201)
def create_audit(
    data: AuditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_researcher),
):
    # Validate project
    project = db.query(Project).filter(
        Project.id == data.project_id, Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate datasets
    for ds_id in [data.reference_dataset_id, data.generated_dataset_id]:
        if not db.query(Dataset).filter(Dataset.id == ds_id, Dataset.project_id == data.project_id).first():
            raise HTTPException(status_code=404, detail=f"Dataset {ds_id} not found")

    audit = Audit(
        project_id=data.project_id,
        reference_dataset_id=data.reference_dataset_id,
        generated_dataset_id=data.generated_dataset_id,
        status=AuditStatus.pending,
    )
    db.add(audit)
    db.commit()
    db.flush()

    # Launch background task
    from workers.tasks import run_audit_task
    task = run_audit_task.delay(str(audit.id))
    audit.task_id = task.id
    audit.status = AuditStatus.running
    db.commit()

    db.commit()
    db.flush()
    return audit


@router.get("/{audit_id}", response_model=AuditResponse)
def get_audit(
    audit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    audit = db.query(Audit).join(Project).filter(
        Audit.id == audit_id,
        Project.owner_id == current_user.id,
    ).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


@router.get("/project/{project_id}", response_model=List[AuditResponse])
def list_audits(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == project_id, Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(Audit).filter(Audit.project_id == project_id).order_by(Audit.created_at.desc()).all()
