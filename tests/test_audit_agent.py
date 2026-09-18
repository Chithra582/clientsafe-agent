"""Unit tests for Audit Agent (FDA 21 CFR Part 11 PDF & JSON)."""

import pytest
from agents.audit_agent import AuditAgent


@pytest.fixture
def audit_agent():
    return AuditAgent()


def test_dossier_json_generation(audit_agent):
    dossier = audit_agent.generate_dossier_json(
        run_id="RUN-TEST-001",
        protocol_meta={"protocol_id": "ONCO-2026-X", "total_rules": 12},
        scrubbing_summary={"sha256_sanitized": "abcdef123456", "entities_count": 8, "zero_phi_leakage": True},
        screening_result={"evaluations": [{"criterion_id": "INC-1", "status": "PASS", "reasoning": "Pass"}]},
        safety_result={"safety_decision": "SAFE", "contraindications_count": 0},
        confidence_result={"governed_status": "ELIGIBLE", "confidence_percentage": 100.0, "hitl_pause_triggered": False},
        patient_record={"pseudonym_id": "SUBJ-TEST01"}
    )

    assert dossier["audit_run_id"] == "RUN-TEST-001"
    assert dossier["dossier_version"] == "1.0-FDA-21CFR11"
    assert dossier["subject_provenance"]["zero_phi_leakage_certified"] is True
    assert dossier["electronic_signature"]["status"] == "SEALED_IMMUTABLE"


def test_dossier_pdf_generation_valid_bytes(audit_agent):
    dossier = audit_agent.generate_dossier_json(
        run_id="RUN-TEST-002",
        protocol_meta={"protocol_id": "ONCO-2026-X", "total_rules": 12},
        scrubbing_summary={"sha256_sanitized": "9876543210fedcba", "entities_count": 6, "zero_phi_leakage": True},
        screening_result={"evaluations": [{"criterion_id": "INC-1", "status": "PASS", "reasoning": "Age >= 18 validated"}]},
        safety_result={"safety_decision": "SAFE", "contraindications_count": 0},
        confidence_result={"governed_status": "ELIGIBLE", "confidence_percentage": 100.0, "hitl_pause_triggered": False},
        patient_record={"pseudonym_id": "SUBJ-TEST02"}
    )

    pdf_bytes = audit_agent.generate_dossier_pdf(dossier)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")
