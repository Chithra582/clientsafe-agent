"""Unit tests for Deterministic Screening Agent."""

import pytest
from agents.screening_agent import ScreeningAgent


@pytest.fixture
def screening_agent():
    return ScreeningAgent()


@pytest.fixture
def sample_rules():
    return [
        {"criterion_id": "INC-1", "type": "inclusion", "field": "age", "op": ">=", "value": 18.0, "unit": "years", "source_page": 4},
        {"criterion_id": "INC-4", "type": "inclusion", "field": "eGFR", "op": ">=", "value": 50.0, "unit": "mL/min", "source_page": 4},
        {"criterion_id": "INC-5B", "type": "inclusion", "field": "Platelets", "op": ">=", "value": 100000.0, "unit": "/uL", "source_page": 4},
        {"criterion_id": "EXC-2", "type": "exclusion", "field": "autoimmune_disease", "op": "==", "value": True, "unit": None, "source_page": 5},
    ]


def test_deterministic_evaluation_eligible(screening_agent, sample_rules):
    patient = {
        "age": 55,
        "clinical_profile": {
            "autoimmune_disease": False,
            "lab_biomarkers": {
                "eGFR": {"value": 75.0},
                "Platelets": {"value": 220000.0}
            }
        }
    }

    res = screening_agent.evaluate_patient(patient, sample_rules)

    assert res["overall_decision"] == "ELIGIBLE"
    assert res["passed_count"] == 4
    assert res["failed_count"] == 0
    assert res["unknown_count"] == 0


def test_deterministic_evaluation_ineligible_threshold_failure(screening_agent, sample_rules):
    # Patient fails eGFR (38 < 50) and has autoimmune disease
    patient = {
        "age": 62,
        "clinical_profile": {
            "autoimmune_disease": True,
            "lab_biomarkers": {
                "eGFR": {"value": 38.0},
                "Platelets": {"value": 180000.0}
            }
        }
    }

    res = screening_agent.evaluate_patient(patient, sample_rules)

    assert res["overall_decision"] == "INELIGIBLE"
    assert "INC-4" in res["failed_criteria"]
    assert "EXC-2" in res["failed_criteria"]
    assert res["failed_count"] >= 2


def test_deterministic_evaluation_missing_fields(screening_agent, sample_rules):
    # Missing Platelets
    patient = {
        "age": 45,
        "clinical_profile": {
            "autoimmune_disease": False,
            "lab_biomarkers": {
                "eGFR": {"value": 65.0}
                # Platelets unrecorded
            }
        }
    }

    res = screening_agent.evaluate_patient(patient, sample_rules)

    assert res["overall_decision"] == "REQUIRES_HUMAN_OVERVIEW"
    assert "INC-5B" in res["unknown_criteria"]
    assert res["unknown_count"] == 1
