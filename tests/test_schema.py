"""Tests for Deterministic JSON Schemas and Outlines-style Enforcement."""
import pytest
from core.schema import (
    ActionType,
    DeterministicRouterCommand,
    DeviceIsolationAction,
    DiagnosticAction,
    IoTDeviceAction,
    IoTDeviceCommand,
    QoSPriorityClass,
    TrafficPriorityAction,
    VASBillingAction,
    VASPackageType,
    validate_and_enforce_schema,
)


def test_traffic_priority_schema_valid():
    payload = TrafficPriorityAction(
        target_mac="A4:C3:F0:12:89:AB",
        priority_class=QoSPriorityClass.WORK_EF,
        duration_minutes=60,
        narrative_response="QoS Work Priority set."
    )
    assert payload.target_mac == "A4:C3:F0:12:89:AB"
    assert payload.priority_class == QoSPriorityClass.WORK_EF
    assert payload.duration_minutes == 60


def test_traffic_priority_mac_normalization():
    payload = TrafficPriorityAction(
        target_mac="a4-c3-f0-12-89-ab",
        priority_class=QoSPriorityClass.GAMING_CS4,
        duration_minutes=30,
        narrative_response="QoS Gaming Priority set."
    )
    assert payload.target_mac == "A4:C3:F0:12:89:AB"


def test_traffic_priority_invalid_mac():
    with pytest.raises(ValueError):
        TrafficPriorityAction(
            target_mac="invalid-mac-address",
            priority_class=QoSPriorityClass.WORK_EF,
            duration_minutes=60,
            narrative_response="QoS test"
        )


def test_device_isolation_schema():
    payload = DeviceIsolationAction(
        action=ActionType.ISOLATE_IOT_DEVICE,
        target_mac="CC:2D:E0:99:88:77",
        quarantine_zone="quarantine_vlan99",
        reason="Suspicious botnet activity",
        narrative_response="Device isolated."
    )
    assert payload.action == ActionType.ISOLATE_IOT_DEVICE
    assert payload.quarantine_zone == "quarantine_vlan99"


def test_iot_device_action_schema():
    payload = IoTDeviceAction(
        device_id="light-123",
        command=IoTDeviceCommand.SET_BRIGHTNESS,
        value=75,
        narrative_response="Brightness set to 75%"
    )
    assert payload.command == IoTDeviceCommand.SET_BRIGHTNESS
    assert payload.value == 75


def test_vas_billing_schema():
    payload = VASBillingAction(
        subscriber_id="SUB-12345",
        package_type=VASPackageType.TURBO_SPEED_1GBPS_2H,
        duration_hours=2,
        narrative_response="Turbo speed activated."
    )
    assert payload.package_type == VASPackageType.TURBO_SPEED_1GBPS_2H
    assert payload.duration_hours == 2


def test_validate_and_enforce_schema_json_string():
    raw_json_str = """
    ```json
    {
        "target_action": "SET_TRAFFIC_PRIORITY",
        "payload": {
            "action": "SET_TRAFFIC_PRIORITY",
            "target_mac": "AA:BB:CC:DD:EE:FF",
            "priority_class": "WORK_EF",
            "duration_minutes": 60,
            "narrative_response": "Prioritas kerja aktif."
        },
        "summary": "Set traffic priority",
        "requires_edge_dispatch": true
    }
    ```
    """
    cmd = validate_and_enforce_schema(raw_json_str)
    assert isinstance(cmd, DeterministicRouterCommand)
    assert cmd.target_action == ActionType.SET_TRAFFIC_PRIORITY
    assert cmd.payload.target_mac == "AA:BB:CC:DD:EE:FF"
    assert cmd.requires_edge_dispatch is True


def test_validate_and_enforce_schema_flat_dict():
    raw_dict = {
        "action": "ISOLATE_IOT_DEVICE",
        "target_mac": "11:22:33:44:55:66",
        "quarantine_zone": "quarantine_vlan99",
        "reason": "Anomalous traffic",
        "narrative_response": "Perangkat diisolasi."
    }
    cmd = validate_and_enforce_schema(raw_dict)
    assert cmd.target_action == ActionType.ISOLATE_IOT_DEVICE
    assert cmd.payload.target_mac == "11:22:33:44:55:66"
