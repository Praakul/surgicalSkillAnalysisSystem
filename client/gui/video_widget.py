# gui/video_widget.py
import os
import cv2
import time
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QMessageBox, QSizePolicy
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap

class VideoWidget(QWidget):
    """Widget for displaying and recording video from camera."""
    
    # Signal when recording fails
    recording_error = pyqtSignal(str)
    
    def __init__(self, parent=None, camera_id=0):
        super().__init__(parent)
        
        # Initialize variables
        self.camera_id = camera_id
        self.cap = None
        self.video_writer = None
        self.timer = None
        self.frame = None
        self.is_recording = False
        self.is_paused = False
        self.recording_start_time = 0
        self.recording_elapsed_time = 0
        self.paused_time = 0
        
        # Setup UI components
        self._setup_ui()
        
        # Try to initialize the camera
        self._init_camera()
        
    def _setup_ui(self):
        """Setup the UI components."""
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Video display label - with improved size policy
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(640, 480)  # Set minimum size for better display
        layout.addWidget(self.video_label)
        
        # Timer label for recording duration
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 128); font-size: 14pt;")
        layout.addWidget(self.timer_label)
        
        self.setLayout(layout)
        
    def _init_camera(self):
        """Initialize the camera capture."""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                self.recording_error.emit("Failed to open camera.")
                return False
            
            # Set higher resolution for better quality
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Start the timer for updating the video display
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._update_frame)
            self.timer.start(30)  # Update every 30ms (approx. 33 fps)
            
            return True
        except Exception as e:
            self.recording_error.emit(f"Camera initialization error: {str(e)}")
            return False
            
    def is_camera_available(self):
        """Check if camera is available and initialized."""
        return self.cap is not None and self.cap.isOpened()
    
    @pyqtSlot()
    def _update_frame(self):
        """Update the video frame and UI."""
        if not self.is_camera_available():
            return
            
        # Try to read a frame
        ret, self.frame = self.cap.read()
        
        if not ret:
            # Handle camera read error
            self.timer.stop()
            QMessageBox.critical(self, "Error", "Failed to read frame from camera.")
            return
            
        # Write frame to video if recording and not paused
        if self.is_recording and not self.is_paused and self.video_writer is not None:
            try:
                self.video_writer.write(self.frame)
            except Exception as e:
                self.is_recording = False
                QMessageBox.critical(self, "Recording Error", f"Failed to write frame: {str(e)}")
        
        # Update the timer display if recording
        if self.is_recording:
            if not self.is_paused:
                current_time = time.time()
                elapsed = (current_time - self.recording_start_time) + self.recording_elapsed_time
                
                # Format as HH:MM:SS
                hours, remainder = divmod(int(elapsed), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.timer_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")
        
        # Convert frame to QImage and display
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            # Create QImage from the frame
            image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Scale image to fill the label while maintaining aspect ratio
            pixmap = QPixmap.fromImage(image)
            
            # Get the current size of the label
            label_width = self.video_label.width()
            label_height = self.video_label.height()
            
            # Scale the pixmap to fit the label's dimensions while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                label_width, 
                label_height,
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            self.video_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Frame conversion error: {str(e)}")
    
    def start_recording(self):
        """Start recording video."""
        if not self.is_camera_available():
            return False
            
        try:
            # Get video properties
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            # Create temporary file for recording
            os.makedirs("data", exist_ok=True)  # Ensure directory exists
            temp_path = os.path.join("data", f"temp_recording_{int(time.time())}.mp4")
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # codec
            self.video_writer = cv2.VideoWriter(
                temp_path, fourcc, fps, (width, height)
            )
            
            # Set recording state
            self.is_recording = True
            self.is_paused = False
            self.recording_start_time = time.time()
            self.recording_elapsed_time = 0
            self.paused_time = 0
            self.temp_recording_path = temp_path
            
            # Show timer
            self.timer_label.setVisible(True)
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Failed to start recording: {str(e)}")
            return False
    
    def toggle_pause(self):
        """Toggle pause/resume recording."""
        if not self.is_recording:
            return False
            
        if self.is_paused:
            # Resume recording
            self.is_paused = False
            self.recording_start_time = time.time()
            return False
        else:
            # Pause recording
            self.is_paused = True
            
            # Calculate elapsed time so far
            current_time = time.time()
            self.recording_elapsed_time += (current_time - self.recording_start_time)
            
            return True
    
    def stop_recording(self, output_path):
        """Stop recording and save to the specified output path."""
        if not self.is_recording:
            return False
            
        try:
            # Release video writer
            if  self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
                
            self.is_recording = False
            self.is_paused = False
            
            # Copy the temp recording to the output path
            # Here we're just renaming since the format is already mp4
            if os.path.exists(self.temp_recording_path):
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # If destination already exists, remove it
                if os.path.exists(output_path):
                    os.remove(output_path)
                
                # Rename file
                os.rename(self.temp_recording_path, output_path)
            
            # Reset recording state
            self.timer_label.setText("00:00:00")
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Failed to save recording: {str(e)}")
            return False
    
    def release_resources(self):
        """Release all resources used by the widget."""
        # Stop timer
        if self.timer is not None and self.timer.isActive():
            self.timer.stop()
        
        # Release video writer
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
        
        # Release camera
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        # Remove temporary files
        if hasattr(self, 'temp_recording_path') and os.path.exists(self.temp_recording_path):
            try:
                os.remove(self.temp_recording_path)
            except:
                pass
    
    def resizeEvent(self, event):
        """Handle resize events to adjust the video display."""
        super().resizeEvent(event)
        
        # Update the video display if we have a frame
        if self.frame is not None:
            try:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                # Create QImage from the frame
                image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Scale image to fit the label while maintaining aspect ratio
                pixmap = QPixmap.fromImage(image)
                self.video_label.setPixmap(pixmap.scaled(
                    self.video_label.width(), 
                    self.video_label.height(),
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                ))
            except:
                pass