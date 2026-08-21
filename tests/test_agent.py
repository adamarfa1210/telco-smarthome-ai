"""Tests for LangGraph Stateful Reasoning Engine and Actionable Tools."""
import pytest
from agent.graph import app_graph, create_router_graph
from agent.tools.billing_vas import purchase_vas_boost_tool, query_billing_profile_tool
from agent.tools.iot_control import control_smart_device_tool
from agent.tools.router_cmd import (
    isolate_iot_device_tool,
    restore_iot_device_tool,
    run_diagnostic_tool,
    set_traffic_priority_tool,
)
from core.schema import ActionType


@pytest.mark.asyncio
async def test_set_traffic_priority_tool():
    res = await set_traffic_priority_tool(
        target_mac="A4:C3:F0:12:89:AB",
        priority_class="WORK_EF",
        duration_minutes=60,
        narrative_response="Work priority activated."
    )
    assert res["status"] == "SUCCESS"
    assert res["action"] == ActionType.SET_TRAFFIC_PRIORITY.value
    assert res["command"]["payload"]["target_mac"] == "A4:C3:F0:12:89:AB"


@pytest.mark.asyncio
async def test_isolate_iot_device_tool():
    res = await isolate_iot_device_tool(
        target_mac="CC:2D:E0:99:88:77",
        reason="Suspicious botnet ping",
        quarantine_zone="quarantine_vlan99"
    )
    assert res["status"] == "SUCCESS"
    assert res["action"] == ActionType.ISOLATE_IOT_DEVICE.value


@pytest.mark.asyncio
async def test_restore_iot_device_tool():
    res = await restore_iot_device_tool(
        target_mac="CC:2D:E0:99:88:77",
        reason="Device security verified"
    )
    assert res["status"] == "SUCCESS"
    assert res["action"] == ActionType.RESTORE_IOT_DEVICE.value


@pytest.mark.asyncio
async def test_run_diagnostic_tool():
    res = await run_diagnostic_tool(
        diagnostic_type="ping",
        target_host="8.8.8.8"
    )
    assert res["status"] == "SUCCESS"
    assert res["action"] == ActionType.DIAGNOSTIC_CHECK.value


@pytest.mark.asyncio
async def test_control_smart_device_tool():
    res = await control_smart_device_tool(
        device_id="bulb-living-01",
        command="TURN_ON",
        value=100
    )
    assert res["status"] == "SUCCESS"
    assert res["action"] == ActionType.SET_IOT_STATE.value


@pytest.mark.asyncio
async def test_purchase_vas_boost_tool():
    res = await purchase_vas_boost_tool(
        subscriber_id="SUB-99881",
        package_type="TURBO_SPEED_1GBPS_2H",
        duration_hours=2
    )
    assert res["status"] == "SUCCESS"
    assert res["action"] == ActionType.UPGRADE_VAS_BOOST.value


@pytest.mark.asyncio
async def test_query_billing_profile_tool():
    res = await query_billing_profile_tool(subscriber_id="SUB-99881")
    assert res["status"] == "SUCCESS"
    assert res["profile"]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_langgraph_full_reasoning_pipeline_work_qos():
    initial_state = {
        "router_id": "RG-CPE-001",
        "subscriber_id": "SUB-88192",
        "user_prompt": "Tolong prioritaskan laptop kerja saya untuk rapat penting.",
        "active_devices": {
            "A4:C3:F0:12:89:AB": {
                "mac": "A4:C3:F0:12:89:AB",
                "ip": "192.168.1.105",
                "hostname": "laptop-thinkpad-work",
                "device_type": "laptop_work"
            }
        },
        "qos_policy": {},
        "security_status": {},
        "latest_telemetry": {"wan_download_mbps": 25.0, "ping_gateway_ms": 4.0}
    }

    graph = create_router_graph()
    final_state = await graph.ainvoke(initial_state)

    assert final_state["structured_command"] is not None
    cmd = final_state["structured_command"]
    assert cmd["target_action"] == ActionType.SET_TRAFFIC_PRIORITY.value
    assert cmd["payload"]["target_mac"] == "A4:C3:F0:12:89:AB"
    assert cmd["payload"]["priority_class"] == "WORK_EF"
    assert final_state["execution_result"] is not None
    assert final_state["final_narrative"] is not None
