import logging
import sys

def setup_logging():
    """Configure application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("server.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce the verbosity of other libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    
    return logging.getLogger("surgical_skills_server")