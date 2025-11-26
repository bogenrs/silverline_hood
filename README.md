# Silverline Hood Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]
[![hacs][hacsbadge]][hacs]
[![Community Forum][forum-shield]][forum]

**This integration allows you to control your Silverline range hood via Home Assistant.**

[🇩🇪 Deutsche Version](README_DE.md)

## Features

- 🌀 **Fan Control**: 4 speed levels (Off, Low, Medium, High, Maximum)
- 💡 **RGBW Lighting**: Full color and brightness control
- 🔄 **Bidirectional Sync**: Automatic detection of changes via remote control
- ⚙️ **Configurable Poll Interval**: 5-300 seconds via Home Assistant UI
- 🌐 **Telnet Communication**: Reliable connection over local network

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add `https://github.com/bogenrs/silverline_hood` as repository
5. Select "Integration" as category
6. Search for "Silverline Hood" and install it
7. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Extract the contents to `custom_components/silverline_hood/`
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Silverline Hood"
4. Enter the IP address of your range hood
5. Enter the port (default: 23)

### Configure Options

After installation, you can configure additional options:

1. Go to **Settings** → **Devices & Services**
2. Find "Silverline Hood" and click **Configure**
3. Set the desired poll interval (5-300 seconds)

## JSON Command Structure

The integration uses the following JSON structure for communication:

```json
{
    "M": 2,      // Motor: 0=Off, 1-4=Speed levels
    "L": 1,      // Light: 0=Off, 1=On
    "R": 255,    // Red (0-255)
    "G": 7,      // Green (0-255)
    "B": 209,    // Blue (0-255)
    "CW": 255,   // Cold White (0-255)
    "BRG": 163,  // Brightness (0-255)
    "T": 0,      // Unknown
    "TM": 0,     // Unknown
    "TS": 255,   // Unknown
    "A": 1       // Status query with {"A": 4}
}