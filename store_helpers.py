import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

DEFAULT_MAX_PAGE_LIMIT = 5
DEFAULT_MIN_PAGE_LIMIT = 1
DEFAULT_MAX_PAGINATION_ROUNDS = 4


def normalize_basket_view(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure basket views always emit lists instead of nulls."""
    normalized = dict(payload or {})
    items = normalized.get("items")
    if items is None:
        normalized["items"] = []
    elif isinstance(items, list):
        normalized["items"] = [item for item in items if item is not None]
    else:
        normalized["items"] = [items]
    return normalized


@dataclass
class InventoryAdjustment:
    """Result of an inventory guard check before adding items."""

    blocked: bool = False
    quantity: Optional[int] = None
    message: Optional[str] = None


class PaginationGuard:
    """Cap STORE pagination requests and optionally auto-fetch multiple pages."""

    def __init__(
        self,
        max_limit: int = DEFAULT_MAX_PAGE_LIMIT,
        min_limit: int = DEFAULT_MIN_PAGE_LIMIT,
        max_rounds: int = DEFAULT_MAX_PAGINATION_ROUNDS,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.max_limit = max_limit
        self.min_limit = min_limit
        self.max_rounds = max_rounds
        self.logger = logger

    def paginate(
        self,
        request_payload: Dict[str, Any],
        dispatch_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        sanitized = self._sanitize_request(request_payload)
        aggregated: List[Any] = []
        offset = sanitized["offset"]
        limit = sanitized["limit"]
        last_payload: Dict[str, Any] = {"products": []}
        rounds = 0
        while rounds < self.max_rounds:
            page_request = dict(sanitized)
            page_request["offset"] = offset
            page_request["limit"] = limit
            try:
                page_payload = dispatch_fn(page_request)
            except Exception as exc:
                if self._should_reduce_limit(exc, limit):
                    limit = self._reduce_limit(limit)
                    sanitized["limit"] = limit
                    self._log(f"Reduced product limit to {limit} after error: {exc}")
                    continue
                raise
            products = page_payload.get("products") or []
            aggregated.extend(products)
            last_payload = page_payload
            next_offset = page_payload.get("next_offset", -1)
            if next_offset == -1 or next_offset == offset:
                break
            offset = next_offset
            rounds += 1
        final_payload = dict(last_payload)
        final_payload["products"] = aggregated
        final_payload["next_offset"] = -1
        return final_payload

    def _sanitize_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        limit = payload.get("limit")
        limit = limit if isinstance(limit, int) and limit > 0 else self.max_limit
        limit = min(limit, self.max_limit)
        offset = payload.get("offset", 0)
        offset = offset if isinstance(offset, int) and offset >= 0 else 0
        sanitized = dict(payload or {})
        sanitized["limit"] = limit
        sanitized["offset"] = offset
        return sanitized

    def _should_reduce_limit(self, exc: Exception, current_limit: int) -> bool:
        if current_limit <= self.min_limit:
            return False
        text = str(exc).lower()
        if "page limit" in text or "limit exceeded" in text or "page limit exceeded" in text:
            return True
        return False

    def _reduce_limit(self, current_limit: int) -> int:
        return max(self.min_limit, current_limit - 1)

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(f"PaginationGuard: {message}")


@dataclass
class CouponVerifier:
    """Track the coupon that delivered the best non-null discount."""

    logger: Optional[logging.Logger] = None
    best_coupon: Optional[str] = field(default=None)
    best_discount: float = field(default=-1.0)

    def evaluate(self, coupon_code: str, basket: Dict[str, Any]) -> Tuple[bool, str]:
        discount_value = self._parse_amount(basket.get("discount"))
        if discount_value is None:
            message = "coupon resulted in null discount"
            self._log(f"{coupon_code}: {message}")
            return False, message
        if discount_value <= 0:
            message = "coupon offered a non-positive discount"
            self._log(f"{coupon_code}: {message}")
            return False, message
        if discount_value > self.best_discount:
            self.best_discount = discount_value
            self.best_coupon = coupon_code
            message = f"new best discount {discount_value}"
            self._log(f"{coupon_code}: {message}")
            return True, message
        message = f"discount {discount_value} <= best {self.best_discount}"
        self._log(f"{coupon_code}: {message}")
        return False, message

    def _parse_amount(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.replace("$", "").strip()
        else:
            cleaned = value
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(f"CouponVerifier: {message}")
