"""
Unit tests for the validation and uncertainty helpers inside agent.py.
"""

import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from agent import StoreGuard, UncertaintyManager, ValidationTracker


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
    note = manager.auto_confirm_default_candidate()
    assert note is not None
    assert "Candidate 1" in note
    assert not manager.needs_confirmation()


class DummyAddRequest:
    def __init__(self, sku: str, quantity: int) -> None:
        self.sku = sku
        self.quantity = quantity

    def model_dump(self) -> Dict[str, Any]:
        return {"sku": self.sku, "quantity": self.quantity}


def test_store_guard_inventory_adjustment():
    guard = StoreGuard(client=None, logger=logging.getLogger("test"))
    guard.record_inventory_snapshot([{"sku": "widget", "available": 3}])
    request = DummyAddRequest("widget", 5)
    adjustment = guard.adjust_inventory_for_add(request)
    assert adjustment.quantity == 3
    assert "reduced" in (adjustment.message or "")
    assert not adjustment.blocked
    assert adjustment.message

    guard.record_inventory_snapshot([{"sku": "empty", "available": 0}])
    blocked_request = DummyAddRequest("empty", 2)
    blocked_adjustment = guard.adjust_inventory_for_add(blocked_request)
    assert blocked_adjustment.blocked
    assert "out of stock" in (blocked_adjustment.message or "")


def test_store_guard_coupon_gate():
    guard = StoreGuard(client=None, logger=logging.getLogger("test"))
    guard.last_coupon_result = {
        "code": "ZERO",
        "accepted": False,
        "reason": "coupon offered no savings",
    }
    allowed, reason = guard.coupon_allows_checkout()
    assert not allowed
    assert "ZERO" in (reason or "")

    guard.last_coupon_result = {
        "code": "WIN",
        "accepted": True,
        "reason": "valid discount",
    }
    allowed, _ = guard.coupon_allows_checkout()
    assert allowed
