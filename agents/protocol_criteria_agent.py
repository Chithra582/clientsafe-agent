"""Protocol Criteria Agent.

Parses clinical trial protocol documents (PDF or text) and extracts
structured inclusion/exclusion criteria with exact source citations.
Separates Agent Reasoning from Deterministic Execution.
"""

import io
from typing import Dict, Any, List, Optional
import pdfplumber
import pypdf

from agents.llm_interface import LLMInterface


class ProtocolCriteriaAgent:
    """Extracts inclusion and exclusion criteria into structured JSON rules."""

    def __init__(self, llm_interface: Optional[LLMInterface] = None):
        self.llm = llm_interface or LLMInterface()

    def parse_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extracts text from PDF bytes using pdfplumber with pypdf fallback."""
        text_content = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for idx, page in enumerate(pdf.pages, start=1):
                    p_text = page.extract_text() or ""
                    text_content.append(f"--- [Page {idx}] ---\n{p_text}")
            return "\n\n".join(text_content)
        except Exception as e:
            # Fallback to pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for idx, page in enumerate(reader.pages, start=1):
                p_text = page.extract_text() or ""
                text_content.append(f"--- [Page {idx}] ---\n{p_text}")
            return "\n\n".join(text_content)

    def extract_criteria(self, protocol_content: str, protocol_id: str = "PROTOCOL-ONCO-2026") -> Dict[str, Any]:
        """Extracts structured inclusion & exclusion criteria rules from protocol text."""
        raw_rules = self.llm.extract_criteria_from_protocol(protocol_content)

        inclusion_criteria = []
        exclusion_criteria = []

        for rule in raw_rules:
            # Normalize schema
            normalized_rule = {
                "criterion_id": rule.get("criterion_id", "CRIT-UNKNOWN"),
                "type": rule.get("type", "inclusion").lower(),
                "category": rule.get("category", "biomarker"),
                "field": rule.get("field", ""),
                "op": rule.get("op", ">="),
                "value": rule.get("value"),
                "unit": rule.get("unit"),
                "source_page": rule.get("source_page", 4),
                "original_text": rule.get("original_text", "")
            }

            if normalized_rule["type"] == "exclusion":
                exclusion_criteria.append(normalized_rule)
            else:
                inclusion_criteria.append(normalized_rule)

        return {
            "protocol_id": protocol_id,
            "total_rules": len(raw_rules),
            "inclusion_count": len(inclusion_criteria),
            "exclusion_count": len(exclusion_criteria),
            "criteria_rules": raw_rules,
            "inclusion_criteria": inclusion_criteria,
            "exclusion_criteria": exclusion_criteria,
            "extraction_source": self.llm.get_active_provider()
        }
