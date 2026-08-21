"""StateGraph Orchestrator and ReAct Decision Machine using LangGraph."""
import logging
from typing import Any, Dict
from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    analyze_state_node,
    enforce_schema_node,
    execute_tool_node,
    format_response_node,
    guardrail_check_node,
    reasoning_llm_node,
)
from agent.state import RouterStateDict

logger = logging.getLogger(__name__)


def create_router_graph():
    """Builds and compiles the TelcoCare LangGraph State Machine."""
    workflow = StateGraph(RouterStateDict)

    # 1. Register Nodes
    workflow.add_node("analyze_state", analyze_state_node)
    workflow.add_node("reasoning_llm", reasoning_llm_node)
    workflow.add_node("enforce_schema", enforce_schema_node)
    workflow.add_node("guardrail_check", guardrail_check_node)
    workflow.add_node("execute_tool", execute_tool_node)
    workflow.add_node("format_response", format_response_node)

    # 2. Configure Linear and Conditional Edges
    workflow.add_edge(START, "analyze_state")
    workflow.add_edge("analyze_state", "reasoning_llm")
    workflow.add_edge("reasoning_llm", "enforce_schema")
    workflow.add_edge("enforce_schema", "guardrail_check")
    workflow.add_edge("guardrail_check", "execute_tool")
    workflow.add_edge("execute_tool", "format_response")
    workflow.add_edge("format_response", END)

    # 3. Compile Graph
    compiled_graph = workflow.compile()
    return compiled_graph


# Pre-compiled default application graph instance
app_graph = create_router_graph()
