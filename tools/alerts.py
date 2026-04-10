"""
Alerts & Notifications tools (Server-synced Price Alerts via REST API).

Tools: get_price_alerts, create_price_alert, delete_price_alert
"""

import os
from typing import Dict, Optional, Annotated
from pydantic import Field

import requests

from .core import mcp, create_response


def _get_api_headers() -> Optional[Dict[str, str]]:
    """Helper to get REST API headers bypassing SDK."""
    token = os.environ.get("FYERS_ACCESS_TOKEN")
    client_id = os.environ.get("FYERS_CLIENT_ID")
    if not token or not client_id:
        return None
    return {
        "Authorization": f"{client_id}:{token}",
        "Content-Type": "application/json"
    }


@mcp.tool()
def get_price_alerts() -> str:
    """Get all active price alerts directly from Fyers Server."""
    headers = _get_api_headers()
    if not headers:
        return create_response(False, error="Not authenticated via .env tokens")

    try:
        res = requests.get("https://api-t1.fyers.in/api/v3/price-alert", headers=headers, timeout=10)
        data = res.json()
        if data.get("code") == 200:
            return create_response(True, data=data.get("data", {}), message="Alerts retrieved successfully")
        return create_response(False, error=f"Failed to get alerts: {data}")
    except Exception as e:
        return create_response(False, error=f"Error retrieving alerts: {str(e)}")


@mcp.tool()
def create_price_alert(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")],
    comparison_type: Annotated[str, Field(description="Comparison type (e.g. 'LTP')")],
    condition: Annotated[str, Field(description="Condition (e.g. 'GT', 'LT')")],
    value: Annotated[str, Field(description="Target price point (e.g. '600')")],
    name: Annotated[str, Field(description="Name of the alert")] = "custom alert"
) -> str:
    """Create a new price alert on the Fyers Server."""
    headers = _get_api_headers()
    if not headers:
        return create_response(False, error="Not authenticated")

    payload = {
        "agent": "fyers-api",
        "alert-type": 1,
        "name": name,
        "symbol": symbol,
        "comparisonType": comparison_type,
        "condition": condition,
        "value": value,
    }

    try:
        res = requests.post("https://api-t1.fyers.in/api/v3/price-alert", headers=headers, json=payload, timeout=10)
        data = res.json()
        if data.get("code") == 200 or data.get("s") == "ok":
            return create_response(True, data=data, message=f"Alert created for {symbol}")
        return create_response(False, error=f"Failed to create alert: {data}")
    except Exception as e:
        return create_response(False, error=str(e))


@mcp.tool()
def delete_price_alert(alert_id: Annotated[str, Field(description="The unique alert ID to delete")]) -> str:
    """Delete an existing price alert from the Fyers Server."""
    headers = _get_api_headers()
    if not headers:
        return create_response(False, error="Not authenticated")

    payload = {"alertId": str(alert_id)}

    try:
        res = requests.delete("https://api-t1.fyers.in/api/v3/price-alert", headers=headers, json=payload, timeout=10)
        data = res.json()
        if data.get("code") == 200 or data.get("s") == "ok":
            return create_response(True, data=data, message=f"Alert {alert_id} deleted")
        return create_response(False, error=f"Failed to delete alert: {data}")
    except Exception as e:
        return create_response(False, error=str(e))
