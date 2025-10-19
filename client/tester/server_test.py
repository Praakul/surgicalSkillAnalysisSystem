# This script is for testing the server by sending video files and user data.

import os
import time
import requests
import argparse
from requests_toolbelt.multipart.encoder import MultipartEncoder
import logging
import json
import concurrent.futures
import sys
from datetime import datetime
import random
import csv

def parse_arguments():
    """Parse command line arguments or return defaults if run directly."""
    # Check if script is run with command line arguments
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="Test server with video uploads")
        parser.add_argument("--url", required=True, help="Server URL")
        parser.add_argument("--video", required=True, help="Path to video file")
        parser.add_argument("--name", required=True, help="User name")
        parser.add_argument("--email", required=True, help="User email")
        parser.add_argument("--program", required=True, help="Program name")
        parser.add_argument("--iteration", required=True, type=int, help="Iteration number")
        parser.add_argument("--notes", default="", help="Additional notes")
        parser.add_argument("--password", help="App password for authentication")
        parser.add_argument("--requests", type=int, default=10, help="Number of requests to send")
        parser.add_argument("--interval", type=float, default=1.0, help="Time interval between requests in seconds")
        parser.add_argument("--concurrent", action="store_true", help="Run requests concurrently")
        parser.add_argument("--concurrency", type=int, default=3, help="Number of concurrent requests")
        parser.add_argument("--vary", action="store_true", help="Vary request data slightly")
        
        args = parser.parse_args()
        
        return {
            "server_url": args.url,
            "video_path": args.video,
            "user_data": {
                "name": args.name,
                "email": args.email,
                "program": args.program,
                "iteration": args.iteration,
                "notes": args.notes
            },
            "app_password": args.password,
            "num_requests": args.requests,
            "interval": args.interval,
            "concurrent": args.concurrent,
            "concurrency": args.concurrency,
            "variation": args.vary
        }
    else:
        # Default parameters when run without command line arguments 
        return {
            # EDIT THESE VALUES FOR YOUR TEST
            "server_url": "http://localhost:8000/submit",
            "video_path": "path/to/your/video.mp4",
            "user_data": {
                "name": "Test User",
                "email": "Enter the email",
                "program": "Test Program",
                "iteration": 1,
                "notes": "Test notes for VSCode run"
            },
            "app_password": None,  # Add your password here if needed(not needed for local testing)
            "num_requests": 10,
            "interval": 1.0,
            "concurrent": 1,  # Set to True for concurrent testing
            "concurrency": 4,
            "variation": False    # Set to True to vary request data
        }

