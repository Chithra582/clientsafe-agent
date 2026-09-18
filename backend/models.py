"""Pydantic schemas for request validation and response models."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ScreeningRequest(BaseModel):
    protocol_text: Optional[str] = Field(None, description="Clinical trial protocol text")
    protocol_id: str = Field("ONCO-2026-X", description="Protocol identifier")
    patient_data: Optional[Dict[str, Any]] = Field(None, description="Structured patient JSON")
    patient_raw_text: Optional[str] = Field(None, description="Unstructured patient clinical progress note")
    preset_patient_id: Optional[str] = Field(None, description="Preset ID: 'patient_01', 'patient_02', or 'patient_03'")


class IngestResponse(BaseModel):
    status: str
    document_type: str
    extracted_length: int
    sample_text: str


class WebhookPayload(BaseModel):
    event_type: str
    patient_pseudonym: str
    confidence: str
    threshold_required: str
    status: str
    urgency: str
    reasons: List[str]
    missing_criteria: List[str] = []
    failed_criteria: List[str] = []
    ambiguities: List[Any] = []
    action_required: str
