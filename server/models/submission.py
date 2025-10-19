# models/submission.py

import uuid
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class SubmissionStatus(str, Enum):
    """Status of a video submission"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    EMAIL_FAILED = "email_failed"
    PENDING_EMAIL = "pending_email"

class UserInfo(BaseModel):
    """User information for a video submission"""
    name: str
    email: str
    iteration_number: int
    program: str
    additional_info: Optional[str] = None

class VideoSubmission:
    """Video submission for analysis"""
    def __init__(self, user_info: UserInfo, video_path: str):
        self.id = str(uuid.uuid4())
        self.user_info = user_info
        self.video_path = video_path
        self.status = SubmissionStatus.QUEUED
        self.queue_time = datetime.now()
        self.processing_start_time: Optional[datetime] = None
        self.completion_time: Optional[datetime] = None
        self.error_message: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_info": self.user_info.dict(),
            "video_path": self.video_path,
            "status": self.status.value,
            "queue_time": self.queue_time.isoformat() if self.queue_time else None,
            "processing_start_time": self.processing_start_time.isoformat() if self.processing_start_time else None,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "error_message": self.error_message
        }