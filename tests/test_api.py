"""Integration Tests for FastAPI API Gateway."""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert "TR-142" in data["compliance"]


def test_health_and_ready():
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "READY"


def test_telemetry_report_and_fetch_state():
    telemetry_payload = {
        "router_id": "RG-TEST-99",
        "subscriber_id": "SUB-TEST-99",
        "cpu_usage_pct": 25.5,
        "ram_usage_pct": 50.0,
        "wan_download_mbps": 45.2,
        "wan_upload_mbps": 10.1,
        "ping_gateway_ms": 3.5,
        "active_devices": [
            {
                "mac": "00:11:22:33:44:55",
                "ip": "192.168.1.50",
                "hostname": "test-work-laptop",
                "device_type": "laptop_work",
                "rssi_dbm": -45,
                "current_rate_mbps": 100.0
            }
        ]
    }
    # 1. Post telemetry
    post_res = client.post("/api/v1/telemetry/report", json=telemetry_payload)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "INGESTED"

    # 2. Get router state
    get_res = client.get("/api/v1/telemetry/state/RG-TEST-99")
    assert get_res.status_code == 200
    state = get_res.json()
    assert state["router_id"] == "RG-TEST-99"
    assert "00:11:22:33:44:55" in state["active_devices"]


def test_control_command_endpoint_qos():
    control_payload = {
        "user_input": "Tolong prioritaskan laptop kerja saya untuk video conference penting.",
        "router_id": "RG-CPE-001",
        "subscriber_id": "SUB-88192"
    }
    response = client.post("/api/v1/control/command", json=control_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["action_type"] == "SET_TRAFFIC_PRIORITY"
    assert data["edge_dispatched"] is True
    assert "WORK_EF" in data["command"]["payload"]["priority_class"]


def test_control_command_endpoint_isolation():
    control_payload = {
        "user_input": "Isolasi perangkat kamera pintar yang mencurigakan kena serangan malware.",
        "router_id": "RG-CPE-001"
    }
    response = client.post("/api/v1/control/command", json=control_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["action_type"] == "ISOLATE_IOT_DEVICE"


def test_direct_execution_endpoint_valid():
    direct_payload = {
        "command": {
            "target_action": "SET_TRAFFIC_PRIORITY",
            "payload": {
                "action": "SET_TRAFFIC_PRIORITY",
                "target_mac": "AA:BB:CC:DD:EE:FF",
                "priority_class": "GAMING_CS4",
                "duration_minutes": 120,
                "narrative_response": "Mode gaming aktif."
            },
            "summary": "Gaming priority",
            "requires_edge_dispatch": True
        }
    }
    response = client.post("/api/v1/control/direct-exec", json=direct_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["action_type"] == "SET_TRAFFIC_PRIORITY"


def test_direct_execution_endpoint_tr142_violation():
    violating_payload = {
        "command": {
            "target_action": "ISOLATE_IOT_DEVICE",
            "payload": {
                "action": "ISOLATE_IOT_DEVICE",
                "target_mac": "AA:BB:CC:DD:EE:FF",
                "quarantine_zone": "quarantine_onu_omci_link",
                "reason": "Test breach",
                "narrative_response": "Test"
            }
        }
    }
    response = client.post("/api/v1/control/direct-exec", json=violating_payload)
    assert response.status_code == 400
    assert "TR-142 Security Breach" in response.json()["detail"]


def test_webhooks_billing():
    payload = {
        "event_id": "EVT-BILLING-101",
        "event_type": "VAS_ACTIVATED",
        "subscriber_id": "SUB-88192",
        "package_type": "TURBO_SPEED_1GBPS_2H"
    }
    response = client.post("/api/v1/webhooks/billing", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSED"


def test_webhooks_iot():
    payload = {
        "event_id": "EVT-IOT-202",
        "device_id": "matter-lock-frontdoor",
        "event_type": "DEVICE_STATUS_CHANGE",
        "data": {"state": "LOCKED"}
    }
    response = client.post("/api/v1/webhooks/iot", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSED"
