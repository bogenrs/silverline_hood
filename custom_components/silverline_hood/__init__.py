"""The Silverline Hood integration."""
import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, STATUS_QUERY, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DEVICE_IDENTIFIER

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["fan", "light"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Silverline Hood component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Silverline Hood from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    coordinator = SilverlineHoodCoordinator(hass, host, port, update_interval)
    
    # Fetch initial data so we have data when entities are loaded
    await coordinator.async_config_entry_first_refresh()
    
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


class SilverlineHoodCoordinator(DataUpdateCoordinator):
    """Coordinator for Silverline Hood communication."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, update_interval: int):
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self._last_sent_state = {
            "M": 0,
            "L": 0,
            "R": 255,
            "G": 255,
            "B": 255,
            "CW": 255,
            "BRG": 255,
            "T": 0,
            "TM": 0,
            "TS": 255,
            "A": 1,
        }

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
async def send_raw_command(self, raw_command: str) -> bool:
    """Send a raw command for testing purposes."""
    try:
        # Parse the JSON to validate it
        command_data = json.loads(raw_command)
        
        _LOGGER.info("Sending raw command: %s", raw_command)
        
        # Connect and handle initial response
        reader, writer = await self._connect_and_read_initial()
        
        # Try different formats
        formats = [
            raw_command + '\n',
            raw_command + '\r\n', 
            raw_command,
        ]
        
        for fmt in formats:
            _LOGGER.debug("Trying raw format: %s", repr(fmt))
            writer.write(fmt.encode())
            await writer.drain()
            await asyncio.sleep(1)
        
        writer.close()
        await writer.wait_closed()
        
        return True
        
    except Exception as ex:
        _LOGGER.error("Error sending raw command: %s", ex)
        return False
    
    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the hood."""
        try:
            return await self._query_status()
        except Exception as ex:
            raise UpdateFailed(f"Error communicating with Silverline Hood: {ex}")

    async def _connect_and_read_initial(self):
        """Connect and read the initial 'okidargb' response."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), timeout=10
        )
        
        # Read initial response (should be "okidargb")
        try:
            initial_response = await asyncio.wait_for(reader.read(100), timeout=3)
            initial_str = initial_response.decode().strip()
            _LOGGER.debug("Initial response from %s:%s: '%s'", self.host, self.port, initial_str)
        except asyncio.TimeoutError:
            _LOGGER.debug("No initial response received from %s:%s", self.host, self.port)
        
        return reader, writer

    async def _query_status(self) -> Dict[str, Any]:
        """Query the current status from the hood."""
        try:
            # Connect and handle initial response
            reader, writer = await self._connect_and_read_initial()
            
            # Send status query - try different formats
            query_command = json.dumps(STATUS_QUERY)
            
            _LOGGER.debug("Sending status query to %s:%s: '%s'", self.host, self.port, query_command)
            
            # Try different line endings
            for line_ending in ['\n', '\r\n', '']:
                try:
                    full_command = query_command + line_ending
                    writer.write(full_command.encode())
                    await writer.drain()
                    
                    # Wait a bit for response
                    await asyncio.sleep(0.5)
                    
                    # Read response
                    response = await asyncio.wait_for(reader.read(1024), timeout=3)
                    
                    if response:
                        response_str = response.decode().strip()
                        _LOGGER.debug("Status response with '%s' ending: '%s'", repr(line_ending), response_str)
                        
                        # Try to parse as JSON
                        try:
                            status_data = json.loads(response_str)
                            _LOGGER.info("Successfully parsed status JSON: %s", status_data)
                            writer.close()
                            await writer.wait_closed()
                            return status_data
                        except json.JSONDecodeError:
                            _LOGGER.debug("Status response is not JSON: '%s'", response_str)
                            continue
                
                except Exception as e:
                    _LOGGER.debug("Error with line ending '%s': %s", repr(line_ending), e)
                    continue
            
            writer.close()
            await writer.wait_closed()
            
            # Return last known state if no valid response
            _LOGGER.debug("No valid status response, returning last known state")
            return self._last_sent_state
                
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout querying Silverline Hood at %s:%s", self.host, self.port)
            raise
        except Exception as ex:
            _LOGGER.error("Error querying Silverline Hood at %s:%s: %s", self.host, self.port, ex)
            raise

    async def send_command(self, command: Dict[str, Any]) -> bool:
        """Send command to the Silverline Hood via Telnet."""
        try:
            # Update the last sent state with the command
            self._last_sent_state.update(command)
            
            # Convert to JSON string
            json_command = json.dumps(self._last_sent_state)
            
            _LOGGER.info("Preparing to send command to %s:%s: %s", self.host, self.port, json_command)
            
            # Connect and handle initial response
            reader, writer = await self._connect_and_read_initial()
            
            # Try different command formats
            formats_to_try = [
                json_command + '\n',           # JSON with newline
                json_command + '\r\n',         # JSON with CRLF
                json_command,                  # JSON without ending
                json_command + '\0',           # JSON with null terminator
            ]
            
            success = False
            for i, cmd_format in enumerate(formats_to_try):
                try:
                    _LOGGER.debug("Trying format %d: '%s' (bytes: %s)", i+1, repr(cmd_format), cmd_format.encode())
                    
                    writer.write(cmd_format.encode())
                    await writer.drain()
                    
                    # Wait a moment for any response
                    await asyncio.sleep(0.5)
                    
                    # Try to read any response
                    try:
                        response = await asyncio.wait_for(reader.read(1024), timeout=2)
                        if response:
                            response_str = response.decode().strip()
                            _LOGGER.debug("Command response for format %d: '%s'", i+1, response_str)
                    except asyncio.TimeoutError:
                        _LOGGER.debug("No response for format %d", i+1)
                    
                    # If we get here without exception, consider it a success
                    _LOGGER.info("Command sent successfully with format %d", i+1)
                    success = True
                    break
                    
                except Exception as e:
                    _LOGGER.debug("Format %d failed: %s", i+1, e)
                    continue
            
            writer.close()
            await writer.wait_closed()
            
            if success:
                _LOGGER.info("Successfully sent command to Silverline Hood")
                # Request immediate refresh to get updated status
                await self.async_request_refresh()
                return True
            else:
                _LOGGER.error("All command formats failed")
                return False
            
        except Exception as ex:
            _LOGGER.error("Error sending command to Silverline Hood at %s:%s: %s", self.host, self.port, ex)
            return False

    @property
    def current_state(self) -> Dict[str, Any]:
        """Return current state from coordinator data."""
        return self.data if self.data else self._last_sent_state

    def update_interval_seconds(self) -> int:
        """Return current update interval in seconds."""
        return int(self.update_interval.total_seconds())