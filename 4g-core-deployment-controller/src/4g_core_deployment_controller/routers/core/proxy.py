"""
Core proxy endpoints to MME and SMF backends.
"""

import logging
from typing import Any

from fastapi import APIRouter, Request
from httpx import AsyncClient, ConnectError, TimeoutException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core", tags=["core"])


async def proxy_request(
    destination_url: str,
    method: str = "GET",
    params: dict | None = None,
    headers: dict | None = None,
) -> tuple[Any, int]:
    """Generic proxy function for HTTP requests to remote destinations."""
    try:
        async with AsyncClient(timeout=5.0) as client:
            response = await client.request(
                method=method,
                url=destination_url,
                params=params,
                headers=headers,
            )
            logger.info(f"Proxy to {destination_url}: {response.status_code}")
            return response.json(), response.status_code
    except TimeoutException:
        logger.error(f"Timeout connecting to {destination_url}")
        return {
            "error": "Gateway timeout",
            "detail": f"Backend {destination_url} did not respond in time",
        }, 504
    except ConnectError as exc:
        logger.error(f"Connection error to {destination_url}: {exc}")
        return {
            "error": "Bad gateway",
            "detail": f"Could not connect to {destination_url}",
        }, 502
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(f"Unexpected error proxying to {destination_url}: {exc}")
        return {
            "error": "Bad gateway",
            "detail": "Unexpected error contacting backend",
        }, 502


@router.get("/enb-info")
async def get_enb_info(request: Request):
    """Proxy: Get information about all connected eNBs from MME."""
    data, status_code = await proxy_request(
        "http://mme:9091/enb-info",
        params=dict(request.query_params),
        headers=dict(request.headers),
    )
    return data, status_code


@router.get("/ue-info")
async def get_ue_info(request: Request):
    """Proxy: Get information about all connected LTE UEs from MME."""
    data, status_code = await proxy_request(
        "http://mme:9091/ue-info",
        params=dict(request.query_params),
        headers=dict(request.headers),
    )
    return data, status_code


@router.get("/pdu-info")
async def get_pdu_info(request: Request):
    """Proxy: Get information about all PDU sessions from SMF."""
    data, status_code = await proxy_request(
        "http://smf:9091/pdu-info",
        params=dict(request.query_params),
        headers=dict(request.headers),
    )
    return data, status_code
