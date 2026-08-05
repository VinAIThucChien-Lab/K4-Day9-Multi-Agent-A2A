"""Payment extraction and reconciliation agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.schemas import CaseContext

if TYPE_CHECKING:
    from src.data_loader import DataLoader


class PaymentAgent:
    """Populate payment facts in the shared case context."""

    def process(self, context: CaseContext, data_loader: DataLoader) -> CaseContext:
        payments = data_loader.get_order_payments(context.claimed_order_id)

        context.affected_entities.payment_ids = [
            f"{context.claimed_order_id}:{row['payment_sequential']}"
            for row in payments[:5]
        ]

        # dict preserves the source-row order while removing duplicates.
        context.payment_reconciliation.payment_types = list(
            dict.fromkeys(row["payment_type"] for row in payments)
        )
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
                # The previous handoff should provide this value. Preserve a safe,
                # explicitly unknown reconciliation if that precondition is unmet.
                context.payment_reconciliation.difference_brl = None
                context.payment_reconciliation.reconciled = None
            else:
                difference = round(payment_total - expected_total, 2)
                context.payment_reconciliation.difference_brl = difference
                context.payment_reconciliation.reconciled = abs(difference) <= 0.10

        context.flags.split_payment = len(payments) >= 2
        return context
