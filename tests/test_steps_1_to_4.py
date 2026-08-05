"""Integration test for Step 1 to Step 4 pipeline execution."""

import os
import json
import glob
from src.config import INPUT_DIR
from src.schemas import CaseContext
from src.data_loader import DataLoader
from src.agents.customer_agent import CustomerAgent
from src.agents.order_product_agent import OrderProductAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.delivery_agent import DeliveryAgent
from src.agents.policy_agent import PolicyAgent


def run_pipeline_steps_1_to_4(input_path: str):
    print(f"\n==================================================")
    print(f"Testing File: {os.path.basename(input_path)}")
    print(f"==================================================")

    # Step 1: Data Engine & Case Context Initialization
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    claimed_order_id = data.get("customer_request", {}).get("claimed_order_id", "")
    context = CaseContext(
        case_id=data["case_id"],
        claimed_order_id=claimed_order_id,
        customer_request=data.get("customer_request", {}),
        investigation_scope=data.get("investigation_scope", {}),
        policy_version=data.get("policy_version", "EC_POLICY_V2")
    )
    print(f"[Step 1 Initialized] Case ID: {context.case_id} | Claimed Order ID: {context.claimed_order_id}")

    # Step 2: Customer Agent & Order-Product Agent
    dl = DataLoader()
    customer_agent = CustomerAgent()
    order_product_agent = OrderProductAgent()

    context = customer_agent.process(context, dl)
    print(f"[Step 2.1 CustomerAgent] Customer Unique ID: {context.customer_context.customer_unique_id}")
    print(f"                        Related Orders: {context.customer_context.related_order_ids}")
    print(f"                        Repeat Customer Flag: {context.flags.repeat_customer}")

    context = order_product_agent.process(context, dl)
    print(f"[Step 2.2 OrderProductAgent] Order Status: {context.flags.order_status}")
    print(f"                             Has Items: {context.flags.has_items}")
    print(f"                             Items Count: {len(context.affected_entities.item_ids)}")
    print(f"                             Sellers Count: {len(context.affected_entities.seller_ids)}")
    print(f"                             Products Count: {len(context.product_context.product_ids)}")
    print(f"                             Categories: {context.product_context.category_names}")
    print(f"                             Expected Total BRL: {context.payment_reconciliation.expected_total_brl}")

    # Step 3: Payment Agent & Delivery Agent
    payment_agent = PaymentAgent()
    delivery_agent = DeliveryAgent()

    context = payment_agent.process(context, dl)
    print(f"[Step 3.1 PaymentAgent] Payment Total BRL: {context.payment_reconciliation.payment_total_brl}")
    print(f"                        Difference BRL: {context.payment_reconciliation.difference_brl}")
    print(f"                        Reconciled: {context.payment_reconciliation.reconciled}")
    print(f"                        Split Payment Flag: {context.flags.split_payment}")

    context = delivery_agent.process(context, dl)
    print(f"[Step 3.2 DeliveryAgent] Delivered At: {context.delivery_analysis.delivered_at}")
    print(f"                         Estimated Delivery At: {context.delivery_analysis.estimated_delivery_at}")
    print(f"                         Delivery Variance (Hours): {context.delivery_analysis.delivery_variance_hours}")
    print(f"                         Late Handoff Sellers: {context.delivery_analysis.late_handoff_seller_ids}")

    # Step 4: Policy Agent (EC_POLICY_V2 Engine)
    policy_agent = PolicyAgent()
    context = policy_agent.process(context)

    print(f"[Step 4 PolicyAgent] Primary Issue: {context.case_assessment.primary_issue}")
    print(f"                     Secondary Issues: {context.case_assessment.secondary_issues}")
    print(f"                     Case Status: {context.case_assessment.case_status}")
    print(f"                     Confidence: {context.case_assessment.confidence}")
    print(f"                     Root Cause: {[c.cause_code for c in context.root_cause_analysis.ranked_causes]}")
    print(f"                     Responsible Parties: {[(p.party_type, p.party_id) for p in context.root_cause_analysis.responsible_parties]}")
    print(f"                     Recommended Refund BRL: {context.financial_resolution.recommended_refund_brl}")
    print(f"                     Resolution Actions: {context.resolution_actions}")
    print(f"                     Evidence IDs ({len(context.evidence_ids)}): {context.evidence_ids}")

    # Integrity Assertions
    assert context.case_assessment.primary_issue in [
        "canceled_order_paid", "unavailable_order_paid", "late_delivery_seller",
        "late_delivery_logistics", "valid_split_payment", "unsupported_late_claim"
    ], f"Invalid primary issue: {context.case_assessment.primary_issue}"

    assert context.case_assessment.case_status in ["action_required", "no_action"]
    assert 0.0 <= context.case_assessment.confidence <= 1.0
    assert isinstance(context.evidence_ids, list)
    for evi in context.evidence_ids:
        assert evi.startswith(("order:", "item:", "payment:", "seller:", "policy:")), f"Invalid evidence format: {evi}"

    print(f"--> Step 1 - Step 4 pipeline test PASSED for {context.case_id}!")
    return context


def test_steps_1_to_4_on_sample_cases():
    input_files = sorted(glob.glob(os.path.join(INPUT_DIR, "EC_*.json")))[:5]
    assert len(input_files) > 0, f"No input files found in {INPUT_DIR}"
    
    for filepath in input_files:
        run_pipeline_steps_1_to_4(filepath)


if __name__ == "__main__":
    test_steps_1_to_4_on_sample_cases()
