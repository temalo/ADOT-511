"""
ADOT API Client
Handles communication with the Arizona DOT 511 API
"""

import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

logger = logging.getLogger(__name__)


class ADOTClient:
    """Client for interacting with ADOT 511 API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ADOT API client
        
        Args:
            api_key: API key for ADOT 511 service (required for API calls)
        """
        self.api_key = api_key
        self.base_url = "https://az511.com/api/v2"
        self.session = requests.Session()
        self.geocoder = Nominatim(user_agent="adot-511-client")
    
    def get_events(self) -> List[Dict]:
        """
        Fetch current traffic events (incidents, roadwork, closures, accidents)
        
        Returns:
            List of event dictionaries containing traffic events
        """
        try:
            if not self.api_key:
                logger.error("API key is required to fetch events")
                return []
            
            endpoint = f"{self.base_url}/get/event"
            params = {"key": self.api_key, "format": "json"}
            
            logger.info(f"Fetching events from {endpoint}")
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved {len(data)} events")
            return data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching events: {e.response.status_code} - {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching events: {e}")
            return []
        except ValueError as e:
            logger.error(f"Error parsing event response JSON: {e}")
            return []
    
    def get_cameras(self) -> List[Dict]:
        """
        Fetch all traffic cameras
        
        Returns:
            List of camera dictionaries with locations and image URLs
        """
        try:
            if not self.api_key:
                logger.error("API key is required to fetch cameras")
                return []
            
            endpoint = f"{self.base_url}/get/cameras"
            params = {"key": self.api_key, "format": "json"}
            
            logger.info(f"Fetching cameras from {endpoint}")
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved {len(data)} cameras")
            return data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching cameras: {e.response.status_code} - {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching cameras: {e}")
            return []
        except ValueError as e:
            logger.error(f"Error parsing camera response JSON: {e}")
            return []
    
    def get_alerts(self) -> List[Dict]:
        """
        Fetch current alerts from ADOT 511 API
        
        Returns:
            List of alert dictionaries containing alert information
        """
        try:
            if not self.api_key:
                logger.error("API key is required to fetch alerts")
                return []
            
            endpoint = f"{self.base_url}/get/alerts"
            params = {"key": self.api_key, "format": "json"}
            
            logger.info(f"Fetching alerts from {endpoint}")
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # API returns a list of alerts directly
            if isinstance(data, list):
                alerts = data
            else:
                logger.warning(f"Unexpected response format: {type(data)}")
                alerts = []
            
            logger.info(f"Retrieved {len(alerts)} alerts")
            return alerts
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching alerts: {e.response.status_code} - {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching alerts: {e}")
            return []
        except ValueError as e:
            logger.error(f"Error parsing alert response JSON: {e}")
            return []
    
    def get_accidents(self) -> List[Dict]:
        """
        Fetch accident events from ADOT 511 API
        
        Returns:
            List of accident dictionaries with selected fields:
            - Organization
            - RoadwayName
            - DirectionOfTravel
            - Description
            - LanesAffected
            - Location (human-readable address from lat/lon)
            - Reported (converted to Arizona local time)
            - LastUpdated (converted to Arizona local time)
        """
        try:
            # Get all events
            events = self.get_events()
            
            # Filter for accidents and extract specific fields
            accidents = []
            for event in events:
                event_type = event.get('EventType', '').lower()
                
                # Check if this is an accident (eventType contains 'accident')
                if 'accident' in event_type:
                    latitude = event.get('Latitude')
                    longitude = event.get('Longitude')
                    
                    accident = {
                        'Organization': event.get('Organization'),
                        'RoadwayName': event.get('RoadwayName'),
                        'DirectionOfTravel': event.get('DirectionOfTravel'),
                        'Description': event.get('Description'),
                        'LanesAffected': event.get('LanesAffected'),
                        'Location': self._get_readable_location(latitude, longitude),
                        'Reported': self._convert_unix_to_arizona_time(event.get('Reported')),
                        'LastUpdated': self._convert_unix_to_arizona_time(event.get('LastUpdated'))
                    }
                    accidents.append(accident)
            
            logger.info(f"Retrieved {len(accidents)} accident events")
            return accidents
            
        except Exception as e:
            logger.error(f"Error fetching accidents: {e}")
            return []
    
    def _convert_unix_to_arizona_time(self, unix_timestamp: Optional[int]) -> Optional[str]:
        """
        Convert Unix timestamp to Arizona local time string
        
        Args:
            unix_timestamp: Unix timestamp (seconds since epoch)
            
        Returns:
            Formatted datetime string in Arizona timezone, or None if timestamp is invalid
        """
        if unix_timestamp is None:
            return None
        
        try:
            # Convert Unix timestamp to datetime in Arizona timezone
            arizona_tz = ZoneInfo('America/Phoenix')
            dt = datetime.fromtimestamp(unix_timestamp, tz=arizona_tz)
            
            # Format as readable string
            return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
            
        except (ValueError, OSError) as e:
            logger.warning(f"Error converting timestamp {unix_timestamp}: {e}")
            return None
    
    def _get_readable_location(self, latitude: Optional[float], longitude: Optional[float]) -> Optional[str]:
        """
        Convert latitude/longitude to intersection format using reverse geocoding
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Intersection format string (e.g., "I-10 and Broadway"), or formatted lat/lon if geocoding fails
        """
        if latitude is None or longitude is None:
            return None
        
        try:
            # Add small delay to respect Nominatim's usage policy (1 request per second)
            time.sleep(1)
            
            location = self.geocoder.reverse(f"{latitude}, {longitude}", timeout=10)
            
            if location and location.raw:
                address = location.raw.get('address', {})
                
                # Extract road names from address components
                roads = []
                
                # Check for highway/interstate
                if 'road' in address:
                    roads.append(address['road'])
                elif 'highway' in address:
                    roads.append(address['highway'])
                
                # Add cross street if available
                if 'street' in address and address['street'] not in roads:
                    roads.append(address['street'])
                
                # Try other common road fields
                for field in ['residential', 'suburb', 'neighbourhood']:
                    if field in address and address[field] not in roads and len(roads) < 2:
                        roads.append(address[field])
                
                # Format as intersection if we have roads
                if len(roads) >= 2:
                    return f"{roads[0]} and {roads[1]}"
                elif len(roads) == 1:
                    # If only one road, add city
                    city = address.get('city') or address.get('town') or address.get('village', '')
                    if city:
                        return f"{roads[0]}, {city}"
                    return roads[0]
                else:
                    # Fallback to full address if no roads found
                    return location.address
            else:
                # Fallback to coordinates if no address found
                return f"{latitude}, {longitude}"
                
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding error for {latitude}, {longitude}: {e}")
            # Return coordinates as fallback
            return f"{latitude}, {longitude}"
        except Exception as e:
            logger.error(f"Unexpected error during geocoding: {e}")
            return f"{latitude}, {longitude}"
