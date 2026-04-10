"""
Core module — shared MCP instance, Fyers client, response helper, OAuth handler.

Every other tool module imports `mcp`, `get_fyers_client`, and `create_response`
from here so that there is exactly ONE MCP server and ONE client factory.
"""

import os
import sys
import io
import json
import logging
import urllib.parse
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional
from datetime import datetime

# Force UTF-8 stdout/stderr for Windows MCP transport
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Silence all logging
logging.disable(logging.CRITICAL)
import warnings

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------

def load_env_file():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")


load_env_file()


# ---------------------------------------------------------------------------
# MCP Server instance (single source of truth)
# ---------------------------------------------------------------------------

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("fyers-mcp-v7")
except ImportError:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "mcp"])
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("fyers-mcp-v7")


# ---------------------------------------------------------------------------
# Shared response helper
# ---------------------------------------------------------------------------

def create_response(
    success: bool, data: Any = None, message: str = "", error: str = None
) -> str:
    """Create JSON response."""
    response = {
        "success": success,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    if error:
        response["error"] = error

    return json.dumps(response)


# ---------------------------------------------------------------------------
# Global Fyers client
# ---------------------------------------------------------------------------

auth_result = {}
auth_server = None
fyers_client = None


class OAuthHandler(BaseHTTPRequestHandler):
    """Handle OAuth redirect from Fyers."""

    def do_GET(self):
        global auth_result

        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        auth_code = (
            query_params.get("auth_code", [None])[0]
            or query_params.get("code", [None])[0]
        )

        if auth_code:
            auth_result["auth_code"] = auth_code
            auth_result["status"] = "success"

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html><body>
            <h2>Authentication Successful!</h2>
            <p>You can close this browser window.</p>
            </body></html>
            """)
        else:
            auth_result["status"] = "error"
            auth_result["error"] = "No auth code received"

            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html><body>
            <h2>Authentication Failed</h2>
            </body></html>
            """)

    def log_message(self, format, *args):
        pass


def start_auth_server():
    """Start local server to capture OAuth redirect."""
    global auth_server

    try:
        auth_server = HTTPServer(("127.0.0.1", 8080), OAuthHandler)
        auth_server.timeout = 60
        auth_server.handle_request()
    except Exception as e:
        print(f"Server error: {e}")


def get_fyers_client():
    """Initialize and return Fyers client."""
    global fyers_client
    try:
        load_env_file()

        from fyers_apiv3 import fyersModel
        import tempfile

        client_id = os.getenv("FYERS_CLIENT_ID")
        access_token = os.getenv("FYERS_ACCESS_TOKEN")

        if not client_id or not access_token:
            return None

        current_token = fyers_client.token if fyers_client else None
        if fyers_client is None or current_token != access_token:
            log_dir = tempfile.gettempdir() + os.sep
            fyers_client = fyersModel.FyersModel(
                client_id=client_id,
                is_async=False,
                token=access_token,
                log_path=log_dir,
            )

    except Exception as e:
        print(f"Error initializing Fyers client: {e}")
        return None

    return fyers_client


def get_env_path() -> str:
    """Return path to the project .env file."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
