import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Email settings
    EMAIL_SERVER: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = "metaldove03@gmail.com"  # Replace with actual email
    EMAIL_PASSWORD: str = "cuwjocgechqmcarm"     # Replace with app password
    EMAIL_FROM: str = "surgical.skills.system@example.com"
    EMAIL_ENABLED: bool = True  # Set to True to actually send emails
    
    # Storage settings
    VIDEO_STORAGE_PATH: str = "videos"
    RESULTS_STORAGE_PATH: str = "results"
    
    # Processing settings
    MAX_CONCURRENT_JOBS: int = 5
    PROCESSING_TIME: int = 30  # seconds to simulate processing
    
    # Network check settings
    NETWORK_CHECK_INTERVAL: int = 60  # seconds
    
    # Create required directories
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        os.makedirs(self.VIDEO_STORAGE_PATH, exist_ok=True)
        os.makedirs(self.RESULTS_STORAGE_PATH, exist_ok=True)

@lru_cache()
def get_settings():
    return Settings()