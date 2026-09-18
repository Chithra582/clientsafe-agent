"""Unit tests for Lyzr AIMS Event Streamer."""

import pytest
import os
from agents.aims_streamer import AimsStreamer


@pytest.fixture
def streamer(tmp_path):
    log_file = tmp_path / "test_aims.jsonl"
    return AimsStreamer(log_path=str(log_file))


def test_aims_emit_and_retrieve_events(streamer):
    evt1 = streamer.emit_event(
        run_id="RUN-AIMS-1",
        triad_layer="ENVIRONMENT",
        agent_name="IngestionManager",
        event_type="PROTOCOL_LOADED",
        payload={"pages": 12}
    )

    evt2 = streamer.emit_event(
        run_id="RUN-AIMS-1",
        triad_layer="AGENT",
        agent_name="PhiScrubberAgent",
        event_type="PHI_REDACTED",
        payload={"count": 5}
    )

    assert evt1["event_id"].startswith("aims-evt-")
    assert evt2["triad_layer"] == "AGENT"

    run_events = streamer.get_run_events("RUN-AIMS-1")
    assert len(run_events) == 2

    latest = streamer.get_latest_events(limit=10)
    assert len(latest) >= 2
