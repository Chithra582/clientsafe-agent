"""Unit tests for enterprise secrets management, database adapter, and event bus."""

import os
import pytest
from backend.secrets_manager import SecretsManager, EnvironmentSecretsProvider, DockerSecretsProvider
from backend.database import DatabaseAdapter
from backend.event_bus import InMemoryEventBus, get_event_bus


def test_secrets_manager_resolution(monkeypatch):
    monkeypatch.setenv("TEST_CLINICAL_KEY", "super-secret-token-12345")
    mgr = SecretsManager()
    val = mgr.get("TEST_CLINICAL_KEY")
    assert val == "super-secret-token-12345"

    masked = mgr.mask_secret(val)
    assert masked.startswith("sup...")
    assert "secret" not in masked


def test_database_adapter_crud(tmp_path):
    test_db = tmp_path / "test_clinsafe.db"
    adapter = DatabaseAdapter(db_url=f"sqlite:///{test_db}")
    adapter.init_db()

    dummy_result = {
        "final_decision": "ELIGIBLE",
        "confidence_percentage": 99.5,
        "hitl_pause_triggered": False,
        "criteria_extraction": {"protocol_id": "ONCO-TEST"},
        "audit_dossier": {"subject_provenance": {"pseudonym_id": "SUBJ-TEST"}},
        "phi_scrubbing": {"entities_redacted_count": 5, "zero_phi_leakage": True},
        "screening_evaluation": {"passed_count": 10},
        "medical_safety": {"safety_decision": "SAFE"}
    }

    adapter.save_screening_run("RUN-TEST-DB-001", dummy_result)
    retrieved = adapter.get_screening_run("RUN-TEST-DB-001")

    assert retrieved is not None
    assert retrieved["run_id"] == "RUN-TEST-DB-001"
    assert retrieved["final_decision"] == "ELIGIBLE"
    assert retrieved["confidence_percentage"] == 99.5

    runs_list = adapter.list_screening_runs(limit=10)
    assert len(runs_list) >= 1


def test_event_bus_pub_sub():
    bus = InMemoryEventBus()
    received = []

    def sample_subscriber(msg):
        received.append(msg)

    bus.subscribe("aims.screening", sample_subscriber)
    bus.publish("aims.screening", {"event": "SCREENING_COMPLETE", "run_id": "RUN-BUS-1"})

    assert len(received) == 1
    assert received[0]["event"] == "SCREENING_COMPLETE"
    assert received[0]["topic"] == "aims.screening"
