"""HITL (Human-In-The-Loop) Webhook Receiver and logs."""

import uuid
from fastapi import APIRouter
from backend.models import WebhookPayload
from backend.database import save_webhook_event, list_webhook_events

router = APIRouter(prefix="/api/webhook", tags=["HITL Webhook"])


@router.post("/hitl")
def receive_hitl_webhook(payload: WebhookPayload):
    """Simulates receiving an external HITL pause notification (Slack / Teams / PagerDuty webhook)."""
    event_id = f"wh-{uuid.uuid4().hex[:10]}"
    save_webhook_event(
        event_id=event_id,
        event_type=payload.event_type,
        patient_id=payload.patient_pseudonym,
        confidence=payload.confidence,
        payload=payload.model_dump()
    )
    return {
        "status": "received",
        "event_id": event_id,
        "message": f"HITL pause logged for subject {payload.patient_pseudonym}. Clinical coordinator notified."
    }


@router.get("/logs")
def get_webhook_logs(limit: int = 20):
    """Retrieves list of received HITL pause events."""
    return list_webhook_events(limit=limit)
