"""Unit tests for Step 4: Policy & Reasoning Agent (EC_POLICY_V2 Engine - Person 4)."""

import pytest
from src.schemas import (
    CaseContext, InternalFlags, DeliveryAnalysis, SellerHandoffAnalysis,
    PaymentReconciliation, AffectedEntities
)
from src.agents.policy_agent import PolicyAgent


@pytest.fixture
def policy_agent():
    return PolicyAgent()


def test_rule_1_canceled_order_paid(policy_agent):
    """Rule 1: order_status == canceled and payment > 0 -> canceled_order_paid, full refund."""
    context = CaseContext(
        case_id="TEST_R1",
        claimed_order_id="ord_1",
        flags=InternalFlags(order_status="canceled"),
        payment_reconciliation=PaymentReconciliation(payment_total_brl=150.00, freight_total_brl=20.00)
    )

    res = policy_agent.process(context)

    assert res.case_assessment.primary_issue == "canceled_order_paid"
    assert res.case_assessment.case_status == "action_required"
    assert res.financial_resolution.recommended_refund_brl == 150.00
    assert res.root_cause_analysis.ranked_causes[0].cause_code == "ORDER_CANCELED_AFTER_PAYMENT"
    assert res.root_cause_analysis.responsible_parties[0].party_type == "platform"
    assert res.root_cause_analysis.responsible_parties[0].party_id == "OLIST_PLATFORM"
    assert "issue_full_refund" in res.resolution_actions


def test_rule_2_unavailable_order_paid(policy_agent):
    """Rule 2: order_status == unavailable and payment > 0 -> unavailable_order_paid, full refund."""
    context = CaseContext(
        case_id="TEST_R2",
        claimed_order_id="ord_2",
        flags=InternalFlags(order_status="unavailable"),
        payment_reconciliation=PaymentReconciliation(payment_total_brl=200.00, freight_total_brl=15.00)
    )

    res = policy_agent.process(context)

    assert res.case_assessment.primary_issue == "unavailable_order_paid"
    assert res.case_assessment.case_status == "action_required"
    assert res.financial_resolution.recommended_refund_brl == 200.00
    assert res.root_cause_analysis.ranked_causes[0].cause_code == "ORDER_UNAVAILABLE_AFTER_PAYMENT"
    assert res.root_cause_analysis.responsible_parties[0].party_type == "platform"
    assert "issue_full_refund" in res.resolution_actions


def test_rule_3_late_delivery_seller(policy_agent):
    """Rule 3: delivery_variance > 0 and late_seller_ids > 0 -> late_delivery_seller, freight refund."""
    context = CaseContext(
        case_id="TEST_R3",
        claimed_order_id="ord_3",
        flags=InternalFlags(order_status="delivered"),
        payment_reconciliation=PaymentReconciliation(payment_total_brl=100.00, freight_total_brl=25.50),
        delivery_analysis=DeliveryAnalysis(
            delivery_variance_hours=12.5,
            late_handoff_seller_ids=["seller_abc"]
        )
    )

    res = policy_agent.process(context)

    assert res.case_assessment.primary_issue == "late_delivery_seller"
    assert res.case_assessment.case_status == "action_required"
    assert res.financial_resolution.recommended_refund_brl == 25.50
    assert res.root_cause_analysis.ranked_causes[0].cause_code == "SELLER_HANDOFF_AFTER_LIMIT"
    assert res.root_cause_analysis.responsible_parties[0].party_type == "seller"
    assert res.root_cause_analysis.responsible_parties[0].party_id == "seller_abc"
    assert "refund_freight" in res.resolution_actions
    assert "review_seller_handoff" in res.resolution_actions


def test_rule_4_late_delivery_logistics(policy_agent):
    """Rule 4: delivery_variance > 0 and late_seller_ids == 0 -> late_delivery_logistics, freight refund."""
    context = CaseContext(
        case_id="TEST_R4",
        claimed_order_id="ord_4",
        flags=InternalFlags(order_status="delivered"),
        payment_reconciliation=PaymentReconciliation(payment_total_brl=100.00, freight_total_brl=18.00),
        delivery_analysis=DeliveryAnalysis(
            delivery_variance_hours=48.0,
            late_handoff_seller_ids=[]
        )
    )

    res = policy_agent.process(context)

    assert res.case_assessment.primary_issue == "late_delivery_logistics"
    assert res.case_assessment.case_status == "action_required"
    assert res.financial_resolution.recommended_refund_brl == 18.00
    assert res.root_cause_analysis.ranked_causes[0].cause_code == "CARRIER_DELIVERED_AFTER_ESTIMATE"
    assert res.root_cause_analysis.responsible_parties[0].party_type == "logistics_provider"
    assert res.root_cause_analysis.responsible_parties[0].party_id == "LOGISTICS_PROVIDER"
    assert "refund_freight" in res.resolution_actions
    assert "review_carrier_delay" in res.resolution_actions


