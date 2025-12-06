# ADOT 511

A Python project for interfacing with the Arizona Department of Transportation (ADOT) 511 API and outputting data to Meshtastic devices.

## Overview

This project provides scripts to:
- Fetch real-time traffic and road condition data from the ADOT 511 API
- Process and format the data
- Send relevant alerts and updates to Meshtastic mesh network devices

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your API credentials and Meshtastic settings (see Configuration section)

## Configuration

Create a `config.json` file with your ADOT API key and Meshtastic connection details.

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
