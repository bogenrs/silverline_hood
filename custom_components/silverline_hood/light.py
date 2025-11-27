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
    """Light entity with corrected RGBW support."""

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
    def available(self) -> bool:
        """Return True if entity is available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        light_state = self._coordinator.current_state.get("L", 1)
        # KORRIGIERT basierend auf Wireshark-Analyse: L:1=AUS, L:2=AN
        is_on = light_state == 2
        _LOGGER.debug("Light state: L=%s, is_on=%s", light_state, is_on)
        return is_on

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

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        state = self._coordinator.current_state
        return {
            "host": self._coordinator.host,
            "port": self._coordinator.port,
            "current_light_state": state.get("L", 1),
            "current_red": state.get("R", 45),
            "current_green": state.get("G", 255),
            "current_blue": state.get("B", 104),
            "current_cold_white": state.get("CW", 110),
            "current_brightness": state.get("BRG", 132),
            "last_command_success": True,  # Könnte erweitert werden
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light with dynamic colors."""
        _LOGGER.info("Light turn_on called with kwargs: %s", kwargs)
        
        # KORRIGIERT: L:2 zum Einschalten (basierend auf Wireshark)
        changes = {"L": 2}
        
        # Add brightness if specified
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            changes["BRG"] = brightness
            _LOGGER.info("Setting brightness to: %s", brightness)
        
        # Add RGBW color if specified
        if ATTR_RGBW_COLOR in kwargs:
            rgbw = kwargs[ATTR_RGBW_COLOR]
            changes.update({
                "R": rgbw[0],    # Rot
                "G": rgbw[1],    # Grün
                "B": rgbw[2],    # Blau
                "CW": rgbw[3]    # Kaltweiß
            })
            _LOGGER.info("Setting RGBW to: R=%s, G=%s, B=%s, CW=%s", 
                        rgbw[0], rgbw[1], rgbw[2], rgbw[3])
        
        # Send smart command (preserves fan status!)
        _LOGGER.debug("Sending light ON command: %s", changes)
        result = await self._coordinator.send_smart_command(changes)
        
        if result:
            _LOGGER.info("✓ Light turned ON successfully")
            self.schedule_update_ha_state()
        else:
            _LOGGER.error("✗ Failed to turn on light")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        _LOGGER.info("Light turn_off called")
        
        # KORRIGIERT: L:1 zum Ausschalten (basierend auf Wireshark)
        changes = {"L": 1}
        
        _LOGGER.debug("Sending light OFF command: %s", changes)
        result = await self._coordinator.send_smart_command(changes)
        
        if result:
            _LOGGER.info("✓ Light turned OFF successfully")
            self.schedule_update_ha_state()
        else:
            _LOGGER.error("✗ Failed to turn off light")

    async def async_update(self):
        """Update light state by querying the device."""
        # Optional: Explicit state update
        try:
            await self._coordinator._query_current_status()
            _LOGGER.debug("Light state updated from device")
        except Exception as ex:
            _LOGGER.debug("Could not update light state: %s", ex)