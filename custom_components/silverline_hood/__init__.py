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
    services_to_remove = [
        "test_exact_command", "send_raw_bytes", "query_status",
        "test_light_on", "test_light_off", "test_fan_on", "test_fan_off",
        "test_minimal", "test_full"
    ]
    
    for service in services_to_remove:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
    
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
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            result = await coordinator.send_exact_command(command_type)
            _LOGGER.info("Service test_exact_command result: %s", result)

    async def handle_send_raw_bytes(call: ServiceCall):
        """Handle send raw bytes service."""
        command = call.data.get("command", '{"A":4}')
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            # Add \r if not present
            if not command.endswith('\r'):
                command += '\r'
            result = await coordinator.send_raw_command(command)
            _LOGGER.info("Service send_raw_bytes result: %s", result)

    async def handle_query_status(call: ServiceCall):
        """Handle query status service."""
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            await coordinator.async_request_refresh()
            _LOGGER.info("Status refresh requested")

    async def handle_test_light_on(call: ServiceCall):
        """Test light on directly."""
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            _LOGGER.info("=== TESTING LIGHT ON ===")
            result = await coordinator.send_smart_command({"L": 2})
            _LOGGER.info("Light ON result: %s", result)

    async def handle_test_light_off(call: ServiceCall):
        """Test light off directly."""
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            _LOGGER.info("=== TESTING LIGHT OFF ===")
            result = await coordinator.send_smart_command({"L": 1})
            _LOGGER.info("Light OFF result: %s", result)

    async def handle_test_fan_on(call: ServiceCall):
        """Test fan on directly."""
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            _LOGGER.info("=== TESTING FAN ON ===")
            result = await coordinator.send_smart_command({"M": 2})
            _LOGGER.info("Fan ON result: %s", result)

    async def handle_test_fan_off(call: ServiceCall):
        """Test fan off directly."""
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            _LOGGER.info("=== TESTING FAN OFF ===")
            result = await coordinator.send_smart_command({"M": 1})
            _LOGGER.info("Fan OFF result: %s", result)

    async def handle_test_minimal(call: ServiceCall):
        """Test minimal command."""
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            _LOGGER.info("=== TESTING MINIMAL COMMAND ===")
            result = await coordinator.send_minimal_command({"L": 2})
            _LOGGER.info("Minimal command result: %s", result)

    async def handle_test_full(call: ServiceCall):
        """Test full command."""
        coordinator = next(iter(hass.data[DOMAIN].values()), None)
        if coordinator:
            _LOGGER.info("=== TESTING FULL COMMAND ===")
            result = await coordinator.send_smart_command({"L": 2})
            _LOGGER.info("Full command result: %s", result)

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
    hass.services.async_register(DOMAIN, "test_light_on", handle_test_light_on)
    hass.services.async_register(DOMAIN, "test_light_off", handle_test_light_off)
    hass.services.async_register(DOMAIN, "test_fan_on", handle_test_fan_on)
    hass.services.async_register(DOMAIN, "test_fan_off", handle_test_fan_off)
    hass.services.async_register(DOMAIN, "test_minimal", handle_test_minimal)
    hass.services.async_register(DOMAIN, "test_full", handle_test_full)

    _LOGGER.info("All Silverline Hood services registered")


