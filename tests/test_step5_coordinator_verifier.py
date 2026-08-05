"""Unit tests for Step 5: Verifier Agent, Coordinator Agent, Output Slicing & Trace Logging (Person 5)."""

import os
import json
import tempfile
import pytest
from src.schemas import (
    CaseContext, AffectedEntities, CustomerContext, ProductContext,
    RootCauseAnalysis, CauseCodeRank, PartyResponsible, InternalFlags
)
from src.agents.verifier_agent import VerifierAgent
from src.agents.coordinator_agent import CoordinatorAgent
from src.data_loader import DataLoader


def test_verifier_agent_array_limits_and_export():
    """5.1 Test VerifierAgent slicing array limits to max bounds and writing output files."""
    context = CaseContext(
        case_id="EC_TEST_LIMITS",
        claimed_order_id="ord_test",
        affected_entities=AffectedEntities(
            order_ids=["ord1", "ord2", "ord3", "ord4", "ord5", "ord6"],  # max 5
            item_ids=["item1", "item2", "item3", "item4", "item5", "item6"],  # max 5
            seller_ids=["s1", "s2", "s3", "s4"],  # max 3
            payment_ids=["p1", "p2", "p3", "p4", "p5", "p6"]  # max 5
        ),
        customer_context=CustomerContext(
            customer_unique_id="cust_unique_1",
            related_order_ids=["r1", "r2", "r3", "r4", "r5", "r6"]  # max 5
        ),
        product_context=ProductContext(
            product_ids=["p1", "p2", "p3", "p4", "p5", "p6"],  # max 5
            category_names=["c1", "c2", "c3", "c4", "c5", "c6"]  # max 5
        ),
        evidence_ids=[f"ev_{i}" for i in range(25)],  # max 20
        resolution_actions=[f"act_{i}" for i in range(10)]  # max 5
    )

    with tempfile.TemporaryDirectory() as tmp_out_dir:
        trace_file = os.path.join(tmp_out_dir, "trace.jsonl")
        agent = VerifierAgent()
        out_dict = agent.verify_and_export(context, output_dir=tmp_out_dir, trace_file=trace_file)

        # Check file creation
        out_json_path = os.path.join(tmp_out_dir, "EC_TEST_LIMITS.json")
        assert os.path.exists(out_json_path)
        assert os.path.exists(trace_file)

        # Verify sliced limits in written output
        with open(out_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["affected_entities"]["order_ids"]) <= 5
        assert len(data["affected_entities"]["item_ids"]) <= 5
        assert len(data["affected_entities"]["seller_ids"]) <= 3
        assert len(data["affected_entities"]["payment_ids"]) <= 5
        assert len(data["customer_context"]["related_order_ids"]) <= 5
        assert len(data["product_context"]["product_ids"]) <= 5
        assert len(data["product_context"]["category_names"]) <= 5
        assert len(data["evidence_ids"]) <= 20
        assert len(data["resolution_actions"]) <= 5


def test_verifier_agent_null_handling_no_items():
    """5.1 Test VerifierAgent null handling when has_items is False."""
    context = CaseContext(
        case_id="EC_TEST_NO_ITEMS",
        claimed_order_id="ord_no_items",
        flags=InternalFlags(has_items=False)
    )

    with tempfile.TemporaryDirectory() as tmp_out_dir:
        trace_file = os.path.join(tmp_out_dir, "trace.jsonl")
        agent = VerifierAgent()
        out_dict = agent.verify_and_export(context, output_dir=tmp_out_dir, trace_file=trace_file)

        assert out_dict["payment_reconciliation"]["item_total_brl"] is None
        assert out_dict["payment_reconciliation"]["freight_total_brl"] is None
        assert out_dict["payment_reconciliation"]["expected_total_brl"] is None
        assert out_dict["payment_reconciliation"]["difference_brl"] is None
        assert out_dict["payment_reconciliation"]["reconciled"] is None


def test_coordinator_agent_end_to_end_single_case():
    """5.2 Test CoordinatorAgent orchestrating a full pipeline run for an input case file."""
    from src.config import INPUT_DIR
    input_file = os.path.join(INPUT_DIR, "EC_001.json")
    if not os.path.exists(input_file):
        pytest.skip(f"Input file {input_file} not found.")

    with tempfile.TemporaryDirectory() as tmp_out_dir:
        trace_file = os.path.join(tmp_out_dir, "trace.jsonl")
        coordinator = CoordinatorAgent()
        res = coordinator.run_case(input_file, output_dir=tmp_out_dir, trace_file=trace_file)

        assert res["case_id"] == "EC_001"
        assert "case_assessment" in res
        assert "primary_issue" in res["case_assessment"]
        assert res["case_assessment"]["confidence"] == 0.95
        assert os.path.exists(os.path.join(tmp_out_dir, "EC_001.json"))