class ServerTester:
    def __init__(self, server_url, video_path, user_data, app_password=None):
        """
        Initialize the ServerTester.
        
        Args:
            server_url (str): URL of the server to test
            video_path (str): Path to the video file
            user_data (dict): User data containing name, email, program, iteration, and optional notes
            app_password (str, optional): App password for authentication if required
        """
        self.server_url = server_url
        self.video_path = video_path
        self.user_data = user_data
        self.app_password = app_password
        
        # Create a timestamped log filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"server_test_{timestamp}.log"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("ServerTester")
        self.logger.info(f"Logging to file: {log_filename}")
        
        # Create a CSV file for results
        self.csv_filename = f"test_results_{timestamp}.csv"
        with open(self.csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Request ID', 'Timestamp', 'Status Code', 'Response Time (s)', 
                'Response Size (bytes)', 'Error'
            ])
        
        # Validate inputs
        self._validate_inputs()
    
    def _validate_inputs(self):
        """Validate input parameters."""
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
        
        # Check video file size
        video_size = os.path.getsize(self.video_path) / (1024 * 1024)  # Size in MB
        self.logger.info(f"Video file size: {video_size:.2f} MB")
        
        required_fields = ['name', 'email', 'program', 'iteration']
        for field in required_fields:
            if field not in self.user_data:
                raise ValueError(f"Missing required field in user_data: {field}")
        
        # Check if server URL is reachable
        try:
            response = requests.head(self.server_url, timeout=5)
            self.logger.info(f"Server URL is reachable, status code: {response.status_code}")
        except Exception as e:
            self.logger.warning(f"Warning: Could not reach server URL: {str(e)}")
            # Ask user if they want to continue
            if input("Continue anyway? (y/n): ").lower() != 'y':
                sys.exit(1)
    
    def prepare_request_data(self, variation=False):
        """
        Prepare the multipart form data for the request.
        
        Args:
            variation (bool): If True, add slight variations to the data
        """
        # If variation is enabled, add small random changes to some fields
        name = self.user_data['name']
        email = self.user_data['email']
        program = self.user_data['program']
        iteration = self.user_data['iteration']
        notes = self.user_data.get('notes', '')
        
        if variation:
            # Add a random suffix to email to simulate different users
            email_parts = email.split('@')
            random_suffix = f"+test{random.randint(1, 9999):04d}"
            email = f"{email_parts[0]}{random_suffix}@{email_parts[1]}"
            
            # Slightly modify iteration
            iteration = iteration + random.randint(-1, 1)
            
            # Add timestamp to notes
            notes = f"{notes} - Test run at {datetime.now().strftime('%H:%M:%S')}"
        
        fields = {
            'video': (os.path.basename(self.video_path), 
                      open(self.video_path, 'rb'), 
                      'video/mp4'),
            'name': name,
            'email': email,
            'program': program,
            'iteration_number': str(iteration),
            'additional_info': notes
        }
        
        return fields
    
    def send_request(self, request_id, variation=False):
        """
        Send a single request to the server.
        
        Args:
            request_id (int): ID of the request for tracking
            variation (bool): If True, vary the request data slightly
        """
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        try:
            fields = self.prepare_request_data(variation)
            
            # Create multipart form data
            m = MultipartEncoder(fields=fields)
            
            # Set headers
            headers = {
                'Content-Type': m.content_type,
                'User-Agent': 'ServerTester/1.0',
                'X-Request-ID': f"test-{request_id}"
            }
            
            # Add authentication if app_password is provided
            auth = None
            if self.app_password:
                auth = (fields['email'], self.app_password)
            
            # Log request details
            self.logger.info(f"Request {request_id}: Sending request to {self.server_url}")
            self.logger.info(f"Request {request_id}: Using email: {fields['email']}")
            
            # Send the request
            response = requests.post(
                self.server_url,
                data=m,
                headers=headers,
                auth=auth,
                timeout=120  # 120 seconds timeout
            )
            end_time = time.time()
            response_time = end_time - start_time
            
            # Log response details
            self.logger.info(f"Request {request_id}: Response Status: {response.status_code}")
            self.logger.info(f"Request {request_id}: Response Time: {response_time:.2f} seconds")
            self.logger.info(f"Request {request_id}: Response Size: {len(response.content)} bytes")
            
            try:
                resp_json = response.json()
                self.logger.info(f"Request {request_id}: Response JSON: {json.dumps(resp_json, indent=2)}")
            except:
                self.logger.info(f"Request {request_id}: Response Text: {response.text[:500]}")  # Log first 500 chars
            
            # Record results to CSV
            with open(self.csv_filename, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    request_id,
                    timestamp,
                    response.status_code,
                    f"{response_time:.3f}",
                    len(response.content),
                    ""
                ])
            
            return {
                'request_id': request_id,
                'timestamp': timestamp,
                'status_code': response.status_code,
                'response_time': response_time,
                'response_size': len(response.content),
                'response': response.text[:1000]  # Store first 1000 chars only
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            error_msg = str(e)
            
            self.logger.error(f"Request {request_id}: Error sending request: {error_msg}")
            
            # Record error to CSV
            with open(self.csv_filename, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    request_id,
                    timestamp,
                    -1,
                    f"{response_time:.3f}",
                    0,
                    error_msg
                ])
            
            return {
                'request_id': request_id,
                'timestamp': timestamp,
                'status_code': -1,
                'response_time': response_time,
                'error': error_msg
            }
        finally:
            # Close the file handle
            if 'fields' in locals() and 'video' in fields:
                fields['video'][1].close()
    
    def run_sequential_test(self, num_requests=10, interval=1.0, variation=False):
        """
        Run multiple sequential requests to test the server.
        
        Args:
            num_requests (int): Number of requests to send
            interval (float): Time interval between requests in seconds
            variation (bool): If True, vary the request data slightly
        """
        self.logger.info(f"Starting sequential test with {num_requests} requests")
        self.logger.info(f"Request interval: {interval} seconds")
        self.logger.info(f"Data variation: {'Enabled' if variation else 'Disabled'}")
        
        results = []
        
        for i in range(num_requests):
            self.logger.info(f"Sending request {i+1}/{num_requests}")
            result = self.send_request(i+1, variation)
            results.append(result)
            
            # Wait before sending the next request (except for the last one)
            if i < num_requests - 1:
                time.sleep(interval)
        
        return results
    
    def run_concurrent_test(self, num_requests=10, concurrency=3, variation=False):
        """
        Run multiple concurrent requests to test the server.
        
        Args:
            num_requests (int): Total number of requests to send
            concurrency (int): Maximum number of concurrent requests
            variation (bool): If True, vary the request data slightly
        """
        self.logger.info(f"Starting concurrent test with {num_requests} requests")
        self.logger.info(f"Concurrency level: {concurrency}")
        self.logger.info(f"Data variation: {'Enabled' if variation else 'Disabled'}")
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Submit all requests
            future_to_id = {
                executor.submit(self.send_request, i+1, variation): i+1 
                for i in range(num_requests)
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_id):
                request_id = future_to_id[future]
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"Request {request_id} completed")
                except Exception as e:
                    self.logger.error(f"Request {request_id} generated an exception: {str(e)}")
        
        return results


def main():
    # Get configuration (either from command line or defaults)
    config = parse_arguments()
    
    # Create tester instance
    tester = ServerTester(
        server_url=config["server_url"],
        video_path=config["video_path"],
        user_data=config["user_data"],
        app_password=config["app_password"]
    )
    
    try:
        if config["concurrent"]:
            results = tester.run_concurrent_test(
                num_requests=config["num_requests"], 
                concurrency=config["concurrency"],
                variation=config["variation"]
            )
        else:
            results = tester.run_sequential_test(
                num_requests=config["num_requests"], 
                interval=config["interval"],
                variation=config["variation"]
            )
        
        # Note: The print_test_summary call has been removed
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user. Exiting...")
        sys.exit(1)


if __name__ == "__main__":
    main()