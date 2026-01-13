"""
Unit tests for the validation and uncertainty helpers inside agent.py.
"""

import logging
import os
import sys

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from agent import UncertaintyManager, ValidationTracker


def test_validation_tracker_requires_successful_validation():
    tracker = ValidationTracker(logging.getLogger("test"))
    tracker.record("analysis", None, True, None, "analysis_result")
    assert not tracker.has_successful_validation()
    tracker.record("validation", "length", True, None, "validated")
    assert tracker.has_successful_validation()


def test_uncertainty_manager_detects_candidates_and_confirms():
    manager = UncertaintyManager(logging.getLogger("test"))
    assert manager.detect_from_task("Decide between apples or bananas.")
    assert manager.should_prompt()
    prompt = manager.prompt_message()
    assert "Candidate 1" in prompt
    assert manager.try_confirm("I will follow Candidate 1")
    assert not manager.needs_confirmation()
