#service/email_service.py

import smtplib
import logging
import asyncio
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import get_settings

logger = logging.getLogger("surgical_skills_server")

# Shared core email sending functionality
def _create_email_message(email: str, name: str, result: float, settings, video_path=None, iteration=None, program=None):
    """Create the email message with appropriate content based on available parameters"""
    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = email
    msg["Subject"] = "Your Surgical Skill Analysis Results"
    
    # Build the body content based on available parameters
    content_parts = [
        f"Hello {name},",
        "",
        "Your surgical skill video has been analyzed. Here are your results:",
        "",
        f"Score: {result}/10"
    ]
    
    # Add parameters that are provided
    if iteration is not None:
        content_parts.append(f"Iteration: {iteration}")
    if program is not None:
        content_parts.append(f"Program: {program}")
    #if video_path is not None:
        #content_parts.append(f"Video: {video_path}")
        
    content_parts.extend([
        f"Great Job! Keep up the good work in your surgical training.",
        "",
        "Thank you for using our Surgical Skill Analysis System!"
    ])
    
    body = "\n".join(content_parts)
    msg.attach(MIMEText(body, "plain"))
    return msg

# Non-async function for the thread pool
def send_result_email(email: str, name: str, result: float, video_path: str):
    """
    Send analysis results via email (non-async version for threading)
    
    Args:
        email: Recipient email address
        name: Recipient name
        result: Analysis score
        video_path: Path to the processed video
    """
    logger.info(f"Sending result email to {email} for video {video_path}")
    settings = get_settings()
    
    try:
        msg = _create_email_message(email, name, result, settings, video_path=video_path)
        
        if settings.EMAIL_ENABLED:
            for attempt in range(3):  # Max 3 retries
                try:
                    with smtplib.SMTP(settings.EMAIL_SERVER, settings.EMAIL_PORT) as server:
                        server.starttls()
                        server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                        server.send_message(msg)
                    
                    logger.info(f"Email sent to {email} for video {video_path}")
                    return True
                except Exception as e:
                    wait_time = 2 ** (attempt + 1)  # Exponential backoff
                    if attempt < 2:  # Don't log "retrying" on the last attempt
                        logger.warning(f"Email sending failed, retrying in {wait_time}s ({attempt+1}/3): {str(e)}")
                        time.sleep(wait_time)
                    else:
                        raise  # Re-raise on the last attempt
            
        else:
            logger.info(f"Email would be sent to {email} (EMAIL_ENABLED=False)")
            return True
                
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        raise

class EmailService:
    def __init__(self):
        self.settings = get_settings()
        self._semaphore = asyncio.Semaphore(5)  # Limit concurrent email sending
        
    async def send_result_email(self, email: str, name: str, result: float, iteration: int, program: str, job_id: Optional[str] = None):
        """
        Send analysis results via email with improved error handling and rate limiting
        
        Args:
            email: Recipient email address
            name: Recipient name
            result: Analysis score
            iteration: Training iteration
            program: Training program name
            job_id: Optional job identifier for tracking
        """
        async with self._semaphore:  # Prevent too many concurrent SMTP connections
            job_info = f" [Job: {job_id}]" if job_id else ""
            logger.info(f"Sending result email to {email}{job_info}")
            
            try:
                msg = _create_email_message(
                    email, name, result, self.settings, 
                    iteration=iteration, program=program
                )
                
                if self.settings.EMAIL_ENABLED:
                    for attempt in range(3):  # Max 3 retries
                        try:
                            async with asyncio.timeout(10):
                                await asyncio.to_thread(self._send_smtp_email, msg)
                            logger.info(f"Email sent to {email}{job_info}")
                            return True
                        except (asyncio.TimeoutError, Exception) as e:
                            wait_time = 2 ** (attempt + 1)
                            if attempt < 2:  # Don't log "retrying" on the last attempt
                                logger.warning(f"Email sending failed, retrying in {wait_time}s ({attempt+1}/3): {str(e)}{job_info}")
                                await asyncio.sleep(wait_time)
                            else:
                                raise  # Re-raise on the last attempt
                else:
                    logger.info(f"Email would be sent to {email} (EMAIL_ENABLED=False){job_info}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to send email to {email}{job_info}: {str(e)}")
                raise
    
    def _send_smtp_email(self, msg):
        """Helper method to send actual SMTP email (runs in thread pool)"""
        settings = self.settings
        with smtplib.SMTP(settings.EMAIL_SERVER, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.send_message(msg)