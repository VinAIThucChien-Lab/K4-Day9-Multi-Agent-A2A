"""Schema verification, limit enforcement, and output export agent."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, Any
from src.config import OUTPUT_DIR, LOGGING_DIR, BASE_DIR
from src.schemas import CaseContext


class VerifierAgent:
    """Validate output schema constraints, apply array limits, write output JSON and log trace."""

    def verify_and_export(
        self,
        context: CaseContext,
        output_dir: str = OUTPUT_DIR,
        trace_file: str = os.path.join(BASE_DIR, "trace.jsonl")
    ) -> Dict[str, Any]:
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(trace_file), exist_ok=True)

        data = context.model_dump()

        # Partial contexts are supported for isolated slicing/null-handling tests.
        # The real coordinator always supplies an assessment before this node.
        if context.case_assessment is not None:
            if context.case_assessment.primary_issue not in {
                "canceled_order_paid", "unavailable_order_paid",
                "late_delivery_seller", "late_delivery_logistics",
                "valid_split_payment", "unsupported_late_claim",
            }:
                raise ValueError("invalid primary_issue")
            if context.case_assessment.case_status not in {"action_required", "no_action"}:
                raise ValueError("invalid case_status")
            if not 0.0 <= context.case_assessment.confidence <= 1.0:
                raise ValueError("confidence must be between 0 and 1")

        # Remove internal flags from final JSON output
        data.pop("flags", None)
        data.pop("claimed_order_id", None)
        data.pop("customer_request", None)
        data.pop("investigation_scope", None)
        data.pop("policy_version", None)

        # Apply array limit constraints
        if "affected_entities" in data and data["affected_entities"]:
            data["affected_entities"]["order_ids"] = data["affected_entities"].get("order_ids", [])[:5]
            data["affected_entities"]["item_ids"] = data["affected_entities"].get("item_ids", [])[:5]
            data["affected_entities"]["seller_ids"] = data["affected_entities"].get("seller_ids", [])[:3]
            data["affected_entities"]["payment_ids"] = data["affected_entities"].get("payment_ids", [])[:5]

        if "customer_context" in data and data["customer_context"]:
            data["customer_context"]["related_order_ids"] = data["customer_context"].get("related_order_ids", [])[:5]

        if "product_context" in data and data["product_context"]:
            data["product_context"]["product_ids"] = data["product_context"].get("product_ids", [])[:5]
            data["product_context"]["category_names"] = data["product_context"].get("category_names", [])[:5]

        if "root_cause_analysis" in data and data["root_cause_analysis"]:
            data["root_cause_analysis"]["ranked_causes"] = data["root_cause_analysis"].get("ranked_causes", [])[:3]
            data["root_cause_analysis"]["responsible_parties"] = data["root_cause_analysis"].get("responsible_parties", [])[:3]

        if "evidence_ids" in data:
            data["evidence_ids"] = data.get("evidence_ids", [])[:20]

        if "resolution_actions" in data:
            data["resolution_actions"] = data.get("resolution_actions", [])[:5]

        # Enforce two-decimal output even if an upstream agent changes later.
        monetary_fields = {
            "item_total_brl", "freight_total_brl", "expected_total_brl",
            "payment_total_brl", "difference_brl", "recommended_refund_brl",
        }
        timing_fields = {"delivery_variance_hours", "handoff_variance_hours"}

        def round_numbers(value: Any, key: str = "") -> Any:
            if isinstance(value, dict):
                return {k: round_numbers(v, k) for k, v in value.items()}
            if isinstance(value, list):
                return [round_numbers(item, key) for item in value]
            if key in monetary_fields | timing_fields and isinstance(value, (int, float)):
                return round(float(value), 2)
            return value

        data = round_numbers(data)

        # Null handling when has_items is False
        if not context.flags.has_items:
            if "payment_reconciliation" in data and data["payment_reconciliation"]:
                data["payment_reconciliation"]["item_total_brl"] = None
                data["payment_reconciliation"]["freight_total_brl"] = None
                data["payment_reconciliation"]["expected_total_brl"] = None
                data["payment_reconciliation"]["difference_brl"] = None
                data["payment_reconciliation"]["reconciled"] = None

        if data.get("case_assessment") is not None:
            refund = data["financial_resolution"]["recommended_refund_brl"]
            expected_status = "action_required" if refund > 0 else "no_action"
            if data["case_assessment"]["case_status"] != expected_status:
                raise ValueError("case_status is inconsistent with recommended refund")

        allowed_party_types = {"platform", "seller", "logistics_provider"}
        for party in data["root_cause_analysis"]["responsible_parties"]:
            if party["party_type"] not in allowed_party_types:
                raise ValueError(f"invalid responsible party type: {party['party_type']}")

        # Write output file
        out_path = os.path.join(output_dir, f"{context.case_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Append trace log
        primary_issue = (
            data.get("case_assessment", {}).get("primary_issue", "")
            if data.get("case_assessment") else ""
        )
        refund = (
            data.get("financial_resolution", {}).get("recommended_refund_brl", 0.0)
            if data.get("financial_resolution") else 0.0
        )
        trace_entry = {
            "case_id": context.case_id,
            "primary_issue": primary_issue,
            "refund": refund,
            "llm_status": context.investigation_scope.get("llm_status", "disabled"),
            "llm_model": context.investigation_scope.get("llm_model"),
            "llm_provider": context.investigation_scope.get("llm_provider"),
            "timestamp": datetime.now().isoformat()
        }
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace_entry) + "\n")

        return data

