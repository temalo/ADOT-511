"""
Meshtastic Listener
Listens for commands on Meshtastic network and responds with ADOT data
"""

import logging
import re
import os
from typing import Optional, Callable
from datetime import datetime
from zoneinfo import ZoneInfo
from .adot_client import ADOTClient
from .meshtastic_sender import MeshtasticSender

logger = logging.getLogger(__name__)


class MeshtasticListener:
    """Listener for Meshtastic messages that processes ADOT data requests"""
    
    # Command patterns
    COMMAND_PATTERN = re.compile(
        r'^\s*(accidents|events|alerts|weather)\s+(.+?)\s*$',
        re.IGNORECASE
    )
    
    def __init__(
        self,
        adot_api_key: str,
        device_path: str = None,
        tcp_host: str = None,
        tcp_port: int = 4403,
        connection_type: str = "serial",
        channel_index: int = 0,
        max_results: int = 3
    ):
        """
        Initialize Meshtastic listener
        
        Args:
            adot_api_key: API key for ADOT 511 API
            device_path: Optional path to Meshtastic device (e.g., COM port)
            tcp_host: Optional hostname or IP address for TCP connection
            tcp_port: TCP port number (default: 4403)
            connection_type: Connection type - "serial" or "tcp" (default: "serial")
            channel_index: Channel index to listen on (default: 0)
            max_results: Maximum number of results to return per query (default: 3)
        """
        self.adot_client = ADOTClient(api_key=adot_api_key)
        self.mesh_sender = MeshtasticSender(
            device_path=device_path,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
            connection_type=connection_type,
            channel_index=channel_index
        )
        self.channel_index = channel_index
        self.max_results = max_results
        self.interface = None
        self.running = False
        
        logger.info(f"MeshtasticListener initialized on channel {channel_index}")
    
    def start(self):
        """Start listening for messages"""
        try:
            logger.info("=" * 70)
            logger.info("Starting Meshtastic listener...")
            logger.info(f"Connection type: {self.mesh_sender.connection_type}")
            logger.info(f"Channel index: {self.channel_index}")
            logger.info(f"Max results per query: {self.max_results}")
            
            if self.mesh_sender.connection_type == "tcp":
                logger.info(f"TCP host: {self.mesh_sender.tcp_host}:{self.mesh_sender.tcp_port}")
            elif self.mesh_sender.connection_type == "serial":
                logger.info(f"Serial device: {self.mesh_sender.device_path}")
            
            logger.info("=" * 70)
            self.running = True
            
            # Temporarily enable meshtastic debug to see what's happening
            logging.getLogger('meshtastic.mesh_interface').setLevel(logging.INFO)
            logging.getLogger('meshtastic.tcp_interface').setLevel(logging.INFO)
            logging.getLogger('meshtastic.serial_interface').setLevel(logging.INFO)
            
            # Initialize meshtastic interface and set up message callback
            logger.info("Connecting to Meshtastic device...")
            if self.mesh_sender.connection_type == "tcp" and self.mesh_sender.tcp_host:
                import meshtastic.tcp_interface
                self.interface = meshtastic.tcp_interface.TCPInterface(
                    hostname=self.mesh_sender.tcp_host,
                    portNumber=self.mesh_sender.tcp_port,
                    connectNow=True
                )
            elif self.mesh_sender.connection_type == "serial" and self.mesh_sender.device_path:
                import meshtastic.serial_interface
                self.interface = meshtastic.serial_interface.SerialInterface(
                    devPath=self.mesh_sender.device_path
                )
            else:
                import meshtastic.serial_interface
                self.interface = meshtastic.serial_interface.SerialInterface()
            
            logger.info("Meshtastic connection established!")
            
            # Share the interface with the sender so it can actually send messages
            self.mesh_sender.interface = self.interface
            logger.info("Interface shared with message sender")
            
            # Set up message callback - pubsub is the correct way for meshtastic library
            import pubsub.pub
            
            def on_receive(packet, interface):
                logger.info("[CALLBACK TRIGGERED] Received a packet")
                self._on_message_received(packet, interface)
            
            # Subscribe to receive events using pubsub
            logger.info("Setting up message callback via pubsub...")
            pubsub.pub.subscribe(on_receive, "meshtastic.receive")
            logger.info("Subscribed to meshtastic.receive messages")
            
            logger.info("\n" + "=" * 70)
            logger.info("LISTENER READY - Monitoring for messages...")
            logger.info("=" * 70)
            logger.info(f"Listening ONLY on channel: {self.channel_index}")
            logger.info("Filtering: TEXT_MESSAGE_APP only (ignoring nodeinfo, telemetry, etc.)")
            logger.info("=" * 70)
            logger.info("Supported commands: 'accidents <location>', 'events <location>'")
            logger.info("Example: 'accidents 101' or 'events phoenix'")
            logger.info("=" * 70)
            logger.info("Text messages on the configured channel will appear below")
            logger.info("=" * 70 + "\n")
            
            # Keep the listener running
            # In production, this would be handled by the meshtastic library's event loop
            # For now, we'll use a simple loop
            import time
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Listener stopped by user")
            self.stop()
        except Exception as e:
            logger.error(f"Error starting listener: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """Stop listening for messages"""
        self.running = False
        if self.interface:
            self.interface.close()
        logger.info("Listener stopped")
    
    def _on_message_received(self, packet, interface):
        """
        Callback function for when a message is received
        
        Args:
            packet: Meshtastic packet data
            interface: Meshtastic interface object
        """
        try:
            # Check if packet has decoded data
            if 'decoded' not in packet:
                # Silently ignore packets without decoded field (ACKs, etc.)
                return
            
            # Check portnum - only process TEXT_MESSAGE_APP
            portnum = packet['decoded'].get('portnum', '')
            if portnum != 'TEXT_MESSAGE_APP':
                # Silently ignore non-text packets (telemetry, nodeinfo, etc.)
                return
            
            # Check if message is on the configured channel
            packet_channel = packet.get('channel', 0)
            if packet_channel != self.channel_index:
                logger.debug(f"[DEBUG] Ignoring message from channel {packet_channel} (listening on channel {self.channel_index})")
                return
            
            # Check for text message
            if 'text' not in packet['decoded']:
                logger.debug(f"[DEBUG] No 'text' field in decoded data - skipping")
                return
            
            message_text = packet['decoded']['text']
            sender_id = packet.get('from', 'Unknown')
            to_id = packet.get('to', 'Unknown')
            
            # Check if this is a message we sent (echo back from the radio)
            # We can identify our own messages by checking if sender is our node
            is_our_message = False
            if hasattr(self.interface, 'myInfo') and self.interface.myInfo:
                our_node_num = self.interface.myInfo.my_node_num
                is_our_message = (sender_id == our_node_num)
            
            # Always log received messages that pass the filters
            logger.info("=" * 70)
            if is_our_message:
                logger.info(f"[OUR MESSAGE ECHOED] From: {sender_id}, To: {to_id}, Channel: {packet_channel}")
            else:
                logger.info(f"[MESSAGE RECEIVED] From: {sender_id}, To: {to_id}, Channel: {packet_channel}")
            logger.info(f"[MESSAGE CONTENT] '{message_text}'")
            logger.info("=" * 70)
            
            # Only process commands from other users, not our own echoed messages
            if not is_our_message:
                self._process_command(message_text, sender_id)
            
        except Exception as e:
            logger.error(f"Error processing received message: {e}", exc_info=True)
    
    def _process_command(self, message: str, sender_id=None):
        """
        Process a command message and respond with data
        
        Args:
            message: Command text to process
            sender_id: Optional ID of the message sender
        """
        # Parse command
        match = self.COMMAND_PATTERN.match(message.strip())
        
        if not match:
            logger.info(f"[DEBUG] Message does not match command pattern: '{message}'")
            logger.info(f"[DEBUG] Expected pattern: '<command_type> <location>' (e.g., 'accidents 101')")
            return
        
        command_type = match.group(1).lower()
        location = match.group(2).strip()
        
        # Normalize interstate highway names (I10 -> I-10, i17 -> I-17, etc.)
        location = self._normalize_interstate(location)
        
        logger.info(f"Processing command: {command_type} for location: {location}")
        
        try:
            if command_type == 'accidents':
                self._handle_accidents_command(location)
            elif command_type == 'events':
                self._handle_events_command(location)
            elif command_type == 'alerts':
                self._handle_alerts_command(location)
            elif command_type == 'weather':
                self._handle_weather_command(location)
            else:
                logger.warning(f"Unknown command type: {command_type}")
                
        except Exception as e:
            logger.error(f"Error handling command: {e}", exc_info=True)
            error_msg = f"Error processing {command_type} request: {str(e)[:100]}"
            self.mesh_sender.send_message(error_msg, channel_index=self.channel_index)
    
    def _normalize_interstate(self, location: str) -> str:
        """
        Normalize interstate highway names to consistent format with dash
        
        Examples:
            I10 -> I-10
            i17 -> I-17
            I-101 -> I-101 (already normalized)
        
        Args:
            location: Location string that may contain interstate reference
            
        Returns:
            Normalized location string
        """
        import re
        # Match patterns like: I10, i10, I-10, i-10 (with or without dash)
        # Captures: (I or i)(optional dash)(numbers)
        pattern = r'\b([Ii])(-?)(\d+)\b'
        
        def normalize_match(match):
            # Always return uppercase I with dash and the numbers
            return f"I-{match.group(3)}"
        
        # Replace all interstate patterns with normalized format
        normalized = re.sub(pattern, normalize_match, location)
        
        return normalized
    
    def _handle_accidents_command(self, location: str):
        """
        Handle accidents command
        
        Args:
            location: Location to search for accidents
        """
        logger.info(f"Fetching accidents for location: {location}")
        
        # Fetch accidents from ADOT API
        accidents = self.adot_client.get_accidents(location=location)
        
        if not accidents:
            response = f"No accidents found for '{location}'"
            logger.info(response)
            self.mesh_sender.send_message(response, channel_index=self.channel_index)
            return
        
        # Limit results
        accidents_to_send = accidents[:self.max_results]
        
        # Send each accident (sender will handle splitting if needed)
        logger.info(f"Sending {len(accidents_to_send)} accident(s) for '{location}'")
        
        for accident in accidents_to_send:
            message = self._format_accident_message(accident)
            logger.info(f"Sending: {message}")
            self.mesh_sender.send_message(message, channel_index=self.channel_index)
    
    def _handle_events_command(self, location: str):
        """
        Handle events command
        
        Args:
            location: Location to search for events
        """
        logger.info(f"Fetching events for location: {location}")
        
        # Fetch events from ADOT API
        events = self.adot_client.get_events(location=location)
        
        # Filter out accidents (use 'accidents' command for those)
        non_accident_events = [
            event for event in events
            if 'accident' not in event.get('EventType', '').lower()
        ]
        
        if not non_accident_events:
            response = f"No events found for '{location}'"
            logger.info(response)
            self.mesh_sender.send_message(response, channel_index=self.channel_index)
            return
        
        # Limit results
        events_to_send = non_accident_events[:self.max_results]
        
        # Send each event (sender will handle splitting if needed)
        logger.info(f"Sending {len(events_to_send)} event(s) for '{location}'")
        
        for event in events_to_send:
            message = self._format_event_message(event)
            logger.info(f"Sending: {message}")
            self.mesh_sender.send_message(message, channel_index=self.channel_index)
    
    def _handle_alerts_command(self, location: str):
        """
        Handle alerts command
        
        Args:
            location: Location to search for alerts
        """
        logger.info(f"Fetching alerts for location: {location}")
        
        # Fetch alerts from ADOT API
        alerts = self.adot_client.get_alerts()
        
        # TODO: Filter alerts by location if the API provides location data
        
        if not alerts:
            response = f"No alerts found"
            logger.info(response)
            self.mesh_sender.send_message(response, channel_index=self.channel_index)
            return
        
        # Limit results
        alerts_to_send = alerts[:self.max_results]
        
        # Send count summary
        total_count = len(alerts)
        if total_count > self.max_results:
            summary = f"Found {total_count} alerts (showing {self.max_results})"
        else:
            summary = f"Found {total_count} alert(s)"
        
        logger.info(summary)
        self.mesh_sender.send_message(summary, channel_index=self.channel_index)
        
        # Send each alert
        for alert in alerts_to_send:
            # Format alert message based on actual API structure
            message = str(alert)[:200]  # Simple truncation for now
            logger.info(f"Sending: {message}")
            self.mesh_sender.send_message(message, channel_index=self.channel_index)
    
    def _handle_weather_command(self, location: str):
        """
        Handle weather command
        
        Args:
            location: Location to search for weather
        """
        response = "Weather command not yet implemented"
        logger.info(response)
        self.mesh_sender.send_message(response, channel_index=self.channel_index)
    
    def _format_accident_message(self, accident: dict) -> str:
        """
        Format an accident dictionary into a concise message
        
        Args:
            accident: Accident data dictionary
            
        Returns:
            Formatted message string
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
    
    def _format_event_message(self, event: dict) -> str:
        """
        Format an event dictionary into a concise message
        
        Args:
            event: Event data dictionary
            
        Returns:
            Formatted message string
        """
        roadway = event.get('RoadwayName', 'Unknown road')
        event_type = event.get('EventType', 'Event')
        direction = event.get('DirectionOfTravel', '')
        location = event.get('Location', '')
        
        # Build compact message
        parts = [f"{event_type.upper()}: {roadway}"]
        
        if direction:
            parts.append(f"({direction})")
        
        if location:
            parts.append(f"@ {location}")
        
        return " ".join(parts)
    
    def test_command(self, command: str):
        """
        Test a command without requiring Meshtastic connection
        
        Args:
            command: Command string to test
        """
        logger.info(f"Testing command: {command}")
        self._process_command(command)
    
    def simulate_message(self, message: str, sender_id: str = "!test1234", channel: int = 0):
        """
        Simulate receiving a message (for testing)
        
        Args:
            message: Message text to simulate
            sender_id: Simulated sender ID
            channel: Simulated channel
        """
        logger.info("=" * 70)
        logger.info("SIMULATING MESSAGE RECEPTION")
        logger.info("=" * 70)
        
        # Create a simulated packet
        packet = {
            'from': sender_id,
            'to': '^all',
            'channel': channel,
            'decoded': {
                'text': message,
                'portnum': 'TEXT_MESSAGE_APP'
            }
        }
        
        # Process as if it was received
        self._on_message_received(packet, None)


def main():
    """Main function for running the listener standalone"""
    import argparse
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Meshtastic Listener for ADOT 511 Integration'
    )
    parser.add_argument(
        '--test',
        type=str,
        help='Test a command without connecting to Meshtastic (e.g., "accidents 101")'
    )
    parser.add_argument(
        '--simulate',
        type=str,
        help='Simulate receiving a message packet (for debugging message reception)'
    )
    
    args = parser.parse_args()
    
    # Get configuration from environment variables
    adot_api_key = os.getenv("ADOT_API_KEY")
    if not adot_api_key:
        logger.error("ADOT_API_KEY environment variable not set")
        return
    
    connection_type = os.getenv("MESHTASTIC_CONNECTION_TYPE", "serial")
    device_path = os.getenv("MESHTASTIC_DEVICE_PATH")
    tcp_host = os.getenv("MESHTASTIC_TCP_HOST")
    tcp_port = int(os.getenv("MESHTASTIC_TCP_PORT", "4403"))
    channel_index = int(os.getenv("MESHTASTIC_CHANNEL_INDEX", "0"))
    max_results = int(os.getenv("MAX_RESULTS_PER_QUERY", "3"))
    
    # Initialize listener
    listener = MeshtasticListener(
        adot_api_key=adot_api_key,
        device_path=device_path,
        tcp_host=tcp_host,
        tcp_port=tcp_port,
        connection_type=connection_type,
        channel_index=channel_index,
        max_results=max_results
    )
    
    # Test mode or run listener
    if args.test:
        listener.test_command(args.test)
    elif args.simulate:
        listener.simulate_message(args.simulate)
    else:
        listener.start()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    main()
