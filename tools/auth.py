"""
Authentication & Profile tools.

Tools: authenticate, check_auth_status, get_profile, logout
"""

import os
import time
import threading
from typing import Annotated

from .core import (
    mcp,
    create_response,
    get_fyers_client,
    load_env_file,
    start_auth_server,
    get_env_path,
)
import tools.core as _core  # for mutating module-level globals


# ============================================================================
# AUTHENTICATION & PROFILE
# ============================================================================

@mcp.tool()
def authenticate() -> str:
    """OAuth authentication - opens browser and captures redirect."""
    import webbrowser

    client_id = os.getenv("FYERS_CLIENT_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    redirect_uri = "http://127.0.0.1:8080/"

    if not client_id or not secret_key:
        return create_response(
            False, error="Missing FYERS_CLIENT_ID or FYERS_SECRET_KEY"
        )

    _core.auth_result = {}
    auth_url = f"https://api-t1.fyers.in/api/v3/generate-authcode?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&state=sample_state"

    try:
        server_thread = threading.Thread(target=start_auth_server, daemon=True)
        server_thread.start()
        time.sleep(1)
        webbrowser.open(auth_url)

        for _ in range(60):
            if _core.auth_result:
                break
            time.sleep(1)

        if not _core.auth_result:
            return create_response(False, error="Authentication timeout")

        if _core.auth_result.get("status") != "success":
            return create_response(False, error=f"Auth failed: {_core.auth_result.get('error')}")

        auth_code = _core.auth_result["auth_code"]

        from fyers_apiv3 import fyersModel

        session = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            grant_type="authorization_code",
        )

        session.set_token(auth_code)
        response = session.generate_token()

        if response.get("code") == 200:
            access_token = response["access_token"]
            env_path = get_env_path()

            env_lines = []
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    env_lines = f.readlines()

            token_found = False
            for i, line in enumerate(env_lines):
                if line.startswith("FYERS_ACCESS_TOKEN="):
                    env_lines[i] = f"FYERS_ACCESS_TOKEN={access_token}\n"
                    token_found = True
                    break

            if not token_found:
                if env_lines and not env_lines[-1].endswith("\n"):
                    env_lines[-1] += "\n"
                env_lines.append(f"FYERS_ACCESS_TOKEN={access_token}\n")

            with open(env_path, "w") as f:
                f.writelines(env_lines)

            os.environ["FYERS_ACCESS_TOKEN"] = access_token
            _core.fyers_client = None

            return create_response(True, message="Authentication successful!")
        else:
            return create_response(False, error=f"Token generation failed: {response}")

    except Exception as e:
        return create_response(False, error=f"Authentication error: {str(e)}")


@mcp.tool()
def check_auth_status() -> str:
    """Check current authentication status."""
    access_token = os.getenv("FYERS_ACCESS_TOKEN")

    if access_token:
        try:
            client = get_fyers_client()
            if client:
                response = client.get_profile()
                if response.get("code") == 200:
                    name = response["data"].get("name", "User")
                    return create_response(True, data={"name": name}, message=f"Authenticated as: {name}")
                else:
                    return create_response(False, error="Token expired or invalid")
            else:
                return create_response(False, error="Client initialization failed")
        except Exception as e:
            return create_response(False, error=f"Auth check failed: {str(e)}")
    else:
        return create_response(False, error="Not authenticated. Use 'authenticate' tool.")


@mcp.tool()
def get_profile() -> str:
    """Get user profile information using fyers.get_profile()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.get_profile()

        if response.get("code") == 200:
            data = response["data"]
            return create_response(
                True,
                data={
                    "name": data.get("name", "N/A"),
                    "email": data.get("email_id", "N/A"),
                    "mobile": data.get("mobile_number", "N/A"),
                    "client_id": data.get("fy_id", "N/A"),
                },
                message="Profile retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get profile: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting profile: {str(e)}")


@mcp.tool()
def logout() -> str:
    """Invalidate the current access token using fyers.logout()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.logout()

        if response.get("code") == 200:
            _core.fyers_client = None
            return create_response(True, message="Logged out successfully")
        else:
            return create_response(False, error=f"Logout failed: {response}")

    except Exception as e:
        return create_response(False, error=f"Error during logout: {str(e)}")
