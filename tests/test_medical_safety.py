"""Unit tests for Medical Safety Agent & Ontology Lookups."""

import pytest
from agents.medical_safety_agent import MedicalSafetyAgent


@pytest.fixture
def safety_agent():
    return MedicalSafetyAgent()


def test_safety_check_clean_patient(safety_agent):
    patient = {
        "clinical_profile": {
            "icd10_code": "C34.90",
            "snomed_concept_id": "254637007",
            "autoimmune_conditions": [],
            "prior_systemic_therapies": [{"regimen": "Carbo/Pem", "days_since_completion": 45}],
            "lab_biomarkers": {
                "eGFR": {"value": 72.0, "unit": "mL/min", "loinc": "33914-3"}
            }
        }
    }

    res = safety_agent.perform_safety_audit(patient)

    assert res["safety_decision"] == "SAFE"
    assert res["contraindications_count"] == 0
    assert res["safety_score"] == 1.0


def test_safety_check_active_contraindication(safety_agent):
    # Patient with Ulcerative Colitis (ICD-10 K50.90 / SNOMED 40103004)
    patient = {
        "clinical_profile": {
            "icd10_code": "C34.90",
            "autoimmune_conditions": [
                {
                    "condition": "Active Ulcerative Colitis",
                    "icd10": "K50.90",
                    "snomed": "40103004"
                }
            ],
            "lab_biomarkers": {
                "eGFR": {"value": 38.0, "loinc": "33914-3"}
            }
        }
    }

    res = safety_agent.perform_safety_audit(patient)

    assert res["safety_decision"] == "CONTRAINDICATION_FLAGGED"
    assert res["contraindications_count"] >= 1
    assert res["safety_score"] < 0.60


def test_safety_check_borderline_ambiguity(safety_agent):
    # Patient with eGFR 51 (near cutoff 50) and washout 24 days
    patient = {
        "clinical_profile": {
            "icd10_code": "C34.90",
            "autoimmune_conditions": [],
            "prior_systemic_therapies": [{"regimen": "Nivolumab", "days_since_completion": 24}],
            "lab_biomarkers": {
                "eGFR": {"value": 51.0, "loinc": "33914-3"}
            }
        }
    }

    res = safety_agent.perform_safety_audit(patient)

    assert res["safety_decision"] == "AMBIGUOUS_SAFETY_RISK"
    assert res["ambiguous_count"] >= 1
