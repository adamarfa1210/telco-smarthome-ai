"""Privacy-Preserving Router Telemetry Ingestion Routes."""
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agent.state import DeviceProfile, TelemetrySnapshot
from core.security import PrivacySanitizer, TR142Validator

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

# Global In-Memory Working State Cache (keyed by router_id)
ROUTER_STATE_CACHE: Dict[str, Dict[str, Any]] = {
    "RG-CPE-001": {
        "router_id": "RG-CPE-001",
        "subscriber_id": "SUB-88192",
        "active_devices": {
            "A4:C3:F0:12:89:AB": {
                "mac": "A4:C3:F0:12:89:AB",
                "ip": "192.168.1.105",
                "hostname": "laptop-thinkpad-work",
                "device_type": "laptop_work",
                "interface": "wlan0",
                "rssi_dbm": -52,
                "current_rate_mbps": 85.0,
                "is_isolated": False,
                "qos_class": "BEST_EFFORT"
            },
            "B8:27:EB:45:67:89": {
                "mac": "B8:27:EB:45:67:89",
                "ip": "192.168.1.110",
                "hostname": "pc-gaming-rig",
                "device_type": "pc_gaming",
                "interface": "eth0",
                "rssi_dbm": -30,
                "current_rate_mbps": 120.0,
                "is_isolated": False,
                "qos_class": "BEST_EFFORT"
            },
            "CC:2D:E0:99:88:77": {
                "mac": "CC:2D:E0:99:88:77",
                "ip": "192.168.1.145",
                "hostname": "smart-cam-porch",
                "device_type": "camera_iot",
                "interface": "wlan1",
                "rssi_dbm": -68,
                "current_rate_mbps": 4.5,
                "is_isolated": False,
                "qos_class": "BEST_EFFORT"
            }
        },
        "qos_policy": {
            "active_priorities": {},
            "cake_bandwidth_cap_mbps": 100
        },
        "security_status": {
            "isolated_devices": [],
            "threat_alerts": []
        },
        "latest_telemetry": {
            "timestamp": time.time(),
            "router_id": "RG-CPE-001",
            "cpu_usage_pct": 14.2,
            "ram_usage_pct": 38.5,
            "wan_download_mbps": 22.4,
            "wan_upload_mbps": 4.8,
            "ping_gateway_ms": 3.2,
            "connected_clients_count": 3
        }
    }
}


class DeviceTelemetryReport(BaseModel):
    mac: str = Field(..., description="Device MAC address")
    ip: str = Field(..., description="Assigned IP address")
    hostname: Optional[str] = Field(default="Unknown", description="DHCP hostname")
    device_type: Optional[str] = Field(default="generic")
    rssi_dbm: Optional[int] = Field(default=-60)
    current_rate_mbps: Optional[float] = Field(default=20.0)


class RouterTelemetryReportRequest(BaseModel):
    router_id: str = Field(..., description="Identifier of the Residential Gateway CPE")
    subscriber_id: str = Field(..., description="Customer / Account ID")
    cpu_usage_pct: float = Field(..., ge=0, le=100)
    ram_usage_pct: float = Field(..., ge=0, le=100)
    wan_download_mbps: float = Field(..., ge=0)
    wan_upload_mbps: float = Field(..., ge=0)
    ping_gateway_ms: float = Field(default=5.0, ge=0)
    active_devices: List[DeviceTelemetryReport] = Field(default_factory=list)


@router.post("/report", status_code=status.HTTP_200_OK)
async def receive_telemetry_report(report: RouterTelemetryReportRequest):
    """
    Receives anonymized router telemetry data conforming to Privacy-by-Design.
    Enforces TR-142 Layer 3 boundary.
    """
    report_dict = report.model_dump()
    
    # 1. TR-142 Compliance Check
    TR142Validator.verify(report_dict)

    # 2. Update Router Cache
    current = ROUTER_STATE_CACHE.setdefault(report.router_id, {
        "router_id": report.router_id,
        "subscriber_id": report.subscriber_id,
        "active_devices": {},
        "qos_policy": {"active_priorities": {}, "cake_bandwidth_cap_mbps": 100},
        "security_status": {"isolated_devices": [], "threat_alerts": []},
        "latest_telemetry": {}
    })

    # Update active devices
    for dev in report.active_devices:
        clean_mac = dev.mac.upper()
        current["active_devices"][clean_mac] = {
            "mac": clean_mac,
            "ip": dev.ip,
            "hostname": PrivacySanitizer.redact_pii(dev.hostname or "Device"),
            "device_type": dev.device_type or "generic",
            "rssi_dbm": dev.rssi_dbm or -60,
            "current_rate_mbps": dev.current_rate_mbps or 20.0,
            "is_isolated": False,
            "qos_class": "BEST_EFFORT"
        }

    # Update latest telemetry snapshot
    current["latest_telemetry"] = {
        "timestamp": time.time(),
        "router_id": report.router_id,
        "cpu_usage_pct": report.cpu_usage_pct,
        "ram_usage_pct": report.ram_usage_pct,
        "wan_download_mbps": report.wan_download_mbps,
        "wan_upload_mbps": report.wan_upload_mbps,
        "ping_gateway_ms": report.ping_gateway_ms,
        "connected_clients_count": len(report.active_devices)
    }

    return {
        "status": "INGESTED",
        "router_id": report.router_id,
        "active_devices_tracked": len(current["active_devices"]),
        "timestamp": time.time()
    }


@router.get("/state/{router_id}", status_code=status.HTTP_200_OK)
async def get_router_state(router_id: str):
    """Fetches the current working state of the router."""
    if router_id not in ROUTER_STATE_CACHE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Router state for '{router_id}' not found."
        )
    return ROUTER_STATE_CACHE[router_id]