class SilverlineHoodCoordinator(DataUpdateCoordinator):
    """Coordinator with regular status updates."""

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self._last_state = {
            "M": 1, "L": 1, "R": 45, "G": 255, "B": 104, 
            "CW": 110, "BRG": 132, "T": 0, "TM": 0, "TS": 0,
            "A": 1, "LM": 0, "CWD": 0, "RGBD": 0
        }
        
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
            return self._last_state

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
                    self._last_state.update(status_data)
                    return status_data
                except json.JSONDecodeError as e:
                    _LOGGER.warning("Cannot parse status JSON: %s", e)
            
            # Fallback to last known state
            return self._last_state
            
        except Exception as ex:
            _LOGGER.debug("Status query error: %s", ex)
            raise UpdateFailed(f"Failed to query status: {ex}")

    async def send_smart_command(self, changes: dict) -> bool:
        """Send command with only changed values."""
        try:
            _LOGGER.info("=== SMART COMMAND START ===")
            _LOGGER.info("Changes requested: %s", changes)
            
            # Get current state
            current_state = self.data or self._last_state
            _LOGGER.info("Current coordinator data: %s", current_state)
            
            # Create new state with changes
            new_state = current_state.copy()
            new_state.update(changes)
            
            # Remove unwanted keys that might cause issues
            clean_state = {}
            for key in ["M", "L", "R", "G", "B", "CW", "BRG", "T", "TM", "TS", "A"]:
                if key in new_state:
                    clean_state[key] = new_state[key]
            
            _LOGGER.info("Sending state: %s", clean_state)
            
            # Send command
            command_str = json.dumps(clean_state) + '\r'
            _LOGGER.info("Command string: %s", repr(command_str))
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial "okidargb"
            try:
                initial = await asyncio.wait_for(reader.read(100), timeout=2)
                _LOGGER.info("Initial response: %s", repr(initial.decode()))
            except asyncio.TimeoutError:
                _LOGGER.info("No initial response")
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            _LOGGER.info("✓ Command sent")
            
            # Read response
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=3)
                if response:
                    response_str = response.decode().strip()
                    _LOGGER.info("✓ Command response: %s", repr(response_str))
                    
                    # Try to parse and update our state
                    try:
                        response_data = json.loads(response_str)
                        self._last_state.update(response_data)
                        _LOGGER.info("✓ State updated from response")
                    except json.JSONDecodeError:
                        _LOGGER.debug("Response not JSON, assuming success")
                        # Update our local state with the changes we sent
                        self._last_state.update(changes)
            except asyncio.TimeoutError:
                _LOGGER.info("No command response (might be normal)")
                # Update our local state with the changes we sent
                self._last_state.update(changes)
            
            writer.close()
            await writer.wait_closed()
            
            # Force refresh after 1 second to see the change
            await asyncio.sleep(1)
            await self.async_request_refresh()
            
            _LOGGER.info("=== SMART COMMAND COMPLETED ===")
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Smart command failed: %s", ex, exc_info=True)
            return False

    async def send_minimal_command(self, changes: dict) -> bool:
        """Send only the changed values - TEST VERSION."""
        try:
            _LOGGER.info("=== MINIMAL COMMAND TEST: %s ===", changes)
            
            # Nur die Änderungen als JSON
            command_str = json.dumps(changes) + '\r'
            _LOGGER.info("Sending minimal: %s", repr(command_str))
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial "okidargb"
            try:
                initial = await asyncio.wait_for(reader.read(100), timeout=2)
                _LOGGER.info("Initial response: %s", repr(initial.decode()))
            except asyncio.TimeoutError:
                _LOGGER.info("No initial response")
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            
            # Read response
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=3)
                if response:
                    response_str = response.decode().strip()
                    _LOGGER.info("✓ Minimal response: %s", repr(response_str))
            except asyncio.TimeoutError:
                _LOGGER.debug("No response to minimal command")
            
            writer.close()
            await writer.wait_closed()
            
            # Force refresh
            await asyncio.sleep(1)
            await self.async_request_refresh()
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Minimal command failed: %s", ex)
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
                initial = await asyncio.wait_for(reader.read(100), timeout=2)
                _LOGGER.info("Initial response: %s", repr(initial.decode()))
            except asyncio.TimeoutError:
                _LOGGER.info("No initial response")
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            
            # Read response
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=3)
                if response:
                    response_str = response.decode().strip()
                    _LOGGER.info("✓ Raw response: %s", repr(response_str))
            except asyncio.TimeoutError:
                _LOGGER.info("No raw command response")
            
            writer.close()
            await writer.wait_closed()
            
            # Force refresh
            await asyncio.sleep(1)
            await self.async_request_refresh()
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Raw command failed: %s", ex)
            return False

    @property
    def current_state(self) -> Dict[str, Any]:
        """Return current state for backward compatibility."""
        return self.data or self._last_state