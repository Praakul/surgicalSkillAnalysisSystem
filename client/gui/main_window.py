# gui/main_window.py

import os
from datetime import datetime
from utils.network import NetworkMonitor
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QComboBox, QPushButton, 
                            QMessageBox, QProgressBar, QGridLayout, QSpinBox,
                            QFileDialog, QFrame, QSplitter, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QFont

from gui.video_widget import VideoWidget
from network.video_sender import VideoSender
from utils.validators import validate_email, validate_name
from utils.config import SERVER_URL, DEFAULT_VIDEO_PATH

class MainWindow(QMainWindow):
    """Main window of the surgical skill analysis client application."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Surgical Skill Analysis - Client")
        self.setMinimumSize(1024, 768)  # Increased minimum size for better layout
        
        # Initialize instance variables
        self.video_widget = None
        self.file_path = None
        self.is_recording = False
        self.sender_thread = None
        
        # Initialize network monitor
        self.network_monitor = NetworkMonitor(SERVER_URL)

        # Setup UI components
        self._setup_ui()
        
        # Setup signals and slots
        self._connect_signals()
        
        # Initialize status bar
        self.statusBar().showMessage("Ready")

       

    def _connect_signals(self):
        """Connect UI signals to their respective slots."""
        # Video control buttons
        self.start_btn.clicked.connect(self.start_recording)
        self.pause_btn.clicked.connect(self.toggle_pause_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        
        # Submission buttons
        self.submit_btn.clicked.connect(self.submit_to_server)
        self.cancel_btn.clicked.connect(self.cancel_submission)
        
        # New network-related connections
        self.retry_btn.clicked.connect(self.retry_upload)
        
    def _setup_ui(self):
        """Setup the user interface components."""
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Create title label
        title_label = QLabel("Surgical Skill Analysis System")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Create splitter for video and form sections to allow user resizing
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)  # Give it a stretch factor of 1
        
        # Video section (now larger by default)
        video_container = self._setup_video_section()
        splitter.addWidget(video_container)
        
        # Form section
        form_container = self._setup_form_section()
        splitter.addWidget(form_container)
        
        # Set initial sizes - video gets 70%, form gets 30%
        splitter.setSizes([700, 300])
        
        # Create status and controls section
        self._setup_status_section(main_layout)
        
    def _setup_video_section(self):
        """Setup the video display and recording section."""
        video_container = QFrame()
        video_container.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        video_layout = QVBoxLayout()
        video_container.setLayout(video_layout)
        
        # Video display - Set a minimum size and expand policy
        self.video_widget = VideoWidget()
        self.video_widget.setMinimumSize(640, 480)  # Minimum size for video
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_layout.addWidget(self.video_widget, 1)  # Give it stretch factor
        
        # Video controls
        video_controls = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Recording")
        self.pause_btn = QPushButton("Pause Recording")
        self.stop_btn = QPushButton("Stop & Save")
        
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        video_controls.addWidget(self.start_btn)
        video_controls.addWidget(self.pause_btn)
        video_controls.addWidget(self.stop_btn)
        
        video_layout.addLayout(video_controls)
        
        self.recording_indicator = QLabel("Not Recording")
        self.recording_indicator.setAlignment(Qt.AlignCenter)
        self.recording_indicator.setStyleSheet("color: gray;")
        video_layout.addWidget(self.recording_indicator)
        
        return video_container
        
    def _setup_form_section(self):
        """Setup the user information form section."""
        form_container = QFrame()
        form_container.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        form_layout = QGridLayout()
        form_container.setLayout(form_layout)
        
        # User information fields
        form_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_input = QLineEdit()
        form_layout.addWidget(self.name_input, 0, 1)
        
        form_layout.addWidget(QLabel("Email:"), 1, 0)
        self.email_input = QLineEdit()
        form_layout.addWidget(self.email_input, 1, 1)
        
        form_layout.addWidget(QLabel("Program:"), 2, 0)
        self.program_input = QComboBox()
        self.program_input.addItems(["General Surgery", "Orthopedics", "Neurosurgery", 
                                     "Cardiac Surgery", "Other"])
        form_layout.addWidget(self.program_input, 2, 1)
        
        form_layout.addWidget(QLabel("Iteration:"), 3, 0)
        self.iteration_input = QSpinBox()
        self.iteration_input.setRange(1, 100)
        form_layout.addWidget(self.iteration_input, 3, 1)
        
        form_layout.addWidget(QLabel("Additional Notes:"), 4, 0)
        self.notes_input = QLineEdit()
        form_layout.addWidget(self.notes_input, 4, 1)
        
        return form_container
        
    def _setup_status_section(self, parent_layout):
        """Setup the status and submission controls section."""
        status_layout = QVBoxLayout()

        # Network status indicator
        self.network_status = QLabel("Not connected")
        self.network_status.setStyleSheet("color: gray;")
        status_layout.addWidget(self.network_status)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        # Submission controls
        submit_layout = QHBoxLayout()
        
        self.submit_btn = QPushButton("Submit to Server")
        self.submit_btn.setEnabled(False)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)

        # New network-related controls
        self.retry_btn = QPushButton("Retry Connection")
        self.retry_btn.setEnabled(False)
        
        submit_layout.addWidget(self.submit_btn)
        submit_layout.addWidget(self.cancel_btn)
        submit_layout.addWidget(self.retry_btn)
        
        status_layout.addLayout(submit_layout)
        
        # Add the status section to parent layout
        parent_layout.addLayout(status_layout)

    @pyqtSlot()
    def start_recording(self):
        """Start video recording."""
        if not self.is_recording:
            # Check if video widget is initialized
            if not self.video_widget.is_camera_available():
                QMessageBox.critical(self, "Error", "Camera is not available.")
                return
            
            # Start recording
            success = self.video_widget.start_recording()
            
            if success:
                self.is_recording = True
                self.recording_indicator.setText("Recording...")
                self.recording_indicator.setStyleSheet("color: red; font-weight: bold;")
                
                # Update button states
                self.start_btn.setEnabled(False)
                self.pause_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
                self.submit_btn.setEnabled(False)
                
                # Update status
                self.statusBar().showMessage("Recording in progress...")
            else:
                QMessageBox.warning(self, "Warning", "Failed to start recording.")
    
    @pyqtSlot()
    def toggle_pause_recording(self):
        """Pause or resume video recording."""
        if self.is_recording:
            is_paused = self.video_widget.toggle_pause()
            
            if is_paused:
                self.pause_btn.setText("Resume Recording")
                self.recording_indicator.setText("Paused")
                self.recording_indicator.setStyleSheet("color: orange; font-weight: bold;")
                self.statusBar().showMessage("Recording paused")
            else:
                self.pause_btn.setText("Pause Recording")
                self.recording_indicator.setText("Recording...")
                self.recording_indicator.setStyleSheet("color: red; font-weight: bold;")
                self.statusBar().showMessage("Recording resumed")
    
    @pyqtSlot()
    def stop_recording(self):
        """Stop and save the video recording."""
        if self.is_recording:
            # First pause the recording while the dialog is open
            was_paused = self.video_widget.is_paused  # Store original pause state
            if not was_paused:
                self.video_widget.toggle_pause()  # Pause the recording
        
            # Generate file name based on current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"surgical_recording_{timestamp}.mp4"
        
            # Ask user for save location
            self.file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Video", 
                os.path.join(DEFAULT_VIDEO_PATH, default_filename),
                "Video Files (*.mp4)"
            )
        
            if self.file_path:
                # Save the recording
                if self.video_widget.stop_recording(self.file_path):
                    self.is_recording = False
                
                    # Update indicators
                    self.recording_indicator.setText("Recording Saved")
                    self.recording_indicator.setStyleSheet("color: green;")
                
                    # Update button states
                    self.start_btn.setEnabled(True)
                    self.pause_btn.setEnabled(False)
                    self.pause_btn.setText("Pause Recording")
                    self.stop_btn.setEnabled(False)
                    self.submit_btn.setEnabled(True)
                
                    # Update status
                    self.statusBar().showMessage(f"Recording saved to {self.file_path}")
                
                    #Show confirmation
                    QMessageBox.information(self, "Success", 
                                     "Recording has been saved successfully.\n"
                                     "You can now submit it to the server for analysis.")
                else:
                    QMessageBox.warning(self, "Warning", "Failed to save the recording.")
            else:
                # User cancelled the save dialog, resume recording if it wasn't paused before
                if not was_paused:
                    self.video_widget.toggle_pause()  # Resume the recording
                self.statusBar().showMessage("Save cancelled, recording continues...")
    
    @pyqtSlot()
    def submit_to_server(self):
        """Submit the recorded video and user information to the server."""
        # Validate inputs
        if not self._validate_inputs():
            return
        
        # Check if file exists
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.critical(self, "Error", "Video file does not exist.")
            return
        
        # Gather user data
        user_data = {
            "name": self.name_input.text(),
            "email": self.email_input.text(),
            "program": self.program_input.currentText(),
            "iteration": self.iteration_input.value(),
            "notes": self.notes_input.text(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Update UI state
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.submit_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        #self.pause_upload_btn.setEnabled(True)
        self.retry_btn.setEnabled(False)
        self.statusBar().showMessage("Preparing to send data to server...")
        
        # Create and start sender thread
        self.sender_thread = VideoSender(SERVER_URL, self.file_path, user_data)
        self.sender_thread.progress_update.connect(self.update_progress)
        self.sender_thread.upload_complete.connect(self.handle_upload_complete)
        self.sender_thread.upload_error.connect(self.handle_upload_error)
        self.sender_thread.connection_status.connect(self.handle_connection_status)
        
        # Start upload
        self.sender_thread.start()
        
    @pyqtSlot()
    def cancel_submission(self):
        """Cancel the ongoing submission."""
        if self.sender_thread and self.sender_thread.isRunning():
            # Request cancellation
            self.sender_thread.cancel_upload()
            self.statusBar().showMessage("Cancelling upload...")
            
            # Wait for thread to finish (with timeout)
            if not self.sender_thread.wait(3000):  # 3 seconds timeout
                self.sender_thread.terminate()
                self.statusBar().showMessage("Upload forcefully terminated")
            
            # Reset UI
            self.reset_submission_ui()

    @pyqtSlot()
    def retry_upload(self):
        """Force retry connection for upload."""
        if self.sender_thread and self.sender_thread.isRunning():
            # Reset retry count and try again
            self.sender_thread.retry_count = 0
            # Resume if paused
            if hasattr(self.sender_thread, 'paused') and self.sender_thread.paused:
                self.sender_thread.resume_upload()
                self.pause_upload_btn.setText("Pause Upload")
            
            self.statusBar().showMessage("Retrying connection...")
            self.retry_btn.setEnabled(False)

    def reset_submission_ui(self):
        """Reset the UI after submission ends (success, failure or cancellation)."""
        self.progress_bar.setVisible(False)
        self.submit_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
    
    @pyqtSlot(int)
    def update_progress(self, value):
        """Update the progress bar value during submission."""
        self.progress_bar.setValue(value)
        if value < 100:
            self.statusBar().showMessage(f"Uploading... {value}%")
        else:
            self.statusBar().showMessage("Upload complete. Waiting for server response...")
    
    @pyqtSlot(str)
    def handle_upload_complete(self, message):
        """Handle successful upload completion."""
        self.reset_submission_ui()
        
        # Show success message
        QMessageBox.information(self, "Upload Successful", 
                             f"{message}\n\nResults will be sent to your email.")
        
        self.statusBar().showMessage("Upload completed successfully")
        
        # Clear the file path to prevent re-submission
        self.file_path = None
        self.submit_btn.setEnabled(False)
        
        # Reset recording indicator
        self.recording_indicator.setText("Not Recording")
        self.recording_indicator.setStyleSheet("color: gray;")
    
    @pyqtSlot(str)
    def handle_upload_error(self, error_message):
        """Handle upload error."""
        self.reset_submission_ui()
        
        # Show error message
        QMessageBox.critical(self, "Upload Failed", 
                          f"Failed to upload video: {error_message}\n\n"
                          "Please check your connection and try again.")
        
        self.statusBar().showMessage("Upload failed")

    @pyqtSlot(bool, str)
    def handle_connection_status(self, connected, message):
        """Handle connection status updates."""
        if connected:
            self.network_status.setText(f"Status: {message}")
            self.network_status.setStyleSheet("color: green;")
            self.retry_btn.setEnabled(False)
        else:
            self.network_status.setText(f"Status: {message}")
            self.network_status.setStyleSheet("color: red; font-weight: bold;")
            self.retry_btn.setEnabled(True)    
        self.statusBar().showMessage(message)

    def _validate_inputs(self):
        """Validate user inputs before submission."""
        # Check name
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter your name.")
            return False
        
        # Validate name format (cannot contain numbers)
        if not validate_name(name):
            QMessageBox.warning(self, "Validation Error", 
                               "Name cannot contain numbers or special characters.")
            return False
        
        # Check email
        email = self.email_input.text().strip()
        if not email or not validate_email(email):
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            return False
            
        return True
    
    def reset_submission_ui(self):
        """Reset the UI after submission ends (success, failure or cancellation)."""
        self.progress_bar.setVisible(False)
        self.submit_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.retry_btn.setEnabled(False)
        self.network_status.setText("Not connected")
        self.network_status.setStyleSheet("color: gray;")

    def closeEvent(self, event):
        """Handle window close event."""
        # Check if recording is in progress
        if self.is_recording:
            reply = QMessageBox.question(self, "Confirm Exit", 
                                      "Recording is in progress. Are you sure you want to exit?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.video_widget.release_resources()
                event.accept()
            else:
                event.ignore()
        else:
            # Clean up resources
            self.video_widget.release_resources()
            
            # Check if upload is in progress
            if self.sender_thread and self.sender_thread.isRunning():
                reply = QMessageBox.question(self, "Confirm Exit", 
                                         "Upload is in progress. Are you sure you want to exit?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    self.sender_thread.cancel_upload()
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
    
                