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


def main():
    """Main execution function"""
    logger.info("Starting ADOT 511 to Meshtastic integration")
    
    try:
        # Initialize ADOT API client
        adot_client = ADOTClient()
        
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
        
        # Fetch alerts
        alerts = adot_client.get_alerts()
        
        # Fetch incidents
        incidents = adot_client.get_incidents()
        
        # Process and send alerts to Meshtastic
        if alerts:
            logger.info(f"Found {len(alerts)} alerts")
            mesh_sender.send_alerts(alerts)
        else:
            logger.info("No alerts found")
        
        # Process and send incidents to Meshtastic
        if incidents:
            logger.info(f"Found {len(incidents)} incidents")
            mesh_sender.send_alerts(incidents)
        else:
            logger.info("No incidents found")
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
