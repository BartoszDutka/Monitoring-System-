"""
API Debugging utilities to help diagnose HTTP API issues.
"""

import json
import time
from datetime import datetime
import os
import requests
from flask import request, Response

# Directory for storing debug logs
DEBUG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(DEBUG_DIR, exist_ok=True)

class RequestDebugger:
    """
    Class to debug and log API requests and responses.
    """
    
    @staticmethod
    def log_request(req=None, prefix="api"):
        """
        Log details of an HTTP request to help with debugging.
        
        Args:
            req: The Flask request object (defaults to current request)
            prefix: A prefix for the log filename
        
        Returns:
            str: Path to the log file
        """
        if req is None:
            req = request
            
        # Create timestamp for the log filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{prefix}_{timestamp}.log"
        filepath = os.path.join(DEBUG_DIR, filename)
        
        # Extract request information
        try:
            headers = {k: v for k, v in req.headers.items()}
            
            # Try to parse body based on content type
            if req.content_type == 'application/json':
                try:
                    body = req.get_json(silent=True) or {}
                except Exception:
                    body = "(invalid JSON)"
            else:
                try:
                    body = req.get_data(as_text=True) or "(empty)"
                except Exception:
                    body = "(binary data)"
            
            # Create log content
            log_content = {
                "timestamp": datetime.now().isoformat(),
                "method": req.method,
                "url": req.url,
                "path": req.path,
                "query_string": req.query_string.decode('utf-8'),
                "headers": headers,
                "content_type": req.content_type,
                "content_length": req.content_length,
                "body": body
            }
            
            # Write to log file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_content, f, indent=2, default=str)
            
            return filepath
            
        except Exception as e:
            # If logging fails, write a simple error message
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Error logging request: {str(e)}")
            return filepath

    @staticmethod
    def test_url(url):
        """
        Test if a URL is accessible and return detailed response information.
        
        Args:
            url: The URL to test
        
        Returns:
            dict: Detailed response information
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=10)
            elapsed = time.time() - start_time
            
            result = {
                "url": url,
                "status_code": response.status_code,
                "elapsed_seconds": elapsed,
                "content_type": response.headers.get('Content-Type'),
                "content_length": len(response.content),
                "headers": dict(response.headers),
                "redirect_history": [
                    {"url": r.url, "status_code": r.status_code}
                    for r in response.history
                ],
                "cookies": dict(response.cookies),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save a sample of the response content
            max_preview = 500  # First 500 chars
            result["content_preview"] = response.text[:max_preview] if response.text else ""
            
            # Save the full response to a file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"url_test_{timestamp}.html"
            filepath = os.path.join(DEBUG_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
                f.write(response.text)
            
            result["response_file"] = filepath
            
            return result
            
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# API endpoint for debugging
def register_debug_endpoints(app):
    """
    Register debug endpoints with a Flask app.
    
    Note: Only enable these in development environments.
    """
    
    @app.route('/api/debug/log_request', methods=['POST'])
    def debug_log_request():
        """Log the current request and return the log path"""
        filepath = RequestDebugger.log_request(prefix="debug")
        return {"status": "success", "log_file": filepath}
        
    @app.route('/api/debug/test_url', methods=['POST'])
    def debug_test_url():
        """Test if a URL is accessible"""
        data = request.json
        url = data.get('url')
        if not url:
            return {"error": "No URL provided"}, 400
            
        result = RequestDebugger.test_url(url)
        return result
