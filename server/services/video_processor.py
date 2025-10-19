#services/video_processor.py

import asyncio
import random
import logging
import time
from models.submission import VideoSubmission

logger = logging.getLogger("surgical_skills_server")

# Core implementation - non-async version that does the actual work
def _process_video_core(video_path):
    """Core video processing implementation"""
    # Simulate processing time
    time.sleep(30)
    
    # Generate a random score between 1 and 10
    score = round(random.uniform(1, 10), 1)
    logger.info(f"Generated score {score} for video")
    
    return score

# Function for thread pool executor to use
def process_video(video_path):
    """
    Process a surgical skill video and generate a score
    For use in threaded contexts (non-async)
    
    Args:
        video_path: Path to the video file
        
    Returns:
        float: Score between 1 and 10
    """
    logger.info(f"Processing video at path: {video_path}")
    
    try:
        # Call the core implementation
        return _process_video_core(video_path)
    except Exception as e:
        logger.error(f"Error processing video at {video_path}: {str(e)}")
        raise

class VideoProcessor:
    @staticmethod
    async def process_video(submission: VideoSubmission):
        """
        Process a surgical skill video and generate a score
        Async wrapper for backward compatibility
        
        Args:
            submission: VideoSubmission object
            
        Returns:
            float: Score between 1 and 10
        """
        logger.info(f"Processing video for submission {submission.id}")
        
        try:
            # Run the core implementation in a thread pool to make it async-compatible
            loop = asyncio.get_running_loop()
            score = await loop.run_in_executor(
                None, _process_video_core, submission.video_path
            )
            return score
        except Exception as e:
            logger.error(f"Error processing video for submission {submission.id}: {str(e)}")
            raise