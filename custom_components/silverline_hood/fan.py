"""Support for Silverline Hood Fan."""
import logging
from typing import Any, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_MOTOR, DOMAIN, SPEED_LIST

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Silverline Hood fan from a config entry."""
    _LOGGER.info("Setting up Silverline Hood fan entity")
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    fan = SilverlineHoodFan(coordinator)
    async_add_entities([fan], True)
    _LOGGER.info("Silverline Hood fan entity added")


class SilverlineHoodFan(FanEntity):
    """Representation of a Silverline Hood Fan."""

    def __init__(self, coordinator):
        """Initialize the fan."""
        self._coordinator = coordinator
        self._attr_name = "Silverline Hood Fan"
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_fan"
        self._attr_supported_features = (
            FanEntityFeature.TURN_ON |
            FanEntityFeature.TURN_OFF |
            FanEntityFeature.SET_SPEED |
            FanEntityFeature.PRESET_MODE
        )
        self._attr_preset_modes = SPEED_LIST[1:]
        self._attr_speed_count = 4
        self._attr_should_poll = False  # Wichtig: kein automatisches Polling
        _LOGGER.info("Fan entity initialized: %s", self._attr_unique_id)

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
        """Return true if fan is on."""
        return self._coordinator.current_state.get(CMD_MOTOR, 0) > 0

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        motor_speed = self._coordinator.current_state.get(CMD_MOTOR, 0)
        if motor_speed == 0:
            return 0
        return int((motor_speed / 4) * 100)

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode."""
        motor_speed = self._coordinator.current_state.get(CMD_MOTOR, 0)
        if motor_speed == 0:
            return None
        return SPEED_LIST[motor_speed] if motor_speed < len(SPEED_LIST) else None

    async def async_turn_on(self, percentage: Optional[int] = None, preset_mode: Optional[str] = None, **kwargs: Any) -> None:
        """Turn on the fan."""
        _LOGGER.info("Fan turn_on called with percentage=%s, preset_mode=%s", percentage, preset_mode)
        
        if preset_mode:
            if preset_mode == "low":
                await self._coordinator.send_exact_command("fan_speed_1")
            elif preset_mode == "medium":
                await self._coordinator.send_exact_command("fan_speed_2")
            elif preset_mode == "high":
                await self._coordinator.send_exact_command("fan_speed_3")
            else:
                await self._coordinator.send_exact_command("fan_speed_1")
        elif percentage:
            if percentage <= 25:
                await self._coordinator.send_exact_command("fan_speed_1")
            elif percentage <= 50:
                await self._coordinator.send_exact_command("fan_speed_2")
            elif percentage <= 75:
                await self._coordinator.send_exact_command("fan_speed_3")
            else:
                await self._coordinator.send_exact_command("fan_speed_3")
        else:
            await self._coordinator.send_exact_command("fan_speed_1")
        
        # Update our internal state immediately
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        _LOGGER.info("Fan turn_off called")
        await self._coordinator.send_exact_command("fan_off")
        self.schedule_update_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        _LOGGER.info("Fan set_percentage called with %s%%", percentage)
        if percentage == 0:
            await self.async_turn_off()
        else:
            await self.async_turn_on(percentage=percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        _LOGGER.info("Fan set_preset_mode called with %s", preset_mode)
        await self.async_turn_on(preset_mode=preset_mode)