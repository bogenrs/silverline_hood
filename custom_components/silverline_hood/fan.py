"""Support for Silverline Hood Fan."""
import logging
from typing import Any, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN, 
    CMD_MOTOR, 
    SPEED_LIST,
    MOTOR_OFF,
    MOTOR_SPEED_1,
    MOTOR_SPEED_2, 
    MOTOR_SPEED_3,
    MOTOR_SPEED_4
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fan."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SilverlineHoodFan(coordinator)], True)


class SilverlineHoodFan(FanEntity):
    """Fan entity with correct motor values."""

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
        self._attr_preset_modes = SPEED_LIST[1:]  # ["low", "medium", "high", "max"]
        self._attr_speed_count = 4
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
        """Return true if fan is on."""
        motor_value = self._coordinator.current_state.get(CMD_MOTOR, 1)
        # M:1 = AUS, M:2-5 = AN
        return motor_value > 1

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        motor_value = self._coordinator.current_state.get(CMD_MOTOR, 1)
        if motor_value <= 1:  # AUS
            return 0
        # M:2-5 → 25%, 50%, 75%, 100%
        speed_level = motor_value - 1  # M:2→1, M:3→2, M:4→3, M:5→4
        return int((speed_level / 4) * 100)

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode."""
        motor_value = self._coordinator.current_state.get(CMD_MOTOR, 1)
        if motor_value <= 1:  # AUS
            return None
        # M:2→low, M:3→medium, M:4→high, M:5→max
        speed_index = motor_value - 1  # M:2→1, M:3→2, M:4→3, M:5→4
        if speed_index <= len(SPEED_LIST) - 1:
            return SPEED_LIST[speed_index]
        return None

    async def async_turn_on(self, percentage: Optional[int] = None, preset_mode: Optional[str] = None, **kwargs: Any) -> None:
        """Turn on the fan."""
        _LOGGER.info("Fan turn_on called with percentage=%s, preset_mode=%s", percentage, preset_mode)
        
        if preset_mode:
            motor_value = self._get_motor_value_from_preset(preset_mode)
        elif percentage:
            motor_value = self._get_motor_value_from_percentage(percentage)
        else:
            motor_value = MOTOR_SPEED_1  # Default: niedrigste Stufe
        
        await self._send_motor_command(motor_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        _LOGGER.info("Fan turn_off called")
        await self._send_motor_command(MOTOR_OFF)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        _LOGGER.info("Fan set_percentage called with %s%%", percentage)
        if percentage == 0:
            await self._send_motor_command(MOTOR_OFF)
        else:
            motor_value = self._get_motor_value_from_percentage(percentage)
            await self._send_motor_command(motor_value)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        _LOGGER.info("Fan set_preset_mode called with %s", preset_mode)
        motor_value = self._get_motor_value_from_preset(preset_mode)
        await self._send_motor_command(motor_value)

    def _get_motor_value_from_percentage(self, percentage: int) -> int:
        """Convert percentage to motor value."""
        if percentage <= 0:
            return MOTOR_OFF      # M:1
        elif percentage <= 25:
            return MOTOR_SPEED_1  # M:2
        elif percentage <= 50:
            return MOTOR_SPEED_2  # M:3
        elif percentage <= 75:
            return MOTOR_SPEED_3  # M:4
        else:
            return MOTOR_SPEED_4  # M:5

    def _get_motor_value_from_preset(self, preset_mode: str) -> int:
        """Convert preset mode to motor value."""
        preset_map = {
            "low": MOTOR_SPEED_1,    # M:2
            "medium": MOTOR_SPEED_2, # M:3
            "high": MOTOR_SPEED_3,   # M:4
            "max": MOTOR_SPEED_4,    # M:5
        }
        return preset_map.get(preset_mode, MOTOR_SPEED_1)

    async def _send_motor_command(self, motor_value: int) -> None:
        """Send motor command with dynamic JSON."""
        # Basis-Befehl mit aktuellem Licht-Status
        current_light = self._coordinator.current_state.get("L", 1)
        
        command_data = {
            "M": motor_value,  # Der wichtige Motor-Wert
            "L": current_light,  # Aktueller Licht-Status beibehalten
            "R": 45,
            "G": 255, 
            "B": 104,
            "CW": 255,
            "BRG": 132,
            "T": 0,
            "TM": 0,
            "TS": 255,
            "A": 1
        }
        
        import json
        command_str = json.dumps(command_data) + '\r'
        
        _LOGGER.info("Sending motor command: M=%s → %s", motor_value, repr(command_str))
        
        # Raw command senden
        result = await self._coordinator.send_raw_command(command_str)
        
        if result:
            # Internen Zustand aktualisieren
            self._coordinator._state.update(command_data)
            self.schedule_update_ha_state()
            _LOGGER.info("Motor command successful: M=%s", motor_value)
        else:
            _LOGGER.error("Motor command failed: M=%s", motor_value)