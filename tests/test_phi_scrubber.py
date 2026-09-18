"""Comprehensive unit tests for PHI Scrubbing Agent (Lyzr Safe AI Gate)."""

import pytest
from agents.phi_scrubber_agent import PhiScrubberAgent


@pytest.fixture
def scrubber():
    return PhiScrubberAgent()


def test_redaction_of_all_hipaa_identifiers(scrubber):
    raw_text = """
    Patient Name: Jonathan Vance, DOB: 1965-06-14, Age: 60
    MRN: MRN-8849201, SSN: 948-12-8841
    Address: 482 Elmhurst Road, Boston, MA 02115
    Phone: +1-555-382-9104, Email: jvance.boston@medmail.org
    Treating Physician: Dr. Aris Thorne, MD
    Facility: Massachusetts General Oncology Center
    """
    res = scrubber.scrub_text(raw_text)

    assert res["zero_phi_leakage"] is True
    assert res["safe_ai_certified"] is True
    assert res["entities_count"] >= 7

    # Ensure no raw identifiers remain in sanitized output
    assert "Jonathan Vance" not in res["sanitized_text"]
    assert "948-12-8841" not in res["sanitized_text"]
    assert "MRN-8849201" not in res["sanitized_text"]
    assert "+1-555-382-9104" not in res["sanitized_text"]
    assert "jvance.boston@medmail.org" not in res["sanitized_text"]
    assert "482 Elmhurst Road" not in res["sanitized_text"]
    assert "Dr. Aris Thorne" not in res["sanitized_text"]


def test_structured_json_patient_scrubbing(scrubber):
    patient_dict = {
        "patient_id": "PT-REAL-9942",
        "name": "Marcus A. Sterling",
        "dob": "1958-03-22",
        "mrn": "MRN-5510294",
        "ssn": "219-45-7712",
        "phone": "+1-555-749-1120",
        "email": "msterling@testdomain.com",
        "address": "1290 Oakwood Crest, Chicago, IL 60611",
        "treating_physician": "Dr. Brenda Chen, MD",
        "institution": "Northwestern Memorial Clinical Pavilion",
        "age": 68,
        "clinical_profile": {
            "ecog_performance_status": 2,
            "cns_status_notes": "Reviewed with Dr. Brenda Chen for patient Marcus A. Sterling"
        }
    }

    res = scrubber.scrub_patient_record(patient_dict)
    scrubbed = res["scrubbed_record"]

    assert scrubbed["name"] == "[PATIENT_NAME_REDACTED]"
    assert scrubbed["ssn"] == "[SSN_REDACTED]"
    assert scrubbed["mrn"] == "[MRN_REDACTED]"
    assert scrubbed["phone"] == "[PHONE_REDACTED]"
    assert scrubbed["email"] == "[EMAIL_REDACTED]"
    assert scrubbed["address"] == "[ADDRESS_REDACTED]"
    assert scrubbed["treating_physician"] == "[PHYSICIAN_REDACTED]"
    assert scrubbed["institution"] == "[HEALTHCARE_FACILITY_REDACTED]"

    # Check pseudonymization
    assert scrubbed["pseudonym_id"].startswith("SUBJ-")
    assert res["zero_phi_leakage"] is True
    assert res["entities_count"] >= 9


def test_empty_and_already_clean_text(scrubber):
    res_empty = scrubber.scrub_text("")
    assert res_empty["zero_phi_leakage"] is True
    assert res_empty["entities_count"] == 0

    clean_text = "Stage IV NSCLC patient with eGFR 68 mL/min and ANC 2800 cells/uL."
    res_clean = scrubber.scrub_text(clean_text)
    assert res_clean["zero_phi_leakage"] is True
    assert "eGFR 68" in res_clean["sanitized_text"]


def test_sha256_provenance_hashes(scrubber):
    text = "Patient Name: Eleanor Rigby-Hughes, MRN: MRN-3918402"
    res = scrubber.scrub_text(text)
    assert "sha256_original" in res
    assert "sha256_sanitized" in res
    assert res["sha256_original"] != res["sha256_sanitized"]
    assert len(res["sha256_sanitized"]) == 64
