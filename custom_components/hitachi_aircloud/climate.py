"""Entidades de clima: uma por unidade interna."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FAN_MODE_TO_CODE,
    FAN_TEXT_TO_MODE,
    MAX_TEMP,
    MIN_TEMP,
    MODE_TEXT_TO_CODE,
    TEMP_STEP,
)
from .coordinator import AirCloudCoordinator

HA_TO_MODE_TEXT = {
    HVACMode.COOL: "Cool",
    HVACMode.HEAT: "Heat",
    HVACMode.FAN_ONLY: "Fan",
    HVACMode.DRY: "Dry",
}
MODE_TEXT_TO_HA = {v: k for k, v in HA_TO_MODE_TEXT.items()}
FAN_MODE_TO_TEXT = {v: k for k, v in FAN_TEXT_TO_MODE.items()}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AirCloudCoordinator = entry.runtime_data
    async_add_entities(AirCloudClimate(coordinator, entry.entry_id, dev) for dev in coordinator.units)


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class AirCloudClimate(CoordinatorEntity[AirCloudCoordinator], ClimateEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.DRY, HVACMode.FAN_ONLY]
    _attr_fan_modes = ["low", "medium", "high", "max", "auto"]
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = TEMP_STEP
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator: AirCloudCoordinator, entry_id: str, dev: int) -> None:
        super().__init__(coordinator)
        self._dev = dev
        self._attr_unique_id = f"{entry_id}_unit_{dev}"
        st = self._status
        model = f"{st.get('Model', '')}{st.get('Capacity', '')}".strip() or None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{dev}")},
            name=f"Ar condicionado {dev}",
            manufacturer="Hitachi",
            model=model,
        )

    @property
    def _status(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self._dev, {})

    @property
    def available(self) -> bool:
        return super().available and bool(self._status)

    @property
    def _is_on(self) -> bool:
        return str(self._status.get("Operation", "")).upper() == "ON"

    @property
    def hvac_mode(self) -> HVACMode:
        if not self._is_on:
            return HVACMode.OFF
        return MODE_TEXT_TO_HA.get(str(self._status.get("Mode")), HVACMode.COOL)

    @property
    def current_temperature(self) -> float | None:
        return _float(self._status.get("Ti"))

    @property
    def target_temperature(self) -> float | None:
        return _float(self._status.get("Tset"))

    @property
    def fan_mode(self) -> str | None:
        return FAN_TEXT_TO_MODE.get(str(self._status.get("Real")))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        st = self._status
        return {"alarme": st.get("ALM"), "unidade": self._dev}

    async def _send(self, *, on: bool | None = None, mode_text: str | None = None,
                    fan: str | None = None, temp: float | None = None) -> None:
        st = self._status
        on = self._is_on if on is None else on
        mode_text = mode_text or str(st.get("Mode") or "Cool")
        if mode_text not in MODE_TEXT_TO_CODE:
            mode_text = "Cool"
        fan = fan or self.fan_mode or "auto"
        temp = temp if temp is not None else (self.target_temperature or 24.0)
        temp = max(MIN_TEMP, min(MAX_TEMP, round(temp / TEMP_STEP) * TEMP_STEP))

        await self.coordinator.api.set_unit(
            self._dev, on, MODE_TEXT_TO_CODE[mode_text], FAN_MODE_TO_CODE[fan], temp
        )
        self.coordinator.set_pending(
            self._dev,
            {
                "Operation": "ON" if on else "OFF",
                "Mode": mode_text,
                "Real": FAN_MODE_TO_TEXT[fan],
                "Tset": f"{temp:.1f}",
            },
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send(on=False)
        else:
            await self._send(on=True, mode_text=HA_TO_MODE_TEXT[hvac_mode])

    async def async_turn_on(self) -> None:
        await self._send(on=True)

    async def async_turn_off(self) -> None:
        await self._send(on=False)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        hvac_mode = kwargs.get("hvac_mode")
        if hvac_mode == HVACMode.OFF:
            await self._send(on=False, temp=float(temp))
        elif hvac_mode:
            await self._send(on=True, mode_text=HA_TO_MODE_TEXT[hvac_mode], temp=float(temp))
        else:
            await self._send(temp=float(temp))

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self._send(fan=fan_mode)
