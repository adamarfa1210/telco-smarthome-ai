"""Value-Added Services (VAS) & Operator Billing Tools."""
import logging
from typing import Any, Dict
from core.schema import (
    ActionType,
    DeterministicRouterCommand,
    VASBillingAction,
    VASPackageType,
)
from integrations.billing_client import billing_client

logger = logging.getLogger(__name__)


async def purchase_vas_boost_tool(
    subscriber_id: str,
    package_type: str,
    duration_hours: int = 2,
    auto_renew: bool = False,
    narrative_response: str = "Paket Value-Added Service berhasil diaktifkan."
) -> Dict[str, Any]:
    """Activates an on-demand speed boost or latency shield via the Operator Core Billing System."""
    pkg_enum = VASPackageType(package_type)
    action_payload = VASBillingAction(
        action=ActionType.UPGRADE_VAS_BOOST,
        subscriber_id=subscriber_id,
        package_type=pkg_enum,
        duration_hours=duration_hours,
        auto_renew=auto_renew,
        narrative_response=narrative_response
    )

    det_cmd = DeterministicRouterCommand(
        target_action=ActionType.UPGRADE_VAS_BOOST,
        payload=action_payload,
        summary=f"VAS Boost {pkg_enum.value} for sub {subscriber_id} ({duration_hours}h)",
        requires_edge_dispatch=False
    )

    # Actuate via Operator Core Billing Client
    billing_result = await billing_client.activate_vas_package(
        subscriber_id=subscriber_id,
        package_type=pkg_enum,
        duration_hours=duration_hours,
        auto_renew=auto_renew
    )

    return {
        "status": "SUCCESS",
        "action": ActionType.UPGRADE_VAS_BOOST.value,
        "command": det_cmd.model_dump(),
        "billing_result": billing_result,
        "narrative": narrative_response
    }


async def query_billing_profile_tool(subscriber_id: str) -> Dict[str, Any]:
    """Queries current subscriber plan, speed tier, and balance."""
    profile = await billing_client.get_subscriber_profile(subscriber_id)
    return {
        "status": "SUCCESS",
        "subscriber_id": subscriber_id,
        "profile": profile
    }
