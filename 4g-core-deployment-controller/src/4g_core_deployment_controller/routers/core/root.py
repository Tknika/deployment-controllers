"""
Core root endpoints to describe the endpoint.
"""

import logging
from typing import Any

from fastapi import APIRouter, Request
from httpx import AsyncClient, ConnectError, TimeoutException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core", tags=["core"])


@router.get("")
async def get_core_endpoints():
    """List available core endpoints."""
    return {
        "endpoints": {
            "/subscribers": "Information and management of subscribers registered in the core",
            "/enb-info": "Information about all connected eNBs and their details (TAs, PLMNs, number of UEs)",
            "/ue-info": "Information about all connected LTE UEs (active eNB, TAI, PDN info)",
            "/pdu-info": "Information about all PDU sessions (IMSI/SUPI, DNN, IPs, S-NSSAI, QoS, state)",
        }
    }