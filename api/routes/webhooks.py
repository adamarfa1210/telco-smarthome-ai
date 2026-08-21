"""Webhook Ingestion Routes for Billing and IoT Events."""
import logging
import time
from typing import Any, Dict
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class BillingWebhookPayload(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="e.g. VAS_ACTIVATED, VAS_EXPIRED, PLAN_UPGRADE")
    subscriber_id: str = Field(..., description="Customer ID")
    package_type: str
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IoTWebhookPayload(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    device_id: str = Field(..., description="Matter or Tuya device ID")
    event_type: str = Field(..., description="e.g. DEVICE_STATUS_CHANGE, DEVICE_ALERT, TAMPER_DETECTED")
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


@router.post("/billing", status_code=status.HTTP_200_OK)
async def receive_billing_webhook(
    payload: BillingWebhookPayload,
    x_webhook_signature: str = Header(None, alias="X-Billing-Signature")
):
    """Processes incoming notifications from operator Core Billing."""
    logger.info(f"Received Billing Webhook: {payload.event_type} for sub {payload.subscriber_id}")
    
    return {
        "status": "PROCESSED",
        "event_id": payload.event_id,
        "event_type": payload.event_type,
        "subscriber_id": payload.subscriber_id,
        "processed_at": time.time()
    }


@router.post("/iot", status_code=status.HTTP_200_OK)
async def receive_iot_webhook(payload: IoTWebhookPayload):
    """Processes real-time state changes from Matter / Tuya Cloud."""
    logger.info(f"Received IoT Webhook: {payload.event_type} for device {payload.device_id}")

    return {
        "status": "PROCESSED",
        "event_id": payload.event_id,
        "device_id": payload.device_id,
        "processed_at": time.time()
    }
