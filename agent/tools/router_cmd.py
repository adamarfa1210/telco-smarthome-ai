"""Router Command Execution Tools (Linux Kernel QoS tc and nftables)."""
import logging
from typing import Any, Dict, Optional
from core.schema import (
    ActionType,
    DeterministicRouterCommand,
    DeviceIsolationAction,
    DiagnosticAction,
    QoSPriorityClass,
    TrafficPriorityAction,
)
from core.security import verify_action_security
from integrations.router_client import router_client

logger = logging.getLogger(__name__)


async def set_traffic_priority_tool(
    target_mac: str,
    priority_class: str = "WORK_EF",
    duration_minutes: int = 60,
    download_bandwidth_mbps: Optional[int] = None,
    upload_bandwidth_mbps: Optional[int] = None,
    narrative_response: str = "Prioritas lalu lintas jaringan telah diperbarui.",
    router_host: str = "192.168.1.1"
) -> Dict[str, Any]:
    """
    Formulates a deterministic QoS traffic control command (Linux tc CAKE/DSCP)
    and dispatches it securely to the OpenWrt Residential Gateway CPE.
    """
    qos_enum = QoSPriorityClass(priority_class)
    action_payload = TrafficPriorityAction(
        target_mac=target_mac,
        priority_class=qos_enum,
        duration_minutes=duration_minutes,
        download_bandwidth_mbps=download_bandwidth_mbps,
        upload_bandwidth_mbps=upload_bandwidth_mbps,
        narrative_response=narrative_response
    )

    command = DeterministicRouterCommand(
        target_action=ActionType.SET_TRAFFIC_PRIORITY,
        payload=action_payload,
        summary=f"Set QoS priority {qos_enum.value} for MAC {target_mac} ({duration_minutes}m)",
        requires_edge_dispatch=True
    )

    # Security check
    verify_action_security(command)

    # Dispatch to edge router
    result = await router_client.dispatch_command(router_host, command)
    return {
        "status": "SUCCESS",
        "action": ActionType.SET_TRAFFIC_PRIORITY.value,
        "command": command.model_dump(),
        "edge_result": result,
        "narrative": narrative_response
    }


async def isolate_iot_device_tool(
    target_mac: str,
    reason: str = "Anomalous traffic detected",
    quarantine_zone: str = "quarantine_vlan99",
    narrative_response: str = "Perangkat IoT telah berhasil diisolasi ke zona karantina demi keamanan jaringan.",
    router_host: str = "192.168.1.1"
) -> Dict[str, Any]:
    """
    Formulates an nftables quarantine rule to isolate a compromised IoT device
    from accessing local LAN devices and restrict its WAN access.
    """
    action_payload = DeviceIsolationAction(
        action=ActionType.ISOLATE_IOT_DEVICE,
        target_mac=target_mac,
        quarantine_zone=quarantine_zone,
        reason=reason,
        narrative_response=narrative_response
    )

    command = DeterministicRouterCommand(
        target_action=ActionType.ISOLATE_IOT_DEVICE,
        payload=action_payload,
        summary=f"Isolate device {target_mac} into {quarantine_zone}: {reason}",
        requires_edge_dispatch=True
    )

    verify_action_security(command)
    result = await router_client.dispatch_command(router_host, command)
    return {
        "status": "SUCCESS",
        "action": ActionType.ISOLATE_IOT_DEVICE.value,
        "command": command.model_dump(),
        "edge_result": result,
        "narrative": narrative_response
    }


async def restore_iot_device_tool(
    target_mac: str,
    reason: str = "Security clearance restored",
    narrative_response: str = "Perangkat IoT telah dikembalikan ke jaringan utama.",
    router_host: str = "192.168.1.1"
) -> Dict[str, Any]:
    """Removes the nftables quarantine isolation rule for a cleared device."""
    action_payload = DeviceIsolationAction(
        action=ActionType.RESTORE_IOT_DEVICE,
        target_mac=target_mac,
        quarantine_zone="lan_main",
        reason=reason,
        narrative_response=narrative_response
    )

    command = DeterministicRouterCommand(
        target_action=ActionType.RESTORE_IOT_DEVICE,
        payload=action_payload,
        summary=f"Restore device {target_mac} to main network: {reason}",
        requires_edge_dispatch=True
    )

    verify_action_security(command)
    result = await router_client.dispatch_command(router_host, command)
    return {
        "status": "SUCCESS",
        "action": ActionType.RESTORE_IOT_DEVICE.value,
        "command": command.model_dump(),
        "edge_result": result,
        "narrative": narrative_response
    }


async def run_diagnostic_tool(
    diagnostic_type: str = "ping",
    target_host: str = "8.8.8.8",
    narrative_response: str = "Diagnostik jaringan berhasil dijalankan.",
    router_host: str = "192.168.1.1"
) -> Dict[str, Any]:
    """Triggers an edge diagnostic check (e.g. latency ping or speedtest)."""
    action_payload = DiagnosticAction(
        action=ActionType.DIAGNOSTIC_CHECK,
        diagnostic_type=diagnostic_type,  # type: ignore
        target_host=target_host,
        narrative_response=narrative_response
    )

    command = DeterministicRouterCommand(
        target_action=ActionType.DIAGNOSTIC_CHECK,
        payload=action_payload,
        summary=f"Diagnostic check {diagnostic_type} towards {target_host}",
        requires_edge_dispatch=True
    )

    verify_action_security(command)
    result = await router_client.dispatch_command(router_host, command)
    return {
        "status": "SUCCESS",
        "action": ActionType.DIAGNOSTIC_CHECK.value,
        "command": command.model_dump(),
        "edge_result": result,
        "narrative": narrative_response
    }
