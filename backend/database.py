"""SQLite database manager for persistent audit records and screening runs."""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from backend.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite schema for runs, dossiers, and webhook logs."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS screening_runs (
        run_id TEXT PRIMARY KEY,
        created_at TEXT,
        protocol_id TEXT,
        patient_pseudonym TEXT,
        final_decision TEXT,
        confidence_percentage REAL,
        hitl_pause_triggered INTEGER,
        entities_redacted_count INTEGER,
        zero_phi_leakage INTEGER,
        screening_summary TEXT,
        safety_summary TEXT,
        dossier_json TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS webhook_events (
        event_id TEXT PRIMARY KEY,
        created_at TEXT,
        event_type TEXT,
        patient_pseudonym TEXT,
        confidence TEXT,
        payload TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_screening_run(run_id: str, result_dict: Dict[str, Any]):
    """Persists completed screening run into SQLite."""
    conn = get_connection()
    cursor = conn.cursor()

    created_at = datetime.now(timezone.utc).isoformat()
    protocol_id = result_dict.get("criteria_extraction", {}).get("protocol_id", "UNKNOWN")
    patient_pseudonym = result_dict.get("audit_dossier", {}).get("subject_provenance", {}).get("pseudonym_id", "UNKNOWN")
    final_decision = result_dict.get("final_decision", "UNKNOWN")
    confidence_pct = result_dict.get("confidence_percentage", 0.0)
    hitl_pause = 1 if result_dict.get("hitl_pause_triggered") else 0
    entities_count = result_dict.get("phi_scrubbing", {}).get("entities_redacted_count", 0)
    zero_leakage = 1 if result_dict.get("phi_scrubbing", {}).get("zero_phi_leakage") else 0

    screening_summary = json.dumps(result_dict.get("screening_evaluation", {}))
    safety_summary = json.dumps(result_dict.get("medical_safety", {}))
    dossier_json = json.dumps(result_dict.get("audit_dossier", {}))

    cursor.execute("""
    INSERT OR REPLACE INTO screening_runs (
        run_id, created_at, protocol_id, patient_pseudonym,
        final_decision, confidence_percentage, hitl_pause_triggered,
        entities_redacted_count, zero_phi_leakage,
        screening_summary, safety_summary, dossier_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id, created_at, protocol_id, patient_pseudonym,
        final_decision, confidence_pct, hitl_pause,
        entities_count, zero_leakage,
        screening_summary, safety_summary, dossier_json
    ))

    conn.commit()
    conn.close()


def get_screening_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single screening run by run_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM screening_runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "run_id": row["run_id"],
        "created_at": row["created_at"],
        "protocol_id": row["protocol_id"],
        "patient_pseudonym": row["patient_pseudonym"],
        "final_decision": row["final_decision"],
        "confidence_percentage": row["confidence_percentage"],
        "hitl_pause_triggered": bool(row["hitl_pause_triggered"]),
        "entities_redacted_count": row["entities_redacted_count"],
        "zero_phi_leakage": bool(row["zero_phi_leakage"]),
        "screening_summary": json.loads(row["screening_summary"] or "{}"),
        "safety_summary": json.loads(row["safety_summary"] or "{}"),
        "dossier_json": json.loads(row["dossier_json"] or "{}")
    }


def list_screening_runs(limit: int = 25) -> List[Dict[str, Any]]:
    """Lists recent screening runs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT run_id, created_at, protocol_id, patient_pseudonym, final_decision, confidence_percentage, hitl_pause_triggered FROM screening_runs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "run_id": r["run_id"],
            "created_at": r["created_at"],
            "protocol_id": r["protocol_id"],
            "patient_pseudonym": r["patient_pseudonym"],
            "final_decision": r["final_decision"],
            "confidence_percentage": r["confidence_percentage"],
            "hitl_pause_triggered": bool(r["hitl_pause_triggered"])
        }
        for r in rows
    ]


def save_webhook_event(event_id: str, event_type: str, patient_id: str, confidence: str, payload: Dict[str, Any]):
    """Saves incoming simulated HITL webhook payload."""
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT INTO webhook_events (event_id, created_at, event_type, patient_pseudonym, confidence, payload)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (event_id, created_at, event_type, patient_id, confidence, json.dumps(payload)))
    conn.commit()
    conn.close()


def list_webhook_events(limit: int = 20) -> List[Dict[str, Any]]:
    """Lists received HITL webhook events."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM webhook_events ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "event_id": r["event_id"],
            "created_at": r["created_at"],
            "event_type": r["event_type"],
            "patient_pseudonym": r["patient_pseudonym"],
            "confidence": r["confidence"],
            "payload": json.loads(r["payload"] or "{}")
        }
        for r in rows
    ]
