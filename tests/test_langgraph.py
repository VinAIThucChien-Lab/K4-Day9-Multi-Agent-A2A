"""Unit test for LangGraph StateGraph Multi-Agent execution."""

import os
import tempfile
import pytest
from src.config import INPUT_DIR
from src.agents.langgraph_orchestrator import LangGraphDisputeOrchestrator


def test_langgraph_orchestrator_invoke():
    """Test invoking the LangGraph StateGraph pipeline on EC_001.json."""
    input_file = os.path.join(INPUT_DIR, "EC_001.json")
    assert os.path.exists(input_file), f"Input file not found: {input_file}"

    orchestrator = LangGraphDisputeOrchestrator()
    with tempfile.TemporaryDirectory() as tmp_dir:
        output = orchestrator.run_case(
            input_file,
            output_dir=tmp_dir,
            trace_file=os.path.join(tmp_dir, "trace.jsonl"),
        )

    assert isinstance(output, dict)
    assert output["case_id"] == "EC_001"
    assert "case_assessment" in output
    assert "primary_issue" in output["case_assessment"]
    assert output["case_assessment"]["primary_issue"] == "unsupported_late_claim"
    assert output["financial_resolution"]["recommended_refund_brl"] == 0.0
    print("\nLangGraph StateGraph invocation passed successfully for EC_001!")
