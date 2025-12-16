"""
Meshtastic Sender
Handles sending messages to Meshtastic mesh network devices
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MeshtasticSender:
    """Client for sending messages to Meshtastic devices"""
    
    MAX_MESSAGE_LENGTH = 200  # Maximum message length for Meshtastic
    
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
        
        # Initialize meshtastic interface based on connection type
        if connection_type == "tcp" and tcp_host:
            import meshtastic.tcp_interface
            self.interface = meshtastic.tcp_interface.TCPInterface(hostname=tcp_host, portNumber=tcp_port)
        elif connection_type == "serial" and device_path:
            import meshtastic.serial_interface
            self.interface = meshtastic.serial_interface.SerialInterface(devPath=device_path)
        # else:
        #     # Default to auto-discovery
        #     import meshtastic.serial_interface
        #     self.interface = meshtastic.serial_interface.SerialInterface()
    
    def send_message(self, message: str, channel_index: Optional[int] = None) -> bool:
        """
        Send a message to the Meshtastic network
        Automatically splits messages longer than 200 characters
        
        Args:
            message: Text message to send
            channel_index: Optional channel index to override default channel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            channel = channel_index if channel_index is not None else self.channel_index
            
            # Split message if it exceeds maximum length
            if len(message) > self.MAX_MESSAGE_LENGTH:
                logger.info(f"Message length {len(message)} exceeds {self.MAX_MESSAGE_LENGTH}, splitting into parts")
                messages = self._split_message(message, self.MAX_MESSAGE_LENGTH)
                
                # Send each part
                for i, msg_part in enumerate(messages, 1):
                    logger.info(f"Sending part {i}/{len(messages)} on channel {channel}: {msg_part[:50]}...")
                    if self.interface:
                        try:
                            result = self.interface.sendText(msg_part, channelIndex=channel)
                            logger.info(f"Part {i}/{len(messages)} sent successfully (ID: {result.id})")
                            # Give time for each part to transmit before sending the next
                            # Meshtastic needs significant time between messages to avoid collisions
                            import time
                            time.sleep(2.0)
                        except Exception as e:
                            logger.error(f"Error sending part {i}: {e}")
                    else:
                        logger.warning("No Meshtastic interface available, message not sent")
                
                return True
            else:
                # Send single message
                logger.info(f"Sending message on channel {channel}: {message[:50]}...")
                logger.debug(f"Interface object: {self.interface}")
                logger.debug(f"Interface type: {type(self.interface)}")
                
                if self.interface:
                    try:
                        result = self.interface.sendText(message, channelIndex=channel)
                        logger.info(f"Message sent successfully (ID: {result.id})")
                        # Give time for the message to actually transmit over the TCP connection
                        # Meshtastic needs significant time between messages to avoid collisions
                        import time
                        time.sleep(2.0)
                    except Exception as e:
                        logger.error(f"Error during sendText: {e}")
                        return False
                else:
                    logger.warning("No Meshtastic interface available, message not sent")
                
                return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def _split_message(self, message: str, max_length: int) -> List[str]:
        """
        Split a long message into multiple messages at logical breakpoints
        
        Args:
            message: Message to split
            max_length: Maximum length per message
            
        Returns:
            List of message parts
        """
        if len(message) <= max_length:
            return [message]
        
        messages = []
        remaining = message
        part_num = 1
        
        while remaining:
            if len(remaining) <= max_length:
                # Last part
                messages.append(remaining)
                break
            
            # Find a good break point (space, comma, parenthesis)
            break_point = max_length
            
            # Look for break characters in reverse from max_length
            for i in range(max_length - 1, max_length // 2, -1):
                if remaining[i] in [' ', ',', ')', ']', '@', '-']:
                    break_point = i + 1
                    break
            
            # Extract this part
            part = remaining[:break_point].rstrip()
            
            # Add continuation indicator if not the first part
            if part_num > 1:
                part = f"...{part}"
            
            messages.append(part)
            remaining = remaining[break_point:].lstrip()
            part_num += 1
        
        return messages
    
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
