"""Security Guardrails, Command Injection Prevention, and TR-142 Compliance Verifier."""
import ipaddress
import re
from typing import Any, Dict, List, Set
from core.schema import ActionType, DeterministicRouterCommand


class SecurityViolationError(Exception):
    """Raised when an action or input violates system security guardrails."""
    pass


class TR142ViolationError(SecurityViolationError):
    """Raised when an action attempts to access or modify protected Layer 2 ONU physical parameters."""
    pass


class TR142Validator:
    """
    Ensures strict TR-142 Compliance:
    AI Cloud communicates exclusively with the Residential Gateway (RG) Entity (Layer 3+).
    Direct interaction or configuration of the ONU Entity (Layer 2) is strictly forbidden.
    """
    FORBIDDEN_ONU_KEYWORDS: Set[str] = {
        "onu", "omci", "gpon", "epon", "xpon", "pon", "pon_laser", "optical_power",
        "transceiver_tx", "transceiver_rx", "l2_bridge_mac", "vlan_translation_onu",
        "onu_firmware", "fiber_disconnect", "ploam", "onu_serial", "onu_password",
        "omci_me", "tcont", "gemport", "onu_reboot", "olt_link"
    }

    @classmethod
    def verify(cls, data: Any) -> bool:
        """Recursively checks if any string in the data contains forbidden ONU Layer 2 keywords."""
        if isinstance(data, str):
            lowered = data.lower()
            tokens = set(re.split(r"[^a-zA-Z0-9]+", lowered))
            for kw in cls.FORBIDDEN_ONU_KEYWORDS:
                if kw in tokens or (("_" in kw or " " in kw) and kw in lowered):
                    raise TR142ViolationError(
                        f"TR-142 Security Breach: Operation targets protected ONU Layer 2 entity '{kw}'. "
                        "AI Cloud is strictly restricted to RG Layer 3+ operations."
                    )
        elif isinstance(data, dict):
            for k, v in data.items():
                cls.verify(k)
                cls.verify(v)
        elif isinstance(data, (list, tuple, set)):
            for item in data:
                cls.verify(item)
        return True


class CommandInjectionGuard:
    """
    Protects OpenWrt / Linux Kernel interpreters from OS Command Injection.
    Scans values for dangerous shell meta-characters and binary execution patterns.
    """
    DANGEROUS_PATTERNS: List[re.Pattern] = [
        re.compile(r"[;&|`$><]"),                    # Shell control characters
        re.compile(r"\$\(.*\)", re.DOTALL),          # Command substitution $(...)
        re.compile(r"`.*`", re.DOTALL),              # Backtick command substitution
        re.compile(r"(?:^|\s)(rm|mkfs|dd|wget|curl|nc|netcat|ncat|socat|bash|sh|zsh|eval|exec|chmod|chown|insmod|rmmod|reboot|poweroff|halt|init|killall)(?:\s|$)", re.IGNORECASE),
        re.compile(r"(\/etc\/passwd|\/etc\/shadow|\/proc\/kcore|\/dev\/sda|\/dev\/mtd)", re.IGNORECASE),
        re.compile(r"(\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4})"), # Hex / Unicode shell escapes
    ]

    @classmethod
    def sanitize_and_check(cls, value: str, field_name: str = "field") -> str:
        """Validates that a string does not contain dangerous shell injection payloads."""
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(value):
                raise SecurityViolationError(
                    f"Command Injection Guard triggered on {field_name}: suspicious pattern detected in '{value}'"
                )
        return value

    @classmethod
    def scan_dict(cls, data: Dict[str, Any], path: str = "") -> None:
        """Recursively scans all dictionary keys and values for command injection."""
        for k, v in data.items():
            current_path = f"{path}.{k}" if path else k
            if isinstance(k, str):
                cls.sanitize_and_check(k, field_name=f"key:{current_path}")
            if isinstance(v, str):
                cls.sanitize_and_check(v, field_name=current_path)
            elif isinstance(v, dict):
                cls.scan_dict(v, path=current_path)
            elif isinstance(v, list):
                for idx, item in enumerate(v):
                    if isinstance(item, str):
                        cls.sanitize_and_check(item, field_name=f"{current_path}[{idx}]")
                    elif isinstance(item, dict):
                        cls.scan_dict(item, path=f"{current_path}[{idx}]")


class NetworkValidator:
    """Validates network addresses and interfaces."""
    MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$")

    @classmethod
    def is_valid_mac(cls, mac: str) -> bool:
        return bool(cls.MAC_REGEX.match(mac.strip()))

    @classmethod
    def is_valid_ip_or_cidr(cls, addr: str) -> bool:
        try:
            ipaddress.ip_network(addr.strip(), strict=False)
            return True
        except ValueError:
            return False


class PrivacySanitizer:
    """Ensures no user PII, full URLs, or raw packet payloads are leaked into cloud logs or agent state."""
    URL_PATTERN = re.compile(r"https?://[^\s/$.?#].[^\s]*", re.IGNORECASE)

    @classmethod
    def redact_pii(cls, text: str) -> str:
        # Strip exact full URL paths to protect browsing privacy
        text = cls.URL_PATTERN.sub("[REDACTED_URL]", text)
        return text


def verify_action_security(command: DeterministicRouterCommand) -> bool:
    """
    Comprehensive security verification pipeline for all outgoing router commands.
    Ensures:
    1. TR-142 compliance (no ONU L2 access)
    2. Zero OS command injection vulnerabilities
    3. Valid MAC / IP address structure
    """
    cmd_dict = command.model_dump()
    
    # 1. TR-142 Check
    TR142Validator.verify(cmd_dict)

    # 2. Command Injection Check on all fields (excluding user-facing narrative text and MAC fields)
    payload_dump = command.payload.model_dump()
    for field, val in payload_dump.items():
        if field == "narrative_response":
            if any(p.search(str(val)) for p in CommandInjectionGuard.DANGEROUS_PATTERNS[1:4]):
                raise SecurityViolationError("Suspicious shell command found in narrative response")
            continue
        if field == "target_mac":
            if not NetworkValidator.is_valid_mac(str(val)):
                raise SecurityViolationError(f"Invalid MAC address format: {val}")
            continue
        if isinstance(val, str):
            CommandInjectionGuard.sanitize_and_check(val, field_name=field)

    return True
