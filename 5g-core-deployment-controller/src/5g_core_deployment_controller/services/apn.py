"""Service layer for APN operations backed by DNN_LIST environment variable."""

import logging
from dataclasses import dataclass

from httpx import ASGITransport, AsyncClient, TimeoutException

from ..models import ApnModel

logger = logging.getLogger(__name__)

ENV_DNN_LIST = "DNN_LIST"


@dataclass
class ApnServiceError(Exception):
    """Business/domain error exposed by APN service."""

    status_code: int
    detail: str


class ApnService:
    """CRUD operations for APNs serialized in DNN_LIST."""

    def __init__(self, app) -> None:
        """Initialize service with ASGI app used for internal /envs calls."""
        self.app = app

    async def list_apns(self) -> list[ApnModel]:
        """Return APN collection from DNN_LIST."""
        dnn_list_value = await self._read_dnn_list()
        return self._parse_dnn_list(dnn_list_value)

    async def create_apn(self, apn: ApnModel) -> ApnModel:
        """Create APN and persist full collection."""
        apns = await self.list_apns()
        if any(existing.name == apn.name for existing in apns):
            raise ApnServiceError(409, f"APN '{apn.name}' already exists")

        apns.append(apn)
        await self._write_dnn_list(self._serialize_dnn_list(apns))
        return apn

    async def replace_apn(self, name: str, apn: ApnModel) -> ApnModel:
        """Replace one APN by name and persist full collection."""
        apns = await self.list_apns()

        for index, existing in enumerate(apns):
            if existing.name == name:
                apns[index] = apn
                await self._write_dnn_list(self._serialize_dnn_list(apns))
                return apn

        raise ApnServiceError(404, f"APN '{name}' not found")

    async def delete_apn(self, name: str) -> None:
        """Delete one APN by name and persist full collection."""
        apns = await self.list_apns()
        updated_apns = [apn for apn in apns if apn.name != name]

        if len(updated_apns) == len(apns):
            raise ApnServiceError(404, f"APN '{name}' not found")

        await self._write_dnn_list(self._serialize_dnn_list(updated_apns))

    async def replace_all_apns(self, apns: list[ApnModel]) -> list[ApnModel]:
        """Replace complete APN collection."""
        await self._write_dnn_list(self._serialize_dnn_list(apns))
        return apns

    async def _read_dnn_list(self) -> str:
        """Read DNN_LIST value from /envs endpoint."""
        try:
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://app", timeout=10.0) as client:
                response = await client.get("/envs")
        except TimeoutException:
            logger.error("Timeout reading /envs for APNs")
            raise ApnServiceError(504, "Timeout while reading APN configuration")
        except Exception as exc:
            logger.error("Unexpected error reading /envs for APNs: %s", exc)
            raise ApnServiceError(502, "Could not read APN configuration from /envs")

        if response.status_code != 200:
            raise ApnServiceError(
                response.status_code,
                f"/envs read failed: {self._extract_error_detail(response)}",
            )

        try:
            variables = response.json()["variables"]
            for variable in variables:
                if variable.get("name") == ENV_DNN_LIST:
                    value = variable.get("value")
                    if value is None:
                        return ""
                    return str(value)
        except Exception as exc:
            logger.error("Invalid /envs response payload for APN read: %s", exc)
            raise ApnServiceError(502, "Invalid payload received from /envs")

        raise ApnServiceError(502, "DNN_LIST variable not found in /envs")

    async def _write_dnn_list(self, value: str) -> None:
        """Write DNN_LIST value through /envs endpoint."""
        payload = {
            "variables": {
                ENV_DNN_LIST: value,
            },
            "restart_services": True,
        }

        try:
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://app", timeout=10.0) as client:
                response = await client.put("/envs", json=payload)
        except TimeoutException:
            logger.error("Timeout writing /envs for APNs")
            raise ApnServiceError(504, "Timeout while updating APN configuration")
        except Exception as exc:
            logger.error("Unexpected error writing /envs for APNs: %s", exc)
            raise ApnServiceError(502, "Could not update APN configuration through /envs")

        if response.status_code not in (200, 202):
            raise ApnServiceError(
                response.status_code,
                f"/envs update failed: {self._extract_error_detail(response)}",
            )

    def _parse_dnn_list(self, raw_value: str) -> list[ApnModel]:
        """Convert DNN_LIST string into APN models."""
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]

        if value.strip() == "":
            return []

        apns: list[ApnModel] = []
        names_seen: set[str] = set()

        entries = [entry.strip() for entry in value.split(";") if entry.strip()]
        for entry in entries:
            parts = [part.strip() for part in entry.split(",")]
            if len(parts) != 3:
                raise ApnServiceError(502, f"Invalid DNN_LIST entry format: '{entry}'")

            apn = ApnModel(name=parts[0], subnet=parts[1], interface=parts[2])
            if apn.name in names_seen:
                raise ApnServiceError(502, f"Duplicated APN name in DNN_LIST: '{apn.name}'")

            names_seen.add(apn.name)
            apns.append(apn)

        return apns

    def _serialize_dnn_list(self, apns: list[ApnModel]) -> str:
        """Convert APN models into DNN_LIST string."""
        names_seen: set[str] = set()
        for apn in apns:
            if apn.name in names_seen:
                raise ApnServiceError(409, f"Duplicated APN name: '{apn.name}'")
            names_seen.add(apn.name)

        return ";".join(f"{apn.name},{apn.subnet},{apn.interface}" for apn in apns)

    def _extract_error_detail(self, response) -> str:
        """Extract best-effort error detail from httpx response."""
        try:
            payload = response.json()
        except ValueError:
            return response.text or "Unexpected error from /envs"

        if isinstance(payload, dict):
            return payload.get("detail") or payload.get("error") or str(payload)

        return str(payload)
