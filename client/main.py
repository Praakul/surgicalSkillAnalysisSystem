# main.py

import sys
import os
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()