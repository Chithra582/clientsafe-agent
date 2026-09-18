"""Unit tests for Confidence Scorer and HITL Governance Agent."""

import pytest
from agents.confidence_scorer import ConfidenceScorer


@pytest.fixture
def scorer():
    return ConfidenceScorer()


def test_high_confidence_eligible(scorer):
    scr_res = {"overall_decision": "ELIGIBLE", "unknown_count": 0}
    saf_res = {"safety_decision": "SAFE", "ambiguous_count": 0}

    res = scorer.calculate_confidence(scr_res, saf_res, patient_id="SUBJ-001")

    assert res["confidence_percentage"] == 100.0
    assert res["governed_status"] == "ELIGIBLE"
    assert res["hitl_pause_triggered"] is False


def test_high_certainty_ineligible(scorer):
    scr_res = {"overall_decision": "INELIGIBLE", "unknown_count": 0}
    saf_res = {"safety_decision": "CONTRAINDICATION_FLAGGED", "ambiguous_count": 0}

    res = scorer.calculate_confidence(scr_res, saf_res, patient_id="SUBJ-002")

    assert res["confidence_percentage"] >= 95.0
    assert res["governed_status"] == "INELIGIBLE"
    assert res["hitl_pause_triggered"] is False


def test_penalties_trigger_hitl_pause_below_90(scorer):
    # 1 missing field (-15%) + 2 ambiguous risks (-24%) + uncertain base (82%) -> ~43%
    scr_res = {"overall_decision": "REQUIRES_HUMAN_OVERVIEW", "unknown_count": 1}
    saf_res = {"safety_decision": "AMBIGUOUS_SAFETY_RISK", "ambiguous_count": 2}

    res = scorer.calculate_confidence(scr_res, saf_res, patient_id="SUBJ-003")

    assert res["confidence_percentage"] < 90.0
    assert res["governed_status"] == "REQUIRES_HUMAN_OVERVIEW"
    assert res["hitl_pause_triggered"] is True
    assert res["webhook_event"] is not None
    assert res["webhook_event"]["event_type"] == "CLINICAL_HITL_PAUSE_TRIGGERED"
