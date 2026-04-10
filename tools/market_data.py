"""
Market Data tools.

Tools: get_quotes, get_market_depth, get_historical_prices, get_market_status, get_option_chain
"""

from typing import Annotated
from pydantic import Field
from datetime import datetime, timedelta

from .core import mcp, create_response, get_fyers_client


# ============================================================================
# MARKET DATA
# ============================================================================

@mcp.tool()
def get_quotes(symbols: Annotated[str, Field(description="Comma-separated symbols (e.g. 'NSE:SBIN-EQ,NSE:RELIANCE-EQ'). Max 50.")]) -> str:
    """Get live quotes for symbols using fyers.quotes()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        # Per SDK docs: symbols is a comma-separated STRING, not a list
        data = {"symbols": symbols.strip()}

        response = client.quotes(data)

        if response.get("code") == 200:
            quotes_data = response.get("d", [])
            quotes_list = []
            if isinstance(quotes_data, list):
                for item in quotes_data:
                    symbol_name = item.get("n", "Unknown")
                    v = item.get("v", {})
                    quotes_list.append({
                        "symbol": symbol_name,
                        "ltp": v.get("lp", 0),
                        "open": v.get("open_price", 0),
                        "high": v.get("high_price", 0),
                        "low": v.get("low_price", 0),
                        "close": v.get("prev_close_price", 0),
                        "change": v.get("ch", 0),
                        "change_percent": v.get("chp", 0),
                        "volume": v.get("volume", 0),
                        "short_name": v.get("short_name", ""),
                        "description": v.get("description", ""),
                    })

            return create_response(
                True,
                data={"quotes": quotes_list},
                message="Quotes retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get quotes: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting quotes: {str(e)}")


@mcp.tool()
def get_market_depth(symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")]) -> str:
    """Get market depth (Level 2 order book) for a symbol using fyers.depth()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        # Per SDK docs: depth() takes symbol (string) and ohlcv_flag
        data = {"symbol": symbol, "ohlcv_flag": "1"}

        response = client.depth(data)

        if response.get("code") == 200:
            depth_data = response.get("d", {})

            # depth response for single symbol
            if isinstance(depth_data, dict):
                depth_info = depth_data
            elif isinstance(depth_data, list) and len(depth_data) > 0:
                depth_info = depth_data[0].get("v", {}) if isinstance(depth_data[0], dict) else {}
            else:
                return create_response(False, error="No depth data available")

            return create_response(
                True,
                data={
                    "symbol": symbol,
                    "depth": depth_info,
                },
                message="Market depth retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get market depth: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting market depth: {str(e)}")


@mcp.tool()
def get_historical_prices(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")],
    timeframe: Annotated[str, Field(description="Resolution ('1','2','3','5','10','15','20','30','60','120','240','D','1D')")] = "D",
    start_date: Annotated[str, Field(description="Start date 'YYYY-MM-DD' (optional)")] = "",
    end_date: Annotated[str, Field(description="End date 'YYYY-MM-DD' (optional)")] = "",
    num_bars: Annotated[int, Field(description="Number of bars if dates not specified")] = 365,
) -> str:
    """Get historical price data (OHLCV) for a symbol using fyers.history()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        # Normalize resolution values
        resolution_map = {
            "1D": "D",
            "1W": "W",
        }
        resolution = resolution_map.get(timeframe, timeframe)

        if not end_date:
            end_dt = datetime.now()
        else:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        if not start_date:
            if timeframe in ["1", "2", "3", "5", "10", "15", "20", "30"]:
                delta_minutes = num_bars * int(timeframe)
                start_dt = end_dt - timedelta(minutes=delta_minutes)
            elif timeframe in ["60", "120", "240"]:
                delta_hours = num_bars * (int(timeframe) // 60)
                start_dt = end_dt - timedelta(hours=delta_hours)
            else:
                start_dt = end_dt - timedelta(days=num_bars)
        else:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")

        # Per SDK docs: date_format "0" = epoch, "1" = yyyy-mm-dd
        # Using epoch format (date_format "0")
        data = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "0",
            "range_from": str(int(start_dt.timestamp())),
            "range_to": str(int(end_dt.timestamp())),
            "cont_flag": "1",
        }

        response = client.history(data)

        if response.get("code") == 200 or response.get("s") == "ok":
            candles = response.get("candles", [])

            if not candles:
                return create_response(
                    True,
                    data={"candles": [], "symbol": symbol, "timeframe": timeframe},
                    message="No historical data found",
                )

            parsed_candles = []
            for candle in candles:
                if isinstance(candle, list) and len(candle) >= 6:
                    parsed_candles.append({
                        "datetime": candle[0],
                        "open": candle[1],
                        "high": candle[2],
                        "low": candle[3],
                        "close": candle[4],
                        "volume": candle[5],
                    })

            return create_response(
                True,
                data={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candles": parsed_candles,
                    "total_candles": len(parsed_candles),
                    "start_date": start_dt.strftime("%Y-%m-%d"),
                    "end_date": end_dt.strftime("%Y-%m-%d"),
                },
                message="Historical data retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get historical data: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting historical data: {str(e)}")


@mcp.tool()
def get_market_status() -> str:
    """Get current market status using fyers.market_status()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.market_status()

        if response.get("code") == 200:
            return create_response(
                True,
                data=response.get("d", response.get("data", {})),
                message="Market status retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get market status: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting market status: {str(e)}")


@mcp.tool()
def get_option_chain(
    symbol: Annotated[str, Field(description="Index/stock symbol (e.g. 'NSE:NIFTY50-INDEX', 'NSE:SBIN-EQ')")],
    strike_count: Annotated[int, Field(description="Number of strikes around ATM (default: 5)")] = 5,
    timestamp: Annotated[int, Field(description="Expiry timestamp, 0 for current (default: 0)")] = 0,
) -> str:
    """Get option chain data for a symbol using fyers.optionchain()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        data = {
            "symbol": symbol,
            "strikecount": strike_count,
        }
        if timestamp > 0:
            data["timestamp"] = timestamp

        response = client.optionchain(data)

        if response.get("code") == 200:
            return create_response(
                True,
                data=response.get("data", {}),
                message="Option chain retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get option chain: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting option chain: {str(e)}")
