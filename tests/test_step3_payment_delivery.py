"""Unit tests for Step 3: Payment Agent & Delivery Agent (Person 3)."""

import pytest
from src.schemas import CaseContext, InternalFlags
from src.data_loader import DataLoader
from src.agents.payment_agent import PaymentAgent
from src.agents.delivery_agent import DeliveryAgent


@pytest.fixture
def data_loader():
    return DataLoader()


def test_step3_payment_agent_reconciliation(data_loader):
    """3.1 Test PaymentAgent calculating payment_total_brl, difference_brl, reconciled, and split_payment flag."""
    order_id = "9b75cdaf2d85857ef023980e15d01546"
    context = CaseContext(case_id="TEST_PAY_01", claimed_order_id=order_id)
    
    # Preset expected total from previous step
    context.flags.has_items = True
    context.payment_reconciliation.expected_total_brl = 212.27

    agent = PaymentAgent()
    updated_context = agent.process(context, data_loader)

    assert isinstance(updated_context.affected_entities.payment_ids, list)
    assert len(updated_context.affected_entities.payment_ids) <= 5
    assert updated_context.payment_reconciliation.payment_total_brl is not None
    
    if updated_context.payment_reconciliation.payment_total_brl > 0:
        assert updated_context.payment_reconciliation.difference_brl is not None
        expected_diff = round(updated_context.payment_reconciliation.payment_total_brl - 212.27, 2)
        assert updated_context.payment_reconciliation.difference_brl == expected_diff
        assert updated_context.payment_reconciliation.reconciled == (abs(expected_diff) <= 0.10)


def test_step3_payment_agent_no_items(data_loader):
    """3.1 Test PaymentAgent null handling when has_items is False."""
    context = CaseContext(case_id="TEST_PAY_02", claimed_order_id="fake_order")
    context.flags.has_items = False

    agent = PaymentAgent()
    updated_context = agent.process(context, data_loader)

    assert updated_context.payment_reconciliation.difference_brl is None
    assert updated_context.payment_reconciliation.reconciled is None


def test_step3_delivery_agent_variance(data_loader):
    """3.2 Test DeliveryAgent timestamp extraction and delivery_variance_hours / seller handoff variance."""
    order_id = "9b75cdaf2d85857ef023980e15d01546"
    context = CaseContext(case_id="TEST_DEL_01", claimed_order_id=order_id)

    agent = DeliveryAgent()
    updated_context = agent.process(context, data_loader)

    assert updated_context.delivery_analysis is not None
    deliv = updated_context.delivery_analysis
    assert hasattr(deliv, "delivered_at")
    assert hasattr(deliv, "estimated_delivery_at")
    assert hasattr(deliv, "carrier_handoff_at")
    assert isinstance(deliv.seller_handoff_analysis, list)
    assert isinstance(deliv.late_handoff_seller_ids, list)
