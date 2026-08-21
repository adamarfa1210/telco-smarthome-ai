"""Natural Language Control & LangGraph Invocation Routes."""
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agent.graph import app_graph
from api.routes.telemetry import ROUTER_STATE_CACHE
from core.schema import AgentOutput, DeterministicRouterCommand, validate_and_enforce_schema
from core.security import verify_action_security

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/control", tags=["Control"])


class ControlCommandRequest(BaseModel):
    user_input: str = Field(..., min_length=2, description="Natural language command from Mobile App / Dashboard")
    router_id: str = Field(default="RG-CPE-001", description="Target router ID")
    subscriber_id: Optional[str] = Field(default=None, description="Subscriber / Customer ID")
    device_context_override: Optional[Dict[str, Any]] = Field(default=None, description="Optional active devices override")


@router.post("/command", response_model=AgentOutput, status_code=status.HTTP_200_OK)
async def process_user_command(req: ControlCommandRequest):
    """
    Primary orchestration endpoint:
    1. Reads router working state.
    2. Runs LangGraph ReAct decision engine.
    3. Enforces Outlines-style deterministic JSON schema.
    4. Dispatches to Edge CPE / IoT / Billing.
    5. Returns formatted response.
    """
    # Fetch cached state
    cached_state = ROUTER_STATE_CACHE.get(req.router_id, {
        "router_id": req.router_id,
        "subscriber_id": req.subscriber_id or "SUB-DEFAULT",
        "active_devices": {},
        "qos_policy": {},
        "security_status": {},
        "latest_telemetry": {}
    })

    subscriber_id = req.subscriber_id or cached_state.get("subscriber_id", "SUB-88192")
    active_devices = req.device_context_override or cached_state.get("active_devices", {})
    qos_policy = cached_state.get("qos_policy", {})
    latest_telemetry = cached_state.get("latest_telemetry", {})

    # Prepare LangGraph state
    initial_state = {
        "router_id": req.router_id,
        "subscriber_id": subscriber_id,
        "user_prompt": req.user_input,
        "messages": [{"role": "user", "content": req.user_input}],
        "active_devices": active_devices,
        "qos_policy": qos_policy,
        "security_status": cached_state.get("security_status", {}),
        "latest_telemetry": latest_telemetry,
        "structured_command": None,
        "execution_result": None,
        "final_narrative": None,
        "error": None
    }

    try:
        final_state = await app_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"LangGraph execution failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing reasoning graph: {str(e)}"
        )

    structured_cmd = final_state.get("structured_command")
    if not structured_cmd:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to formulate a valid deterministic command."
        )

    action_type = structured_cmd.get("target_action", "UNKNOWN")
    narrative = final_state.get("final_narrative") or structured_cmd.get("summary", "Perintah berhasil diproses.")
    exec_res = final_state.get("execution_result", {})

    return AgentOutput(
        success=True,
        action_type=action_type,
        command=structured_cmd,
        user_message=narrative,
        edge_dispatched=structured_cmd.get("requires_edge_dispatch", False),
        metadata={
            "router_id": req.router_id,
            "subscriber_id": subscriber_id,
            "execution_details": exec_res
        }
    )


class DirectExecutionRequest(BaseModel):
    command: Dict[str, Any] = Field(..., description="Pre-validated JSON payload")
    router_id: str = Field(default="RG-CPE-001")


@router.post("/direct-exec", response_model=AgentOutput, status_code=status.HTTP_200_OK)
async def direct_execute_command(req: DirectExecutionRequest):
    """Admin endpoint for executing pre-formed deterministic commands under strict schema validation."""
    try:
        validated_cmd = validate_and_enforce_schema(req.command)
        verify_action_security(validated_cmd)
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    return AgentOutput(
        success=True,
        action_type=validated_cmd.target_action,
        command=validated_cmd.model_dump(),
        user_message=validated_cmd.summary,
        edge_dispatched=validated_cmd.requires_edge_dispatch
    )
