"""Service layer for core Open5GS info SSE streaming."""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient, ConnectError, TimeoutException

logger = logging.getLogger(__name__)

DEFAULT_CORE_INFO_BACKENDS = {
    "gnb-info": "http://amf:9091/gnb-info?page=-1",
    "ue-info": "http://amf:9091/ue-info?page=-1",
    "pdu-info": "http://smf:9091/pdu-info?page=-1",
}


@dataclass
class CoreInfoStreamServiceError(Exception):
    """Business/domain error exposed by core info stream service."""

    status_code: int
    detail: str


class CoreInfoStreamService:
    """Manage a global poller and SSE fan-out for core info resources."""

    def __init__(
        self,
        poll_interval_seconds: float | None = None,
        backend_urls: dict[str, str] | None = None,
    ) -> None:
        self.poll_interval_seconds = (
            poll_interval_seconds
            if poll_interval_seconds is not None
            else float(os.getenv("CORE_INFO_STREAM_POLL_INTERVAL_SECONDS", "2"))
        )
        self.backend_urls = backend_urls or DEFAULT_CORE_INFO_BACKENDS.copy()

        self._latest_core_info: dict[str, Any] = {}
        self._latest_core_info_hashes: dict[str, str] = {}
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._poller_task: asyncio.Task | None = None
        self._state_lock = asyncio.Lock()

    async def register_subscriber(self) -> tuple[asyncio.Queue[str], dict[str, Any]]:
        """Register one SSE subscriber and return queue + initial snapshot."""
        snapshot, fetch_error = await self._fetch_snapshot()
        if fetch_error is not None or snapshot is None:
            raise CoreInfoStreamServiceError(
                status_code=503,
                detail="Could not connect to Open5GS",
            )

        subscriber_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=10)

        async with self._state_lock:
            for resource_name, resource_data in snapshot.items():
                self._latest_core_info[resource_name] = resource_data
                self._latest_core_info_hashes[resource_name] = self._stable_payload_hash(resource_data)

            self._subscribers.add(subscriber_queue)
            if self._poller_task is None or self._poller_task.done():
                self._poller_task = asyncio.create_task(self._poll_changes())

        return subscriber_queue, snapshot

    async def unregister_subscriber(self, subscriber_queue: asyncio.Queue[str]) -> None:
        """Unregister one SSE subscriber and stop poller when nobody is listening."""
        async with self._state_lock:
            self._subscribers.discard(subscriber_queue)
            if not self._subscribers and self._poller_task is not None:
                self._poller_task.cancel()
                self._poller_task = None

    @staticmethod
    def format_sse_message(event: str, payload: dict[str, Any]) -> str:
        """Build an SSE message string for one event."""
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def _fetch_snapshot(self) -> tuple[dict[str, Any] | None, str | None]:
        snapshot: dict[str, Any] = {}
        for resource_name, backend_url in self.backend_urls.items():
            data, status_code = await self._fetch_backend_json(backend_url)
            if status_code != 200:
                return None, f"Failed to fetch {resource_name} from Open5GS"
            snapshot[resource_name] = data
        return snapshot, None

    async def _fetch_backend_json(self, destination_url: str) -> tuple[Any, int]:
        try:
            async with AsyncClient(timeout=5.0) as client:
                response = await client.get(url=destination_url)
                logger.debug("Proxy to %s: %s", destination_url, response.status_code)
                return response.json(), response.status_code
        except TimeoutException:
            logger.error("Timeout connecting to %s", destination_url)
            return {
                "error": "Gateway timeout",
                "detail": f"Backend {destination_url} did not respond in time",
            }, 504
        except ConnectError as exc:
            logger.error("Connection error to %s: %s", destination_url, exc)
            return {
                "error": "Bad gateway",
                "detail": f"Could not connect to {destination_url}",
            }, 502
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Unexpected error proxying to %s: %s", destination_url, exc)
            return {
                "error": "Bad gateway",
                "detail": "Unexpected error contacting backend",
            }, 502

    async def _poll_changes(self) -> None:
        while True:
            try:
                snapshot, fetch_error = await self._fetch_snapshot()
                if fetch_error is not None or snapshot is None:
                    await asyncio.sleep(self.poll_interval_seconds)
                    continue

                changed_payload: dict[str, Any] = {}
                async with self._state_lock:
                    for resource_name, resource_data in snapshot.items():
                        current_hash = self._stable_payload_hash(resource_data)
                        previous_hash = self._latest_core_info_hashes.get(resource_name)
                        if previous_hash != current_hash:
                            changed_payload[resource_name] = resource_data
                            self._latest_core_info_hashes[resource_name] = current_hash
                            self._latest_core_info[resource_name] = resource_data

                if changed_payload:
                    message = self.format_sse_message("update", changed_payload)
                    self._broadcast(message)

                await asyncio.sleep(self.poll_interval_seconds)
            except asyncio.CancelledError:
                break

    def _broadcast(self, message: str) -> None:
        for subscriber_queue in list(self._subscribers):
            try:
                subscriber_queue.put_nowait(message)
            except asyncio.QueueFull:
                try:
                    _ = subscriber_queue.get_nowait()
                    subscriber_queue.put_nowait(message)
                except asyncio.QueueEmpty:
                    continue

    @staticmethod
    def _stable_payload_hash(payload: Any) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
