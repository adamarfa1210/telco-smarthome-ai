"""Short-term and Long-term Network State Definitions for LangGraph."""
from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field
from core.schema import (
    DeterministicRouterCommand,
    QoSPriorityClass,
)


class DeviceProfile(BaseModel):
    """Profile of a connected device in the home network."""
    mac: str = Field(..., description="Device MAC address")
    ip: str = Field(..., description="Assigned IPv4/IPv6 address")
    hostname: str = Field(default="Unknown Device", description="Friendly device name or hostname")
    device_type: str = Field(default="generic", description="laptop, phone, pc_gaming, smart_tv, camera, iot")
    interface: str = Field(default="wlan0", description="wlan0, wlan1, eth0")
    rssi_dbm: int = Field(default=-60, description="WiFi Signal Strength in dBm")
    current_rate_mbps: float = Field(default=50.0, description="Current throughput rate")
    is_isolated: bool = Field(default=False, description="Whether device is in quarantine VLAN")
    qos_class: QoSPriorityClass = Field(default=QoSPriorityClass.BEST_EFFORT)


class QoSPolicy(BaseModel):
    """Active traffic prioritization policy on the router."""
    active_priorities: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    cake_bandwidth_cap_mbps: int = Field(default=100)
    gaming_mode_enabled: bool = Field(default=False)
    work_mode_enabled: bool = Field(default=False)


class SecurityStatus(BaseModel):
    """Network threat and quarantine status."""
    isolated_devices: List[str] = Field(default_factory=list)
    threat_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    firewall_strict_mode: bool = Field(default=False)


class TelemetrySnapshot(BaseModel):
    """Real-time anonymized telemetry snapshot."""
    timestamp: float
    router_id: str
    cpu_usage_pct: float = Field(default=12.5)
    ram_usage_pct: float = Field(default=45.0)
    wan_download_mbps: float = Field(default=18.4)
    wan_upload_mbps: float = Field(default=3.2)
    ping_gateway_ms: float = Field(default=4.8)
    connected_clients_count: int = Field(default=5)


class RouterState(BaseModel):
    """Pydantic representation of the working network and conversational state."""
    router_id: str = "RG-CPE-001"
    subscriber_id: str = "SUB-88192"
    user_prompt: str = ""
    messages: List[Dict[str, str]] = Field(default_factory=list)
    active_devices: Dict[str, DeviceProfile] = Field(default_factory=dict)
    qos_policy: QoSPolicy = Field(default_factory=QoSPolicy)
    security_status: SecurityStatus = Field(default_factory=SecurityStatus)
    latest_telemetry: Optional[TelemetrySnapshot] = None
    structured_command: Optional[DeterministicRouterCommand] = None
    execution_result: Optional[Dict[str, Any]] = None
    final_narrative: Optional[str] = None
    error: Optional[str] = None


class RouterStateDict(TypedDict, total=False):
    """TypedDict interface required by LangGraph StateGraph."""
    router_id: str
    subscriber_id: str
    user_prompt: str
    messages: List[Dict[str, str]]
    active_devices: Dict[str, Dict[str, Any]]
    qos_policy: Dict[str, Any]
    security_status: Dict[str, Any]
    latest_telemetry: Optional[Dict[str, Any]]
    structured_command: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]
    final_narrative: Optional[str]
    error: Optional[str]
    next_step: Optional[str]
