"""Smart Home IoT Actuation Tools (Matter & Tuya Integration)."""
import logging
from typing import Any, Dict, Optional, Union
from core.schema import (
    ActionType,
    DeterministicRouterCommand,
    IoTDeviceAction,
    IoTDeviceCommand,
)
from integrations.tuya_client import tuya_client

logger = logging.getLogger(__name__)


async def control_smart_device_tool(
    device_id: str,
    command: str,
    device_type: str = "smart_bulb",
    value: Optional[Union[int, float, str, bool]] = None,
    narrative_response: str = "Perintah IoT berhasil dikirimkan ke perangkat."
) -> Dict[str, Any]:
    """Sends control actuation (e.g. on/off, dimming, lock) to Matter or Tuya IoT devices."""
    cmd_enum = IoTDeviceCommand(command)
    action_payload = IoTDeviceAction(
        action=ActionType.SET_IOT_STATE,
        device_id=device_id,
        device_type=device_type,
        command=cmd_enum,
        value=value,
        narrative_response=narrative_response
    )

    det_cmd = DeterministicRouterCommand(
        target_action=ActionType.SET_IOT_STATE,
        payload=action_payload,
        summary=f"IoT {device_type} [{device_id}] -> {cmd_enum.value} ({value})",
        requires_edge_dispatch=False
    )

    # Actuate via Tuya/Matter integration client
    tuya_result = await tuya_client.send_device_command(
        device_id=device_id,
        command=cmd_enum,
        value=value
    )

    return {
        "status": "SUCCESS",
        "action": ActionType.SET_IOT_STATE.value,
        "command": det_cmd.model_dump(),
        "iot_result": tuya_result,
        "narrative": narrative_response
    }
