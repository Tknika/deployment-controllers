"""
Core proxy endpoints to MME and SMF backends.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from httpx import AsyncClient, ConnectError, TimeoutException
from starlette.responses import StreamingResponse

from ...services import CoreInfoStreamService, CoreInfoStreamServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core", tags=["core"])
core_info_stream_service = CoreInfoStreamService()


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
            logger.debug(f"Proxy to {destination_url}: {response.status_code}")
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


@router.get("/gnb-info")
async def get_gnb_info(request: Request):
    """Proxy: Get information about all connected gNBs from MME."""
    data, status_code = await proxy_request(
        "http://amf:9091/gnb-info?page=-1",
        params=dict(request.query_params),
        headers=dict(request.headers),
    )
    return data, status_code


@router.get("/ue-info")
async def get_ue_info(request: Request):
    """Proxy: Get information about all connected 5G UEs from AMF."""
    data, status_code = await proxy_request(
        "http://amf:9091/ue-info?page=-1",
        params=dict(request.query_params),
        headers=dict(request.headers),
    )
    return data, status_code


@router.get("/pdu-info")
async def get_pdu_info(request: Request):
    """Proxy: Get information about all PDU sessions from SMF."""
    data, status_code = await proxy_request(
        "http://smf:9091/pdu-info?page=-1",
        params=dict(request.query_params),
        headers=dict(request.headers),
    )
    return data, status_code


@router.get("/info-stream")
async def get_core_info_stream(request: Request):
    """SSE stream for enb-info, ue-info and pdu-info updates from Open5GS."""
    try:
        subscriber_queue, initial_snapshot = await core_info_stream_service.register_subscriber()
    except CoreInfoStreamServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    async def event_generator():
        try:
            yield core_info_stream_service.format_sse_message("snapshot", initial_snapshot)
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(subscriber_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                yield message
        finally:
            await core_info_stream_service.unregister_subscriber(subscriber_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
