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
    """Simple coordinator for Silverline Hood communication."""

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

    async def send_exact_command(self, command_type: str) -> bool:
        """Send exact commands as seen in Wireshark."""
        try:
            _LOGGER.info("=== STARTING EXACT COMMAND SEND ===")
            _LOGGER.info("Target: %s:%s", self.host, self.port)
            _LOGGER.info("Command type: %s", command_type)
            
            # Define exact commands from Wireshark capture
            commands = {
                "light_on": '{"M":1,"L":2,"R":45,"G":255,"B":104,"CW":110,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',
                "light_off": '{"M":1,"L":0,"R":45,"G":255,"B":104,"CW":110,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',

                # KORRIGIERTE FAN-BEFEHLE
                "fan_off": '{"M":1,"L":1,"R":45,"G":255,"B":104,"CW":255,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',      # M:1 = AUS
                "fan_speed_1": '{"M":2,"L":1,"R":45,"G":255,"B":104,"CW":255,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',  # M:2 = Stufe 1  
                "fan_speed_2": '{"M":3,"L":1,"R":45,"G":255,"B":104,"CW":255,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',  # M:3 = Stufe 2
                "fan_speed_3": '{"M":4,"L":1,"R":45,"G":255,"B":104,"CW":255,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',  # M:4 = Stufe 3
                "fan_speed_4": '{"M":5,"L":1,"R":45,"G":255,"B":104,"CW":255,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',  # M:5 = Stufe 4

                "status_query": '{"A":4}\r',
            }
            
            if command_type not in commands:
                _LOGGER.error("Unknown command type: %s. Available: %s", command_type, list(commands.keys()))
                return False
                
            command_str = commands[command_type]
            
            _LOGGER.info("Command string: %s", repr(command_str))
            _LOGGER.info("Command bytes: %s", [hex(b) for b in command_str.encode()])
            
            # Open connection
            _LOGGER.info("Opening connection...")
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            _LOGGER.info("✓ Connection established to %s:%s", self.host, self.port)
            
            # Read initial response
            _LOGGER.info("Waiting for initial response...")
            try:
                initial_response = await asyncio.wait_for(reader.read(100), timeout=5)
                initial_str = initial_response.decode()
                _LOGGER.info("✓ Initial response received: %s", repr(initial_str))
                
                if "okidargb" in initial_str:
                    _LOGGER.info("✓ Received expected 'okidargb' response")
                else:
                    _LOGGER.warning("⚠ Did not receive expected 'okidargb', got: %s", repr(initial_str))
                    
            except asyncio.TimeoutError:
                _LOGGER.warning("⚠ No initial response received within 5 seconds")
            
            # Send the exact command
            _LOGGER.info("Sending command...")
            writer.write(command_str.encode())
            await writer.drain()
            _LOGGER.info("✓ Command sent and flushed")
            
            # Wait for response
            _LOGGER.info("Waiting for command response...")
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=5)
                if response:
                    response_str = response.decode()
                    _LOGGER.info("✓ Command response received: %s", repr(response_str))
                    
                    # Try to parse JSON if possible
                    try:
                        response_json = json.loads(response_str.strip())
                        _LOGGER.info("✓ Parsed response JSON: %s", response_json)
                        
                        # Update our state if we got a status response
                        if command_type == "status_query" and isinstance(response_json, dict):
                            self._state.update(response_json)
                            _LOGGER.info("✓ Updated internal state from response")
                        # Update state for other commands too
                        elif isinstance(response_json, dict):
                            self._state.update(response_json)
                            
                    except json.JSONDecodeError:
                        _LOGGER.info("ℹ Response is not JSON")
                else:
                    _LOGGER.info("ℹ No response received")
            except asyncio.TimeoutError:
                _LOGGER.info("ℹ No response within timeout")
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            _LOGGER.info("✓ Connection closed")
            _LOGGER.info("=== COMMAND SEND COMPLETED SUCCESSFULLY ===")
            
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Error in send_exact_command: %s", ex, exc_info=True)
            return False

    async def send_raw_command(self, command_str: str) -> bool:
        """Send raw command string."""
        try:
            _LOGGER.info("=== SENDING RAW COMMAND ===")
            _LOGGER.info("Command: %s", repr(command_str))
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            # Read initial response
            try:
                initial_response = await asyncio.wait_for(reader.read(100), timeout=3)
                initial_str = initial_response.decode()
                _LOGGER.debug("Initial response for raw command: %s", repr(initial_str))
            except asyncio.TimeoutError:
                _LOGGER.debug("No initial response for raw command")
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            _LOGGER.info("✓ Raw command sent")
            
            # Try to read response
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=3)
                if response:
                    response_str = response.decode()
                    _LOGGER.info("✓ Raw command response: %s", repr(response_str))
                    
                    # Try to parse and update state
                    try:
                        response_json = json.loads(response_str.strip())
                        self._state.update(response_json)
                        _LOGGER.info("✓ Updated state from raw command response")
                    except json.JSONDecodeError:
                        _LOGGER.debug("Raw response is not JSON")
            except asyncio.TimeoutError:
                _LOGGER.debug("No response for raw command")
            
            writer.close()
            await writer.wait_closed()
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Error in send_raw_command: %s", ex)
            return False

    async def query_extended_status(self) -> bool:
        """Query extended status information."""  
        try:
            _LOGGER.info("=== STARTING EXTENDED STATUS QUERY ===")
            
            # Normale Status-Abfrage
            await self.send_exact_command("status_query")
            
            # Mögliche weitere Befehle für mehr Daten
            extended_queries = [
                '{"A":10}\r',  # Andere Status-Query
                '{"A":5}\r',   # Noch eine Query
                '{"A":1}\r',   # Weitere Query
            ]
            
            for i, query in enumerate(extended_queries, 1):
                try:
                    _LOGGER.info("Extended query %d: %s", i, repr(query))
                    await self.send_raw_command(query)
                    await asyncio.sleep(0.5)  # Kurz warten zwischen Abfragen
                except Exception as e:
                    _LOGGER.debug("Extended query %d failed: %s", i, e)
                    continue
            
            _LOGGER.info("=== EXTENDED STATUS QUERY COMPLETED ===")
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