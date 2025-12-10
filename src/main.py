"""
ADOT 511 to Meshtastic Integration
Main entry point for the application
"""

import logging
import os
from adot_client import ADOTClient
from meshtastic_sender import MeshtasticSender

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
    
    # Build compact message
    parts = [f"ACCIDENT: {roadway}"]
    
    if direction:
        parts.append(f"({direction})")
    
    if lanes and lanes != "No Data":
        parts.append(f"Lanes: {lanes}")
    
    if location:
        parts.append(f"@ {location}")
    
    return " ".join(parts)


def main():
    """Main execution function"""
    logger.info("Starting ADOT 511 to Meshtastic integration")
    
    try:
        # Get API key from environment variable
        adot_api_key = os.getenv("ADOT_API_KEY")
        if not adot_api_key:
            logger.error("ADOT_API_KEY environment variable not set")
            raise ValueError("ADOT_API_KEY is required")
        
        # Initialize ADOT API client
        adot_client = ADOTClient(api_key=adot_api_key)
        
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
        
        # Fetch data from ADOT API
        logger.info("Fetching data from ADOT 511 API...")
        
        # Fetch accidents
        accidents = adot_client.get_accidents()
        
        # Process and send accidents to Meshtastic
        if accidents:
            logger.info(f"Found {len(accidents)} accidents")
            for accident in accidents:
                # Format accident message
                message = _format_accident_message(accident)
                mesh_sender.send_message(message)
        else:
            logger.info("No accidents found")
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
