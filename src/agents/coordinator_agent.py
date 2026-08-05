"""Coordinator Agent powered by LangGraph StateGraph orchestration."""

from __future__ import annotations

import json
from typing import Dict, Any, Optional
from src.schemas import CaseContext
from src.data_loader import DataLoader
from src.agents.langgraph_orchestrator import LangGraphDisputeOrchestrator


class CoordinatorAgent:
    """Coordinator Agent invoking the LangGraph Multi-Agent StateGraph."""

    def __init__(self, data_loader: Optional[DataLoader] = None):
        self.data_loader = data_loader or DataLoader()
        self.orchestrator = LangGraphDisputeOrchestrator(data_loader=self.data_loader)

    def run_case(
        self,
        input_case_path: str,
        output_dir: Optional[str] = None,
        trace_file: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.orchestrator.run_case(
            input_case_path=input_case_path,
            output_dir=output_dir,
            trace_file=trace_file
        )
