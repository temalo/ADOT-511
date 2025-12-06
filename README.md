# ADOT 511

A Python project for interfacing with the Arizona Department of Transportation (ADOT) 511 API and outputting data to Meshtastic devices.

## Overview

This project provides scripts to:
- Fetch real-time alerts, incidents, and road condition data from the ADOT 511 API
- Process and format the data
- Send relevant alerts and updates to Meshtastic mesh network devices

## Features

- **ADOT 511 API Integration**: Retrieves current alerts and traffic incidents
- **Meshtastic Communication**: Supports both serial and TCP connections
- **Configurable Channels**: Send messages to specific Meshtastic channels
- **Automated Alerts**: Formats and distributes traffic information to mesh networks

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your API credentials and Meshtastic settings (see Configuration section)

## Configuration

Configure the application using environment variables. You can create a `.env` file in the project root:

### Meshtastic Connection Options

#### Serial Connection (Default)
```bash
MESHTASTIC_CONNECTION_TYPE=serial
MESHTASTIC_DEVICE_PATH=COM3  # Windows: COM3, Linux: /dev/ttyUSB0
```

#### TCP Connection
```bash
MESHTASTIC_CONNECTION_TYPE=tcp
MESHTASTIC_TCP_HOST=192.168.1.100
MESHTASTIC_TCP_PORT=4403  # Default port is 4403
```

#### Channel Configuration
```bash
MESHTASTIC_CHANNEL_INDEX=0  # Default is 0 (primary channel)
```

### ADOT API Configuration
Add your ADOT API credentials as needed.

## Usage

```bash
python src/main.py
```

## Project Structure

```
ADOT-511/
├── src/              # Source code
├── tests/            # Unit tests
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## License

MIT License
