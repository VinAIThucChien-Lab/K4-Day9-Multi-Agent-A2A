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

        # ------------------------------------------------------------------
        # LLM: Đánh giá mức độ nghiêm trọng của delay và trách nhiệm carrier
        # Python đã tính: delivery_variance_hours, late_handoff, late_seller_ids
        # LLM quyết định: delay_severity, carrier_accountability
        # ------------------------------------------------------------------
        from src.llm_client import call_llm

        handoff_summary = [
            {"seller_id": s.seller_id, "handoff_variance_hours": s.handoff_variance_hours, "late_handoff": s.late_handoff}
            for s in seller_analyses
        ]

        prompt = f"""Bạn là một chuyên gia phân tích vận chuyển thương mại điện tử. Hãy đánh giá mức độ nghiêm trọng của việc giao hàng chậm trễ và trách nhiệm của đơn vị vận chuyển.

Thông tin giao hàng (đã được hệ thống tính toán trước):
- delivery_variance_hours: {delivery_variance_hours} (dương = trễ, âm = sớm, None = chưa giao)
- late_handoff_seller_ids: {late_seller_ids}
- seller_handoff_summary: {handoff_summary}

Hãy quyết định:
- delay_severity: "none" (độ lệch <= 0 hoặc None), "minor" (trễ 1-24h), "significant" (trễ 24-72h), "severe" (trễ hơn 72h)
- carrier_accountability: "low" (không trễ hoặc lỗi do người bán), "medium" (trễ nhưng không rõ ràng nguyên nhân), "high" (trễ đáng kể và không phải lỗi của người bán)"""

        schema = {
            "type": "object",
            "properties": {
                "delay_severity": {"type": "string", "enum": ["none", "minor", "significant", "severe"]},
                "carrier_accountability": {"type": "string", "enum": ["low", "medium", "high"]}
            },
            "required": ["delay_severity", "carrier_accountability"],
            "additionalProperties": False
        }

        result = call_llm(prompt, schema=schema, max_tokens=1024)

        if result:
            context.flags.delay_severity = result.get("delay_severity", "none")
            context.flags.carrier_accountability = result.get("carrier_accountability", "low")
        else:
            # Fallback: deterministic rules
            if delivery_variance_hours is None or delivery_variance_hours <= 0:
                context.flags.delay_severity = "none"
                context.flags.carrier_accountability = "low"
            elif delivery_variance_hours <= 24:
                context.flags.delay_severity = "minor"
                context.flags.carrier_accountability = "low" if late_seller_ids else "medium"
            elif delivery_variance_hours <= 72:
                context.flags.delay_severity = "significant"
                context.flags.carrier_accountability = "low" if late_seller_ids else "high"
            else:
                context.flags.delay_severity = "severe"
                context.flags.carrier_accountability = "low" if late_seller_ids else "high"

        return context
