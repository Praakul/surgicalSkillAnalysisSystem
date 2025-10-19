# services/job_queue.py

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from config import get_settings
from models.submission import VideoSubmission, SubmissionStatus
from services.video_processor import process_video
from services.email_service import send_result_email
from utils.network import NetworkMonitor

settings = get_settings()
logger = logging.getLogger("surgical_skills_server")

class JobQueue:
    """
    Manages video processing jobs with parallel execution capabilities
    """
    def __init__(self):
        self.processing_queue: List[VideoSubmission] = []
        self.currently_processing: int = 0
        self.completed_jobs: Dict[str, Dict[str, Any]] = {}
        self.failed_jobs: Dict[str, Dict[str, Any]] = {}
        self.results_cache: Dict[str, float] = {}
        self.network_monitor = NetworkMonitor()
        self.max_concurrent_jobs = settings.MAX_CONCURRENT_JOBS
        self.processing_lock = asyncio.Lock()
        self.queue_change_event = asyncio.Event()
        self.shutdown_event = asyncio.Event()
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_jobs)
        
        # Start the queue processor
        self.queue_processor_task = None
        self.main_event_loop = None

    async def start_processor(self):
        """Start the queue processor if not already running"""
        if self.main_event_loop is None:
            self.main_event_loop = asyncio.get_running_loop()  # Store loop safely
        
        if self.queue_processor_task is None or self.queue_processor_task.done():
            self.queue_processor_task = asyncio.create_task(self.queue_processor())
            logger.info("Starting queue processor")
    
    async def add_submission(self, submission: VideoSubmission) -> str:
        """
        Add a new submission to the processing queue
        """
        # Set initial status
        submission.status = SubmissionStatus.QUEUED
        submission.queue_time = datetime.now()
        
        # Add to queue
        async with self.processing_lock:
            self.processing_queue.append(submission)
            logger.info(f"Added submission {submission.id} to the queue")
        
        # Signal that queue has changed
        self.queue_change_event.set()
        
        # Start the queue processor if needed
        await self.start_processor()
        
        return submission.id
    
    async def queue_processor(self):
        """
        Process submissions in the queue, handling network issues and parallel processing
        """
        while not self.shutdown_event.is_set():
            # Wait for queue changes or periodically check
            try:
                # Wait for queue change event, but also check periodically
                await asyncio.wait_for(self.queue_change_event.wait(), timeout=30)
                self.queue_change_event.clear()
            except asyncio.TimeoutError:
                # Check if we have pending tasks or network issues to resolve
                pass
            
            # Check network connectivity if needed
            if self.network_monitor.should_check_connectivity(30):  # Check every minute
                self.network_monitor.check_connectivity()
            
            # Skip processing if network is down
            if not self.network_monitor.is_connected :
                logger.warning("Network is down, waiting for connectivity to resume processing")
                continue
            
            # Process items in the queue
            await self._process_queue_items()
            
            # If queue is empty, check if we're done
            if not self.processing_queue and self.currently_processing == 0:
                logger.info("Queue processor stopped - no more jobs")
                break
    
    async def _process_queue_items(self):
        """Process available items in the queue"""
        while (self.processing_queue and 
               self.currently_processing < self.max_concurrent_jobs and 
               not self.shutdown_event.is_set()):
            
            # Get next submission
            async with self.processing_lock:
                if not self.processing_queue:
                    break
                
                submission = self.processing_queue.pop(0)
                self.currently_processing += 1
            
            # Update status
            submission.status = SubmissionStatus.PROCESSING
            submission.processing_start_time = datetime.now()
            
            # Process in thread pool to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            try:
                # Submit task to thread pool
                await loop.run_in_executor(
                    self.executor, 
                    partial(self._process_submission, submission)
                )
            except Exception as e:
                logger.error(f"Error scheduling job {submission.id}: {str(e)}")
                submission.status = SubmissionStatus.FAILED
                submission.error_message = str(e)
                self._record_failed_job(submission)
                
                async with self.processing_lock:
                    self.currently_processing -= 1

    
    async def retry_failed_emails(self):
        """Retry sending emails for submissions that failed due to network issues"""
        retried = 0
        if not self.network_monitor.check_connectivity():
            return 0
    
        # Find submissions with PENDING_EMAIL status
        pending_emails = [job for job in self.completed_jobs.values() 
                        if job["submission"].status == SubmissionStatus.PENDING_EMAIL]
    
        for job in pending_emails:
            submission = job["submission"]
            try:
                # Try to send email again
                send_result_email(
                    submission.user_info.email,
                    submission.user_info.name,
                    job["score"],
                    submission.video_path
                )
            
                # Update status
                submission.status = SubmissionStatus.COMPLETED
                submission.completion_time = datetime.now()
                retried += 1
                logger.info(f"Successfully retried email for submission {submission.id}")
            except Exception as e:
                logger.error(f"Failed to retry email for {submission.id}: {str(e)}")
    
        return retried                
    
   
    async def periodic_maintenance(self):
        """Perform periodic maintenance tasks"""
        while not self.shutdown_event.is_set():
            await asyncio.sleep(60)  # Run every 1 minutes
        
            # Retry pending emails
            if self.network_monitor.is_connected:
                retried = await self.retry_failed_emails()
                if retried > 0:
                    logger.info(f"Retried {retried} pending emails during maintenance")
        
            # Clean up old temporary files
            # Other maintenance tasks

    def _process_submission(self, submission: VideoSubmission):
        """
        Process a single submission (runs in a separate thread)
        """
        logger.info(f"Processing submission {submission.id}")
        
        try:
            logger.info(f"Processing video for submission {submission.id}")
            score = process_video(submission.video_path)
            
            self.results_cache[submission.id] = score
            logger.info(f"Generated score {score} for submission {submission.id}")
            
            if settings.EMAIL_ENABLED:
                if self.network_monitor.check_connectivity():
                    try:
                        send_result_email(
                            submission.user_info.email,
                            submission.user_info.name,
                            score,
                            submission.video_path
                        )
                        submission.status = SubmissionStatus.COMPLETED
                        submission.completion_time = datetime.now()
                        self._record_completed_job(submission)
                        
                    except Exception as e:
                        logger.error(f"Failed to send email to {submission.user_info.email}: {str(e)}")
                        submission.status = SubmissionStatus.EMAIL_FAILED
                        submission.error_message = f"Video processed successfully, but failed to send email: {str(e)}"
                        self._record_failed_job(submission)
                else:
                    logger.warning(f"Network is down, marking submission {submission.id} as pending email")
                    submission.status = SubmissionStatus.PENDING_EMAIL
                    submission.error_message = "Video processed successfully, but network is down for email delivery"
                    self._record_completed_job(submission)
            else:
                submission.status = SubmissionStatus.COMPLETED
                submission.completion_time = datetime.now()
                self._record_completed_job(submission)
                
        except Exception as e:
            logger.error(f"Error processing submission {submission.id}: {str(e)}")
            submission.status = SubmissionStatus.FAILED
            submission.error_message = str(e)
            self._record_failed_job(submission)
        
        finally:
            if self.main_event_loop:
                asyncio.run_coroutine_threadsafe(
                    self._decrement_processing_count(), self.main_event_loop
                )
            else:
                logger.error("Main event loop not set when trying to decrement processing count.")
    
    async def _decrement_processing_count(self):
        """Safely decrement the processing count"""
        async with self.processing_lock:
            self.currently_processing -= 1
            # Signal that the queue has changed
            self.queue_change_event.set()
    
    def _record_completed_job(self, submission: VideoSubmission):
        """Record a completed job"""
        self.completed_jobs[submission.id] = {
            "submission": submission,
            "user_info": submission.user_info,
            "score": self.results_cache.get(submission.id),
            "processing_time": (submission.completion_time - submission.processing_start_time).total_seconds()
            if submission.completion_time and submission.processing_start_time else None
        }
    
    def _record_failed_job(self, submission: VideoSubmission):
        """Record a failed job"""
        self.failed_jobs[submission.id] = {
            "submission": submission,
            "user_info": submission.user_info,
            "error": submission.error_message,
            "timestamp": datetime.now()
        }
    
    def get_submission_status(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a submission
        """
        # Check if in queue
        for submission in self.processing_queue:
            if submission.id == submission_id:
                queue_position = self.processing_queue.index(submission) + 1
                return {
                    "id": submission_id,
                    "status": submission.status.value,
                    "queue_position": queue_position,
                    "estimated_time": queue_position * settings.PROCESSING_TIME
                }
        
        # Check if completed
        if submission_id in self.completed_jobs:
            job = self.completed_jobs[submission_id]
            return {
                "id": submission_id,
                "status": job["submission"].status.value,
                "score": job["score"],
                "processing_time": job["processing_time"]
            }
        
        # Check if failed
        if submission_id in self.failed_jobs:
            job = self.failed_jobs[submission_id]
            return {
                "id": submission_id,
                "status": job["submission"].status.value,
                "error": job["error"]
            }
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current status of the queue
        """
        return {
            "queue_length": len(self.processing_queue),
            "currently_processing": self.currently_processing,
            "completed_jobs": len(self.completed_jobs),
            "failed_jobs": len(self.failed_jobs),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "network_status": "connected" if self.network_monitor.is_connected else "disconnected",
            "estimated_wait_time": len(self.processing_queue) * settings.PROCESSING_TIME / max(1, self.max_concurrent_jobs)
        }
    
    def cancel_submission(self, submission_id: str) -> bool:
        """
        Cancel a queued submission
        """
        async def _cancel():
            async with self.processing_lock:
                for i, submission in enumerate(self.processing_queue):
                    if submission.id == submission_id:
                        self.processing_queue.pop(i)
                        self.queue_change_event.set()
                        return True
                return False
        
        # Run in event loop
        loop = asyncio.get_event_loop()
        return asyncio.run_coroutine_threadsafe(_cancel(), loop).result()
    
    async def shutdown(self):
        """
        Shutdown the queue processor gracefully
        """
        self.shutdown_event.set()
        self.queue_change_event.set()
        
        if self.queue_processor_task:
            await self.queue_processor_task
        
        self.executor.shutdown(wait=True)
        logger.info("Job queue shutdown complete")