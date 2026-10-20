"""Cliente da interface web local do Hitachi airCloud Gateway (HC-IOTGW).

Fluxo confirmado no gateway real:
- Login: POST index.cgi?mod=0&act=1 (campos mod, act, username, password); sessão por cookie.
- Status: GET index.cgi?mod=3&act=35&dev=N -> JSON. Sem sessão válida, devolve a página de login.
- Comando: POST index.cgi?mod=3&act=33&dev=N (OnOff, OperationMode, FanSpeed, SetTemp).
  As caixas de bloqueio do controle remoto não são enviadas (ficam liberadas).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class AirCloudError(Exception):
    """Erro genérico do gateway."""


class CannotConnect(AirCloudError):
    """Gateway inacessível."""


class InvalidAuth(AirCloudError):
    """Usuário ou senha recusados."""


class AirCloudApi:
    """Acesso ao gateway com relogin automático."""

    def __init__(self, session: aiohttp.ClientSession, host: str, username: str, password: str) -> None:
        self._session = session
        self._url = f"https://{host}/index.cgi"
        self._username = username
        self._password = password
        self._lock = asyncio.Lock()
        self._logged_in = False

    async def _request(self, method: str, params: dict[str, str], data: dict[str, str] | None = None) -> str:
        try:
            async with self._session.request(
                method,
                self._url,
                params=params,
                data=data,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                return await resp.text(errors="replace")
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err)) from err

    async def _login(self) -> None:
        params = {"mod": "0", "act": "1"}
        await self._request(
            "POST",
            params,
            {"mod": "0", "act": "1", "username": self._username, "password": self._password},
        )
        if await self._raw_status(0) is None:
            self._logged_in = False
            raise InvalidAuth("o gateway recusou o login")
        self._logged_in = True

    async def _raw_status(self, dev: int) -> dict[str, Any] | None:
        text = await self._request("GET", {"mod": "3", "act": "35", "dev": str(dev)})
        try:
            data = json.loads(text)
        except ValueError:
            return None  # página de login: sessão expirada
        return data if isinstance(data, dict) else None

    async def login(self) -> None:
        async with self._lock:
            await self._login()

    async def get_status(self, dev: int) -> dict[str, Any]:
        async with self._lock:
            if not self._logged_in:
                await self._login()
            data = await self._raw_status(dev)
            if data is None:
                _LOGGER.debug("Sessão expirada, refazendo login")
                await self._login()
                data = await self._raw_status(dev)
                if data is None:
                    raise InvalidAuth("sem sessão após relogin")
            return data

    async def discover_units(self, max_units: int) -> list[int]:
        """Unidades internas existentes (as inexistentes voltam com Capacity 0)."""
        units: list[int] = []
        for dev in range(max_units):
            data = await self.get_status(dev)
            cap = str(data.get("Capacity", "0")).strip()
            if cap not in ("", "0"):
                units.append(dev)
        return units

    async def set_unit(self, dev: int, on: bool, mode_code: int, fan_code: int, temp: float) -> None:
        params = {"mod": "3", "act": "33", "dev": str(dev)}
        data = {
            "mod": "3",
            "act": "33",
            "dev": str(dev),
            "OnOff": "1" if on else "0",
            "OperationMode": str(mode_code),
            "FanSpeed": str(fan_code),
            "SetTemp": f"{temp:.1f}",
        }
        async with self._lock:
            if not self._logged_in:
                await self._login()
            text = await self._request("POST", params, data)
            if _is_login_page(text):
                _LOGGER.debug("Sessão expirada ao enviar comando, refazendo login")
                await self._login()
                text = await self._request("POST", params, data)
                if _is_login_page(text):
                    raise InvalidAuth("comando recusado: sem sessão")


def _is_login_page(text: str) -> bool:
    low = text.lower()
    return "<title>login</title>" in low or 'name="password"' in low
