"""Automated test suite for Governed Clinical Trial Screening Agent."""

import json
import os
import pytest
from agents.orchestrator import ClinicalScreeningOrchestrator
from agents.phi_scrubber_agent import PhiScrubberAgent
from agents.medical_safety_agent import MedicalSafetyAgent


@pytest.fixture
def orchestrator():
    return ClinicalScreeningOrchestrator()


@pytest.fixture
def protocol_text():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_samples", "protocol_nsclc_phase3.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_phi_scrubber_redacts_all_identifiers():
    scrubber = PhiScrubberAgent()
    sample_text = """
    Patient Name: Jonathan Vance, DOB: 1965-06-14
    MRN: MRN-8849201, SSN: 948-12-8841
    Address: 482 Elmhurst Road, Boston, MA 02115
    Phone: +1-555-382-9104, Email: jvance.boston@medmail.org
    Doctor: Dr. Aris Thorne, MD at Massachusetts General Oncology Center
    """
    res = scrubber.scrub_text(sample_text)
    assert res["zero_phi_leakage"] is True
    assert "Jonathan Vance" not in res["sanitized_text"]
    assert "948-12-8841" not in res["sanitized_text"]
    assert "MRN-8849201" not in res["sanitized_text"]
    assert "jvance.boston@medmail.org" not in res["sanitized_text"]
    assert "+1-555-382-9104" not in res["sanitized_text"]
    assert res["entities_count"] >= 5


def test_patient_1_clearly_eligible(orchestrator, protocol_text):
    path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_samples", "patient_01_eligible.json")
    with open(path, "r", encoding="utf-8") as f:
        patient_data = json.load(f)

    result = orchestrator.run_pipeline(protocol_text, patient_data)

    assert result["final_decision"] == "ELIGIBLE"
    assert result["confidence_percentage"] >= 90.0
    assert result["hitl_pause_triggered"] is False
    assert result["screening_evaluation"]["failed_count"] == 0
    assert result["screening_evaluation"]["unknown_count"] == 0
    assert len(result["pdf_bytes"]) > 1000
    assert result["phi_scrubbing"]["zero_phi_leakage"] is True


def test_patient_2_clearly_ineligible(orchestrator, protocol_text):
    path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_samples", "patient_02_ineligible.json")
    with open(path, "r", encoding="utf-8") as f:
        patient_data = json.load(f)

    result = orchestrator.run_pipeline(protocol_text, patient_data)

    assert result["final_decision"] == "INELIGIBLE"
    assert result["screening_evaluation"]["failed_count"] >= 2
    # eGFR (INC-4) and ECOG (INC-3) must fail
    failed = result["screening_evaluation"]["failed_criteria"]
    assert "INC-3" in failed or "INC-4" in failed or "EXC-2" in failed
    # Medical safety should flag Ulcerative colitis contraindication
    assert result["medical_safety"]["safety_decision"] == "CONTRAINDICATION_FLAGGED"


def test_patient_3_borderline_triggers_hitl_pause(orchestrator, protocol_text):
    path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_samples", "patient_03_borderline.json")
    with open(path, "r", encoding="utf-8") as f:
        patient_data = json.load(f)

    result = orchestrator.run_pipeline(protocol_text, patient_data)

    # Borderline: missing Platelet count + 25 day washout + eGFR 51
    assert result["final_decision"] == "REQUIRES_HUMAN_OVERVIEW"
    assert result["confidence_percentage"] < 90.0
    assert result["hitl_pause_triggered"] is True
    assert "INC-5B" in result["screening_evaluation"]["unknown_criteria"]


def test_unstructured_clinical_note_ingestion(orchestrator, protocol_text):
    path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_samples", "patient_01_note.txt")
    with open(path, "r", encoding="utf-8") as f:
        note_text = f.read()

    result = orchestrator.run_pipeline(protocol_text, note_text, patient_format="text")

    assert result["phi_scrubbing"]["zero_phi_leakage"] is True
    assert result["final_decision"] == "ELIGIBLE"
    assert len(result["pdf_bytes"]) > 1000
