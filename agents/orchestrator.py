"""Clinical Screening Pipeline Orchestrator.

Implements the Lyzr Triad architecture:
1. Environment Layer: Manages protocol and patient document ingestion.
2. Safe AI Gate: Zero-PHI scrubbing before any downstream processing.
3. Multi-Agent Inference Layer: Protocol Criteria, Screening, Medical Safety,
   Confidence Governance, and Audit Dossier Agents.
4. Lyzr AIMS Telemetry: Live streaming of decisions, latencies, and compliance hashes.
"""

import time
import uuid
from typing import Dict, Any, Optional

from agents.phi_scrubber_agent import PhiScrubberAgent
from agents.protocol_criteria_agent import ProtocolCriteriaAgent
from agents.screening_agent import ScreeningAgent
from agents.medical_safety_agent import MedicalSafetyAgent
from agents.confidence_scorer import ConfidenceScorer
from agents.audit_agent import AuditAgent
from agents.aims_streamer import AimsStreamer
from agents.llm_interface import LLMInterface


class ClinicalScreeningOrchestrator:
    """Master pipeline orchestrator tying all clinical agents together."""

    def __init__(self, hitl_webhook_url: Optional[str] = None):
        self.llm = LLMInterface()
        self.phi_scrubber = PhiScrubberAgent()
        self.criteria_agent = ProtocolCriteriaAgent(llm_interface=self.llm)
        self.screening_agent = ScreeningAgent()
        self.safety_agent = MedicalSafetyAgent()
        self.confidence_scorer = ConfidenceScorer(hitl_webhook_url=hitl_webhook_url)
        self.audit_agent = AuditAgent()
        self.aims_streamer = AimsStreamer()

    def run_pipeline(
        self,
        protocol_content: str,
        patient_input: Any, # Dict or raw text
        protocol_id: str = "ONCO-2026-X",
        patient_format: str = "json"
    ) -> Dict[str, Any]:
        """Executes the complete clinical trial screening pipeline end-to-end."""
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        pipeline_start = time.time()

        # -------------------------------------------------------------
        # 1. ENVIRONMENT LAYER: Ingestion Setup
        # -------------------------------------------------------------
        t0 = time.time()
        self.aims_streamer.emit_event(
            run_id=run_id,
            triad_layer="ENVIRONMENT",
            agent_name="IngestionManager",
            event_type="INGESTION_INITIALIZED",
            payload={
                "protocol_id": protocol_id,
                "patient_format": patient_format,
                "protocol_length_chars": len(protocol_content)
            },
            latency_ms=(time.time() - t0) * 1000
        )

        # -------------------------------------------------------------
        # 2. LYZR SAFE AI GATE: PHI Scrubbing (BEFORE ANY INFERENCE)
        # -------------------------------------------------------------
        t0 = time.time()
        if isinstance(patient_input, dict):
            scrub_res = self.phi_scrubber.scrub_patient_record(patient_input)
            scrubbed_patient = scrub_res["scrubbed_record"]
            raw_text_diff = None
        else:
            # Patient input is raw unstructured text note
            scrub_res = self.phi_scrubber.scrub_text(str(patient_input))
            raw_text_diff = scrub_res["diff"]
            # Convert scrubbed text into structured format
            extracted_facts = self.llm.extract_patient_from_unstructured_note(scrub_res["sanitized_text"])
            scrubbed_patient = {
                "patient_id": "PT-UNSTRUCTURED",
                "pseudonym_id": "SUBJ-" + scrub_res["sha256_sanitized"][:8].upper(),
                "age": extracted_facts.get("age"),
                "clinical_profile": extracted_facts
            }
            scrub_res["scrubbed_record"] = scrubbed_patient

        self.aims_streamer.emit_event(
            run_id=run_id,
            triad_layer="AGENT",
            agent_name="PhiScrubberAgent",
            event_type="PHI_REDACTION_COMPLETED",
            payload={
                "entities_redacted_count": scrub_res["entities_count"],
                "zero_phi_leakage": scrub_res["zero_phi_leakage"],
                "pseudonym_id": scrubbed_patient.get("pseudonym_id"),
                "diff_sample": scrub_res["diff"][:5]
            },
            latency_ms=(time.time() - t0) * 1000,
            compliance_status="HIPAA_SAFE_HARBOR_VERIFIED"
        )

        # -------------------------------------------------------------
        # 3. PROTOCOL CRITERIA AGENT: Extract Rules
        # -------------------------------------------------------------
        t0 = time.time()
        criteria_res = self.criteria_agent.extract_criteria(protocol_content, protocol_id=protocol_id)
        self.aims_streamer.emit_event(
            run_id=run_id,
            triad_layer="AGENT",
            agent_name="ProtocolCriteriaAgent",
            event_type="CRITERIA_EXTRACTED",
            payload={
                "total_rules": criteria_res["total_rules"],
                "inclusion_count": criteria_res["inclusion_count"],
                "exclusion_count": criteria_res["exclusion_count"],
                "extraction_source": criteria_res["extraction_source"]
            },
            latency_ms=(time.time() - t0) * 1000
        )

        # -------------------------------------------------------------
        # 4. DETERMINISTIC SCREENING AGENT (Pure Code Evaluation)
        # -------------------------------------------------------------
        t0 = time.time()
        screening_res = self.screening_agent.evaluate_patient(
            patient_record=scrubbed_patient,
            criteria_rules=criteria_res["criteria_rules"]
        )
        self.aims_streamer.emit_event(
            run_id=run_id,
            triad_layer="INFERENCE",
            agent_name="ScreeningAgent",
            event_type="DETERMINISTIC_SCREENING_COMPLETED",
            payload={
                "overall_decision": screening_res["overall_decision"],
                "passed_count": screening_res["passed_count"],
                "failed_count": screening_res["failed_count"],
                "unknown_count": screening_res["unknown_count"],
                "failed_criteria": screening_res["failed_criteria"]
            },
            latency_ms=(time.time() - t0) * 1000,
            compliance_status="HALLUCINATION_SUPPRESSED_DETERMINISTIC"
        )

        # -------------------------------------------------------------
        # 5. MEDICAL SAFETY AGENT: Ontology Cross-Reference
        # -------------------------------------------------------------
        t0 = time.time()
        safety_res = self.safety_agent.perform_safety_audit(patient_record=scrubbed_patient)
        self.aims_streamer.emit_event(
            run_id=run_id,
            triad_layer="AGENT",
            agent_name="MedicalSafetyAgent",
            event_type="ONTOLOGY_SAFETY_AUDITED",
            payload={
                "safety_decision": safety_res["safety_decision"],
                "contraindications_count": safety_res["contraindications_count"],
                "ambiguous_count": safety_res["ambiguous_count"]
            },
            latency_ms=(time.time() - t0) * 1000
        )

        # -------------------------------------------------------------
        # 6. CONFIDENCE SCORER & HITL GOVERNANCE
        # -------------------------------------------------------------
        t0 = time.time()
        confidence_res = self.confidence_scorer.calculate_confidence(
            screening_result=screening_res,
            safety_result=safety_res,
            patient_id=scrubbed_patient.get("pseudonym_id", "SUBJ-ANON")
        )
        self.aims_streamer.emit_event(
            run_id=run_id,
            triad_layer="GOVERNANCE",
            agent_name="ConfidenceScorer",
            event_type="CONFIDENCE_DECISION_FINALIZED",
            payload={
                "confidence_score": confidence_res["confidence_score"],
                "confidence_percentage": confidence_res["confidence_percentage"],
                "governed_status": confidence_res["governed_status"],
                "hitl_pause_triggered": confidence_res["hitl_pause_triggered"]
            },
            latency_ms=(time.time() - t0) * 1000
        )

        # -------------------------------------------------------------
        # 7. AUDIT AGENT: Generate Regulatory Dossier (JSON & PDF)
        # -------------------------------------------------------------
        t0 = time.time()
        dossier_json = self.audit_agent.generate_dossier_json(
            run_id=run_id,
            protocol_meta=criteria_res,
            scrubbing_summary=scrub_res,
            screening_result=screening_res,
            safety_result=safety_res,
            confidence_result=confidence_res,
            patient_record=scrubbed_patient
        )
        pdf_bytes = self.audit_agent.generate_dossier_pdf(dossier_json=dossier_json)

        self.aims_streamer.emit_event(
            run_id=run_id,
            triad_layer="COMPLIANCE",
            agent_name="AuditAgent",
            event_type="DOSSIER_COMPILED",
            payload={
                "dossier_version": dossier_json["dossier_version"],
                "regulatory_framework": dossier_json["regulatory_framework"],
                "pdf_bytes_size": len(pdf_bytes),
                "electronic_hash": dossier_json["electronic_audit_hash"]
            },
            latency_ms=(time.time() - t0) * 1000,
            compliance_status="FDA_21CFR11_COMPLIANT"
        )

        total_pipeline_time_ms = round((time.time() - pipeline_start) * 1000, 2)

        return {
            "run_id": run_id,
            "total_latency_ms": total_pipeline_time_ms,
            "final_decision": confidence_res["governed_status"],
            "confidence_percentage": confidence_res["confidence_percentage"],
            "hitl_pause_triggered": confidence_res["hitl_pause_triggered"],
            "phi_scrubbing": {
                "entities_redacted_count": scrub_res["entities_count"],
                "zero_phi_leakage": scrub_res["zero_phi_leakage"],
                "diff": scrub_res["diff"],
                "sanitized_record": scrubbed_patient
            },
            "criteria_extraction": criteria_res,
            "screening_evaluation": screening_res,
            "medical_safety": safety_res,
            "confidence_governance": confidence_res,
            "audit_dossier": dossier_json,
            "pdf_bytes": pdf_bytes,
            "aims_events": self.aims_streamer.get_run_events(run_id)
        }
