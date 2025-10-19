# Surgical Skill Analysis System

A Multiclient and server system for recording, submitting, processing, and evaluating surgical procedures. This system consists of two main components: a client application for video capture and submission, and a server for processing and analysis.

## System Architecture

```
┌─────────────────┐       ┌─────────────────┐       ┌───────────────┐
│ Client          │       │ Server          │       │ Email         │
│ - Video capture │──────▶│ - Queue mgmt    │──────▶│ Notification  │
│ - User info     │◀──────│ - Processing    │       │ to User       │
│ - Submission    │       │ - Results       │       └───────────────┘
└─────────────────┘       └─────────────────┘
```

## Client Features

- Video recording using webcam with start, pause, and stop controls
- User information capture (name, email, program, iteration, additional details)
- Video upload to analysis server with progress tracking
- Resilient network failure handling and automatic retries
- User-friendly interface with status updates

## Server Features

- REST API built with FastAPI for receiving video submissions
- Asynchronous processing queue for handling multiple submissions
- Email notifications for sending evaluation results
- Robust error handling and edge case management
- Network connectivity monitoring with automatic retries

## Installation

### Client Installation


1. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Server Installation

1. Navigate to the server directory:
   ```
   cd ../server
   ```

2. Create a virtual environment (if not already created):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Update configuration settings in `config.py` if needed.

## Running the System

### Starting the Server

```bash
cd server
python main.py
```

By default, the server will run on `http://0.0.0.0:8000`.

### Starting the Client

```bash
cd client
python main.py
```

## API Endpoints

### Submit a Video

**Endpoint:** `POST /submit`

**Form Data:**

- `video`: Video file (required)
- `name`: User's name (required)
- `email`: User's email (required)
- `iteration_number`: Iteration number (required)
- `program`: Program name (required)
- `additional_info`: Additional information (optional)

**Response:**
```json
{
    "submission_id": "unique-id",
    "status": "accepted",
    "message": "Your video has been queued for processing",
    "queue_position": 1,
    "estimated_processing_time": 30
}
```

### Check Submission Status

**Endpoint:** `GET /status/{submission_id}`

**Response:**
```json
{
    "status": "queued",
    "submission_time": "2023-05-01T12:00:00",
    "queue_position": 1,
    "estimated_processing_time": 30
}
```

Possible status values:

- `queued`: In queue waiting for processing
- `processing`: Currently being processed
- `completed`: Processing completed
- `failed`: Processing failed
- `waiting_for_internet`: Waiting for internet connection
- `cancelled`: Submission was cancelled

### Other Endpoints

- **Cancel a Submission:** `DELETE /submission/{submission_id}`
- **Server Health Check:** `GET /health`
- **Queue Status:** `GET /queue-status`

## Client Configuration

The client application uses a flexible configuration system with multiple layers:

1. **Default Configuration**: Default values are defined in `utils/config.py`
2. **Local Configuration Override**: Create a `utils/local_config.py` file to override default settings
3. **Configuration File**: Uses a `config.ini` file for persistent configuration

### Configurable Settings

- Server URL and endpoints
- Connection and upload timeouts
- Default video path and format
- Video quality settings
- UI refresh rates
- Retry settings and policies

## Server Configuration

All configuration options are in `config.py`:

```python
# Server settings
HOST: str = "0.0.0.0"
PORT: int = 8000
DEBUG: bool = True

# Email settings
EMAIL_SERVER: str = "smtp.gmail.com"
EMAIL_PORT: int = 587
EMAIL_USERNAME: str = "your_email@gmail.com"
EMAIL_PASSWORD: str = "your_app_password"
EMAIL_FROM: str = "surgical.skills.system@example.com"
EMAIL_ENABLED: bool = False  # Set to True to actually send emails

# Storage settings
VIDEO_STORAGE_PATH: str = "videos"
RESULTS_STORAGE_PATH: str = "results"

# Processing settings
MAX_CONCURRENT_JOBS: int = 3
PROCESSING_TIME: int = 30  # seconds

# Network check settings
NETWORK_CHECK_INTERVAL: int = 60  # seconds
```


## Edge Cases Handled

### Network Issues

- Connection timeouts with automatic retries
- Server unavailability detection
- Upload interruptions with resumption
- Periodic connectivity checks on server
- Queuing of submissions during network outages

### Processing Queue Management

- Simultaneous video submissions handling
- Configurable concurrent processing limit
- Accurate queue position and processing time estimates
- Automatic retry mechanism when connectivity is lost

### Error Handling

- Comprehensive error catching and logging
- Failed uploads and processing errors are properly reported
- Email delivery failures with retry mechanisms
- User-friendly error messages

### Resource Management

- Video files storage organization
- Results maintenance and organization
- Server resources monitoring
