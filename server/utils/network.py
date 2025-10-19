#utils/network.py

import socket
import logging
from datetime import datetime

logger = logging.getLogger("surgical_skills_server")

class NetworkMonitor:
    def __init__(self):
        self.last_check_time = datetime.now()
        self.is_connected = True
        self.check_connectivity()
    
    def check_connectivity(self):
        """Check internet connectivity by attempting to connect to a reliable server"""
        try:
            # Try connecting to Google's DNS server
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            if not self.is_connected:
                logger.info("Internet connection restored")
            self.is_connected = True
        except OSError:
            if self.is_connected:
                logger.warning("Internet connection lost")
            self.is_connected = False
        
        self.last_check_time = datetime.now()
        return self.is_connected
    
    def should_check_connectivity(self, interval_seconds):
        """Determine if it's time to check connectivity again"""
        time_since_check = (datetime.now() - self.last_check_time).total_seconds()
        return time_since_check >= interval_seconds