def test_rule_5_valid_split_payment(policy_agent):
    """Rule 5: split_payment == True, reconciled == True, not late -> valid_split_payment, 0 refund."""
    context = CaseContext(
        case_id="TEST_R5",
        claimed_order_id="ord_5",
        flags=InternalFlags(order_status="delivered", split_payment=True),
        payment_reconciliation=PaymentReconciliation(payment_total_brl=200.00, expected_total_brl=200.00, difference_brl=0.0, reconciled=True),
        delivery_analysis=DeliveryAnalysis(delivery_variance_hours=-24.0, late_handoff_seller_ids=[])
    )

    res = policy_agent.process(context)

    assert res.case_assessment.primary_issue == "valid_split_payment"
    assert res.case_assessment.case_status == "no_action"
    assert res.financial_resolution.recommended_refund_brl == 0.0
    assert res.root_cause_analysis.ranked_causes[0].cause_code == "MULTIPLE_PAYMENTS_RECONCILED"
    assert res.root_cause_analysis.responsible_parties == []
    assert "explain_valid_split_payment" in res.resolution_actions
    assert "verify_payment_allocation" not in res.resolution_actions


def test_rule_6_unsupported_late_claim(policy_agent):
    """Rule 6: not late, reconciled -> unsupported_late_claim, 0 refund."""
    context = CaseContext(
        case_id="TEST_R6",
        claimed_order_id="ord_6",
        flags=InternalFlags(order_status="delivered"),
        payment_reconciliation=PaymentReconciliation(payment_total_brl=100.00, expected_total_brl=100.00, difference_brl=0.0, reconciled=True),
        delivery_analysis=DeliveryAnalysis(delivery_variance_hours=-10.0, late_handoff_seller_ids=[])
    )

    res = policy_agent.process(context)

    assert res.case_assessment.primary_issue == "unsupported_late_claim"
    assert res.case_assessment.case_status == "no_action"
    assert res.financial_resolution.recommended_refund_brl == 0.0
    assert res.root_cause_analysis.ranked_causes[0].cause_code == "DELIVERY_WITHIN_ESTIMATE"
    assert "reject_late_refund" in res.resolution_actions


def test_secondary_issues_order(policy_agent):
    """Test secondary issues are appended in strict priority order 1->5."""
    context = CaseContext(
        case_id="TEST_SEC",
        claimed_order_id="ord_sec",
        flags=InternalFlags(
            order_status="delivered",
            multi_item_order=True,
            multi_seller_order=True,
            split_payment=True,
            repeat_customer=True,
            multiple_categories=True
        ),
        payment_reconciliation=PaymentReconciliation(payment_total_brl=100.00, expected_total_brl=100.00, difference_brl=0.0, reconciled=True),
        delivery_analysis=DeliveryAnalysis(delivery_variance_hours=-5.0, late_handoff_seller_ids=[])
    )

    res = policy_agent.process(context)
    expected_order = ["multi_item_order", "multi_seller_order", "split_payment", "repeat_customer", "multiple_categories"]
    assert res.case_assessment.secondary_issues == expected_order


def test_evidence_ids_format(policy_agent):
    """Test evidence_ids follow strict prefix format: order:, item:, payment:, seller:, policy:."""
    context = CaseContext(
        case_id="TEST_EVI",
        claimed_order_id="ord_123",
        affected_entities=AffectedEntities(
            order_ids=["ord_123"],
            item_ids=["item:ord_123:1"],
            payment_ids=["payment:ord_123:1"],
            seller_ids=["seller_abc"]
        ),
        payment_reconciliation=PaymentReconciliation(payment_total_brl=100.00, freight_total_brl=20.00),
        delivery_analysis=DeliveryAnalysis(delivery_variance_hours=10.0, late_handoff_seller_ids=["seller_abc"])
    )

    res = policy_agent.process(context)
    for evi in res.evidence_ids:
        assert evi.startswith("order:") or evi.startswith("item:") or evi.startswith("payment:") or evi.startswith("seller:") or evi.startswith("policy:")
