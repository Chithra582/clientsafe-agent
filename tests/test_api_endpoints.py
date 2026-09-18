"""Comprehensive API integration tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "Environment Layer" in data["triad_architecture"]


def test_api_presets():
    res = client.get("/api/ingest/presets")
    assert res.status_code == 200
    data = res.json()
    assert len(data["presets"]) == 3
    assert data["protocol_id"] == "ONCO-2026-X"


def test_api_screen_preset_patient_1():
    res = client.post("/api/screen/run", json={"preset_patient_id": "patient_01"})
    assert res.status_code == 200
    data = res.json()
    assert data["final_decision"] == "ELIGIBLE"
    assert data["confidence_percentage"] >= 90.0
    assert data["hitl_pause_triggered"] is False

    run_id = data["run_id"]

    # Test PDF download
    res_pdf = client.get(f"/api/dossier/{run_id}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    # Test JSON dossier
    res_json = client.get(f"/api/dossier/{run_id}/json")
    assert res_json.status_code == 200
    assert res_json.json()["audit_run_id"] == run_id


def test_api_screen_preset_patient_2():
    res = client.post("/api/screen/run", json={"preset_patient_id": "patient_02"})
    assert res.status_code == 200
    data = res.json()
    assert data["final_decision"] == "INELIGIBLE"
    assert data["medical_safety"]["safety_decision"] == "CONTRAINDICATION_FLAGGED"


def test_api_screen_preset_patient_3_hitl():
    res = client.post("/api/screen/run", json={"preset_patient_id": "patient_03"})
    assert res.status_code == 200
    data = res.json()
    assert data["final_decision"] == "REQUIRES_HUMAN_OVERVIEW"
    assert data["confidence_percentage"] < 90.0
    assert data["hitl_pause_triggered"] is True


def test_api_aims_endpoints():
    res_evts = client.get("/api/aims/events")
    assert res_evts.status_code == 200
    assert isinstance(res_evts.json(), list)

    res_stats = client.get("/api/aims/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "total_screened_patients" in stats
    assert "fda_part_11_compliance_rate" in stats


def test_api_webhook_logging():
    payload = {
        "event_type": "CLINICAL_HITL_PAUSE_TRIGGERED",
        "patient_pseudonym": "SUBJ-API-TEST",
        "confidence": "68.5%",
        "threshold_required": "90.0%",
        "status": "REQUIRES_HUMAN_OVERVIEW",
        "urgency": "HIGH",
        "reasons": ["Missing Platelets lab"],
        "missing_criteria": ["INC-5B"],
        "action_required": "Coordinator review required."
    }
    res_post = client.post("/api/webhook/hitl", json=payload)
    assert res_post.status_code == 200
    assert res_post.json()["status"] == "received"

    res_logs = client.get("/api/webhook/logs")
    assert res_logs.status_code == 200
    assert any(log["patient_pseudonym"] == "SUBJ-API-TEST" for log in res_logs.json())
