"""The Silverline Hood integration."""
import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import voluptuous as vol

from .const import DOMAIN

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
    
    # Initial data fetch
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _register_services(hass)
    
    _LOGGER.info("Silverline Hood integration setup completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove services
    hass.services.async_remove(DOMAIN, "test_exact_command")
    hass.services.async_remove(DOMAIN, "send_raw_bytes")
    hass.services.async_remove(DOMAIN, "query_status")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def _register_services(hass: HomeAssistant):
    """Register services."""
    
    async def handle_test_exact_command(call: ServiceCall):
        """Handle test exact command service."""
        command_type = call.data.get("command_type", "status_query")
        # Get first coordinator
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            result = await coordinator.send_exact_command(command_type)
            _LOGGER.info("Service result: %s", result)

    async def handle_send_raw_bytes(call: ServiceCall):
        """Handle send raw bytes service."""
        command = call.data.get("command", '{"A":4}')
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            # Add \r if not present
            if not command.endswith('\r'):
                command += '\r'
            result = await coordinator.send_raw_command(command)
            _LOGGER.info("Raw command result: %s", result)

    async def handle_query_status(call: ServiceCall):
        """Handle query status service."""
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            await coordinator.async_request_refresh()

    # Service schemas
    test_command_schema = vol.Schema({
        vol.Required("command_type", default="status_query"): vol.In([
            "light_on", "light_off", "fan_speed_1", "fan_speed_2", 
            "fan_speed_3", "fan_speed_4", "fan_off", "status_query"
        ])
    })

    raw_bytes_schema = vol.Schema({
        vol.Required("command", default='{"A":4}'): cv.string
    })

    # Register services
    hass.services.async_register(DOMAIN, "test_exact_command", handle_test_exact_command, schema=test_command_schema)
    hass.services.async_register(DOMAIN, "send_raw_bytes", handle_send_raw_bytes, schema=raw_bytes_schema)
    hass.services.async_register(DOMAIN, "query_status", handle_query_status)


class SilverlineHoodCoordinator(DataUpdateCoordinator):
    """Coordinator with regular status updates."""

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),  # Update alle 10 Sekunden
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the hood."""
        try:
            return await self._query_current_status()
        except Exception as ex:
            # Don't fail on update errors, return last known state
            _LOGGER.debug("Status update failed: %s", ex)
            if hasattr(self, '_last_state'):
                return self._last_state
            # Return default state if no previous state exists
            return {
                "M": 1, "L": 1, "R": 45, "G": 255, "B": 104, 
                "CW": 110, "BRG": 132, "T": 0, "TM": 0, "TS": 0,
                "A": 1, "LM": 0, "CWD": 0, "RGBD": 0
            }

    async def _query_current_status(self) -> Dict[str, Any]:
        """Query current status and return parsed data."""
        try:
            _LOGGER.debug("=== QUERYING STATUS ===")
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial "okidargb"
            try:
                initial = await asyncio.wait_for(reader.read(100), timeout=3)
                initial_str = initial.decode().strip()
                _LOGGER.debug("Initial response: %s", repr(initial_str))
            except asyncio.TimeoutError:
                _LOGGER.debug("No initial response")
            
            # Send status query
            status_cmd = '{"A":4}\r'
            _LOGGER.debug("Sending status query: %s", repr(status_cmd))
            writer.write(status_cmd.encode())
            await writer.drain()
            
            # Read response
            response = await asyncio.wait_for(reader.read(2048), timeout=5)
            writer.close()
            await writer.wait_closed()
            
            if response:
                response_str = response.decode().strip()
                _LOGGER.debug("Status response: %s", repr(response_str))
                
                try:
                    status_data = json.loads(response_str)
                    _LOGGER.debug("✓ Parsed status JSON: %s", status_data)
                    self._last_state = status_data
                    return status_data
                except json.JSONDecodeError as e:
                    _LOGGER.warning("Cannot parse status JSON: %s", e)
            
            # Fallback to last known state
            if hasattr(self, '_last_state'):
                return self._last_state
                
            raise UpdateFailed("No valid status received")
            
        except Exception as ex:
            _LOGGER.debug("Status query error: %s", ex)
            raise

    async def send_smart_command(self, changes: dict) -> bool:
        """Send command with only changed values."""
        try:
            _LOGGER.info("=== SMART COMMAND: %s ===", changes)
            
            # Get current state first
            current_state = self.data or {}
            if not current_state:
                _LOGGER.warning("No current state available, using defaults")
                current_state = {
                    "M": 1, "L": 1, "R": 45, "G": 255, "B": 104, 
                    "CW": 110, "BRG": 132, "T": 0, "TM": 0, "TS": 0, "A": 1
                }
            
            # Create new state with changes
            new_state = current_state.copy()
            new_state.update(changes)
            
            # Send command
            command_str = json.dumps(new_state) + '\r'
            _LOGGER.info("Sending smart command: %s", repr(command_str))
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial "okidargb"
            try:
                await asyncio.wait_for(reader.read(100), timeout=2)
            except asyncio.TimeoutError:
                pass
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            
            # Read response
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=3)
                if response:
                    response_str = response.decode().strip()
                    _LOGGER.info("✓ Command response: %s", repr(response_str))
            except asyncio.TimeoutError:
                _LOGGER.debug("No command response (normal)")
            
            writer.close()
            await writer.wait_closed()
            
            # Force refresh after command
            await self.async_request_refresh()
            
            _LOGGER.info("✓ Smart command completed successfully")
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Smart command failed: %s", ex)
            return False

    async def send_exact_command(self, command_type: str) -> bool:
        """Send exact predefined commands."""
        command_changes = {
            "light_on": {"L": 2},
            "light_off": {"L": 1}, 
            "fan_off": {"M": 1},
            "fan_speed_1": {"M": 2},
            "fan_speed_2": {"M": 3},
            "fan_speed_3": {"M": 4},
            "fan_speed_4": {"M": 5},
        }
        
        if command_type == "status_query":
            await self.async_request_refresh()
            return True
        
        if command_type in command_changes:
            return await self.send_smart_command(command_changes[command_type])
        
        _LOGGER.error("Unknown command type: %s", command_type)
        return False

    async def send_raw_command(self, command_str: str) -> bool:
        """Send raw command string."""
        try:
            _LOGGER.info("=== RAW COMMAND: %s ===", repr(command_str))
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial "okidargb"
            try:
                await asyncio.wait_for(reader.read(100), timeout=2)
            except asyncio.TimeoutError:
                pass
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            
            writer.close()
            await writer.wait_closed()
            
            # Force refresh
            await self.async_request_refresh()
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Raw command failed: %s", ex)
            return False