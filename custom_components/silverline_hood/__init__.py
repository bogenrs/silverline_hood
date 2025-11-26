"""The Silverline Hood integration."""
import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN, 
    STATUS_QUERY, 
    CONF_UPDATE_INTERVAL, 
    DEFAULT_UPDATE_INTERVAL, 
    DEVICE_IDENTIFIER,
    CMD_LINE_ENDING,
    CMD_MOTOR,
    CMD_LIGHT,
    CMD_RED,
    CMD_GREEN,
    CMD_BLUE,
    CMD_COLD_WHITE,
    CMD_BRIGHTNESS,
    CMD_T,
    CMD_TM,
    CMD_TS,
    CMD_A,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["fan", "light"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Silverline Hood component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Silverline Hood from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    coordinator = SilverlineHoodCoordinator(hass, host, port)
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


class SilverlineHoodCoordinator:
    """Simple coordinator for Silverline Hood communication."""

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        """Initialize the coordinator."""
        self.hass = hass
        self.host = host
        self.port = port
        
        # Initial state basierend auf der App-Kommunikation
        self._state = {
            CMD_MOTOR: 0,
            CMD_LIGHT: 0,
            CMD_RED: 45,
            CMD_GREEN: 255,
            CMD_BLUE: 104,
            CMD_COLD_WHITE: 255,
            CMD_BRIGHTNESS: 132,
            CMD_T: 0,
            CMD_TM: 0,
            CMD_TS: 255,
            CMD_A: 1,
        }

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send command to the Silverline Hood via Telnet."""
        try:
            # Update the internal state with the command
            self._state.update(command)
            
            # Convert to JSON string mit Carriage Return (wie in der App)
            json_command = json.dumps(self._state) + CMD_LINE_ENDING
            
            _LOGGER.info("Sending command to %s:%s: %s", self.host, self.port, repr(json_command))
            
            # Connect
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial response (should be "okidargb")
            try:
                initial_response = await asyncio.wait_for(reader.read(100), timeout=3)
                initial_str = initial_response.decode().strip()
                _LOGGER.debug("Initial response: '%s'", initial_str)
            except asyncio.TimeoutError:
                _LOGGER.debug("No initial response received")
            
            # Send command with exact format from app
            _LOGGER.debug("Sending bytes: %s", json_command.encode())
            writer.write(json_command.encode())
            await writer.drain()
            
            # Wait for any response
            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=2)
                if response:
                    response_str = response.decode().strip()
                    _LOGGER.debug("Command response: '%s'", response_str)
            except asyncio.TimeoutError:
                _LOGGER.debug("No command response received")
            
            writer.close()
            await writer.wait_closed()
            
            _LOGGER.info("Command sent successfully to Silverline Hood")
            return True
            
        except Exception as ex:
            _LOGGER.error("Error sending command to Silverline Hood: %s", ex)
            return False

    async def query_status(self) -> Dict[str, Any]:
        """Query current status from hood."""
        try:
            # Connect
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial response
            try:
                initial_response = await asyncio.wait_for(reader.read(100), timeout=3)
                initial_str = initial_response.decode().strip()
                _LOGGER.debug("Initial response for status: '%s'", initial_str)
            except asyncio.TimeoutError:
                _LOGGER.debug("No initial response for status")
            
            # Send status query
            status_cmd = json.dumps(STATUS_QUERY) + CMD_LINE_ENDING
            _LOGGER.debug("Sending status query: %s", repr(status_cmd))
            writer.write(status_cmd.encode())
            await writer.drain()
            
            # Read status response
            response = await asyncio.wait_for(reader.read(2048), timeout=5)
            if response:
                response_str = response.decode().strip()
                _LOGGER.debug("Status response: '%s'", response_str)
                
                try:
                    status_data = json.loads(response_str)
                    _LOGGER.info("Successfully parsed status: %s", status_data)
                    writer.close()
                    await writer.wait_closed()
                    return status_data
                except json.JSONDecodeError as e:
                    _LOGGER.warning("Cannot parse status JSON: %s", e)
            
            writer.close()
            await writer.wait_closed()
            return self._state
            
        except Exception as ex:
            _LOGGER.error("Error querying status: %s", ex)
            return self._state

    @property
    def current_state(self) -> Dict[str, Any]:
        """Return current state."""
        return self._state.copy()

    def update_interval_seconds(self) -> int:
        """Return update interval (not used in simple version)."""
        return 30