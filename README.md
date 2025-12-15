# ADOT 511

A Python project for interfacing with the Arizona Department of Transportation (ADOT) 511 API and outputting data to Meshtastic devices.

## Overview

This project provides scripts to:
- Fetch real-time alerts, incidents, and road condition data from the ADOT 511 API
- Process and format the data
- Send relevant alerts and updates to Meshtastic mesh network devices

## Features

- **ADOT 511 API Integration**: Retrieves real-time traffic incidents, accidents, and road events from Arizona's 511 system
- **Meshtastic Communication**: Supports both serial and TCP connections to Meshtastic devices
- **Two-Way Listener**: Monitors Meshtastic channels for commands and responds automatically with real-time traffic data
- **Intelligent Message Formatting**: 
  - Formats accident data with location, direction, lanes affected, and elapsed time
  - Automatically splits messages longer than 200 characters at logical breakpoints
  - Sends multiple results with proper spacing
- **Geocoding**: Converts coordinates to human-readable addresses for better location context
- **Configurable Channels**: Send and receive messages on specific Meshtastic channels
- **Command Pattern Matching**: Recognizes natural language commands like "accidents 101" or "events phoenix"
- **One-Time Query Mode**: Run standalone queries without starting the listener
- **Debug & Testing Modes**: Offline testing with --test and --simulate flags

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
MESHTASTIC_CHANNEL_INDEX=1  # Channel to listen on and send messages to (default: 0)
```

**Note:** Make sure the channel index matches the channel you want to monitor. The listener will only process messages from the configured channel.

### ADOT API Configuration
```bash
ADOT_API_KEY=your_api_key_here  # Required: Your ADOT 511 API key
```

### Debug Mode
```bash
ENABLE_MESHTASTIC_SEND=false  # Set to 'true' to enable Meshtastic sending, 'false' for debug mode (default: false)
```

### Listener Mode Configuration
```bash
MAX_RESULTS_PER_QUERY=3  # Maximum number of results to return per command (default: 3)
```

### Advanced Configuration
```bash
# Optional geocoding cache directory (improves performance for repeated queries)
# The application will automatically cache geocoded locations
```

## Usage

### One-Time Query Mode

Run the application with optional command-line parameters:

```bash
python src/main.py [search_type] [location]
```

#### Parameters

- **search_type** (optional): Type of data to search for
  - Options: `accidents`, `events`, `alerts`, `weather`, `listen`
  - Default: `accidents`
  - Case-insensitive
  
- **location** (optional): Location to search (not used in listen mode)
  - Default: `phoenix`
  - Case-insensitive

#### Examples

```bash
# Use default parameters (accidents in Phoenix)
python src/main.py

# Search for accidents in Tucson
python src/main.py accidents tucson

# Search for weather in Phoenix (case-insensitive)
python src/main.py WEATHER Phoenix

# Search for alerts in Flagstaff
python src/main.py alerts flagstaff

# Search for accidents on I-101
python src/main.py accidents 101

# Search for accidents on I-10
python src/main.py accidents i-10
```

### Listener Mode

Start the listener to monitor Meshtastic channels for commands:

```bash
python src/main.py listen
```

The listener will monitor the configured Meshtastic channel and respond to commands in the format:

```
<command_type> <location>
```

#### Supported Commands

- `accidents <location>` - Search for accidents in the specified location
- `events <location>` - Search for non-accident events (construction, road closures, etc.)
- `alerts <location>` - Search for alerts (placeholder - not yet implemented)
- `weather <location>` - Search for weather (placeholder - not yet implemented)

#### Command Examples

When the listener is running, other Meshtastic users on the same channel can send these commands:

- `accidents 101` - Find accidents on the 101 Loop
- `accidents I-17` - Find accidents on Interstate 17
- `accidents I17` - Also finds accidents on Interstate 17 (dash optional)
- `accidents phoenix` - Find accidents in the Phoenix area
- `accidents i-10` - Find accidents on I-10 (case-insensitive)
- `accidents I10` - Same as I-10 (normalized automatically)
- `events tucson` - Find events (construction, closures) in Tucson
- `events scottsdale` - Find events in Scottsdale
- `events i8` - Find events on Interstate 8 (normalized to I-8)

**Note:** Interstate highway names are automatically normalized for consistency. Whether you send `I10`, `i10`, `I-10`, or `i-10`, the system treats them all as `I-10`.

The listener will:
1. Receive the command from the mesh network
2. Query the ADOT 511 API for matching incidents
3. Format each result with location, direction, and time information
4. Send up to 3 results (configurable via `MAX_RESULTS_PER_QUERY`) back to the mesh
5. Automatically split messages longer than 200 characters at logical breakpoints

#### Response Format

**Accidents:**
```
ACCIDENT: I-10 (East) @ Papago Freeway, Avondale [2h15m ago]
```

**Events:**
```
EVENT: Road Work - I-17 (North) @ Happy Valley [Active]
```

If no results are found, the listener will respond with:
```
No accidents found for 'location'
```

### Standalone Listener Testing

You can test the listener functionality without a Meshtastic connection:

```bash
# Test accident query (offline test mode)
python src/meshtastic_listener.py --test "accidents 101"

# Test event query (offline test mode)
python src/meshtastic_listener.py --test "events phoenix"

# Simulate receiving a Meshtastic message (with full debug output)
python src/meshtastic_listener.py --simulate "accidents 101"

