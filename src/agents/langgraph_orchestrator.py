"""LangGraph & LangChain State Graph Orchestrator for Multi-Agent Dispute Resolution."""

from __future__ import annotations

import json
import os
from typing import TypedDict, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from src.schemas import CaseContext
from src.data_loader import DataLoader
from src.agents.customer_agent import CustomerAgent
from src.agents.order_product_agent import OrderProductAgent
from src.agents.payment_agent import PaymentAgent
from src.agents.delivery_agent import DeliveryAgent
from src.agents.policy_agent import PolicyAgent
from src.agents.verifier_agent import VerifierAgent


class DisputeGraphState(TypedDict):
    """LangGraph Shared State across all Domain & Policy Agents."""
    case_id: str
    claimed_order_id: str
    context: CaseContext
    output_dir: Optional[str]
    trace_file: Optional[str]
    output: Optional[Dict[str, Any]]


class LangGraphDisputeOrchestrator:
    """Multi-Agent Pipeline constructed using LangGraph StateGraph."""

    def __init__(
        self,
        data_loader: Optional[DataLoader] = None,
        enable_llm: bool = False,
    ):
        self.data_loader = data_loader or DataLoader()
        self.customer_agent = CustomerAgent()
        self.order_product_agent = OrderProductAgent()
        self.payment_agent = PaymentAgent()
        self.delivery_agent = DeliveryAgent()
        self.enable_llm = enable_llm
        if enable_llm:
            # Import lazily so the deterministic submission path has no network
            # dependency and does not require the Hugging Face client at runtime.
            from src.agents.llm_agent import LLMReasoningAgent

            self.llm_agent = LLMReasoningAgent()
        self.policy_agent = PolicyAgent()
        self.verifier_agent = VerifierAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(DisputeGraphState)

        # 1. Node definitions
        def customer_node(state: DisputeGraphState) -> DisputeGraphState:
            state["context"] = self.customer_agent.process(state["context"], self.data_loader)
            return state

        def order_product_node(state: DisputeGraphState) -> DisputeGraphState:
            state["context"] = self.order_product_agent.process(state["context"], self.data_loader)
            return state

        def payment_node(state: DisputeGraphState) -> DisputeGraphState:
            state["context"] = self.payment_agent.process(state["context"], self.data_loader)
            return state

        def delivery_node(state: DisputeGraphState) -> DisputeGraphState:
            state["context"] = self.delivery_agent.process(state["context"], self.data_loader)
            return state

        def llm_reasoning_node(state: DisputeGraphState) -> DisputeGraphState:
            state["context"] = self.llm_agent.process(state["context"])
            return state

        def policy_node(state: DisputeGraphState) -> DisputeGraphState:
            state["context"] = self.policy_agent.process(state["context"])
            return state

        def verifier_node(state: DisputeGraphState) -> DisputeGraphState:
            kwargs = {}
            if state.get("output_dir"):
                kwargs["output_dir"] = state["output_dir"]
            if state.get("trace_file"):
                kwargs["trace_file"] = state["trace_file"]

            out_dict = self.verifier_agent.verify_and_export(state["context"], **kwargs)
            state["output"] = out_dict
            return state

        # 2. Add nodes to graph
        workflow.add_node("customer_agent", customer_node)
        workflow.add_node("order_product_agent", order_product_node)
        workflow.add_node("payment_agent", payment_node)
        workflow.add_node("delivery_agent", delivery_node)
        if self.enable_llm:
            workflow.add_node("llm_agent", llm_reasoning_node)
        workflow.add_node("policy_agent", policy_node)
        workflow.add_node("verifier_agent", verifier_node)

        # 3. Add edges for sequential A2A Handoff flow
        workflow.add_edge(START, "customer_agent")
        workflow.add_edge("customer_agent", "order_product_agent")
        workflow.add_edge("order_product_agent", "payment_agent")
        workflow.add_edge("payment_agent", "delivery_agent")
        if self.enable_llm:
            workflow.add_edge("delivery_agent", "llm_agent")
            workflow.add_edge("llm_agent", "policy_agent")
        else:
            workflow.add_edge("delivery_agent", "policy_agent")
        workflow.add_edge("policy_agent", "verifier_agent")
        workflow.add_edge("verifier_agent", END)

        return workflow.compile()

    def run_case(
        self,
        input_case_path: str,
        output_dir: Optional[str] = None,
        trace_file: Optional[str] = None
    ) -> Dict[str, Any]:
        with open(input_case_path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        case_id = case_data["case_id"]
        customer_request = case_data.get("customer_request", {})
        claimed_order_id = customer_request.get("claimed_order_id", "")

        context = CaseContext(
            case_id=case_id,
            claimed_order_id=claimed_order_id,
            customer_request=customer_request,
            investigation_scope=case_data.get("investigation_scope", {}),
            policy_version=case_data.get("policy_version", "EC_POLICY_V2")
        )

        initial_state: DisputeGraphState = {
            "case_id": case_id,
            "claimed_order_id": claimed_order_id,
            "context": context,
            "output_dir": output_dir,
            "trace_file": trace_file,
            "output": None
        }

        # Invoke LangGraph StateGraph execution
        final_state = self.graph.invoke(initial_state)
        return final_state["output"]
