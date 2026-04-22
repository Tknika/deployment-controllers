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
            "/apns": "List, create and replace APNs through DNN_LIST",
            "/apns/{name}": "Replace or delete one APN by name",
            "/gnb-info": "Information about all connected gNBs and their details (TAs, PLMNs, number of UEs)",
            "/ue-info": "Information about all connected 5G UEs (active gNB, TAI, PDN info)",
            "/pdu-info": "Information about all PDU sessions (IMSI/SUPI, DNN, IPs, S-NSSAI, QoS, state)",
        }
    }