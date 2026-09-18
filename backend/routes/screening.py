"""Screening execution and history routes."""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from backend.models import ScreeningRequest
from backend.config import DATA_DIR, DOSSIERS_DIR
from backend.database import save_screening_run, get_screening_run, list_screening_runs
from agents.orchestrator import ClinicalScreeningOrchestrator

router = APIRouter(prefix="/api/screen", tags=["Screening"])
orchestrator = ClinicalScreeningOrchestrator()


@router.post("/run")
def run_screening(req: ScreeningRequest):
    """Executes the multi-agent clinical trial screening pipeline."""
    # 1. Resolve protocol text
    protocol_text = req.protocol_text
    if not protocol_text:
        default_proto = DATA_DIR / "synthetic_samples" / "protocol_nsclc_phase3.txt"
        if default_proto.exists():
            with open(default_proto, "r", encoding="utf-8") as f:
                protocol_text = f.read()
        else:
            raise HTTPException(status_code=400, detail="No protocol text provided or found.")

    # 2. Resolve patient data
    patient_input = None
    patient_format = "json"

    if req.preset_patient_id:
        preset_map = {
            "patient_01": "patient_01_eligible.json",
            "patient_02": "patient_02_ineligible.json",
            "patient_03": "patient_03_borderline.json"
        }
        filename = preset_map.get(req.preset_patient_id)
        if filename:
            path = DATA_DIR / "synthetic_samples" / filename
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    patient_input = json.load(f)
                    patient_format = "json"

    if patient_input is None:
        if req.patient_data:
            patient_input = req.patient_data
            patient_format = "json"
        elif req.patient_raw_text:
            patient_input = req.patient_raw_text
            patient_format = "text"
        else:
            raise HTTPException(status_code=400, detail="No patient data or unstructured note provided.")

    # 3. Execute pipeline
    result = orchestrator.run_pipeline(
        protocol_content=protocol_text,
        patient_input=patient_input,
        protocol_id=req.protocol_id or "ONCO-2026-X",
        patient_format=patient_format
    )

    run_id = result["run_id"]

    # 4. Save PDF to disk
    pdf_bytes = result.pop("pdf_bytes", None)
    if pdf_bytes:
        pdf_file = DOSSIERS_DIR / f"{run_id}.pdf"
        with open(pdf_file, "wb") as f:
            f.write(pdf_bytes)

    # 5. Save JSON dossier to disk
    json_file = DOSSIERS_DIR / f"{run_id}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result["audit_dossier"], f, indent=2)

    # 6. Persist to SQLite
    save_screening_run(run_id, result)

    return result


@router.get("/history")
def get_history():
    """Lists recent screening execution runs."""
    return list_screening_runs(limit=30)


@router.get("/run/{run_id}")
def get_run_details(run_id: str):
    """Fetches full details of a screening run."""
    run = get_screening_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found.")
    return run
