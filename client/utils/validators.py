# utils/validators.py

import re

def validate_email(email):
    """
    Validate email format.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email is valid, False otherwise
    """
    # Simple regex pattern for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_name(name):
    """
    Validate name format - should not contain numbers or special characters.
    
    Args:
        name (str): Name to validate
        
    Returns:
        bool: True if name is valid, False otherwise
    """
    # Check if the name contains any digits
    if re.search(r'\d', name):
        return False
    
    # Check if the name contains only letters, spaces, hyphens, and apostrophes
    # This allows names like "Mary-Jane" or "O'Connor" but rejects special characters
    pattern = r'^[a-zA-Z\s\-\']+$'
    return bool(re.match(pattern, name))    