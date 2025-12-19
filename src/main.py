"""
ADOT 511 to Meshtastic Integration
Main entry point for the application
"""

import argparse
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from adot_client import ADOTClient
from meshtastic_sender import MeshtasticSender

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def _format_accident_message(accident: dict) -> str:
    """
    Format an accident dictionary into a concise message for Meshtastic
    
    Args:
        accident: Accident data dictionary
        
    Returns:
        Formatted message string (will be truncated to 200 chars by sender)
    """
    roadway = accident.get('RoadwayName', 'Unknown road')
    direction = accident.get('DirectionOfTravel', '')
    lanes = accident.get('LanesAffected', '')
    location = accident.get('Location', '')
    last_updated_str = accident.get('LastUpdated', '')
    
    # Calculate elapsed time since last update
    elapsed_str = ""
    if last_updated_str:
        try:
            # Parse the timestamp string (format: '2025-12-11 14:30:00 MST')
            # Remove timezone abbreviation for parsing
            timestamp_without_tz = ' '.join(last_updated_str.split()[:-1])
            last_updated_dt = datetime.strptime(timestamp_without_tz, '%Y-%m-%d %H:%M:%S')
            
            # Make it timezone-aware (Arizona time)
            arizona_tz = ZoneInfo('America/Phoenix')
            last_updated_dt = last_updated_dt.replace(tzinfo=arizona_tz)
            
            # Get current time in Arizona timezone
            now = datetime.now(arizona_tz)
            
            # Calculate elapsed time
            elapsed = now - last_updated_dt
            
            # Format elapsed time
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            
            if hours > 0:
                elapsed_str = f"{hours}h{minutes}m ago"
            else:
                elapsed_str = f"{minutes}m ago"
        except Exception as e:
            logger.warning(f"Error calculating elapsed time: {e}")
            elapsed_str = ""
    
    # Build compact message
    parts = [f"ACCIDENT: {roadway}"]
    
    if direction:
        parts.append(f"({direction})")
    
    if lanes and lanes != "No Data":
        parts.append(f"Lanes: {lanes}")
    
    if location:
        parts.append(f"@ {location}")
    
    if elapsed_str:
        parts.append(f"[{elapsed_str}]")
    
    return " ".join(parts)


