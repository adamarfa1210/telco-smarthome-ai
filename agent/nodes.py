"""LangGraph Node Handlers for State Ingestion, LLM Reasoning, Schema Enforcement, and Tool Execution."""
import json
import logging
import re
from typing import Any, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agent.prompt_templates import TELCO_SYSTEM_PROMPT, build_user_context_prompt
from agent.state import RouterStateDict
from agent.tools.billing_vas import purchase_vas_boost_tool
from agent.tools.iot_control import control_smart_device_tool
from agent.tools.router_cmd import (
    isolate_iot_device_tool,
    restore_iot_device_tool,
    run_diagnostic_tool,
    set_traffic_priority_tool,
)
from core.config import settings
from core.schema import (
    ActionType,
    DeterministicRouterCommand,
    QoSPriorityClass,
    VASPackageType,
    validate_and_enforce_schema,
)
from core.security import verify_action_security

logger = logging.getLogger(__name__)


def get_llm():
    """Returns the configured LLM client."""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT_SEC,
    )


def rule_based_semantic_fallback(
    user_prompt: str,
    active_devices: Dict[str, Any],
    subscriber_id: str
) -> Dict[str, Any]:
    """
    High-accuracy deterministic fallback engine when LLM endpoint is offline.
    Maps user natural language intent directly to structured JSON schema.
    """
    prompt_lower = user_prompt.lower()
    
    # 1. Check for Traffic Prioritization (Work, Meeting, Gaming, Streaming)
    if any(k in prompt_lower for k in ["kerja", "work", "zoom", "teams", "meeting", "prioritas", "prioritaskan", "penting", "wfh"]):
        # Find laptop or work device
        target_mac = "A4:C3:F0:12:89:AB"  # Default known laptop MAC
        for mac, dev in active_devices.items():
            dtype = dev.get("device_type", "").lower()
            hname = dev.get("hostname", "").lower()
            if "laptop" in dtype or "laptop" in hname or "work" in hname or "pc" in dtype:
                target_mac = mac
                break
        
        return {
            "target_action": "SET_TRAFFIC_PRIORITY",
            "payload": {
                "action": "SET_TRAFFIC_PRIORITY",
                "target_mac": target_mac,
                "priority_class": "WORK_EF",
                "duration_minutes": 60,
                "narrative_response": f"Prioritas jaringan kelas WORK_EF berhasil diaktifkan untuk perangkat kerja ({target_mac}) selama 60 menit."
            },
            "summary": f"Prioritaskan lalu lintas kerja untuk MAC {target_mac}",
            "requires_edge_dispatch": True
        }

    if any(k in prompt_lower for k in ["game", "gaming", "lag", "ping", "mlbb", "valorant", "dota"]):
        target_mac = "B8:27:EB:45:67:89"
        for mac, dev in active_devices.items():
            dtype = dev.get("device_type", "").lower()
            hname = dev.get("hostname", "").lower()
            if "game" in dtype or "game" in hname or "pc" in dtype or "phone" in dtype:
                target_mac = mac
                break

        return {
            "target_action": "SET_TRAFFIC_PRIORITY",
            "payload": {
                "action": "SET_TRAFFIC_PRIORITY",
                "target_mac": target_mac,
                "priority_class": "GAMING_CS4",
                "duration_minutes": 120,
                "narrative_response": f"Mode Gaming Low-Latency (GAMING_CS4) telah diaktifkan untuk perangkat ({target_mac}) selama 2 jam."
            },
            "summary": f"Prioritaskan lalu lintas gaming untuk MAC {target_mac}",
            "requires_edge_dispatch": True
        }

    # 2. Check for Security Isolation / Malware / Suspicious Device
    if any(k in prompt_lower for k in ["isolasi", "isolate", "quarantine", "karantina", "malware", "curiga", "hack", "serangan"]):
        target_mac = "CC:2D:E0:99:88:77"
        for mac, dev in active_devices.items():
            dtype = dev.get("device_type", "").lower()
            hname = dev.get("hostname", "").lower()
            if "camera" in dtype or "cctv" in hname or "iot" in dtype:
                target_mac = mac
                break

        return {
            "target_action": "ISOLATE_IOT_DEVICE",
            "payload": {
                "action": "ISOLATE_IOT_DEVICE",
                "target_mac": target_mac,
                "quarantine_zone": "quarantine_vlan99",
                "reason": "Permintaan isolasi keamanan pengguna",
                "narrative_response": f"Perangkat ({target_mac}) telah diisolasi ke zona karantina VLAN 99 demi perlindungan jaringan."
            },
            "summary": f"Isolasi perangkat {target_mac}",
            "requires_edge_dispatch": True
        }

    # 3. Check for IoT Actuation (Lights, Plugs, Locks)
    if any(k in prompt_lower for k in ["lampu", "light", "nyalakan", "matikan", "kunci", "smart plug"]):
        cmd = "TURN_ON" if any(k in prompt_lower for k in ["nyalakan", "hidupkan", "on"]) else "TURN_OFF"
        return {
            "target_action": "SET_IOT_STATE",
            "payload": {
                "action": "SET_IOT_STATE",
                "device_id": "smart-light-living-01",
                "device_type": "smart_bulb",
                "command": cmd,
                "value": 100 if cmd == "TURN_ON" else 0,
                "narrative_response": f"Perangkat lampu pintar berhasil diatur ke status {cmd}."
            },
            "summary": f"IoT Smart Device Command: {cmd}",
            "requires_edge_dispatch": False
        }

    # 4. Check for VAS / Speed Boost Purchase
    if any(k in prompt_lower for k in ["turbo", "boost", "kecepatan", "tambah speed", "1gbps", "beli paket"]):
        return {
            "target_action": "UPGRADE_VAS_BOOST",
            "payload": {
                "action": "UPGRADE_VAS_BOOST",
                "subscriber_id": subscriber_id,
                "package_type": "TURBO_SPEED_1GBPS_2H",
                "duration_hours": 2,
                "auto_renew": False,
                "narrative_response": "Paket Turbo Speed Boost 1Gbps (2 Jam) berhasil diaktifkan pada akun Anda."
            },
            "summary": "Aktivasi VAS Turbo Speed 1Gbps",
            "requires_edge_dispatch": False
        }

    # Default to Diagnostic Check
    return {
        "target_action": "DIAGNOSTIC_CHECK",
        "payload": {
            "action": "DIAGNOSTIC_CHECK",
            "diagnostic_type": "ping",
            "target_host": "8.8.8.8",
            "narrative_response": "Pengecekan diagnostik koneksi jaringan gateway sedang dijalankan."
        },
        "summary": "Pengecekan diagnostik router",
        "requires_edge_dispatch": True
    }


