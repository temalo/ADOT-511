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