def main():
    """Main execution function"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='ADOT 511 to Meshtastic Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'search_type',
        nargs='?',
        default='accidents',
        help='Type of data to search for: accidents, events, alerts, weather, or listen (default: accidents)'
    )
    parser.add_argument(
        'location',
        nargs='?',
        default='phoenix',
        help='Location to search (default: phoenix). Use "all" to retrieve all results without filtering.'
    )
    
    args = parser.parse_args()
    
    # Make parameters case-insensitive
    search_type = args.search_type.lower()
    location = args.location.lower()
    
    # Handle 'all' keyword for location (retrieve all results)
    if location == 'all':
        location = None
    
    # Validate search type
    valid_search_types = ['accidents', 'events', 'alerts', 'weather', 'listen']
    if search_type not in valid_search_types:
        logger.error(f"Invalid search type '{search_type}'. Must be one of: {', '.join(valid_search_types)}")
        return
    
    # Handle listen mode
    if search_type == 'listen':
        # Enable debug logging for listener mode
        logging.getLogger().setLevel(logging.DEBUG)
        
        # Suppress noisy library debug messages
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('meshtastic').setLevel(logging.WARNING)
        logging.getLogger('geopy').setLevel(logging.WARNING)
        
        logger.info("Starting Meshtastic listener mode...")
        from meshtastic_listener import MeshtasticListener
        
        # Get API key from environment variable
        adot_api_key = os.getenv("ADOT_API_KEY")
        if not adot_api_key:
            logger.error("ADOT_API_KEY environment variable not set")
            raise ValueError("ADOT_API_KEY is required")
        
        # Get Meshtastic connection settings from environment variables
        connection_type = os.getenv("MESHTASTIC_CONNECTION_TYPE", "serial")
        device_path = os.getenv("MESHTASTIC_DEVICE_PATH")
        tcp_host = os.getenv("MESHTASTIC_TCP_HOST")
        tcp_port = int(os.getenv("MESHTASTIC_TCP_PORT", "4403"))
        channel_index = int(os.getenv("MESHTASTIC_CHANNEL_INDEX", "0"))
        max_results = int(os.getenv("MAX_RESULTS_PER_QUERY", "3"))
        
        # Initialize and start listener
        listener = MeshtasticListener(
            adot_api_key=adot_api_key,
            device_path=device_path,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
            connection_type=connection_type,
            channel_index=channel_index,
            max_results=max_results
        )
        
        # Start listening (this will block until interrupted)
        listener.start()
        return
    
    logger.info(f"Starting ADOT 511 to Meshtastic integration - Search Type: {search_type}, Location: {location if location else 'all'}")
    
    try:
        # Get API key from environment variable
        adot_api_key = os.getenv("ADOT_API_KEY")
        if not adot_api_key:
            logger.error("ADOT_API_KEY environment variable not set")
            raise ValueError("ADOT_API_KEY is required")
        
        # Initialize ADOT API client
        adot_client = ADOTClient(api_key=adot_api_key)
        
        # Check if Meshtastic sending is enabled
        enable_send = os.getenv("ENABLE_MESHTASTIC_SEND", "false").lower() == "true"
        
        if not enable_send:
            print("\n[DEBUG] Initialized ADOT API client")
        mesh_sender = None
        
        if enable_send:
            # Get Meshtastic connection settings from environment variables
            connection_type = os.getenv("MESHTASTIC_CONNECTION_TYPE", "serial")
            device_path = os.getenv("MESHTASTIC_DEVICE_PATH")
            tcp_host = os.getenv("MESHTASTIC_TCP_HOST")
            tcp_port = int(os.getenv("MESHTASTIC_TCP_PORT", "4403"))
            channel_index = int(os.getenv("MESHTASTIC_CHANNEL_INDEX", "0"))
            
            # Initialize Meshtastic sender
            logger.info(f"Initializing Meshtastic with {connection_type} connection on channel {channel_index}")
            mesh_sender = MeshtasticSender(
                device_path=device_path,
                tcp_host=tcp_host,
                tcp_port=tcp_port,
                connection_type=connection_type,
                channel_index=channel_index
            )
        else:
            logger.info("DEBUG MODE: Meshtastic sending is disabled")
        
        # Fetch data from ADOT API
        location_str = location if location else 'all locations'
        logger.info(f"Fetching {search_type} data from ADOT 511 API for {location_str}...")
        if not enable_send:
            print(f"[DEBUG] Fetching {search_type} from ADOT 511 API for {location_str}...")
        
        # Fetch data based on search type
        if search_type == 'accidents':
            # Fetch accidents
            accidents = adot_client.get_accidents(location=location)
            
            if not enable_send:
                print(f"[DEBUG] Retrieved {len(accidents)} accidents")
            
            # Process and send accidents to Meshtastic
            if accidents:
                logger.info(f"Found {len(accidents)} accidents")
                if not enable_send:
                    print(f"[DEBUG] Processing {len(accidents)} accidents...\n")
                
                # Track seen accidents to avoid duplicates
                seen_accidents = set()
                processed_count = 0
                
                for accident in accidents:
                    # Create unique key from accident details
                    accident_key = (
                        accident.get('RoadwayName', ''),
                        accident.get('DirectionOfTravel', ''),
                        accident.get('Location', ''),
                        accident.get('LastUpdated', '')
                    )
                    
                    # Skip if we've already seen this accident
                    if accident_key in seen_accidents:
                        continue
                    
                    seen_accidents.add(accident_key)
                    processed_count += 1
                    
                    # Format accident message
                    message = _format_accident_message(accident)
                    
                    if enable_send:
                        # Send to Meshtastic
                        logger.info(f"Sending message: {message}")
                        mesh_sender.send_message(message)
                    else:
                        # Print to console instead
                        print(f"\n{'='*60}")
                        print(f"{message}")
                        print(f"{'='*60}\n")
                
                if not enable_send and len(accidents) != processed_count:
                    print(f"[DEBUG] Skipped {len(accidents) - processed_count} duplicate accidents")
            else:
                message = "No accidents found"
                logger.info(message)
                if enable_send:
                    mesh_sender.send_message(message)
                else:
                    print(f"\n{'='*60}")
                    print(f"{message}")
                    print(f"{'='*60}\n")
        elif search_type == 'events':
            # Fetch all events
            events = adot_client.get_events(location=location)
            
            # Filter out accidents and incidents (use 'accidents' search type for those)
            non_accident_events = [
                event for event in events 
                if 'accident' not in event.get('EventType', '').lower()
            ]
            
            if not enable_send:
                print(f"[DEBUG] Retrieved {len(non_accident_events)} events (filtered out {len(events) - len(non_accident_events)} accidents)")
            
            # Process and send events to Meshtastic
            if non_accident_events:
                logger.info(f"Found {len(non_accident_events)} events")
                if not enable_send:
                    print(f"[DEBUG] Processing {len(non_accident_events)} events...\n")
                
                # Track seen events to avoid duplicates
                seen_events = set()
                processed_count = 0
                
                for event in non_accident_events:
                    # Create unique key from event details
                    event_key = (
                        event.get('RoadwayName', ''),
                        event.get('EventType', ''),
                        event.get('DirectionOfTravel', ''),
                        event.get('Location', '')
                    )
                    
                    # Skip if we've already seen this event
                    if event_key in seen_events:
                        continue
                    
                    seen_events.add(event_key)
                    processed_count += 1
                    
                    # Format event message
                    roadway = event.get('RoadwayName', 'Unknown road')
                    event_type = event.get('EventType', 'Event')
                    direction = event.get('DirectionOfTravel', '')
                    
                    # Build compact message
                    parts = [f"{event_type.upper()}: {roadway}"]
                    if direction:
                        parts.append(f"({direction})")
                    
                    message = " ".join(parts)
                    
                    if enable_send:
                        # Send to Meshtastic
                        logger.info(f"Sending message: {message}")
                        mesh_sender.send_message(message)
                    else:
                        # Print to console instead
                        print(f"\n{'='*60}")
                        print(f"{message}")
                        print(f"{'='*60}\n")
                
                if not enable_send and len(non_accident_events) != processed_count:
                    print(f"[DEBUG] Skipped {len(non_accident_events) - processed_count} duplicate events")
            else:
                message = "No events found"
                logger.info(message)
                if enable_send:
                    mesh_sender.send_message(message)
                else:
                    print(f"\n{'='*60}")
                    print(f"{message}")
                    print(f"{'='*60}\n")
        elif search_type == 'alerts':
            logger.info("Alerts search not yet implemented")
            print("[INFO] Alerts search not yet implemented")
        elif search_type == 'weather':
            logger.info("Weather search not yet implemented")
            print("[INFO] Weather search not yet implemented")
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
