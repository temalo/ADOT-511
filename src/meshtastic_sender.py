"""
Meshtastic Sender
Handles sending messages to Meshtastic mesh network devices
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MeshtasticSender:
    """Client for sending messages to Meshtastic devices"""
    
    def __init__(
        self, 
        device_path: str = None, 
        tcp_host: str = None, 
        tcp_port: int = 4403,
        connection_type: str = "serial",
        channel_index: int = 0
    ):
        """
        Initialize Meshtastic sender
        
        Args:
            device_path: Optional path to Meshtastic device (e.g., COM port or /dev/ttyUSB0)
            tcp_host: Optional hostname or IP address for TCP connection
            tcp_port: TCP port number (default: 4403)
            connection_type: Connection type - "serial" or "tcp" (default: "serial")
            channel_index: Channel index to send messages on (default: 0)
        """
        self.device_path = device_path
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.connection_type = connection_type
        self.channel_index = channel_index
        self.interface = None
        
        # TODO: Initialize meshtastic interface based on connection type
        # if connection_type == "tcp" and tcp_host:
        #     self.interface = meshtastic.TCPInterface(hostname=tcp_host, portNumber=tcp_port)
        # elif connection_type == "serial" and device_path:
        #     self.interface = meshtastic.SerialInterface(device_path)
        # else:
        #     # Default to auto-discovery
        #     self.interface = meshtastic.SerialInterface()
    
    def send_message(self, message: str, channel_index: Optional[int] = None) -> bool:
        """
        Send a message to the Meshtastic network
        
        Args:
            message: Text message to send
            channel_index: Optional channel index to override default channel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            channel = channel_index if channel_index is not None else self.channel_index
            logger.info(f"Sending message on channel {channel}: {message[:50]}...")
            
            # TODO: Implement actual Meshtastic sending
            # self.interface.sendText(message, channelIndex=channel)
            
            logger.info("Message sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_alerts(self, incidents: List[Dict]) -> None:
        """
        Format and send incident alerts
        
        Args:
            incidents: List of incident data from ADOT API
        """
        for incident in incidents:
            # Format incident into a concise message
            message = self._format_incident(incident)
            self.send_message(message)
    
    def _format_incident(self, incident: Dict) -> str:
        """
        Format an incident into a message string
        
        Args:
            incident: Incident data dictionary
            
        Returns:
            Formatted message string
        """
        # TODO: Customize formatting based on actual ADOT API response structure
        location = incident.get('location', 'Unknown location')
        description = incident.get('description', 'Traffic incident')
        
        return f"ADOT Alert: {description} at {location}"
    
    def close(self):
        """Close the Meshtastic interface"""
        if self.interface:
            self.interface.close()
