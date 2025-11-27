"""Support for Silverline Hood Light."""
import logging
from typing import Any, Optional, Tuple

from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS, ATTR_RGBW_COLOR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SilverlineHoodLight(coordinator)], True)


class SilverlineHoodLight(CoordinatorEntity, LightEntity):
    """Light entity with automatic updates."""

    def __init__(self, coordinator):
        """Initialize the light."""
        super().__init__(coordinator)
        self._attr_name = "Silverline Hood Light"
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_light"
        self._attr_supported_color_modes = {ColorMode.RGBW}
        self._attr_color_mode = ColorMode.RGBW

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self.coordinator.host}_{self.coordinator.port}")},
            "name": "Silverline Hood",
            "manufacturer": "Silverline",
            "model": "Smart Hood",
        }

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        if not self.coordinator.data:
            return False
        light_state = self.coordinator.data.get("L", 1)
        return light_state == 2

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness."""
        if not self.coordinator.data:
            return 132
        return self.coordinator.data.get("BRG", 132)

    @property
    def rgbw_color(self) -> Optional[Tuple[int, int, int, int]]:
        """Return the rgbw color value."""
        if not self.coordinator.data:
            return (45, 255, 104, 110)
        data = self.coordinator.data
        return (
            data.get("R", 45),
            data.get("G", 255),
            data.get("B", 104),
            data.get("CW", 110),
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        _LOGGER.info("Light turn_on called: %s", kwargs)
        
        changes = {"L": 2}
        
        if ATTR_BRIGHTNESS in kwargs:
            changes["BRG"] = kwargs[ATTR_BRIGHTNESS]
        
        if ATTR_RGBW_COLOR in kwargs:
            rgbw = kwargs[ATTR_RGBW_COLOR]
            changes.update({
                "R": rgbw[0], "G": rgbw[1], 
                "B": rgbw[2], "CW": rgbw[3]
            })
        
        await self.coordinator.send_smart_command(changes)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        _LOGGER.info("Light turn_off called")
        await self.coordinator.send_smart_command({"L": 1})