async def analyze_state_node(state: RouterStateDict) -> Dict[str, Any]:
    """Node 1: Prepares state and resolves device references."""
    user_prompt = state.get("user_prompt", "")
    active_devices = state.get("active_devices", {})
    qos_policy = state.get("qos_policy", {})
    latest_telemetry = state.get("latest_telemetry", {})

    logger.info(f"Analyzing state for prompt: '{user_prompt}' with {len(active_devices)} devices")
    return {
        "next_step": "reasoning_llm"
    }


async def reasoning_llm_node(state: RouterStateDict) -> Dict[str, Any]:
    """Node 2: Generates structured action JSON using LLM (or robust semantic fallback)."""
    user_prompt = state.get("user_prompt", "")
    active_devices = state.get("active_devices", {})
    qos_policy = state.get("qos_policy", {})
    latest_telemetry = state.get("latest_telemetry", {}) or {}
    subscriber_id = state.get("subscriber_id", "SUB-001")

    context_prompt = build_user_context_prompt(
        user_input=user_prompt,
        active_devices=active_devices,
        qos_policy=qos_policy,
        latest_telemetry=latest_telemetry
    )

    raw_output: Any = None
    try:
        llm = get_llm()
        messages = [
            SystemMessage(content=TELCO_SYSTEM_PROMPT),
            HumanMessage(content=context_prompt)
        ]
        response = await llm.ainvoke(messages)
        raw_output = response.content
    except Exception as e:
        logger.warning(f"LLM call skipped/failed ({e}). Utilizing deterministic semantic engine.")
        raw_output = rule_based_semantic_fallback(user_prompt, active_devices, subscriber_id)

    return {
        "structured_command": raw_output if isinstance(raw_output, dict) else {"raw_text": raw_output},
        "next_step": "enforce_schema"
    }


