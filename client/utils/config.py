# utils/config.py

import os

# Server configuration
SERVER_URL = "http://0.0.0.0:8000/submit"  # Default server URL

# File paths
DEFAULT_VIDEO_PATH = os.path.join(os.path.expanduser("~"), "Videos")

# Timeouts (in seconds)
CONNECTION_TIMEOUT = 60
UPLOAD_TIMEOUT = 600  # 10 minutes for large videos

# Video settings
DEFAULT_FPS = 30
DEFAULT_VIDEO_QUALITY = 60  # 0-100 scale
MAX_VIDEO_SIZE_MB = 500  # Maximum video size in MB

# User interface settings
UI_REFRESH_RATE = 30  # milliseconds

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Load environment-specific config if available
try:
    from utils.local_config import * # type: ignore
except ImportError:
    pass

# Create a config.ini file if it doesn't exist
def create_default_config():
    import configparser
    
    if os.path.exists('config.ini'):
        return
        
    config = configparser.ConfigParser()
    
    config['SERVER'] = {
        'URL': SERVER_URL,
        'CONNECTION_TIMEOUT': str(CONNECTION_TIMEOUT),
        'UPLOAD_TIMEOUT': str(UPLOAD_TIMEOUT)
    }
    
    config['VIDEO'] = {
        'DEFAULT_PATH': DEFAULT_VIDEO_PATH,
        'DEFAULT_FPS': str(DEFAULT_FPS),
        'DEFAULT_QUALITY': str(DEFAULT_VIDEO_QUALITY),
        'MAX_SIZE_MB': str(MAX_VIDEO_SIZE_MB)
    }
    
    config['UI'] = {
        'REFRESH_RATE': str(UI_REFRESH_RATE)
    }
    
    config['RETRY'] = {
        'MAX_RETRIES': str(MAX_RETRIES),
        'RETRY_DELAY': str(RETRY_DELAY)
    }
    
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

# Load config from ini file if exists
def load_config():
    import configparser
    
    if not os.path.exists('config.ini'):
        create_default_config()
        return
        
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Update global variables
    global SERVER_URL, CONNECTION_TIMEOUT, UPLOAD_TIMEOUT
    global DEFAULT_VIDEO_PATH, DEFAULT_FPS, DEFAULT_VIDEO_QUALITY, MAX_VIDEO_SIZE_MB
    global UI_REFRESH_RATE, MAX_RETRIES, RETRY_DELAY
    
    # Server settings
    if 'SERVER' in config:
        SERVER_URL = config['SERVER'].get('URL', SERVER_URL)
        CONNECTION_TIMEOUT = config['SERVER'].getint('CONNECTION_TIMEOUT', CONNECTION_TIMEOUT)
        UPLOAD_TIMEOUT = config['SERVER'].getint('UPLOAD_TIMEOUT', UPLOAD_TIMEOUT)
    
    # Video settings
    if 'VIDEO' in config:
        DEFAULT_VIDEO_PATH = config['VIDEO'].get('DEFAULT_PATH', DEFAULT_VIDEO_PATH)
        DEFAULT_FPS = config['VIDEO'].getint('DEFAULT_FPS', DEFAULT_FPS)
        DEFAULT_VIDEO_QUALITY = config['VIDEO'].getint('DEFAULT_QUALITY', DEFAULT_VIDEO_QUALITY)
        MAX_VIDEO_SIZE_MB = config['VIDEO'].getint('MAX_SIZE_MB', MAX_VIDEO_SIZE_MB)
    
    # UI settings
    if 'UI' in config:
        UI_REFRESH_RATE = config['UI'].getint('REFRESH_RATE', UI_REFRESH_RATE)
    
    # Retry settings
    if 'RETRY' in config:
        MAX_RETRIES = config['RETRY'].getint('MAX_RETRIES', MAX_RETRIES)
        RETRY_DELAY = config['RETRY'].getint('RETRY_DELAY', RETRY_DELAY)

# Try to load config when module is imported
try:
    load_config()
except:
    # Use defaults if config loading fails
    pass