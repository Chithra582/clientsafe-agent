"""Ingestion routes for clinical trial protocols and patient records."""

import json
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.config import UPLOADS_DIR, DATA_DIR
from agents.protocol_criteria_agent import ProtocolCriteriaAgent

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])
criteria_agent = ProtocolCriteriaAgent()


@router.post("/protocol")
async def ingest_protocol(file: UploadFile = File(...)):
    """Accepts protocol file (PDF or TXT) and extracts raw text."""
    contents = await file.read()
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        extracted_text = criteria_agent.parse_pdf_bytes(contents)
    elif filename.endswith(".txt") or filename.endswith(".json"):
        extracted_text = contents.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or TXT.")

    return {
        "status": "success",
        "filename": file.filename,
        "length_chars": len(extracted_text),
        "text_preview": extracted_text[:800],
        "extracted_text": extracted_text
    }


@router.post("/patient")
async def ingest_patient(file: UploadFile = File(...)):
    """Accepts patient file (JSON, TXT, or PDF) and parses content."""
    contents = await file.read()
    filename = file.filename.lower()

    if filename.endswith(".json"):
        try:
            parsed_json = json.loads(contents.decode("utf-8", errors="ignore"))
            return {
                "status": "success",
                "format": "json",
                "patient_data": parsed_json
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")
    elif filename.endswith(".pdf"):
        extracted_text = criteria_agent.parse_pdf_bytes(contents)
        return {
            "status": "success",
            "format": "text",
            "raw_text": extracted_text
        }
    else:
        text = contents.decode("utf-8", errors="ignore")
        return {
            "status": "success",
            "format": "text",
            "raw_text": text
        }


@router.get("/presets")
def get_presets():
    """Returns available synthetic demo presets for 1-click execution."""
    synthetic_dir = DATA_DIR / "synthetic_samples"

    presets = []
    preset_configs = [
        {
            "id": "patient_01",
            "name": "Patient 1: Jonathan Vance (Eligible)",
            "file_json": "patient_01_eligible.json",
            "file_txt": "patient_01_note.txt",
            "expected_decision": "ELIGIBLE",
            "clinical_summary": "60yo male, Stage IV NSCLC, ECOG 1, eGFR 68 mL/min, ANC 2800, Platelets 215k, Washout 47d, no autoimmune or cardiac risk.",
            "badge_color": "green"
        },
        {
            "id": "patient_02",
            "name": "Patient 2: Marcus A. Sterling (Ineligible)",
            "file_json": "patient_02_ineligible.json",
            "file_txt": "patient_02_note.txt",
            "expected_decision": "INELIGIBLE",
            "clinical_summary": "68yo male, Stage IV NSCLC, ECOG 2 (fails cutoff <=1), eGFR 38 mL/min (fails cutoff >=50), Active Ulcerative Colitis (fails autoimmune exclusion).",
            "badge_color": "red"
        },
        {
            "id": "patient_03",
            "name": "Patient 3: Eleanor Rigby-Hughes (Borderline / Ambiguous)",
            "file_json": "patient_03_borderline.json",
            "file_txt": "patient_03_note.txt",
            "expected_decision": "REQUIRES_HUMAN_OVERVIEW",
            "clinical_summary": "54yo female, eGFR 51 mL/min (borderline close to cutoff 50), prior nivolumab washout 25d (short of 28d), missing platelet count -> Triggers HITL pause.",
            "badge_color": "amber"
        }
    ]

    for p in preset_configs:
        json_path = synthetic_dir / p["file_json"]
        txt_path = synthetic_dir / p["file_txt"]
        p_data = None
        txt_data = None

        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                p_data = json.load(f)
        if txt_path.exists():
            with open(txt_path, "r", encoding="utf-8") as f:
                txt_data = f.read()

        presets.append({
            **p,
            "patient_data": p_data,
            "patient_note": txt_data
        })

    # Also load sample protocol text
    proto_path = synthetic_dir / "protocol_nsclc_phase3.txt"
    proto_text = ""
    if proto_path.exists():
        with open(proto_path, "r", encoding="utf-8") as f:
            proto_text = f.read()

    return {
        "presets": presets,
        "protocol_sample_text": proto_text,
        "protocol_id": "ONCO-2026-X"
    }
