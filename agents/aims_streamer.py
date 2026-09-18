"""Lyzr AIMS (Agent Intelligence Management System) Event Streamer.

Logs and streams structured events representing:
1. Environment Layer (Protocol & EHR Ingestion sandbox)
2. Agent Layer (PHI Scrubber, Criteria Agent, Screening Agent, Medical Safety Agent, Audit Agent)
3. Inference & Compliance Layer (Tokens, Latency, Zero PHI verification, FDA Part 11 Audit Trail)
"""

import os
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class AimsStreamer:
    """Manages Lyzr AIMS event telemetry and persistent event streaming."""

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "aims_events.jsonl"
        )
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.memory_events: List[Dict[str, Any]] = []

    def emit_event(
        self,
        run_id: str,
        triad_layer: str,
        agent_name: str,
        event_type: str,
        payload: Dict[str, Any],
        tokens_used: int = 0,
        latency_ms: float = 0.0,
        compliance_status: str = "COMPLIANT"
    ) -> Dict[str, Any]:
        """Emits an immutable telemetry event formatted for Lyzr AIMS."""
        event = {
            "event_id": f"aims-evt-{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "triad_layer": triad_layer,  # ENVIRONMENT, AGENT, INFERENCE, GOVERNANCE
            "agent_name": agent_name,
            "event_type": event_type,
            "tokens_used": tokens_used,
            "latency_ms": round(latency_ms, 2),
            "compliance_status": compliance_status,
            "payload": payload
        }

        self.memory_events.append(event)

        # Append to persistent JSONL stream
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            print(f"[AIMS] Failed writing event to disk: {e}")

        return event

    def get_run_events(self, run_id: str) -> List[Dict[str, Any]]:
        """Returns all AIMS events associated with a specific screening execution."""
        return [e for e in self.memory_events if e.get("run_id") == run_id]

    def get_latest_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent events across runs."""
        # Read from file if memory is empty
        if not self.memory_events and os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            self.memory_events.append(json.loads(line.strip()))
            except Exception:
                pass
        return self.memory_events[-limit:]
