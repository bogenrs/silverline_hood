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

    def __init__(self, coordinator):
        """Initialize the fan."""
        super().__init__(coordinator)
        self._attr_name = "Silverline Hood Fan"
        self._attr_unique_id = f"{coordinator.host}_fan"
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
        )
        self._attr_preset_modes = SPEED_LIST[1:]  # Exclude 'off' from presets
        self._attr_speed_count = 4

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
        """Return true if fan is on."""
        return self.coordinator.current_state.get(CMD_MOTOR, 0) > 0

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        motor_speed = self.coordinator.current_state.get(CMD_MOTOR, 0)
        if motor_speed == 0:
            return 0
        return int((motor_speed / 4) * 100)

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode."""
        motor_speed = self.coordinator.current_state.get(CMD_MOTOR, 0)
        if motor_speed == 0:
            return None
        return SPEED_LIST[motor_speed]

    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if preset_mode:
            speed = SPEED_LIST.index(preset_mode)
        elif percentage:
            speed = max(1, min(4, int((percentage / 100) * 4 + 0.5)))
        else:
            speed = 1

        await self.coordinator.send_command({CMD_MOTOR: speed})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self.coordinator.send_command({CMD_MOTOR: MOTOR_OFF})

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        if percentage == 0:
            await self.async_turn_off()
        else:
            speed = max(1, min(4, int((percentage / 100) * 4 + 0.5)))
            await self.coordinator.send_command({CMD_MOTOR: speed})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        speed = SPEED_LIST.index(preset_mode)
        await self.coordinator.send_command({CMD_MOTOR: speed})