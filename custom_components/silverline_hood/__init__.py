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

from .const import DOMAIN, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["fan", "light"]

# Service schemas
SERVICE_TEST_EXACT_COMMAND_SCHEMA = vol.Schema({
    vol.Required("command_type"): cv.string,
})

SERVICE_SEND_RAW_BYTES_SCHEMA = vol.Schema({
    vol.Required("command"): cv.string,
})


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

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def async_test_exact_command(call: ServiceCall):
        """Service to test exact commands."""
        command_type = call.data.get("command_type")
        _LOGGER.info("Service called: test_exact_command with type: %s", command_type)
        result = await coordinator.send_exact_command(command_type)
        _LOGGER.info("Service result: %s", result)

    async def async_send_raw_bytes(call: ServiceCall):
        """Service to send raw bytes."""
        command = call.data.get("command")
        _LOGGER.info("Service called: send_raw_bytes with command: %s", repr(command))
        result = await coordinator.send_raw_command(command)
        _LOGGER.info("Service result: %s", result)

    async def async_query_status(call: ServiceCall):
        """Service to query status."""
        _LOGGER.info("Service called: query_status")
        result = await coordinator.send_exact_command("status_query")
        _LOGGER.info("Status query result: %s", result)

    # Register services
    hass.services.async_register(
        DOMAIN, 
        "test_exact_command", 
        async_test_exact_command,
        schema=SERVICE_TEST_EXACT_COMMAND_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, 
        "send_raw_bytes", 
        async_send_raw_bytes,
        schema=SERVICE_SEND_RAW_BYTES_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, 
        "query_status", 
        async_query_status
    )

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


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


class SilverlineHoodCoordinator:
    """Test coordinator that mimics exact app communication."""

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
                "fan_speed_1": '{"M":1,"L":1,"R":45,"G":255,"B":104,"CW":255,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',
                "fan_speed_2": '{"M":2,"L":1,"R":45,"G":255,"B":104,"CW":255,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',
                "fan_speed_3": '{"M":3,"L":1,"R":45,"G":255,"B":104,"CW":3,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',
                "fan_off": '{"M":0,"L":1,"R":45,"G":255,"B":104,"CW":255,"BRG":132,"T":0,"TM":0,"TS":255,"A":1}\r',
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
                _LOGGER.info("  Response bytes: %s", [hex(b) for b in initial_response])
                
                # Check if we got the expected response
                if "okidargb" in initial_str:
                    _LOGGER.info("✓ Received expected 'okidargb' response")
                else:
                    _LOGGER.warning("⚠ Did not receive expected 'okidargb', got: %s", repr(initial_str))
                    
            except asyncio.TimeoutError:
                _LOGGER.warning("⚠ No initial response received within 5 seconds")
                initial_str = ""
            
            # Send the exact command
            _LOGGER.info("Sending command...")
            _LOGGER.info("  Bytes to send: %s", [hex(b) for b in command_str.encode()])
            
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
                    _LOGGER.info("  Response bytes: %s", [hex(b) for b in response])
                    
                    # Try to parse JSON if possible
                    try:
                        response_json = json.loads(response_str.strip())
                        _LOGGER.info("✓ Parsed response JSON: %s", response_json)
                        
                        # Update our state if we got a status response
                        if command_type == "status_query" and isinstance(response_json, dict):
                            self._state.update(response_json)
                            _LOGGER.info("✓ Updated internal state from response")
                            
                    except json.JSONDecodeError as e:
                        _LOGGER.info("ℹ Response is not JSON: %s", e)
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
            
        except asyncio.TimeoutError:
            _LOGGER.error("✗ Timeout connecting to %s:%s", self.host, self.port)
            return False
        except ConnectionRefusedError:
            _LOGGER.error("✗ Connection refused by %s:%s", self.host, self.port)
            return False
        except Exception as ex:
            _LOGGER.error("✗ Error in send_exact_command: %s", ex, exc_info=True)
            return False

    async def send_raw_command(self, command_str: str) -> bool:
        """Send raw command string."""
        try:
            _LOGGER.info("=== SENDING RAW COMMAND ===")
            _LOGGER.info("Command: %s", repr(command_str))
            _LOGGER.info("Bytes: %s", [hex(b) for b in command_str.encode()])
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            
            _LOGGER.info("✓ Connection established")
            
            # Read initial response
            try:
                initial_response = await asyncio.wait_for(reader.read(100), timeout=3)
                initial_str = initial_response.decode()
                _LOGGER.info("✓ Initial response: %s", repr(initial_str))
            except asyncio.TimeoutError:
                _LOGGER.info("ℹ No initial response")
            
            # Send command
            writer.write(command_str.encode())
            await writer.drain()
            _LOGGER.info("✓ Raw command sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(reader.read(2048), timeout=3)
                if response:
                    response_str = response.decode()
                    _LOGGER.info("✓ Response: %s", repr(response_str))
            except asyncio.TimeoutError:
                _LOGGER.info("ℹ No response")
            
            writer.close()
            await writer.wait_closed()
            _LOGGER.info("✓ Connection closed")
            
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Error in send_raw_command: %s", ex)
            return False

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Legacy method for compatibility with fan/light entities."""
        _LOGGER.info("=== LEGACY SEND_COMMAND CALLED ===")
        _LOGGER.info("Command: %s", command)
        
        # Map commands to exact types based on Wireshark data
        if command.get("L") == 2:  # Light on
            _LOGGER.info("→ Mapping to light_on")
            return await self.send_exact_command("light_on")
        elif command.get("L") == 0:  # Light off
            _LOGGER.info("→ Mapping to light_off")
            return await self.send_exact_command("light_off")
        elif command.get("M") == 1:  # Fan speed 1
            _LOGGER.info("→ Mapping to fan_speed_1")
            return await self.send_exact_command("fan_speed_1")
        elif command.get("M") == 2:  # Fan speed 2
            _LOGGER.info("→ Mapping to fan_speed_2")
            return await self.send_exact_command("fan_speed_2")
        elif command.get("M") == 3:  # Fan speed 3
            _LOGGER.info("→ Mapping to fan_speed_3")
            return await self.send_exact_command("fan_speed_3")
        elif command.get("M") == 0:  # Fan off
            _LOGGER.info("→ Mapping to fan_off")
            return await self.send_exact_command("fan_off")
        else:
            # Fallback: build command from current state
            _LOGGER.info("→ Using fallback method")
            self._state.update(command)
            command_str = json.dumps(self._state) + '\r'
            _LOGGER.info("→ Fallback command: %s", repr(command_str))
            return await self.send_raw_command(command_str)

    @property
    def current_state(self) -> Dict[str, Any]:
        """Return current state."""
        return self._state.copy()

    def update_interval_seconds(self) -> int:
        """Return update interval."""
        return 30

    # Additional debug methods
    async def test_connection_only(self) -> bool:
        """Test just the connection without sending commands."""
        try:
            _LOGGER.info("=== TESTING CONNECTION ONLY ===")
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=10
            )
            _LOGGER.info("✓ Connection successful")
            
            # Just read initial response
            try:
                response = await asyncio.wait_for(reader.read(100), timeout=5)
                response_str = response.decode()
                _LOGGER.info("✓ Initial response: %s", repr(response_str))
            except asyncio.TimeoutError:
                _LOGGER.info("ℹ No initial response")
            
            writer.close()
            await writer.wait_closed()
            _LOGGER.info("✓ Connection closed cleanly")
            return True
            
        except Exception as ex:
            _LOGGER.error("✗ Connection test failed: %s", ex)
            return False