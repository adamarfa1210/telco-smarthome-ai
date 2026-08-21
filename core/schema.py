"""Deterministic Schemas and Schema Enforcement for Router Commands."""
import json
import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    SET_TRAFFIC_PRIORITY = "SET_TRAFFIC_PRIORITY"
    ISOLATE_IOT_DEVICE = "ISOLATE_IOT_DEVICE"
    RESTORE_IOT_DEVICE = "RESTORE_IOT_DEVICE"
    SET_IOT_STATE = "SET_IOT_STATE"
    UPGRADE_VAS_BOOST = "UPGRADE_VAS_BOOST"
    DIAGNOSTIC_CHECK = "DIAGNOSTIC_CHECK"


class QoSPriorityClass(str, Enum):
    WORK_EF = "WORK_EF"          # Expedited Forwarding (VoIP/Work Video Call/Conference)
    GAMING_CS4 = "GAMING_CS4"    # Class Selector 4 (Low latency gaming)
    STREAMING_AF = "STREAMING_AF"# Assured Forwarding (4K/8K Video Streaming)
    BEST_EFFORT = "BEST_EFFORT"  # Default Best Effort
    BACKGROUND_BK = "BACKGROUND_BK" # Bulk downloads/backups


class VASPackageType(str, Enum):
    TURBO_SPEED_1GBPS_2H = "TURBO_SPEED_1GBPS_2H"
    GAMING_PING_SHIELD_24H = "GAMING_PING_SHIELD_24H"
    FAMILY_PROTECTION_MONTHLY = "FAMILY_PROTECTION_MONTHLY"
    WORK_FROM_HOME_BOOST_8H = "WORK_FROM_HOME_BOOST_8H"


class IoTDeviceCommand(str, Enum):
    TURN_ON = "TURN_ON"
    TURN_OFF = "TURN_OFF"
    SET_BRIGHTNESS = "SET_BRIGHTNESS"
    SET_TEMPERATURE = "SET_TEMPERATURE"
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"


# --- Action Payload Schemas ---

