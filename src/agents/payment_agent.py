"""PaymentAgent: extract payment facts + LLM evaluates payment anomaly."""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.schemas import CaseContext
from src.llm_client import call_llm

if TYPE_CHECKING:
    from src.data_loader import DataLoader


class PaymentAgent:
    """Populate payment facts in the shared case context."""

    def process(self, context: CaseContext, data_loader: DataLoader) -> CaseContext:
        payments = data_loader.get_order_payments(context.claimed_order_id)

        context.affected_entities.payment_ids = [
            f"{context.claimed_order_id}:{row['payment_sequential']}"
            for row in payments
        ]

        # dict preserves the source-row order while removing duplicates.
        context.payment_reconciliation.payment_types = list(
            dict.fromkeys(row["payment_type"] for row in payments)
        )
        # ------------------------------------------------------------------
        # Python tính (deterministic)
        # ------------------------------------------------------------------
        payment_total = round(
            sum(float(row["payment_value"]) for row in payments), 2
        )
        context.payment_reconciliation.payment_total_brl = payment_total

        if not context.flags.has_items:
            context.payment_reconciliation.difference_brl = None
            context.payment_reconciliation.reconciled = None
        else:
            expected_total = context.payment_reconciliation.expected_total_brl
            if expected_total is None:
                context.payment_reconciliation.difference_brl = None
                context.payment_reconciliation.reconciled = None
            else:
                difference = round(payment_total - expected_total, 2)
                context.payment_reconciliation.difference_brl = difference
                context.payment_reconciliation.reconciled = abs(difference) <= 0.10

        context.flags.split_payment = len(payments) >= 2

        # ------------------------------------------------------------------
        # LLM: Đánh giá tính bất thường của payment pattern
        # Python đã tính: payment_total, difference_brl, reconciled, split_payment
        # LLM quyết định: payment_anomaly level
        # ------------------------------------------------------------------
        diff = context.payment_reconciliation.difference_brl
        reconciled = context.payment_reconciliation.reconciled
        payment_types = context.payment_reconciliation.payment_types
        num_payments = len(payments)

        prompt = f"""Bạn là một chuyên gia phân tích thanh toán thương mại điện tử. Hãy đánh giá mức độ bất thường của mẫu thanh toán.

Thông tin thanh toán (đã được hệ thống tính toán trước):
- payment_total_brl: {payment_total}
- expected_total_brl: {context.payment_reconciliation.expected_total_brl}
- difference_brl: {diff}
- reconciled: {reconciled}
- split_payment: {context.flags.split_payment}
- num_payment_rows: {num_payments}
- payment_types: {payment_types}

Hãy quyết định:
- payment_anomaly: 
  "none" = khớp (reconciled) và bình thường
  "minor_discrepancy" = chênh lệch nhỏ (0.10 < diff <= 5.00 BRL) nhưng các phần khác bình thường
  "suspicious" = chênh lệch lớn, không khớp mặc dù có chia nhỏ thanh toán (split payment), hoặc mẫu bất thường
- anomaly_notes: giải thích ngắn gọn về quyết định của bạn"""

        schema = {
            "type": "object",
            "properties": {
                "payment_anomaly": {"type": "string", "enum": ["none", "minor_discrepancy", "suspicious"]},
                "anomaly_notes": {"type": "string"}
            },
            "required": ["payment_anomaly", "anomaly_notes"],
            "additionalProperties": False
        }

        result = call_llm(prompt, schema=schema, max_tokens=1024)

        if result:
            context.flags.payment_anomaly = result.get("payment_anomaly", "none")
        else:
            # Fallback: simple rule
            if diff is None:
                context.flags.payment_anomaly = "none"
            elif abs(diff) <= 0.10:
                context.flags.payment_anomaly = "none"
            elif abs(diff) <= 5.00:
                context.flags.payment_anomaly = "minor_discrepancy"
            else:
                context.flags.payment_anomaly = "suspicious"

        return context
