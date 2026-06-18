from datetime import datetime
from workers.celery_app import celery_app
from utils.logger import logger

import database.session
import models.audit
import models.dataset
import models.report
import models.project
import services.audit_orchestrator
import utils.dataset_loader
from uuid import UUID

@celery_app.task(bind=True, name="run_audit_task")
def run_audit_task(self, audit_id: UUID):
    """
    Background task: loads datasets, runs full audit, saves results.
    """
    from database.session import SessionLocal
    from models.audit import Audit, AuditResult, AuditStatus, RiskLevel
    from models.dataset import Dataset
    from models.report import Notification
    from models.project import Project
    from utils.dataset_loader import load_texts
    from services.audit_orchestrator import run_full_audit

    db = SessionLocal()

    try:
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            logger.error(f"Audit {audit_id} not found")
            return

        audit.status = AuditStatus.running
        audit.progress = 5
        db.commit()

        # Load datasets
        ref_dataset = db.query(Dataset).filter(Dataset.id == audit.reference_dataset_id).first()
        gen_dataset = db.query(Dataset).filter(Dataset.id == audit.generated_dataset_id).first()

        reference_texts = load_texts(ref_dataset.file_path)
        generated_texts = load_texts(gen_dataset.file_path)

        logger.info(f"Audit {audit_id}: {len(reference_texts)} ref, {len(generated_texts)} gen texts")

        # Progress callback updates the audit row
        def update_progress(pct: int):
            audit.progress = pct
            db.commit()

        # Run the pipeline
        results = run_full_audit(
            reference_texts=reference_texts,
            generated_texts=generated_texts,
            progress_callback=update_progress,
        )

        # Save results
        audit_result = AuditResult(
            audit_id=audit_id,
            exact_match_score=results["exact_match_score"],
            matched_records=results["matched_records"],
            ngram_overlap_score=results["ngram_overlap_score"],
            semantic_similarity_score=results["semantic_similarity_score"],
            top_matches=results["top_matches"],
            membership_probability=results["membership_probability"],
            canary_exposure_score=results["canary_exposure_score"],
            canary_hits=results["canary_hits"],
            sensitive_data_detected=results["sensitive_data_detected"],
            sensitive_findings=results["sensitive_findings"],
            risk_score=results["risk_score"],
            risk_level=RiskLevel(results["risk_level"]),
        )
        db.add(audit_result)

        audit.status = AuditStatus.completed
        audit.progress = 100
        audit.completed_at = datetime.utcnow()
        db.commit()

        # Send notification to project owner
        project = db.query(Project).filter(Project.id == audit.project_id).first()
        risk_level = results["risk_level"]
        notification = Notification(
            user_id=project.owner_id,
            title=f"Audit Complete — {risk_level} Risk",
            message=(
                f"Audit for project '{project.name}' finished. "
                f"Risk Score: {results['risk_score']}/100 ({risk_level}). "
                f"Exact matches: {results['matched_records']}. "
                f"Sensitive data detected: {results['sensitive_data_detected']}."
            ),
        )
        db.add(notification)
        db.commit()

        logger.info(f"Audit {audit_id} completed. Risk: {risk_level} ({results['risk_score']})")
        return {"audit_id": audit_id, "risk_score": results["risk_score"]}

    except Exception as e:
        logger.error(f"Audit {audit_id} failed: {e}")
        audit = db.query(Audit).filter(Audit.id == audit_id).first()
        if audit:
            from models.audit import AuditStatus
            audit.status = AuditStatus.failed
            audit.progress = 0
            db.commit()
        raise

    finally:
        db.close()
