"""Support for Silverline Hood Light."""
import logging
from typing import Any, Optional, Tuple

from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS, ATTR_RGBW_COLOR
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_LIGHT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Silverline Hood light from a config entry."""
    _LOGGER.info("Setting up Silverline Hood light entity")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    light = SilverlineHoodLight(coordinator)
    async_add_entities([light], True)
    _LOGGER.info("Silverline Hood light entity added")


class SilverlineHoodLight(LightEntity):
    """Representation of a Silverline Hood Light."""

    def __init__(self, coordinator):
        """Initialize the light."""
        self._coordinator = coordinator
        self._attr_name = "Silverline Hood Light"
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_light"
        self._attr_supported_color_modes = {ColorMode.RGBW}
        self._attr_color_mode = ColorMode.RGBW
        self._attr_should_poll = False  # Wichtig: kein automatisches Polling
        _LOGGER.info("Light entity initialized: %s", self._attr_unique_id)

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
        # Basierend auf Wireshark: L:2 = an, L:0 = aus
        return self._coordinator.current_state.get(CMD_LIGHT, 0) == 2

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        return self._coordinator.current_state.get("BRG", 255)

    @property
    def rgbw_color(self) -> Optional[Tuple[int, int, int, int]]:
        """Return the rgbw color value."""
        state = self._coordinator.current_state
        return (
            state.get("R", 45),
            state.get("G", 255),
            state.get("B", 104),
            state.get("CW", 255),
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        _LOGGER.info("Light turn_on called with kwargs: %s", kwargs)
        
        # Für jetzt verwenden wir den einfachen light_on Befehl
        # Später können wir das erweitern für Farben/Helligkeit
        await self._coordinator.send_exact_command("light_on")
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        _LOGGER.info("Light turn_off called")
        await self._coordinator.send_exact_command("light_off")
        self.schedule_update_ha_state()