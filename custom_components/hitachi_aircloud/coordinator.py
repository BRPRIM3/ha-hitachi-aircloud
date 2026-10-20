"""Coordinator: lê o status de todas as unidades e guarda comandos pendentes."""
from __future__ import annotations

from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AirCloudApi, CannotConnect, InvalidAuth
from .const import DOMAIN, PENDING_TIMEOUT_SECONDS, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class AirCloudCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Dados: {dev: status_json}."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: AirCloudApi, units: list[int]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.api = api
        self.units = units
        # dev -> (campos esperados, prazo)
        self._pending: dict[int, tuple[dict[str, str], float]] = {}

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        result: dict[int, dict[str, Any]] = {}
        try:
            for dev in self.units:
                result[dev] = await self.api.get_status(dev)
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CannotConnect as err:
            raise UpdateFailed(f"Gateway inacessível: {err}") from err
        return self._apply_pending(result)

    def _apply_pending(self, data: dict[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
        now = time.monotonic()
        for dev, (fields, deadline) in list(self._pending.items()):
            current = data.get(dev)
            if current is None:
                continue
            confirmed = all(str(current.get(k)) == v for k, v in fields.items())
            if confirmed or now > deadline:
                self._pending.pop(dev, None)
                continue
            current.update(fields)
        return data

    def set_pending(self, dev: int, fields: dict[str, str]) -> None:
        """Mostra o valor enviado até o gateway confirmar (ou expirar)."""
        self._pending[dev] = (fields, time.monotonic() + PENDING_TIMEOUT_SECONDS)
        if self.data and dev in self.data:
            self.data[dev].update(fields)
            self.async_set_updated_data(self.data)
