"""Regulatory Audit Dossier download routes (PDF and JSON)."""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from backend.config import DOSSIERS_DIR
from backend.database import get_screening_run

router = APIRouter(prefix="/api/dossier", tags=["Dossier"])


@router.get("/{run_id}/pdf")
def download_pdf_dossier(run_id: str):
    """Downloads FDA 21 CFR Part 11 compliant audit dossier in PDF format."""
    pdf_path = DOSSIERS_DIR / f"{run_id}.pdf"
    if not pdf_path.exists():
        # Check database
        run = get_screening_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Dossier PDF for run '{run_id}' not found.")
        from agents.audit_agent import AuditAgent
        agent = AuditAgent()
        pdf_bytes = agent.generate_dossier_pdf(run["dossier_json"], output_path=str(pdf_path))
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=FDA_Audit_Dossier_{run_id}.pdf"}
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"FDA_Audit_Dossier_{run_id}.pdf"
    )


@router.get("/{run_id}/json")
def download_json_dossier(run_id: str):
    """Downloads FDA-style structured JSON audit dossier."""
    json_path = DOSSIERS_DIR / f"{run_id}.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    run = get_screening_run(run_id)
    if run and run.get("dossier_json"):
        return run["dossier_json"]

    raise HTTPException(status_code=404, detail=f"Dossier JSON for run '{run_id}' not found.")
