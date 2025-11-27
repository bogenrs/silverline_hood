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
        return light_state in [2, 3]  # On in both white (L:2) and RGB (L:3) mode

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness."""
        if not self.coordinator.data:
            return 165  # Default middle value
        device_brg = self.coordinator.data.get("BRG", 165)
        return self._convert_brightness_from_device(device_brg)

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

    def _convert_brightness_to_device(self, ha_brightness: int) -> int:
        """Convert HA brightness (0-255) to device range (161-170)."""
        # HA: 0-255 -> Device: 161-170 (nur 9 Stufen!)
        if ha_brightness <= 0:
            return 161  # Minimum device brightness
        return int(161 + (ha_brightness * (170 - 161) / 255))

    def _convert_brightness_from_device(self, device_brightness: int) -> int:
        """Convert device brightness (161-170) to HA range (0-255)."""
        # Device: 161-170 -> HA: 0-255
        if device_brightness <= 161:
            return 1  # Minimum HA brightness
        return int((device_brightness - 161) * 255 / (170 - 161))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        _LOGGER.info("Light turn_on called: %s", kwargs)
        
        changes = {}
        
        if ATTR_BRIGHTNESS in kwargs:
            ha_brightness = kwargs[ATTR_BRIGHTNESS]
            device_brightness = self._convert_brightness_to_device(ha_brightness)
            changes["BRG"] = device_brightness
            _LOGGER.debug("Brightness: HA %d -> Device %d", ha_brightness, device_brightness)
        
        if ATTR_RGBW_COLOR in kwargs:
            rgbw = kwargs[ATTR_RGBW_COLOR]
            r, g, b, w = rgbw[0], rgbw[1], rgbw[2], rgbw[3]
            
            # Determine mode based on RGBW values
            if r > 0 or g > 0 or b > 0:
                # RGB mode - colors are being used
                _LOGGER.debug("Using RGB mode (L:3) for colors R:%d G:%d B:%d", r, g, b)
                changes.update({
                    "L": 3,  # RGB mode
                    "R": r, "G": g, "B": b,
                    "CW": 0,  # Clear white in RGB mode
                })
            else:
                # White mode - only white channel
                _LOGGER.debug("Using White mode (L:2) for white value: %d", w)
                changes.update({
                    "L": 2,  # White mode
                    "CW": w,
                    "R": 0, "G": 0, "B": 0,  # Clear RGB in white mode
                })
        else:
            # No color specified - use previous mode or default to white
            if not self.coordinator.data or self.coordinator.data.get("L", 1) == 1:
                changes["L"] = 2  # Default to white mode
            # If device is already in L:2 or L:3, keep current mode
        
        await self.coordinator.send_smart_command(changes)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        _LOGGER.info("Light turn_off called")
        await self.coordinator.send_smart_command({"L": 1})