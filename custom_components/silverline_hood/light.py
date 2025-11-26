"""Support for Silverline Hood Light."""
import logging
from typing import Any, Optional, Tuple

from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS, ATTR_RGBW_COLOR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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


class SilverlineHoodLight(LightEntity):
    """Light entity with dynamic RGBW support."""

    def __init__(self, coordinator):
        """Initialize the light."""
        self._coordinator = coordinator
        self._attr_name = "Silverline Hood Light"
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_light"
        self._attr_supported_color_modes = {ColorMode.RGBW}
        self._attr_color_mode = ColorMode.RGBW
        self._attr_should_poll = False

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._coordinator.host}_{self._coordinator.port}")},
            "name": "Silverline Hood",
            "manufacturer": "Silverline",
            "model": "Smart Hood",
        }

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._coordinator.current_state.get("L", 0) == 2

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        return self._coordinator.current_state.get("BRG", 132)

    @property
    def rgbw_color(self) -> Optional[Tuple[int, int, int, int]]:
        """Return the rgbw color value."""
        state = self._coordinator.current_state
        return (
            state.get("R", 45),
            state.get("G", 255),
            state.get("B", 104),
            state.get("CW", 110),
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light with dynamic colors."""
        _LOGGER.info("Light turn_on called with kwargs: %s", kwargs)
        
        # Start with base state
        command_data = {
            "M": 1,     # Motor bleibt an
            "L": 2,     # Licht an
            "R": 45,    # Default Rot
            "G": 255,   # Default Grün  
            "B": 104,   # Default Blau
            "CW": 110,  # Default Kaltweiß
            "BRG": 132, # Default Helligkeit
            "T": 0,
            "TM": 0,
            "TS": 255,
            "A": 1
        }
        
        # Helligkeit anwenden
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            command_data["BRG"] = brightness
            _LOGGER.info("Setting brightness to: %s", brightness)
        
        # RGBW-Farbe anwenden  
        if ATTR_RGBW_COLOR in kwargs:
            rgbw = kwargs[ATTR_RGBW_COLOR]
            command_data["R"] = rgbw[0]    # Rot
            command_data["G"] = rgbw[1]    # Grün
            command_data["B"] = rgbw[2]    # Blau
            command_data["CW"] = rgbw[3]   # Kaltweiß
            _LOGGER.info("Setting RGBW to: R=%s, G=%s, B=%s, CW=%s", 
                        rgbw[0], rgbw[1], rgbw[2], rgbw[3])
        
        # Befehl als JSON + \r erstellen
        import json
        command_str = json.dumps(command_data) + '\r'
        
        _LOGGER.info("Sending dynamic command: %s", repr(command_str))
        
        # Raw command senden (dynamisch)
        await self._coordinator.send_raw_command(command_str)
        
        # Internen Zustand aktualisieren
        self._coordinator._state.update(command_data)
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        _LOGGER.info("Light turn_off called")
        await self._coordinator.send_exact_command("light_off")
        self.schedule_update_ha_state()