"""
Watchlist Management tools (Local JSON Store synced with Live Prices).

Tools: get_watchlists, get_watchlists_by_id, create_watchlist,
       add_symbols_to_watchlist, remove_symbols_from_watchlist, delete_watchlist
"""

import os
import json
import uuid
from typing import Dict, Any, Annotated
from pydantic import Field
from datetime import datetime

from .core import mcp, create_response, get_fyers_client

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "watchlists.json")


def _load_watchlists() -> Dict[str, Any]:
    if not os.path.exists(WATCHLIST_FILE):
        return {}
    try:
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_watchlists(data: Dict[str, Any]) -> bool:
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving watchlists: {e}")
        return False


@mcp.tool()
def get_watchlists() -> str:
    """Get all user watchlists (local storage)."""
    db = _load_watchlists()

    summary = []
    for wid, data in db.items():
        summary.append({
            "id": wid,
            "name": data.get("name", "Unnamed"),
            "symbol_count": len(data.get("symbols", []))
        })

    return create_response(True, data={"watchlists": summary, "count": len(summary)}, message="Watchlists retrieved")


@mcp.tool()
def get_watchlists_by_id(watchlist_id: Annotated[str, Field(description="ID of the watchlist to retrieve")]) -> str:
    """Get detailed info about a specific watchlist, including live market data."""
    db = _load_watchlists()
    if watchlist_id not in db:
        return create_response(False, error=f"Watchlist {watchlist_id} not found")

    wl = db[watchlist_id]
    symbols = wl.get("symbols", [])

    if not symbols:
        return create_response(True, data=wl, message="Watchlist is empty")

    # Fetch live quotes
    try:
        client = get_fyers_client()
        if client:
            sym_str = ",".join(symbols[:50])  # Fyers quotes API limit is typically 50
            quote_resp = client.quotes({"symbols": sym_str})
            if quote_resp.get("code") == 200:
                quotes_data = quote_resp.get("d", [])
                live_data = []
                for item in quotes_data:
                    v = item.get("v", {})
                    live_data.append({
                        "symbol": item.get("n", ""),
                        "ltp": v.get("lp", 0),
                        "change": v.get("ch", 0),
                        "change_percent": v.get("chp", 0),
                        "high": v.get("high_price", 0),
                        "low": v.get("low_price", 0)
                    })
                wl["live_data"] = live_data
    except Exception as e:
        wl["live_data_error"] = str(e)

    return create_response(True, data=wl, message="Watchlist details retrieved")


@mcp.tool()
def create_watchlist(
    name: Annotated[str, Field(description="Name of the watchlist")],
    symbols: Annotated[str, Field(description="Comma-separated list of symbols (optional)")] = ""
) -> str:
    """Create a new local watchlist."""
    db = _load_watchlists()
    wid = str(uuid.uuid4())[:8]

    sym_list = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else []

    db[wid] = {
        "id": wid,
        "name": name,
        "symbols": sym_list,
        "created_at": datetime.now().isoformat()
    }

    if _save_watchlists(db):
        return create_response(True, data=db[wid], message=f"Watchlist '{name}' created")
    return create_response(False, error="Failed to save watchlist")


@mcp.tool()
def add_symbols_to_watchlist(
    watchlist_id: Annotated[str, Field(description="ID of the watchlist")],
    symbols: Annotated[str, Field(description="Comma-separated symbols to add")]
) -> str:
    """Add symbols to an existing local watchlist."""
    db = _load_watchlists()
    if watchlist_id not in db:
        return create_response(False, error=f"Watchlist {watchlist_id} not found")

    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    existing = set(db[watchlist_id].get("symbols", []))

    for s in sym_list:
        if s not in existing:
            db[watchlist_id].setdefault("symbols", []).append(s)

    if _save_watchlists(db):
        return create_response(True, data=db[watchlist_id], message="Symbols added to watchlist")
    return create_response(False, error="Failed to update watchlist")


@mcp.tool()
def remove_symbols_from_watchlist(
    watchlist_id: Annotated[str, Field(description="ID of the watchlist")],
    symbols: Annotated[str, Field(description="Comma-separated symbols to remove")]
) -> str:
    """Remove symbols from a local watchlist."""
    db = _load_watchlists()
    if watchlist_id not in db:
        return create_response(False, error=f"Watchlist {watchlist_id} not found")

    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]

    db[watchlist_id]["symbols"] = [s for s in db[watchlist_id].get("symbols", []) if s not in sym_list]

    if _save_watchlists(db):
        return create_response(True, data=db[watchlist_id], message="Symbols removed from watchlist")
    return create_response(False, error="Failed to update watchlist")


@mcp.tool()
def delete_watchlist(watchlist_id: Annotated[str, Field(description="ID of the local watchlist to delete")]) -> str:
    """Delete an existing local watchlist."""
    db = _load_watchlists()
    if watchlist_id not in db:
        return create_response(False, error=f"Watchlist {watchlist_id} not found")

    del db[watchlist_id]

    if _save_watchlists(db):
        return create_response(True, message=f"Watchlist {watchlist_id} deleted")
    return create_response(False, error="Failed to delete watchlist")
