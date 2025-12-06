"""
ADOT 511 to Meshtastic Integration
Main entry point for the application
"""

import logging
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
        
        # Initialize Meshtastic sender
        mesh_sender = MeshtasticSender()
        
        # Fetch data from ADOT API
        logger.info("Fetching data from ADOT 511 API...")
        incidents = adot_client.get_incidents()
        
        # Process and send to Meshtastic
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
