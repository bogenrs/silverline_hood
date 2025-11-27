"""The Silverline Hood integration."""
import asyncio
import json
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["fan", "light", "sensor"]


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

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services nach dem Platform-Setup
    async def handle_test_exact_command(call: ServiceCall):
        """Handle test exact command service."""
        command_type = call.data.get("command_type", "status_query")
        _LOGGER.info("Service called: test_exact_command with type: %s", command_type)
        result = await coordinator.send_exact_command(command_type)
        _LOGGER.info("Service result: %s", result)

    async def handle_send_raw_bytes(call: ServiceCall):
        """Handle send raw bytes service."""
        command = call.data.get("command", '{"A":4}\r')
        _LOGGER.info("Service called: send_raw_bytes with command: %s", repr(command))
        result = await coordinator.send_raw_command(command)
        _LOGGER.info("Service result: %s", result)

    async def handle_query_status(call: ServiceCall):
        """Handle query status service."""
        _LOGGER.info("Service called: query_status")
        result = await coordinator.send_exact_command("status_query")
        _LOGGER.info("Status query result: %s", result)

    async def handle_extended_status(call: ServiceCall):
        """Handle extended status query."""
        _LOGGER.info("Service called: query_extended_status")
        result = await coordinator.query_extended_status()
        _LOGGER.info("Extended status result: %s", result)

    # Service-Schemas
    test_command_schema = vol.Schema({
        vol.Required("command_type", default="status_query"): vol.In([
            "light_on", "light_off", "fan_speed_1", "fan_speed_2", 
            "fan_speed_3", "fan_speed_4", "fan_off", "status_query"
        ])
    })

    raw_bytes_schema = vol.Schema({
        vol.Required("command", default='{"A":4}\r'): cv.string
    })

    # Services registrieren
    hass.services.async_register(
        DOMAIN,
        "test_exact_command",
        handle_test_exact_command,
        schema=test_command_schema
    )
    
    hass.services.async_register(
        DOMAIN,
        "send_raw_bytes",
        handle_send_raw_bytes,
        schema=raw_bytes_schema
    )
    
    hass.services.async_register(
        DOMAIN,
        "query_status",
        handle_query_status
    )

    hass.services.async_register(
        DOMAIN,
        "query_extended_status",
        handle_extended_status
    )

    _LOGGER.info("Silverline Hood integration setup completed with services")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove services
    hass.services.async_remove(DOMAIN, "test_exact_command")
    hass.services.async_remove(DOMAIN, "send_raw_bytes")
    hass.services.async_remove(DOMAIN, "query_status")
    hass.services.async_remove(DOMAIN, "query_extended_status")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


