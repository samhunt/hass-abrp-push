"""ABRP Telemetry API client."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import ABRP_API_URL

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = ClientTimeout(total=15)


class AbrpApiError(Exception):
    """Raised when ABRP rejects or fails a telemetry request."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class AbrpApiClient:
    """Thin client for Iternio / ABRP telemetry send."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        user_token: str,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._user_token = user_token

    async def async_send_telemetry(self, tlm: dict[str, Any]) -> dict[str, Any]:
        """POST telemetry to ABRP.

        Auth uses the application API key. The per-vehicle user token is part of
        the JSON body so ABRP can route the update to the correct car.
        """
        payload = {"token": self._user_token, "tlm": tlm}
        headers = {
            "Authorization": f"APIKEY {self._api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }

        try:
            async with self._session.post(
                ABRP_API_URL,
                json=payload,
                headers=headers,
                timeout=_TIMEOUT,
            ) as response:
                body_text = await response.text()
                if response.status >= 400:
                    raise AbrpApiError(
                        f"HTTP {response.status}: {body_text[:200]}",
                        status=response.status,
                    )

                data: Any
                try:
                    data = json.loads(body_text) if body_text else {}
                except ValueError:
                    data = {"raw": body_text}

                if isinstance(data, dict):
                    status = data.get("status")
                    if status is not None and str(status).lower() not in {
                        "ok",
                        "success",
                    }:
                        _LOGGER.warning("ABRP soft failure response: %s", data)
                    return data

                return {"raw": data}
        except ClientError as err:
            raise AbrpApiError(f"Network error: {err}") from err
