# utils/error_handler.py

import traceback
import logging
import os
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox

# Configure logging
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, f"error_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ErrorHandler:
    """Class for handling and logging errors."""
    
    @staticmethod
    def log_error(error, context=None):
        """Log an error to the error log.
        
        Args:
            error (Exception): The error to log
            context (str, optional): Context information
        """
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        # Create log message
        log_message = f"ERROR: {error_message}"
        if context:
            log_message = f"{context} - {log_message}"
        
        # Log the error
        logging.error(log_message)
        logging.error(error_traceback)
    
    @staticmethod
    def show_error_dialog(parent, title, message, detailed_message=None):
        """Show an error dialog to the user.
        
        Args:
            parent (QWidget): Parent widget for the dialog
            title (str): Dialog title
            message (str): Error message
            detailed_message (str, optional): Detailed error information
        """
        error_box = QMessageBox(parent)
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle(title)
        error_box.setText(message)
        
        if detailed_message:
            error_box.setDetailedText(detailed_message)
            
        error_box.exec_()
    
    @staticmethod
    def handle_exception(parent, error, context=None, show_dialog=True):
        """Log an error and optionally show an error dialog.
        
        Args:
            parent (QWidget): Parent widget for the dialog
            error (Exception): The error to handle
            context (str, optional): Context information
            show_dialog (bool): Whether to show an error dialog
        """
        # Log the error
        ErrorHandler.log_error(error, context)
        
        # Show error dialog if requested
        if show_dialog:
            title = "Error"
            message = str(error)
            detailed_message = traceback.format_exc()
            
            if context:
                title = f"{context} Error"
                
            ErrorHandler.show_error_dialog(parent, title, message, detailed_message)
    
    @staticmethod
    def check_and_log_system():
        """Check system requirements and log any issues."""
        issues = []
        
        # Check OpenCV installation
        try:
            import cv2
            cv_version = cv2.__version__
            logging.info(f"OpenCV version: {cv_version}")
        except ImportError:
            issues.append("OpenCV is not installed. Please install it using 'pip install opencv-python'.")
        
        # Check PyQt5 installation
        try:
            from PyQt5.QtCore import QT_VERSION_STR
            logging.info(f"Qt version: {QT_VERSION_STR}")
        except ImportError:
            issues.append("PyQt5 is not installed. Please install it using 'pip install PyQt5'.")
        
        # Check requests installation
        try:
            import requests
            requests_version = requests.__version__
            logging.info(f"Requests version: {requests_version}")
        except ImportError:
            issues.append("Requests is not installed. Please install it using 'pip install requests'.")
        
        # Check requests_toolbelt installation
        try:
            import requests_toolbelt
            toolbelt_version = requests_toolbelt.__version__
            logging.info(f"Requests-Toolbelt version: {toolbelt_version}")
        except ImportError:
            logging.warning("Requests-Toolbelt is not installed. File upload progress tracking will be disabled.")
        
        # Check for camera access
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                issues.append("Cannot access camera. Please check camera connections and permissions.")
            else:
                cap.release()
        except Exception as e:
            issues.append(f"Camera check failed: {str(e)}")
        
        # Log all issues
        if issues:
            for issue in issues:
                logging.error(f"System check issue: {issue}")
            return False, issues
        
        logging.info("System check passed. All requirements met.")
        return True, []