"""
PDF Report Generator
Produces a professional audit report using ReportLab.
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


RISK_COLORS = {
    "Low": colors.HexColor("#22c55e"),
    "Medium": colors.HexColor("#f59e0b"),
    "High": colors.HexColor("#f97316"),
    "Critical": colors.HexColor("#ef4444"),
}


def generate_report(audit_data: dict, output_dir: str = "reports_output") -> str:
    """
    audit_data keys: project_name, model_name, audit_id, created_at,
                     risk_score, risk_level, exact_match_score, matched_records,
                     ngram_overlap_score, semantic_similarity_score,
                     membership_probability, canary_exposure_score,
                     sensitive_data_detected, total_sensitive_findings,
                     top_matches (list), sensitive_findings (list)
    Returns: file path to generated PDF
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"audit_report_{audit_data['audit_id'][:8]}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    # --- Title ---
    title_style = ParagraphStyle("Title", fontSize=22, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#1e293b"), spaceAfter=6)
    sub_style = ParagraphStyle("Sub", fontSize=11, fontName="Helvetica",
                                textColor=colors.HexColor("#64748b"), spaceAfter=20)

    story.append(Paragraph("Audito — Privacy Leakage Audit Report", title_style))
    story.append(Paragraph(
        f"Project: {audit_data['project_name']} &nbsp;|&nbsp; Model: {audit_data['model_name']} &nbsp;|&nbsp; "
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        sub_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 16))

    # --- Executive Summary ---
    heading = ParagraphStyle("H1", fontSize=14, fontName="Helvetica-Bold",
                              textColor=colors.HexColor("#1e293b"), spaceAfter=8)
    body = ParagraphStyle("Body", fontSize=10, fontName="Helvetica",
                           textColor=colors.HexColor("#374151"), leading=16, spaceAfter=6)

    story.append(Paragraph("Executive Summary", heading))
    risk_level = audit_data["risk_level"]
    risk_color = RISK_COLORS.get(risk_level, colors.gray)

    summary_text = (
        f"This audit analyzed model outputs from <b>{audit_data['model_name']}</b> against the reference dataset. "
        f"The overall risk score is <b>{audit_data['risk_score']}/100</b> — classified as "
        f"<font color='{risk_color.hexval()}'><b>{risk_level}</b></font>. "
        f"A total of <b>{audit_data.get('matched_records', 0)}</b> exact or near-exact matches were found. "
        f"Sensitive data was {'<b>detected</b>' if audit_data['sensitive_data_detected'] else 'not detected'} in the outputs."
    )
    story.append(Paragraph(summary_text, body))
    story.append(Spacer(1, 12))

    # --- Risk Score Table ---
    story.append(Paragraph("Risk Score Breakdown", heading))
    table_data = [
        ["Module", "Score", "Weight"],
        ["Exact Match Detection", f"{round(audit_data['exact_match_score']*100, 1)}%", "25%"],
        ["Semantic Similarity", f"{round(audit_data['semantic_similarity_score']*100, 1)}%", "25%"],
        ["Membership Inference", f"{round(audit_data['membership_probability']*100, 1)}%", "20%"],
        ["Canary Exposure", f"{audit_data['canary_exposure_score']}/100", "15%"],
        ["Sensitive Data", "Detected" if audit_data["sensitive_data_detected"] else "None", "15%"],
        ["OVERALL RISK SCORE", f"{audit_data['risk_score']}/100 — {risk_level}", ""],
    ]
    t = Table(table_data, colWidths=[3*inch, 1.5*inch, 1*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f8fafc"), colors.white]),
        ("BACKGROUND", (0, -1), (-1, -1), risk_color),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    # --- Semantic Top Matches ---
    top_matches = audit_data.get("top_matches") or []
    if top_matches:
        story.append(Paragraph("Top Semantic Matches", heading))
        story.append(Paragraph(
            "The following generated outputs closely match reference dataset entries:", body
        ))
        for i, match in enumerate(top_matches[:5]):
            story.append(Paragraph(
                f"<b>Match {i+1}</b> (similarity: {match.get('similarity_score', 0):.2%})", body
            ))
            story.append(Paragraph(f"Reference: {match.get('reference', '')[:200]}", body))
            story.append(Paragraph(f"Generated: {match.get('generated', '')[:200]}", body))
            story.append(Spacer(1, 6))

    # --- Sensitive Findings ---
    sensitive_findings = audit_data.get("sensitive_findings") or []
    if sensitive_findings:
        story.append(Paragraph("Sensitive Data Findings", heading))
        sf_data = [["Type", "Masked Value", "Context"]]
        for f in sensitive_findings[:10]:
            sf_data.append([
                f.get("type", ""),
                f.get("masked_value", ""),
                f.get("context", "")[:80],
            ])
        st = Table(sf_data, colWidths=[1.5*inch, 1.5*inch, 3.5*inch])
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dc2626")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#fef2f2"), colors.white]),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(st)
        story.append(Spacer(1, 16))

    # --- Recommendations ---
    story.append(Paragraph("Recommendations", heading))
    recommendations = _get_recommendations(audit_data)
    for rec in recommendations:
        story.append(Paragraph(f"• {rec}", body))

    doc.build(story)
    return filepath


def _get_recommendations(data: dict) -> list:
    recs = []
    if data["exact_match_score"] > 0.3:
        recs.append("High exact match rate detected. Review training data deduplication and apply differential privacy.")
    if data["semantic_similarity_score"] > 0.7:
        recs.append("Model outputs show high semantic similarity to training data. Consider output filtering or watermarking.")
    if data["membership_probability"] > 0.6:
        recs.append("High membership inference risk. Evaluate training data with privacy-preserving techniques.")
    if data["canary_exposure_score"] > 30:
        recs.append("Canary strings were found in model outputs. Investigate memorization of specific training samples.")
    if data["sensitive_data_detected"]:
        recs.append("Sensitive PII or secrets were found in outputs. Implement output scrubbing before production deployment.")
    if not recs:
        recs.append("No critical issues found. Continue monitoring with periodic audits.")
    return recs
