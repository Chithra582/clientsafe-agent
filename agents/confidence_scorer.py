"""Confidence Scorer & Human-In-The-Loop (HITL) Governance Agent.

Calculates composite confidence score based on agreement between
Deterministic Screening Agent and Medical Safety Agent, penalized for
missing/ambiguous fields.
Fires a simulated HITL webhook pause whenever confidence drops below 90%.
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional


class ConfidenceScorer:
    """Calculates governance confidence and enforces HITL gating."""

    def __init__(self, hitl_webhook_url: Optional[str] = None):
        self.webhook_url = hitl_webhook_url or os.getenv("HITL_WEBHOOK_URL", "http://localhost:8000/api/webhook/hitl")

    def calculate_confidence(
        self,
        screening_result: Dict[str, Any],
        safety_result: Dict[str, Any],
        patient_id: str = "SUBJ-ANON"
    ) -> Dict[str, Any]:
        """Calculates multi-agent agreement and confidence score."""
        scr_decision = screening_result.get("overall_decision", "UNKNOWN")
        safety_decision = safety_result.get("safety_decision", "UNKNOWN")
        unknown_count = screening_result.get("unknown_count", 0)
        ambiguous_count = safety_result.get("ambiguous_count", 0)

        # 1. Base agreement score
        if scr_decision == "ELIGIBLE" and safety_decision == "SAFE":
            base_score = 1.00
            agreement_type = "STRONG_CONVERGENT_ELIGIBLE"
        elif scr_decision == "INELIGIBLE" and safety_decision == "CONTRAINDICATION_FLAGGED":
            base_score = 0.98
            agreement_type = "STRONG_CONVERGENT_INELIGIBLE"
        elif scr_decision == "INELIGIBLE" and safety_decision == "SAFE":
            base_score = 0.95
            agreement_type = "CRITERIA_RULE_DISQUALIFICATION"
        elif scr_decision == "ELIGIBLE" and safety_decision == "CONTRAINDICATION_FLAGGED":
            base_score = 0.65
            agreement_type = "CRITICAL_SAFETY_DISAGREEMENT"
        elif scr_decision == "REQUIRES_HUMAN_OVERVIEW" or safety_decision == "AMBIGUOUS_SAFETY_RISK":
            base_score = 0.82
            agreement_type = "UNCERTAIN_INPUTS"
        else:
            base_score = 0.70
            agreement_type = "MODERATE_AGREEMENT"

        # 2. Penalties
        missing_penalty = unknown_count * 0.15
        ambiguity_penalty = ambiguous_count * 0.12

        total_penalty = missing_penalty + ambiguity_penalty
        final_confidence = max(0.10, min(1.00, base_score - total_penalty))
        final_confidence_pct = round(final_confidence * 100, 1)

        # 3. HITL Gating Threshold: 90%
        hitl_pause_triggered = final_confidence_pct < 90.0

        if hitl_pause_triggered:
            governed_status = "REQUIRES_HUMAN_OVERVIEW"
        else:
            governed_status = scr_decision

        reasons = []
        if unknown_count > 0:
            reasons.append(f"{unknown_count} critical biomarker/clinical field(s) unrecorded or missing.")
        if ambiguous_count > 0:
            reasons.append(f"{ambiguous_count} borderline or ambiguous clinical/washout boundary condition(s) detected.")
        if agreement_type == "CRITICAL_SAFETY_DISAGREEMENT":
            reasons.append("Screening criteria passed but medical safety agent identified active contraindications.")

        webhook_event = None
        if hitl_pause_triggered:
            webhook_event = self._fire_hitl_webhook(
                patient_id=patient_id,
                confidence_pct=final_confidence_pct,
                governed_status=governed_status,
                reasons=reasons,
                screening_result=screening_result,
                safety_result=safety_result
            )

        return {
            "confidence_score": round(final_confidence, 4),
            "confidence_percentage": final_confidence_pct,
            "governed_status": governed_status,
            "hitl_pause_triggered": hitl_pause_triggered,
            "agreement_type": agreement_type,
            "penalties": {
                "missing_fields_penalty": round(missing_penalty, 2),
                "ambiguity_penalty": round(ambiguity_penalty, 2),
                "total_deductions": round(total_penalty, 2)
            },
            "reasons_for_flag": reasons,
            "webhook_event": webhook_event
        }

    def _fire_hitl_webhook(
        self,
        patient_id: str,
        confidence_pct: float,
        governed_status: str,
        reasons: List[str],
        screening_result: Dict[str, Any],
        safety_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Dispatches simulated Slack/Teams-ready HITL webhook payload."""
        payload = {
            "event_type": "CLINICAL_HITL_PAUSE_TRIGGERED",
            "patient_pseudonym": patient_id,
            "confidence": f"{confidence_pct}%",
            "threshold_required": "90.0%",
            "status": governed_status,
            "urgency": "HIGH",
            "reasons": reasons,
            "missing_criteria": screening_result.get("unknown_criteria", []),
            "failed_criteria": screening_result.get("failed_criteria", []),
            "ambiguities": safety_result.get("ambiguous_safety_risks", []),
            "action_required": "Clinical Research Coordinator (CRC) must inspect patient dossier and confirm manual override or repeat testing."
        }

        # Attempt sending to local or remote webhook endpoint asynchronously or silently
        try:
            requests.post(self.webhook_url, json=payload, timeout=2.0)
        except Exception:
            # Non-blocking if server is starting or endpoint not up yet
            pass

        return payload