class TrafficPriorityAction(BaseModel):
    action: Literal[ActionType.SET_TRAFFIC_PRIORITY] = ActionType.SET_TRAFFIC_PRIORITY
    target_mac: str = Field(..., description="Target device MAC address in standard format (e.g. AA:BB:CC:DD:EE:FF)")
    priority_class: QoSPriorityClass = Field(default=QoSPriorityClass.WORK_EF, description="QoS priority profile")
    duration_minutes: int = Field(default=60, ge=1, le=1440, description="Duration in minutes (1 to 1440)")
    download_bandwidth_mbps: Optional[int] = Field(default=None, ge=1, le=10000, description="Optional bandwidth cap/reservation in Mbps")
    upload_bandwidth_mbps: Optional[int] = Field(default=None, ge=1, le=10000, description="Optional upload bandwidth cap/reservation in Mbps")
    narrative_response: str = Field(..., description="User-facing explanation in natural Indonesian or requested language")

    @field_validator("target_mac")
    @classmethod
    def validate_mac(cls, v: str) -> str:
        v = v.strip().upper().replace("-", ":")
        if not re.match(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$", v):
            raise ValueError(f"Invalid MAC address format: {v}")
        return v


class DeviceIsolationAction(BaseModel):
    action: Literal[ActionType.ISOLATE_IOT_DEVICE, ActionType.RESTORE_IOT_DEVICE]
    target_mac: str = Field(..., description="Target device MAC address to isolate/restore")
    quarantine_zone: str = Field(default="quarantine_vlan99", description="Designated nftables isolation zone")
    reason: str = Field(..., description="Reason for isolation or restoration")
    narrative_response: str = Field(..., description="User-facing explanation")

    @field_validator("target_mac")
    @classmethod
    def validate_mac(cls, v: str) -> str:
        v = v.strip().upper().replace("-", ":")
        if not re.match(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$", v):
            raise ValueError(f"Invalid MAC address format: {v}")
        return v


class IoTDeviceAction(BaseModel):
    action: Literal[ActionType.SET_IOT_STATE] = ActionType.SET_IOT_STATE
    device_id: str = Field(..., description="Matter node ID or Tuya device ID")
    device_type: str = Field(default="generic_iot", description="Device category e.g., smart_bulb, smart_plug, lock")
    command: IoTDeviceCommand = Field(..., description="IoT action command")
    value: Optional[Union[int, float, str, bool]] = Field(default=None, description="Optional value (e.g. brightness 0-100 or temp)")
    narrative_response: str = Field(..., description="User-facing explanation")


class VASBillingAction(BaseModel):
    action: Literal[ActionType.UPGRADE_VAS_BOOST] = ActionType.UPGRADE_VAS_BOOST
    subscriber_id: str = Field(..., description="Customer / Account ID")
    package_type: VASPackageType = Field(..., description="VAS Turbo / Add-on package identifier")
    duration_hours: int = Field(default=2, ge=1, le=720, description="Duration of package")
    auto_renew: bool = Field(default=False, description="Whether package auto-renews")
    narrative_response: str = Field(..., description="User-facing explanation")


class DiagnosticAction(BaseModel):
    action: Literal[ActionType.DIAGNOSTIC_CHECK] = ActionType.DIAGNOSTIC_CHECK
    diagnostic_type: Literal["ping", "speedtest", "wifi_interference", "dns_check"] = "ping"
    target_host: Optional[str] = Field(default="8.8.8.8", description="Target host or IP for diagnostic")
    narrative_response: str = Field(..., description="User-facing explanation")


# Discriminated Union for All Possible Deterministic Commands
RouterActionUnion = Union[
    TrafficPriorityAction,
    DeviceIsolationAction,
    IoTDeviceAction,
    VASBillingAction,
    DiagnosticAction,
]


class DeterministicRouterCommand(BaseModel):
    """Complete structured output payload generated by the AI Reasoning Engine."""
    target_action: ActionType = Field(..., description="Primary action category")
    payload: RouterActionUnion = Field(..., description="Strictly validated action schema payload")
    summary: str = Field(..., description="Brief human-readable summary of executed action")
    requires_edge_dispatch: bool = Field(default=True, description="Whether this command must be sent to RG router kernel")


class AgentOutput(BaseModel):
    """Final output returned to user API."""
    success: bool = True
    action_type: ActionType
    command: Dict[str, Any]
    user_message: str
    edge_dispatched: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


def validate_and_enforce_schema(raw_output: Union[str, Dict[str, Any]]) -> DeterministicRouterCommand:
    """
    Enforces deterministic schema parsing.
    Extracts JSON from LLM text responses, validates against strict Pydantic models,
    and guarantees a valid DeterministicRouterCommand output.
    """
    data: Dict[str, Any] = {}

    if isinstance(raw_output, str):
        # Clean markdown codeblocks if present
        clean_text = raw_output.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        # Try parsing JSON
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            # Try regex extraction of JSON object
            match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError as err:
                    raise ValueError(f"Unable to parse structured JSON from LLM output: {err}")
            else:
                raise ValueError("No valid JSON structure found in output.")
    elif isinstance(raw_output, dict):
        data = raw_output
    else:
        raise TypeError(f"Expected str or dict, got {type(raw_output).__name__}")

    # Determine action type and validate corresponding payload
    action_str = data.get("target_action") or data.get("action")
    if not action_str:
        raise ValueError("Missing 'target_action' or 'action' field in output.")

    try:
        action_type = ActionType(action_str)
    except ValueError:
        raise ValueError(f"Unrecognized action type: {action_str}")

    # Construct payload if raw flat dict was given
    payload_data = data.get("payload", data)
    if "action" not in payload_data:
        payload_data["action"] = action_type.value

    # Parse specific payload
    payload: RouterActionUnion
    if action_type == ActionType.SET_TRAFFIC_PRIORITY:
        payload = TrafficPriorityAction.model_validate(payload_data)
        requires_edge = True
    elif action_type in (ActionType.ISOLATE_IOT_DEVICE, ActionType.RESTORE_IOT_DEVICE):
        payload = DeviceIsolationAction.model_validate(payload_data)
        requires_edge = True
    elif action_type == ActionType.SET_IOT_STATE:
        payload = IoTDeviceAction.model_validate(payload_data)
        requires_edge = False
    elif action_type == ActionType.UPGRADE_VAS_BOOST:
        payload = VASBillingAction.model_validate(payload_data)
        requires_edge = False
    elif action_type == ActionType.DIAGNOSTIC_CHECK:
        payload = DiagnosticAction.model_validate(payload_data)
        requires_edge = True
    else:
        raise ValueError(f"Unsupported action type for validation: {action_type}")

    summary = data.get("summary") or payload_data.get("narrative_response", f"Executed {action_type.value}")
    return DeterministicRouterCommand(
        target_action=action_type,
        payload=payload,
        summary=summary,
        requires_edge_dispatch=requires_edge
    )
