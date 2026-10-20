"""Integração Hitachi airCloud Gateway (HC-IOTGW) para Home Assistant."""
from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import AirCloudApi
from .coordinator import AirCloudCoordinator

PLATFORMS = [Platform.CLIMATE]
CONF_UNITS = "units"


def create_api(hass: HomeAssistant, host: str, username: str, password: str) -> AirCloudApi:
    # Cookie jar "unsafe" para aceitar cookies de host por IP; certificado autoassinado.
    session = async_create_clientsession(
        hass, verify_ssl=False, cookie_jar=aiohttp.CookieJar(unsafe=True)
    )
    return AirCloudApi(session, host, username, password)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = create_api(hass, entry.data[CONF_HOST], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    coordinator = AirCloudCoordinator(hass, entry, api, list(entry.data.get(CONF_UNITS, [])))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
