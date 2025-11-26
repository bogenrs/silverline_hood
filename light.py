"""Support for Silverline Hood Light."""
import logging
from typing import Any, Optional, Tuple

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CMD_BLUE,
    CMD_BRIGHTNESS,
    CMD_COLD_WHITE,
    CMD_GREEN,
    CMD_LIGHT,
    CMD_RED,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Silverline Hood light from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SilverlineHoodLight(coordinator)], True)


class SilverlineHoodLight(CoordinatorEntity, LightEntity):
    """Representation of a Silverline Hood Light."""

    def __init__(self, coordinator):
        """Initialize the light."""
        super().__init__(coordinator)
        self._attr_name = "Silverline Hood Light"
        self._attr_unique_id = f"{coordinator.host}_light"
        self._attr_supported_color_modes = {ColorMode.RGBW}
        self._attr_color_mode = ColorMode.RGBW

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.host)},
            "name": "Silverline Hood",
            "manufacturer": "Silverline",
            "model": "Smart Hood",
            "sw_version": f"Update: {self.coordinator.update_interval_seconds()}s",
        }

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "update_interval_seconds": self.coordinator.update_interval_seconds(),
            "host": self.coordinator.host,
            "port": self.coordinator.port,
        }

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.coordinator.current_state.get(CMD_LIGHT, 0) == 1

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        return self.coordinator.current_state.get(CMD_BRIGHTNESS, 255)

    @property
    def rgbw_color(self) -> Optional[Tuple[int, int, int, int]]:
        """Return the rgbw color value."""
        state = self.coordinator.current_state
        return (
            state.get(CMD_RED, 255),
            state.get(CMD_GREEN, 255),
            state.get(CMD_BLUE, 255),
            state.get(CMD_COLD_WHITE, 255),
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        command = {CMD_LIGHT: 1}

        if ATTR_BRIGHTNESS in kwargs:
            command[CMD_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]

        if ATTR_RGBW_COLOR in kwargs:
            rgbw = kwargs[ATTR_RGBW_COLOR]
            command[CMD_RED] = rgbw[0]
            command[CMD_GREEN] = rgbw[1]
            command[CMD_BLUE] = rgbw[2]
            command[CMD_COLD_WHITE] = rgbw[3]

        await self.coordinator.send_command(command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        await self.coordinator.send_command({CMD_LIGHT: 0})