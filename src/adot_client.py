"""
ADOT API Client
Handles communication with the Arizona DOT 511 API
"""

import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ADOTClient:
    """Client for interacting with ADOT 511 API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ADOT API client
        
        Args:
            api_key: Optional API key for ADOT 511 service
        """
        self.api_key = api_key
        self.base_url = "https://api.az511.gov/api/v2"
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
    
    def get_incidents(self) -> List[Dict]:
        """
        Fetch current traffic incidents
        
        Returns:
            List of incident dictionaries
        """
        try:
            # TODO: Update endpoint based on actual ADOT API documentation
            response = self.session.get(f"{self.base_url}/incidents")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved {len(data)} incidents")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching incidents: {e}")
            return []
    
    def get_road_conditions(self) -> List[Dict]:
        """
        Fetch current road conditions
        
        Returns:
            List of road condition dictionaries
        """
        try:
            # TODO: Update endpoint based on actual ADOT API documentation
            response = self.session.get(f"{self.base_url}/roadconditions")
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved road conditions")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching road conditions: {e}")
            return []
    
    def get_alerts(self) -> List[Dict]:
        """
        Fetch current alerts from ADOT 511 API
        
        Returns:
            List of alert dictionaries containing alert information
        """
        try:
            endpoint = f"{self.base_url}/get/alerts"
            logger.info(f"Fetching alerts from {endpoint}")
            
            response = self.session.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle different possible response structures
            if isinstance(data, dict):
                # If response is wrapped in a container object
                alerts = data.get('alerts', data.get('data', []))
            elif isinstance(data, list):
                # If response is directly a list of alerts
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