class SilverlineHoodCoordinator:
    """Smart coordinator for Silverline Hood communication."""

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        """Initialize the coordinator."""
        self.hass = hass
        self.host = host
        self.port = port
        
        # Exact state from Wireshark capture
        self._state = {
            "M": 1,
            "L": 1,
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

    async def _query_current_status(self) -> bool:
        """Query current status and update internal state."""
        try:
            _LOGGER.debug("Querying current status before command...")
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial response
            try:
                await asyncio.wait_for(reader.read(100), timeout=2)
            except asyncio.TimeoutError:
                pass
            
            # Send status query
            status_cmd = '{"A":4}\r'
            writer.write(status_cmd.encode())
            await writer.drain()
            
            # Read status response
            response = await asyncio.wait_for(reader.read(2048), timeout=3)
            if response:
                response_str = response.decode().strip()
                try:
                    status_data = json.loads(response_str)
                    # Update internal state with current values
                    self._state.update(status_data)
                    _LOGGER.debug("✓ Status updated: %s", status_data)
                    writer.close()
                    await writer.wait_closed()
                    return True
                except json.JSONDecodeError:
                    _LOGGER.debug("Status response not JSON: %s", response_str)
            
            writer.close()
            await writer.wait_closed()
            return False
            
        except Exception as ex:
            _LOGGER.debug("Status query failed: %s", ex)
            return False

    async def send_smart_command(self, changes: dict) -> bool:
        """Send command with only changed values, preserving current state."""
        try:
            _LOGGER.info("=== SMART COMMAND: %s ===", changes)
            
            # First, get current status
            await self._query_current_status()
            
            # Apply only the requested changes
            new_state = self._state.copy()
            new_state.update(changes)
            
            _LOGGER.info("Current state: %s", {k: self._state.get(k) for k in changes.keys()})
            _LOGGER.info("New state: %s", {k: new_state.get(k) for k in changes.keys()})
            
            # Send the complete command with preserved values
            command_str = json.dumps(new_state) + '\r'
            _LOGGER.info("Sending smart command: %s", repr(command_str))
            
            # Send command
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial response
            try:
                await asyncio.wait_for(reader.read(100), timeout=2)
            except asyncio.TimeoutError:
                pass
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            
            # Read response and update state
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=3)
                if response:
                    response_str = response.decode().strip()
                    try:
                        response_json = json.loads(response_str)
                        self._state.update(response_json)
                        _LOGGER.info("✓ Smart command successful, state updated")
                    except json.JSONDecodeError:
                        # Command successful even without JSON response
                        self._state.update(new_state)
                        _LOGGER.info("✓ Smart command sent, state assumed updated")
            except asyncio.TimeoutError:
                # No response is often normal, assume success
                self._state.update(new_state)
                _LOGGER.info("✓ Smart command sent, no response (normal)")
            
            writer.close()
            await writer.wait_closed()
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Smart command failed: %s", ex)
            return False

    async def send_exact_command(self, command_type: str) -> bool:
        """Send exact commands as seen in Wireshark."""
        try:
            _LOGGER.info("=== EXACT COMMAND: %s ===", command_type)
            
            # Define ONLY the changes for each command type
            command_changes = {
                # Light commands - only change light-related values
                "light_on": {"L": 2},
                "light_off": {"L": 0},
                
                # Fan commands - only change motor value
                "fan_off": {"M": 1},         # M:1 = AUS
                "fan_speed_1": {"M": 2},     # M:2 = Stufe 1  
                "fan_speed_2": {"M": 3},     # M:3 = Stufe 2
                "fan_speed_3": {"M": 4},     # M:4 = Stufe 3
                "fan_speed_4": {"M": 5},     # M:5 = Stufe 4
                
                # Status query
                "status_query": {},  # Special case
            }
            
            if command_type == "status_query":
                return await self._query_current_status()
            
            if command_type not in command_changes:
                _LOGGER.error("Unknown command type: %s", command_type)
                return False
            
            # Use smart command with only the necessary changes
            changes = command_changes[command_type]
            return await self.send_smart_command(changes)
            
        except Exception as ex:
            _LOGGER.error("✗ Error in send_exact_command: %s", ex, exc_info=True)
            return False

    async def send_raw_command(self, command_str: str) -> bool:
        """Send raw command string."""
        try:
            _LOGGER.info("=== RAW COMMAND ===")
            _LOGGER.info("Command: %s", repr(command_str))
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial response
            try:
                await asyncio.wait_for(reader.read(100), timeout=2)
            except asyncio.TimeoutError:
                pass
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            
            # Try to read and parse response
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=3)
                if response:
                    response_str = response.decode().strip()
                    try:
                        response_json = json.loads(response_str)
                        self._state.update(response_json)
                        _LOGGER.info("✓ Raw command response parsed and state updated")
                    except json.JSONDecodeError:
                        _LOGGER.info("✓ Raw command sent, response not JSON")
            except asyncio.TimeoutError:
                _LOGGER.info("✓ Raw command sent, no response")
            
            writer.close()
            await writer.wait_closed()
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Error in send_raw_command: %s", ex)
            return False

    async def query_extended_status(self) -> bool:
        """Query extended status information."""  
        try:
            _LOGGER.info("=== EXTENDED STATUS QUERY ===")
            
            # Normale Status-Abfrage
            await self._query_current_status()
            
            # Mögliche weitere Befehle für mehr Daten
            extended_queries = [
                '{"A":10}\r',
                '{"A":5}\r',
                '{"A":1}\r',
            ]
            
            for i, query in enumerate(extended_queries, 1):
                try:
                    _LOGGER.debug("Extended query %d: %s", i, repr(query))
                    await self.send_raw_command(query)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    _LOGGER.debug("Extended query %d failed: %s", i, e)
                    continue
            
            return True
            
        except Exception as ex:
            _LOGGER.error("Error in extended status query: %s", ex)
            return False

    @property
    def current_state(self) -> Dict[str, Any]:
        """Return current state."""
        return self._state.copy()

    def update_interval_seconds(self) -> int:
        """Return update interval."""
        return 30