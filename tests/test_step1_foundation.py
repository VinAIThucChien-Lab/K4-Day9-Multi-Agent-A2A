"""Unit tests for Step 1: Config, Data Schemas, and Data Loader (Person 1)."""

import os
import pytest
from src.config import BASE_DIR, DATA_DIR, INPUT_DIR, OUTPUT_DIR, LLM_MODEL_NAME
from src.schemas import (
    CaseContext, CaseAssessment, AffectedEntities, CustomerContext,
    ProductContext, DeliveryAnalysis, PaymentReconciliation,
    RootCauseAnalysis, FinancialResolution, InternalFlags, SellerHandoffAnalysis
)
from src.data_loader import DataLoader


def test_step1_config_constants():
    """1.1 Verify config paths and model parameter constraints."""
    assert os.path.isabs(BASE_DIR)
    assert DATA_DIR.endswith("data")
    assert INPUT_DIR.endswith("input")
    assert OUTPUT_DIR.endswith("output")
    assert LLM_MODEL_NAME == "qwen/qwen3-4b:free"


def test_step1_schemas_instantiation():
    """1.2 Verify Pydantic data contract schemas."""
    context = CaseContext(
        case_id="EC_001",
        claimed_order_id="e4834301c8177937d5085580f7454200",
        flags=InternalFlags(order_status="delivered", repeat_customer=True)
    )
    assert context.case_id == "EC_001"
    assert context.policy_version == "EC_POLICY_V2"
    assert context.flags.repeat_customer is True
    assert isinstance(context.affected_entities, AffectedEntities)
    assert context.payment_reconciliation.currency == "BRL"


def test_step1_data_loader_queries():
    """1.3 Verify DataLoader O(1) lookups and helper methods."""
    data_loader = DataLoader()
    
    # Test order lookup
    test_order_id = "9b75cdaf2d85857ef023980e15d01546"
    order = data_loader.get_order(test_order_id)
    assert isinstance(order, dict)
    if order:
        assert order.get("order_id") == test_order_id

        # Test customer ID lookup
        customer_id = data_loader.get_customer_id_by_order(test_order_id)
        assert customer_id != ""

        # Test customer unique ID lookup
        unique_id = data_loader.get_customer_unique_id(customer_id)
        assert unique_id != ""

        # Test items and payments lookup
        items = data_loader.get_order_items(test_order_id)
        payments = data_loader.get_order_payments(test_order_id)
        assert isinstance(items, list)
        assert isinstance(payments, list)


def test_step1_category_translation():
    """1.3 Verify category names remain in the source language."""
    data_loader = DataLoader()
    translated = data_loader.translate_category("perfumaria")
    assert translated == "perfumaria"