# Test with a non-command message (to see debug output for unmatched patterns)
python src/meshtastic_listener.py --simulate "hello world"
```

These test modes allow you to:
- Verify command parsing without a Meshtastic connection
- Test ADOT API integration and response formatting
- Debug message handling logic
- See how the listener responds to various inputs

### How It Works

#### Listener Operation

1. **Connection**: Establishes TCP or serial connection to your Meshtastic device
2. **Monitoring**: Listens for TEXT_MESSAGE_APP packets on the configured channel
3. **Filtering**: Ignores telemetry, nodeinfo, and other non-text packets
4. **Command Parsing**: Matches incoming messages against the pattern `<command> <location>`
5. **Location Normalization**: Automatically normalizes interstate highway names (I10 → I-10, i17 → I-17)
6. **API Query**: Fetches real-time data from ADOT 511 API based on the command
7. **Geocoding**: Converts coordinates to readable addresses (cached for performance)
8. **Formatting**: Formats results with clear location, direction, and timing information
9. **Message Splitting**: Automatically splits long messages at logical breakpoints (spaces, commas, parentheses)
10. **Transmission**: Sends formatted responses back to the mesh network with 0.5s delays between messages

#### Message Length Handling

Meshtastic has a 200-character limit per message. The application automatically:
- Detects messages that exceed 200 characters
- Splits them at logical breakpoints (spaces, commas, closing parentheses)
- Adds "..." to continuation messages
- Preserves message integrity and readability

Example of a split message:
```
Part 1: ACCIDENT: 101-LOOP (West) @ Agua Fria Freeway and The Highlands at...
Part 2: ...Arrowhead Ranch [15m ago]
```

### Debug Output

The listener includes comprehensive logging to help monitor and troubleshoot operation:

#### What Gets Logged

- **Connection Status**: TCP/serial connection establishment and node information
- **Channel Filtering**: Which channel is being monitored
- **Received Messages**: All text messages on the configured channel with sender info
- **Command Processing**: Command parsing and location extraction
- **API Queries**: ADOT 511 API requests and result counts
- **Geocoding**: Address lookups and caching
- **Message Sending**: Transmission status with message IDs
- **Errors**: Clear error messages for any failures

#### Message Reception

The listener shows detailed information for each received message:

```
======================================================================
[MESSAGE RECEIVED] From: 331505969, To: 4294967295, Channel: 1
[MESSAGE CONTENT] 'Accidents 101'
======================================================================
```

#### Ignored Messages

Messages that don't match the command pattern are logged but not processed:

```
[DEBUG] Message does not match command pattern: 'hello world'
[DEBUG] Expected pattern: '<command_type> <location>' (e.g., 'accidents 101')
```

#### Automatic Filtering

The listener automatically filters out and silently ignores:
- Telemetry packets (TELEMETRY_APP)
- Node information broadcasts (NODEINFO_APP)
- Position updates (POSITION_APP)
- Messages on other channels
- Non-text packets

When running in listen mode (`python src/main.py listen`), debug logging is automatically enabled.

## Troubleshooting

### Common Issues

**Listener not receiving messages:**
- Verify `MESHTASTIC_CHANNEL_INDEX` matches the channel you're sending messages on
- Check that your Meshtastic device is connected (TCP: verify IP/port, Serial: verify COM port)
- Ensure messages are TEXT_MESSAGE_APP type (regular text messages)

**Messages not being sent:**
- The TCP connection may reconnect automatically - this is normal behavior
- Each message includes a 0.5 second delay to ensure transmission
- Check that the ADOT API is returning results for your query location

**API returns no results:**
- Try a broader location (e.g., "phoenix" instead of a specific street)
- Major highways work well: "101", "I-17", "I-10"
- Location matching is case-insensitive and flexible

**Messages being split unexpectedly:**
- This is normal for long messages (>200 characters)
- The split logic preserves message readability
- Adjust `MAX_RESULTS_PER_QUERY` to reduce response length

## Project Structure

```
ADOT-511/
├── src/
│   ├── main.py                    # Main entry point for one-time queries and listener
│   ├── adot_client.py            # ADOT 511 API client
│   ├── meshtastic_sender.py      # Meshtastic message sending with auto-split
│   ├── meshtastic_listener.py    # Command listener and response handler
│   └── __pycache__/              # Python cache files
├── tests/                         # Unit tests (future)
├── requirements.txt               # Python dependencies
├── .env.example                  # Example environment configuration
└── README.md                     # This file
```

## Dependencies

Key Python packages used:
- **meshtastic** (>=2.2.0): Interface with Meshtastic devices via TCP or serial
- **requests**: HTTP client for ADOT 511 API
- **python-dotenv**: Environment variable management
- **geopy**: Geocoding for coordinate-to-address conversion

See `requirements.txt` for complete list.

## Implementation Notes

### Current Status

**Fully Implemented:**
- ✅ Accidents search (via ADOT 511 API)
- ✅ Events search (filters out accidents to show construction, closures, etc.)
- ✅ Meshtastic TCP and serial connections
- ✅ Two-way listener with command parsing
- ✅ Automatic message splitting at 200 characters
- ✅ Geocoding with caching
- ✅ Channel-specific filtering
- ✅ Time elapsed calculation for incidents

**Placeholders (Future Implementation):**
- ⏳ Alerts command
- ⏳ Weather command

### Technical Details

- **Pubsub Pattern**: Uses pubsub library for Meshtastic message callbacks
- **Regex Matching**: Commands parsed with pattern `^\s*(accidents|events|alerts|weather)\s+(.+?)\s*$`
- **Interstate Normalization**: Automatically converts `I10`, `i10`, `I-10` (any case, with/without dash) to standard `I-10` format
- **Geocoding Provider**: OpenStreetMap Nominatim (1 second rate limit)
- **Timezone**: Arizona time (America/Phoenix) for elapsed time calculations
- **Message Priority**: All sent messages use RELIABLE priority
- **Auto-reconnect**: TCP socket reconnects automatically if disconnected

## License

MIT License