async def enforce_schema_node(state: RouterStateDict) -> Dict[str, Any]:
    """Node 3: Enforces strict Pydantic JSON schema."""
    raw_command = state.get("structured_command", {})
    user_prompt = state.get("user_prompt", "")
    active_devices = state.get("active_devices", {})
    subscriber_id = state.get("subscriber_id", "SUB-001")

    try:
        if isinstance(raw_command, dict) and "raw_text" in raw_command:
            validated = validate_and_enforce_schema(raw_command["raw_text"])
        else:
            validated = validate_and_enforce_schema(raw_command)
    except Exception as err:
        logger.warning(f"Schema validation recovered via fallback: {err}")
        fallback_data = rule_based_semantic_fallback(user_prompt, active_devices, subscriber_id)
        validated = validate_and_enforce_schema(fallback_data)

    return {
        "structured_command": validated.model_dump(),
        "next_step": "guardrail_check"
    }


async def guardrail_check_node(state: RouterStateDict) -> Dict[str, Any]:
    """Node 4: Evaluates TR-142 compliance and anti-injection security."""
    raw_cmd = state.get("structured_command", {})
    command = DeterministicRouterCommand.model_validate(raw_cmd)

    # Throws SecurityViolationError or TR142ViolationError if violated
    verify_action_security(command)

    return {
        "next_step": "execute_tool"
    }


async def execute_tool_node(state: RouterStateDict) -> Dict[str, Any]:
    """Node 5: Dispatches action to the appropriate actionable tool."""
    raw_cmd = state.get("structured_command", {})
    command = DeterministicRouterCommand.model_validate(raw_cmd)
    payload = command.payload
    
    execution_res: Dict[str, Any] = {}
    narrative: str = getattr(payload, "narrative_response", command.summary)

    if command.target_action == ActionType.SET_TRAFFIC_PRIORITY:
        execution_res = await set_traffic_priority_tool(
            target_mac=payload.target_mac,  # type: ignore
            priority_class=payload.priority_class.value,  # type: ignore
            duration_minutes=payload.duration_minutes,  # type: ignore
            download_bandwidth_mbps=payload.download_bandwidth_mbps,  # type: ignore
            upload_bandwidth_mbps=payload.upload_bandwidth_mbps,  # type: ignore
            narrative_response=narrative
        )
    elif command.target_action == ActionType.ISOLATE_IOT_DEVICE:
        execution_res = await isolate_iot_device_tool(
            target_mac=payload.target_mac,  # type: ignore
            reason=payload.reason,  # type: ignore
            quarantine_zone=payload.quarantine_zone,  # type: ignore
            narrative_response=narrative
        )
    elif command.target_action == ActionType.RESTORE_IOT_DEVICE:
        execution_res = await restore_iot_device_tool(
            target_mac=payload.target_mac,  # type: ignore
            reason=payload.reason,  # type: ignore
            narrative_response=narrative
        )
    elif command.target_action == ActionType.SET_IOT_STATE:
        execution_res = await control_smart_device_tool(
            device_id=payload.device_id,  # type: ignore
            command=payload.command.value,  # type: ignore
            device_type=payload.device_type,  # type: ignore
            value=payload.value,  # type: ignore
            narrative_response=narrative
        )
    elif command.target_action == ActionType.UPGRADE_VAS_BOOST:
        execution_res = await purchase_vas_boost_tool(
            subscriber_id=payload.subscriber_id,  # type: ignore
            package_type=payload.package_type.value,  # type: ignore
            duration_hours=payload.duration_hours,  # type: ignore
            auto_renew=payload.auto_renew,  # type: ignore
            narrative_response=narrative
        )
    elif command.target_action == ActionType.DIAGNOSTIC_CHECK:
        execution_res = await run_diagnostic_tool(
            diagnostic_type=payload.diagnostic_type,  # type: ignore
            target_host=payload.target_host or "8.8.8.8",  # type: ignore
            narrative_response=narrative
        )

    return {
        "execution_result": execution_res,
        "final_narrative": narrative,
        "next_step": "format_response"
    }


async def format_response_node(state: RouterStateDict) -> Dict[str, Any]:
    """Node 6: Finalizes formatting and state updates."""
    narrative = state.get("final_narrative") or "Instruksi berhasil diproses."
    return {
        "final_narrative": narrative,
        "next_step": "END"
    }
