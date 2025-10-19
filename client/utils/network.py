# utils/network.py

import socket
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

class NetworkMonitor(QObject):
    """Monitor network connectivity to a server."""
    
    # Signals
    connection_changed = pyqtSignal(bool, str)  # Connected (True/False), Message
    
    def __init__(self, server_url, check_interval=5):
        super().__init__()
        
        self.server_url = server_url
        self.check_interval = check_interval  # Seconds between checks
        self.is_connected = False
        self.is_running = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start monitoring the network connectivity."""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring the network connectivity."""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            self.monitor_thread = None
    
    def _monitor_loop(self):
        """Background thread for periodic connection checks."""
        while self.is_running:
            connected = self._check_connection()
            
            # Only emit signal if the status changed
            if connected != self.is_connected:
                self.is_connected = connected
                
                if connected:
                    self.connection_changed.emit(True, "Connected to server")
                else:
                    self.connection_changed.emit(False, "Disconnected from server")
            
            # Sleep until next check
            time.sleep(self.check_interval)
    
    def _check_connection(self):
        """Check if we can connect to the server."""
        try:
            # Parse the server URL to get hostname
            if self.server_url.startswith('http://'):
                host = self.server_url[7:].split('/')[0]
            elif self.server_url.startswith('https://'):
                host = self.server_url[8:].split('/')[0]
            else:
                host = self.server_url.split('/')[0]
                
            # If there's a port specified, extract it
            if ':' in host:
                host, port_str = host.split(':')
                port = int(port_str)
            else:
                # Default ports
                if self.server_url.startswith('https://'):
                    port = 443
                else:
                    port = 80
            
            # Try to establish a socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)  # 2 second timeout
            sock.connect((host, port))
            sock.close()
            return True
            
        except (socket.timeout, socket.error, ValueError):
            return False
        
    def check_now(self):
        """Immediately check and return the connection status."""
        connected = self._check_connection()
        self.is_connected = connected
        return connected