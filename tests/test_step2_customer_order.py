"""Unit tests for Step 2: Customer Agent & Order-Product Agent (Person 2)."""

import pytest
from src.schemas import CaseContext, InternalFlags
from src.data_loader import DataLoader
from src.agents.customer_agent import CustomerAgent
from src.agents.order_product_agent import OrderProductAgent


@pytest.fixture
def data_loader():
    return DataLoader()


def test_step2_customer_agent_existing_order(data_loader):
    """2.1 Test CustomerAgent populating customer_context and repeat_customer flag."""
    order_id = "9b75cdaf2d85857ef023980e15d01546"
    context = CaseContext(case_id="TEST_01", claimed_order_id=order_id)
    
    agent = CustomerAgent()
    updated_context = agent.process(context, data_loader)
    
    assert updated_context.customer_context is not None
    assert isinstance(updated_context.customer_context.customer_unique_id, str)
    assert isinstance(updated_context.customer_context.related_order_ids, list)
    assert len(updated_context.customer_context.related_order_ids) <= 5
    assert order_id not in updated_context.customer_context.related_order_ids
    assert updated_context.flags.repeat_customer == (len(updated_context.customer_context.related_order_ids) > 0)


def test_step2_order_product_agent_valid_order(data_loader):
    """2.2 Test OrderProductAgent with valid items."""
    order_id = "9b75cdaf2d85857ef023980e15d01546"
    context = CaseContext(case_id="TEST_02", claimed_order_id=order_id)
    
    agent = OrderProductAgent()
    updated_context = agent.process(context, data_loader)
    
    assert updated_context.flags.order_status != ""
    assert updated_context.affected_entities.order_ids == [order_id]
    
    if updated_context.flags.has_items:
        assert len(updated_context.affected_entities.item_ids) > 0
        assert len(updated_context.affected_entities.seller_ids) > 0
        assert len(updated_context.product_context.product_ids) > 0
        assert updated_context.payment_reconciliation.item_total_brl is not None
        assert updated_context.payment_reconciliation.freight_total_brl is not None
        assert updated_context.payment_reconciliation.expected_total_brl == round(
            updated_context.payment_reconciliation.item_total_brl + updated_context.payment_reconciliation.freight_total_brl, 2
        )


def test_step2_order_product_agent_nonexistent_order(data_loader):
    """2.2 Test OrderProductAgent with empty/no items order."""
    fake_order_id = "non_existent_order_99999"
    context = CaseContext(case_id="TEST_03", claimed_order_id=fake_order_id)
    
    agent = OrderProductAgent()
    updated_context = agent.process(context, data_loader)
    
    assert updated_context.flags.has_items is False
    assert updated_context.affected_entities.item_ids == []
    assert updated_context.affected_entities.seller_ids == []
    assert updated_context.product_context.product_ids == []
    assert updated_context.product_context.category_names == []
    assert updated_context.payment_reconciliation.item_total_brl is None
    assert updated_context.payment_reconciliation.freight_total_brl is None
    assert updated_context.payment_reconciliation.expected_total_brl is None
