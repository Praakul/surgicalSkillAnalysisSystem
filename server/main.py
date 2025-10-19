
# main.py

import uvicorn
import logging
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from api.routes import router
from services.job_queue import JobQueue
from utils.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger("surgical_skills_server")

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Surgical Skills Analysis Server",
    description="Server for analyzing surgical skill videos",
    version="1.0.0"
    #timeout= settings.REQUEST_TIMEOUT
)
    

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create global job queue instance
job_queue = JobQueue()

# Include router
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    """Run on server startup"""
    logger.info("Starting Surgical Skill Analysis Server")
    
    # Ensure storage directories exist
    os.makedirs(settings.VIDEO_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.RESULTS_STORAGE_PATH, exist_ok=True)
    
    logger.info(f"Video storage path: {settings.VIDEO_STORAGE_PATH}")
    logger.info(f"Results storage path: {settings.RESULTS_STORAGE_PATH}")
    logger.info(f"Max concurrent jobs: {settings.MAX_CONCURRENT_JOBS}")
    
    # Start job queue processor
    await job_queue.start_processor()

@app.on_event("shutdown")
async def shutdown_event():
    """Run on server shutdown"""
    logger.info("Shutting down Surgical Skill Analysis Server")
    await job_queue.shutdown()

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=settings.DEBUG
    )    