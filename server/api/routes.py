#api/routes.py

import os
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Optional
from config import get_settings
from models.submission import UserInfo, VideoSubmission
from services.job_queue import JobQueue

router = APIRouter()
settings = get_settings()
job_queue = JobQueue()

@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    name: str = Form(...),
    email: str = Form(...),
    iteration_number: int = Form(...),
    program: str = Form(...),
    additional_info: Optional[str] = Form(None)
):
    """Submit a surgical skill video for analysis"""
    print(f"Received submission from: {name}, {email}")
    print(f"Video filename: {video.filename}")
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{video.filename}"
    video_path = os.path.join(settings.VIDEO_STORAGE_PATH, filename)
    
    # Save the uploaded video
    try:
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
            print(f"Video saved to: {video_path}, size: {len(content)} bytes")
    except Exception as e:
        print(f"Error saving video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")
    
    # Create user info object
    user_info = UserInfo(
        name=name,
        email=email,
        iteration_number=iteration_number,
        program=program,
        additional_info=additional_info
    )
    
    # Create submission object
    submission = VideoSubmission(
        user_info=user_info,
        video_path=video_path,
    )
    
    # Add to job queue
    await job_queue.add_submission(submission)
    print(f"Submission added to queue with ID: {submission.id}")
    
    # Calculate queue stats
    queue_position = len(job_queue.processing_queue)
    estimated_time = queue_position * settings.PROCESSING_TIME
    
    response_data = {
        "submission_id": submission.id,
        "status": "accepted",
        "message": "Your video has been queued for processing",
        "queue_position": queue_position,
        "estimated_processing_time": estimated_time  # seconds
    }
    
    print(f"Sending response: {response_data}")
    return response_data

@router.get("/status/{submission_id}")
async def get_status(submission_id: str):
    """Get the status of a submitted video"""
    status_info = job_queue.get_submission_status(submission_id)
    if status_info is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return status_info

@router.get("/health")
async def health_check():
    """Server health check endpoint"""
    return {
        "status": "healthy",
        "queue_size": len(job_queue.processing_queue),
        "processing": job_queue.currently_processing,
        "internet_connection": job_queue.network_monitor.is_connected,
        "timestamp": datetime.now().isoformat()
    }

@router.delete("/submission/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_submission(submission_id: str):
    """Cancel a queued submission"""
    success = job_queue.cancel_submission(submission_id)
    if not success:
        submission_status = job_queue.get_submission_status(submission_id)
        if submission_status is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel submission with status '{submission_status['status']}'"
            )
    
    return JSONResponse(status_code=200, content={"message": "Submission cancelled successfully"})

@router.get("/queue-status")
async def queue_status():
    """Get the current queue status"""
    return job_queue.get_queue_status()