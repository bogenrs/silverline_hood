"""Support for Silverline Hood Fan."""
import logging
from typing import Any, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CMD_MOTOR,
    DOMAIN,
    MOTOR_OFF,
    SPEED_LIST,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Silverline Hood fan from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SilverlineHoodFan(coordinator)], True)


class SilverlineHoodFan(CoordinatorEntity, FanEntity):
    """Representation of a Silverline Hood Fan."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator):
        """Initialize the fan."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_{coordinator.port}_fan"
        
        # Supported features
        self._attr_supported_features = (
            FanEntityFeature.TURN_ON |
            FanEntityFeature.TURN_OFF |
            FanEntityFeature.SET_SPEED |
            FanEntityFeature.PRESET_MODE
        )
        
        self._attr_preset_modes = SPEED_LIST[1:]  # Exclude 'off' from presets
        self._attr_speed_count = 4

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self.coordinator.host}_{self.coordinator.port}")},
            "name": "Silverline Hood",
            "manufacturer": "Silverline",
            "model": "Smart Hood",
            "sw_version": f"Update: {self.coordinator.update_interval_seconds()}s",
        }

    @property
    def name(self) -> str:
        """Return the name of the fan."""
        return "Fan"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "update_interval_seconds": self.coordinator.update_interval_seconds(),
            "host": self.coordinator.host,
            "port": self.coordinator.port,
            "current_motor_speed": self.coordinator.current_state.get(CMD_MOTOR, 0),
        }

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        return self.coordinator.current_state.get(CMD_MOTOR, 0) > 0

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        motor_speed = self.coordinator.current_state.get(CMD_MOTOR, 0)
        if motor_speed == 0:
            return 0
        # Convert speed 1-4 to percentage 25-100
        return int((motor_speed / 4) * 100)

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode."""
        motor_speed = self.coordinator.current_state.get(CMD_MOTOR, 0)
        if motor_speed == 0:
            return None
        return SPEED_LIST[motor_speed] if motor_speed < len(SPEED_LIST) else None

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if preset_mode:
            if preset_mode in SPEED_LIST:
                speed = SPEED_LIST.index(preset_mode)
            else:
                _LOGGER.warning("Unknown preset mode: %s", preset_mode)
                speed = 1
        elif percentage:
            # Convert percentage to speed 1-4
            if percentage <= 25:
                speed = 1
            elif percentage <= 50:
                speed = 2
            elif percentage <= 75:
                speed = 3
            else:
                speed = 4
        else:
            speed = 1

        _LOGGER.debug("Turning on fan with speed: %s", speed)
        await self.coordinator.send_command({CMD_MOTOR: speed})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        _LOGGER.debug("Turning off fan")
        await self.coordinator.send_command({CMD_MOTOR: MOTOR_OFF})

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        if percentage == 0:
            await self.async_turn_off()
        else:
            # Convert percentage to speed 1-4
            if percentage <= 25:
                speed = 1
            elif percentage <= 50:
                speed = 2
            elif percentage <= 75:
                speed = 3
            else:
                speed = 4
            
            _LOGGER.debug("Setting fan speed to %s (%s%%)", speed, percentage)
            await self.coordinator.send_command({CMD_MOTOR: speed})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode in SPEED_LIST:
            speed = SPEED_LIST.index(preset_mode)
            _LOGGER.debug("Setting preset mode to %s (speed %s)", preset_mode, speed)
            await self.coordinator.send_command({CMD_MOTOR: speed})
        else:
            _LOGGER.warning("Unknown preset mode: %s", preset_mode)