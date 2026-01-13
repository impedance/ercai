import os
import sys

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from store_helpers import CouponVerifier, PaginationGuard, normalize_basket_view


def test_normalize_basket_view_handles_null_items():
    payload = {"items": None}
    normalized = normalize_basket_view(payload)
    assert normalized["items"] == []


def test_pagination_guard_limits_and_aggregation():
    guard = PaginationGuard(max_limit=3, max_rounds=3)
    seen_limits = []

    def dispatch_fn(payload):
        seen_limits.append(payload["limit"])
        offset = payload["offset"]
        count = payload["limit"]
        next_offset = offset + count
        if next_offset >= 6:
            next_offset = -1
        return {
            "products": [{"sku": f"item-{offset}-{i}"} for i in range(count)],
            "next_offset": next_offset,
        }

    result = guard.paginate({"limit": 10, "offset": 0}, dispatch_fn)
    assert all(limit <= 3 for limit in seen_limits)
    assert result["next_offset"] == -1
    assert len(result["products"]) == sum(seen_limits)


def test_pagination_guard_reduces_limit_on_error():
    guard = PaginationGuard(max_limit=5, min_limit=1, max_rounds=2)
    attempts = {"count": 0}

    def dispatch_fn(payload):
        if payload["limit"] > 2 and attempts["count"] == 0:
            attempts["count"] += 1
            raise RuntimeError("page limit exceeded: 5 > 2")
        return {"products": [{"sku": "ok"}], "next_offset": -1}

    result = guard.paginate({"limit": 5, "offset": 0}, dispatch_fn)
    assert attempts["count"] == 1
    assert result["products"][0]["sku"] == "ok"


def test_coupon_verifier_tracks_best_discount():
    verifier = CouponVerifier()
    ok, msg = verifier.evaluate("SAVE10", {"discount": "10"})
    assert ok
    assert verifier.best_coupon == "SAVE10"
    worse, _ = verifier.evaluate("SKIP", {"discount": "5"})
    assert not worse
    null_ok, _ = verifier.evaluate("ZERO", {"discount": None})
    assert not null_ok


def test_coupon_verifier_rejects_zero_discount():
    verifier = CouponVerifier()
    zero_ok, msg = verifier.evaluate("ZERO", {"discount": 0})
    assert not zero_ok
    assert "non-positive" in msg


def test_normalize_basket_view_converts_single_item():
    payload = {"items": {"sku": "single"}}
    normalized = normalize_basket_view(payload)
    assert isinstance(normalized["items"], list)
    assert normalized["items"][0]["sku"] == "single"


def test_coupon_verifier_updates_best_discount():
    verifier = CouponVerifier()
    assert verifier.evaluate("BASE", {"discount": "5"})[0]
    assert verifier.best_coupon == "BASE"
    assert verifier.evaluate("BETTER", {"discount": "15"})[0]
    assert verifier.best_coupon == "BETTER"


def test_pagination_guard_respects_max_rounds():
    guard = PaginationGuard(max_limit=2, max_rounds=1)

    def dispatch_fn(payload):
        return {
            "products": [{"sku": f"item-{payload['offset']}"}],
            "next_offset": payload["offset"] + 1,
        }

    result = guard.paginate({"offset": 0, "limit": 2}, dispatch_fn)
    assert result["next_offset"] == -1
    assert len(result["products"]) == 1


def run_all_tests():
    test_normalize_basket_view_handles_null_items()
    test_pagination_guard_limits_and_aggregation()
    test_pagination_guard_reduces_limit_on_error()
    test_coupon_verifier_tracks_best_discount()


if __name__ == "__main__":
    run_all_tests()
