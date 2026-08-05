"""Delivery timing and seller handoff analysis agent."""

from __future__ import annotations

from datetime import datetime
from math import isnan
from typing import TYPE_CHECKING, Any, Optional

from src.schemas import CaseContext, DeliveryAnalysis, SellerHandoffAnalysis

if TYPE_CHECKING:
    from src.data_loader import DataLoader


def _optional_timestamp(value: Any) -> Optional[str]:
    """Convert empty CSV/Pandas timestamp values to None."""
    if value is None:
        return None
    if isinstance(value, float) and isnan(value):
        return None
    text = str(value).strip()
    return text or None


def _parse_timestamp(value: str) -> datetime:
    """Parse Olist's ISO-compatible timestamp representation."""
    return datetime.fromisoformat(value)


class DeliveryAgent:
    """Populate delivery variance and per-seller handoff facts."""

    def process(self, context: CaseContext, data_loader: DataLoader) -> CaseContext:
        order = data_loader.get_order(context.claimed_order_id)
        delivered_at = _optional_timestamp(
            order.get("order_delivered_customer_date")
        )
        estimated_delivery_at = _optional_timestamp(
            order.get("order_estimated_delivery_date")
        )
        carrier_handoff_at = _optional_timestamp(
            order.get("order_delivered_carrier_date")
        )

        delivery_variance_hours = None
        if delivered_at is not None and estimated_delivery_at is not None:
            difference = (
                _parse_timestamp(delivered_at)
                - _parse_timestamp(estimated_delivery_at)
            )
            delivery_variance_hours = round(
                difference.total_seconds() / 3600.0, 2
            )

        # Keep seller insertion order and retain the earliest non-empty limit.
        seller_limits: dict[str, Optional[str]] = {}
        for item in data_loader.get_order_items(context.claimed_order_id):
            seller_id = item["seller_id"]
            shipping_limit = _optional_timestamp(item.get("shipping_limit_date"))
            if seller_id not in seller_limits:
                seller_limits[seller_id] = shipping_limit
            elif shipping_limit is not None:
                current_limit = seller_limits[seller_id]
                if current_limit is None or _parse_timestamp(
                    shipping_limit
                ) < _parse_timestamp(current_limit):
                    seller_limits[seller_id] = shipping_limit

        seller_analyses = []
        late_seller_ids = []
        for seller_id, shipping_limit_at in seller_limits.items():
            handoff_variance_hours = None
            late_handoff = False
            if carrier_handoff_at is not None and shipping_limit_at is not None:
                difference = (
                    _parse_timestamp(carrier_handoff_at)
                    - _parse_timestamp(shipping_limit_at)
                )
                handoff_variance_hours = round(
                    difference.total_seconds() / 3600.0, 2
                )
                late_handoff = handoff_variance_hours > 0

            seller_analyses.append(
                SellerHandoffAnalysis(
                    seller_id=seller_id,
                    shipping_limit_at=shipping_limit_at,
                    handoff_variance_hours=handoff_variance_hours,
                    late_handoff=late_handoff,
                )
            )
            if late_handoff:
                late_seller_ids.append(seller_id)

        context.delivery_analysis = DeliveryAnalysis(
            delivered_at=delivered_at,
            estimated_delivery_at=estimated_delivery_at,
            carrier_handoff_at=carrier_handoff_at,
            delivery_variance_hours=delivery_variance_hours,
            seller_handoff_analysis=seller_analyses,
            late_handoff_seller_ids=late_seller_ids,
        )
        return context
