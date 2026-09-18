"""Unit tests for Protocol Criteria Agent."""

import os
import pytest
from agents.protocol_criteria_agent import ProtocolCriteriaAgent


@pytest.fixture
def criteria_agent():
    return ProtocolCriteriaAgent()


def test_extract_criteria_from_protocol_text(criteria_agent):
    sample_protocol = """
    SECTION 4.1: INCLUSION CRITERIA (Page 4)
    INC-1: Age >= 18 years at time of consent.
    INC-2: Stage IV Non-Small Cell Lung Cancer (NSCLC).
    INC-3: ECOG Performance Status score of 0 or 1.
    INC-4: Adequate renal function: eGFR >= 50 mL/min/1.73m2.
    INC-5: ANC >= 1500 cells/uL, Platelets >= 100,000 /uL, Hemoglobin >= 9.0 g/dL.
    INC-6: Total Bilirubin <= 1.5x ULN, ALT <= 2.5x ULN.
    INC-7: Washout period of at least 28 days (>= 28 days) from prior chemotherapy.

    SECTION 4.2: EXCLUSION CRITERIA (Page 5)
    EXC-1: Active brain metastases.
    EXC-2: Active autoimmune disease requiring systemic immunosuppressive therapy.
    EXC-3: Unstable cardiac disease: NYHA Class III or IV heart failure.
    EXC-6: Uncontrolled glycemic status: HbA1c >= 8.5%.
    """

    res = criteria_agent.extract_criteria(sample_protocol, protocol_id="ONCO-TEST")

    assert res["protocol_id"] == "ONCO-TEST"
    assert res["total_rules"] >= 10
    assert res["inclusion_count"] >= 7
    assert res["exclusion_count"] >= 3

    # Check normalized structure of eGFR rule
    egfr_rule = next(r for r in res["criteria_rules"] if r["field"] == "eGFR")
    assert egfr_rule["type"] == "inclusion"
    assert egfr_rule["op"] in [">=", ">"]
    assert egfr_rule["value"] == 50.0
    assert egfr_rule["source_page"] in [4, 5]


def test_pdf_parsing_fallback(criteria_agent):
    pdf_path = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic_samples", "protocol_nsclc_phase3.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        extracted = criteria_agent.parse_pdf_bytes(pdf_bytes)
        assert len(extracted) > 100
        assert "INCLUSION" in extracted.upper()
