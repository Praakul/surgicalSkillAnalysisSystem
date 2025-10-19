# network/video_sender.py

import os
import time
import requests
from utils.error_handler import ErrorHandler
from PyQt5.QtCore import QThread, pyqtSignal

class VideoSender(QThread):
    """Thread for uploading video and user data to the server."""
    
    # Signals
    progress_update = pyqtSignal(int)
    upload_complete = pyqtSignal(str)
    upload_error = pyqtSignal(str)
    connection_status = pyqtSignal(bool, str)  # Connected (True/False), Message
    
    # Constants for retry handling
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __init__(self, server_url, video_path, user_data):
        super().__init__()
        
        self.server_url = server_url
        self.video_path = video_path
        self.user_data = user_data
        self.cancelled = False
        self.paused = False
        self.retry_count = 0
        self.last_progress = 0
        self.session = requests.Session()  # Use a session for connection pooling
        
    def cancel_upload(self):
        """Cancel the ongoing upload."""
        self.cancelled = True
        self.upload_error.emit("Upload cancelled by user")
        
    def run(self):
        """Run the upload thread."""
        try:
            # Check if file exists
            if not os.path.exists(self.video_path):
                self.upload_error.emit("Video file not found.")
                return
            
            # Format fields according to server expectations
            with open(self.video_path, 'rb') as video_file:
                self._attempt_upload(video_file)
                
        except Exception as e:
            if self.cancelled and "cancelled by user" in str(e):
                self.upload_error.emit("Upload cancelled by user")
            else:
                error_msg = f"Upload error: {str(e)}"
                self.upload_error.emit(error_msg)
                ErrorHandler.log_error("VideoSender", error_msg)
    
    def _attempt_upload(self, video_file):
        """Attempt to upload the video with retry logic."""
        self.retry_count = 0
        success = False
        
        while not success and self.retry_count < self.MAX_RETRIES and not self.cancelled:
            if self.retry_count > 0:
                # Sleep before retry
                self.connection_status.emit(False, f"Connection lost. Retrying in {self.RETRY_DELAY} seconds...")
                
                # Wait with cancellation check
                for i in range(self.RETRY_DELAY):
                    if self.cancelled:
                        break
                    time.sleep(1)
                
                if self.cancelled:
                    break
                    
                self.connection_status.emit(True, "Reconnecting...")
            
            # Reset file position if retrying
            video_file.seek(0)
            
            try:
                success = self._execute_upload(video_file)
            except requests.exceptions.RequestException as e:
                self.retry_count += 1
                if self.retry_count >= self.MAX_RETRIES:
                    self.upload_error.emit(f"Failed to connect after {self.MAX_RETRIES} attempts: {str(e)}")
                    return
            
            # Wait while paused
            while self.paused and not self.cancelled:
                time.sleep(0.5)
    
    def _execute_upload(self, video_file):
        """Execute the actual upload with the current file position."""
        # Get file size for progress calculation
        file_size = os.path.getsize(self.video_path)
        
        # Format fields according to server expectations
        fields = {
            'video': (os.path.basename(self.video_path), 
                      video_file, 
                      'video/mp4'),
            'name': self.user_data['name'],
            'email': self.user_data['email'],
            'program': self.user_data['program'],
            'iteration_number': str(self.user_data['iteration']),  # Convert to string for form data
            'additional_info': self.user_data.get('notes', ''),
        }
        
        
        def progress_callback(monitor):
            if self.cancelled:
                # Cancel the request by raising an exception
                raise Exception("Upload cancelled by user")
            
            if self.paused:
                # Pause the request by raising a specific exception
                raise ConnectionResetError("Upload paused by user")
                
            bytes_sent = monitor.bytes_read
            progress = int((bytes_sent / file_size) * 100)
            self.last_progress = progress  # Store progress for potential resume
            self.progress_update.emit(progress)
        
        # Use requests-toolbelt for progress monitoring
        try:
            from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
            
            # Create multipart encoder with properly formatted fields
            encoder = MultipartEncoder(fields=fields)
            
            # Create monitor with callback
            monitor = MultipartEncoderMonitor(encoder, progress_callback)
            
            # Make the request with progress monitoring
            headers = {'Content-Type': monitor.content_type}
            
            # Check for cancellation
            if self.cancelled:
                self.upload_error.emit("Upload cancelled by user")
                return False
                
            # Make the request with proper timeout and network error handling
            try:
                self.connection_status.emit(True, "Connected to server")
                response = self.session.post(
                    self.server_url, 
                    data=monitor, 
                    headers=headers,
                    timeout=60  # 60 seconds timeout
                )
                
                # Set progress to 100% after upload completes
                self.progress_update.emit(100)
                
                # Handle response
                if response.status_code in [200, 201, 202]:
                    try:
                        result = response.json()
                        message = result.get('message', 'Upload successful. Results will be emailed to you.')
                        queue_position = result.get('queue_position', 0)
                        
                        # Add queue position info if available
                        if queue_position > 0:
                            message += f"\n\nYour submission is #{queue_position} in the processing queue."
                            estimated_time = result.get('estimated_processing_time', queue_position * 30)  # Use server estimate if available
                            if estimated_time > 60:
                                message += f"\nEstimated processing time: {estimated_time // 60} minutes."
                            else:
                                message += f"\nEstimated processing time: {estimated_time} seconds."
                        
                        self.upload_complete.emit(message)
                        return True
                    except ValueError:
                        # Response is not JSON
                        self.upload_complete.emit("Upload successful. Results will be emailed to you.")
                        return True
                else:
                    # Handle error response
                    try:
                        error_data = response.json()
                        error_message = error_data.get('detail', f"Server returned error code: {response.status_code}")
                        self.upload_error.emit(error_message)
                    except ValueError:
                        # Response is not JSON
                        self.upload_error.emit(f"Server returned error code: {response.status_code}")
                    return False
            
            except requests.exceptions.Timeout:
                self.connection_status.emit(False, "Connection to server timed out.")
                raise requests.exceptions.RequestException("Connection timeout")
                
            except requests.exceptions.ConnectionError:
                self.connection_status.emit(False, "Lost connection to server.")
                raise requests.exceptions.RequestException("Connection error")
                
            except ConnectionResetError as e:
                # This is our custom exception for pausing
                if "paused by user" in str(e):
                    return False
                raise
            
        except ImportError:
            # Fallback if requests-toolbelt is not available
            self.upload_error.emit("Required library 'requests-toolbelt' is not available for progress monitoring.")
            return False