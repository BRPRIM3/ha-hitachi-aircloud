"""Config flow: IP, usuário e senha do gateway."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME

from . import CONF_UNITS, create_api
from .api import CannotConnect, InvalidAuth
from .const import DOMAIN, MAX_UNITS_PROBE

_LOGGER = logging.getLogger(__name__)

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class AirCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip().removeprefix("https://").removeprefix("http://").rstrip("/")
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            api = create_api(self.hass, host, user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            try:
                await api.login()
                units = await api.discover_units(MAX_UNITS_PROBE)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Erro inesperado ao configurar o gateway")
                errors["base"] = "unknown"
            else:
                if not units:
                    errors["base"] = "no_units"
                else:
                    return self.async_create_entry(
                        title=f"airCloud {host}",
                        data={**user_input, CONF_HOST: host, CONF_UNITS: units},
                    )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
