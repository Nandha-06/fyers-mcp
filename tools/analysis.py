"""
Technical Analysis tools — indicators, pivot points, VWAP, candlestick patterns, OI analysis.

Tools: get_technical_indicators, pivot_points, vwap_calculator, candlestick_patterns, oi_analysis
"""

import math
from typing import Dict, Any, List, Annotated
from pydantic import Field
from datetime import datetime, timedelta

from .core import mcp, create_response, get_fyers_client


# ============================================================================
# INDICATOR CALCULATION HELPERS (private)
# ============================================================================

def _calculate_sma(prices: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average."""
    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(None)
        else:
            avg = sum(prices[i - period + 1 : i + 1]) / period
            sma.append(round(avg, 2))
    return sma


def _calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average."""
    ema = []
    multiplier = 2 / (period + 1)

    for i in range(len(prices)):
        if i == 0:
            ema.append(prices[0])
        else:
            ema_val = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
            ema.append(round(ema_val, 2))
    return ema


def _calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(0, change))
        losses.append(max(0, -change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)


def _calculate_macd(
    prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Dict[str, Any]:
    """Calculate MACD."""
    if len(prices) < slow:
        return {"macd": 0, "signal": 0, "histogram": 0}

    ema_fast = _calculate_ema(prices, fast)
    ema_slow = _calculate_ema(prices, slow)

    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]

    if len(macd_line) < signal:
        return {"macd": 0, "signal": 0, "histogram": 0}

    signal_line = _calculate_ema(macd_line[-signal:], signal)
    macd_value = macd_line[-1]
    signal_value = signal_line[-1]
    histogram = macd_value - signal_value

    return {
        "macd": round(macd_value, 2),
        "signal": round(signal_value, 2),
        "histogram": round(histogram, 2),
    }


def _calculate_bollinger_bands(
    prices: List[float], period: int = 20, num_std: float = 2.0
) -> Dict[str, float]:
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        return {"upper": 0, "middle": 0, "lower": 0}

    recent = prices[-period:]
    middle = sum(recent) / period
    std_dev = math.sqrt(sum((x - middle) ** 2 for x in recent) / period)

    return {
        "upper": round(middle + num_std * std_dev, 2),
        "middle": round(middle, 2),
        "lower": round(middle - num_std * std_dev, 2),
    }


# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

@mcp.tool()
def get_technical_indicators(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")],
    timeframe: Annotated[str, Field(description="Resolution ('1','5','15','60','D','W')")] = "D",
    indicators: Annotated[str, Field(description="Comma-separated ('rsi,macd,sma,ema,bb') or 'all'")] = "all",
) -> str:
    """Get technical indicators for a symbol (calculated from historical data).

    Uses fyers.history() to fetch data and calculates indicators locally.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        # Fetch historical data using correct SDK parameter format
        data = {
            "symbol": symbol,
            "resolution": timeframe,
            "date_format": "0",
            "range_from": str(int((datetime.now() - timedelta(days=200)).timestamp())),
            "range_to": str(int(datetime.now().timestamp())),
            "cont_flag": "1",
        }

        hist_response = client.history(data)

        if hist_response.get("code") != 200 and hist_response.get("s") != "ok":
            return create_response(False, error="Failed to get historical data for indicators")

        candles = hist_response.get("candles", [])
        if not candles:
            return create_response(False, error="No historical data available for indicators")

        close_prices = []
        for candle in candles:
            if isinstance(candle, list) and len(candle) >= 6:
                close_prices.append(candle[4])

        if not close_prices:
            return create_response(False, error="Invalid candle data")

        requested = (
            ["rsi", "macd", "sma", "ema", "bb"]
            if indicators == "all"
            else [i.strip().lower() for i in indicators.split(",")]
        )

        result = {"symbol": symbol, "timeframe": timeframe, "indicators": {}}

        if "rsi" in requested:
            rsi_val = _calculate_rsi(close_prices, 14)
            result["indicators"]["rsi"] = {
                "value": rsi_val,
                "signal": (
                    "Overbought (>70)" if rsi_val > 70
                    else "Oversold (<30)" if rsi_val < 30
                    else "Neutral"
                ),
            }

        if "macd" in requested:
            macd_result = _calculate_macd(close_prices)
            result["indicators"]["macd"] = {
                **macd_result,
                "signal_text": "Bullish" if macd_result["histogram"] > 0 else "Bearish",
            }

        if "sma" in requested:
            sma_20 = _calculate_sma(close_prices, 20)[-1] if len(close_prices) >= 20 else None
            sma_50 = _calculate_sma(close_prices, 50)[-1] if len(close_prices) >= 50 else None
            result["indicators"]["sma"] = {
                "sma_20": sma_20,
                "sma_50": sma_50,
                "current_price": close_prices[-1],
            }

        if "ema" in requested:
            ema_12 = _calculate_ema(close_prices, 12)[-1]
            ema_26 = _calculate_ema(close_prices, 26)[-1]
            result["indicators"]["ema"] = {
                "ema_12": ema_12,
                "ema_26": ema_26,
                "current_price": close_prices[-1],
            }

        if "bb" in requested:
            bb = _calculate_bollinger_bands(close_prices)
            result["indicators"]["bollinger_bands"] = {
                **bb,
                "current_price": close_prices[-1],
            }

        return create_response(
            True, data=result, message="Technical indicators calculated successfully"
        )

    except Exception as e:
        return create_response(False, error=f"Error calculating technical indicators: {str(e)}")


# ============================================================================
# PIVOT POINTS
# ============================================================================

@mcp.tool()
def pivot_points(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")],
    pivot_type: Annotated[str, Field(description="Type: 'standard', 'fibonacci', 'woodie', or 'camarilla'")] = "standard"
) -> str:
    """Calculate pivot point support/resistance levels for a symbol.

    Uses previous day's OHLC data from fyers.history().
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        # Fetch last 5 days of daily data to get previous day candle
        data = {
            "symbol": symbol,
            "resolution": "D",
            "date_format": "0",
            "range_from": str(int((datetime.now() - timedelta(days=10)).timestamp())),
            "range_to": str(int(datetime.now().timestamp())),
            "cont_flag": "1",
        }

        response = client.history(data)

        if response.get("code") != 200 and response.get("s") != "ok":
            return create_response(False, error="Failed to get historical data for pivot calculation")

        candles = response.get("candles", [])
        if len(candles) < 2:
            return create_response(False, error="Insufficient historical data")

        # Use the second-to-last candle (previous completed day)
        prev_candle = candles[-2]
        high = prev_candle[2]
        low = prev_candle[3]
        close = prev_candle[4]
        open_price = prev_candle[1]

        pivot_type = pivot_type.lower()
        levels = {}

        if pivot_type == "standard":
            pp = (high + low + close) / 3
            levels = {
                "PP": round(pp, 2),
                "R1": round(2 * pp - low, 2),
                "R2": round(pp + (high - low), 2),
                "R3": round(high + 2 * (pp - low), 2),
                "S1": round(2 * pp - high, 2),
                "S2": round(pp - (high - low), 2),
                "S3": round(low - 2 * (high - pp), 2),
            }

        elif pivot_type == "fibonacci":
            pp = (high + low + close) / 3
            diff = high - low
            levels = {
                "PP": round(pp, 2),
                "R1": round(pp + 0.382 * diff, 2),
                "R2": round(pp + 0.618 * diff, 2),
                "R3": round(pp + 1.0 * diff, 2),
                "S1": round(pp - 0.382 * diff, 2),
                "S2": round(pp - 0.618 * diff, 2),
                "S3": round(pp - 1.0 * diff, 2),
            }

        elif pivot_type == "woodie":
            pp = (high + low + 2 * close) / 4
            levels = {
                "PP": round(pp, 2),
                "R1": round(2 * pp - low, 2),
                "R2": round(pp + (high - low), 2),
                "S1": round(2 * pp - high, 2),
                "S2": round(pp - (high - low), 2),
            }

        elif pivot_type == "camarilla":
            diff = high - low
            levels = {
                "PP": round((high + low + close) / 3, 2),
                "R1": round(close + diff * 1.1 / 12, 2),
                "R2": round(close + diff * 1.1 / 6, 2),
                "R3": round(close + diff * 1.1 / 4, 2),
                "R4": round(close + diff * 1.1 / 2, 2),
                "S1": round(close - diff * 1.1 / 12, 2),
                "S2": round(close - diff * 1.1 / 6, 2),
                "S3": round(close - diff * 1.1 / 4, 2),
                "S4": round(close - diff * 1.1 / 2, 2),
            }
        else:
            return create_response(False, error="Invalid pivot type. Use: standard, fibonacci, woodie, camarilla")

        return create_response(
            True,
            data={
                "symbol": symbol,
                "pivot_type": pivot_type,
                "previous_day": {
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                },
                "levels": levels,
            },
            message=f"{pivot_type.title()} pivot points calculated successfully",
        )

    except Exception as e:
        return create_response(False, error=f"Error calculating pivot points: {str(e)}")


# ============================================================================
# VWAP CALCULATOR
# ============================================================================

@mcp.tool()
def vwap_calculator(symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")]) -> str:
    """Calculate today's VWAP (Volume Weighted Average Price) for a symbol.

    Uses fyers.history() with 1-minute intraday data.
    VWAP = cumulative(price * volume) / cumulative(volume)
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        now = datetime.now()

        data = {
            "symbol": symbol,
            "resolution": "1",
            "date_format": "0",
            "range_from": str(int(today.timestamp())),
            "range_to": str(int(now.timestamp())),
            "cont_flag": "1",
        }

        response = client.history(data)

        if response.get("code") != 200 and response.get("s") != "ok":
            return create_response(False, error="Failed to get intraday data for VWAP")

        candles = response.get("candles", [])
        if not candles:
            return create_response(False, error="No intraday data available (market may be closed)")

        cumulative_tp_vol = 0
        cumulative_vol = 0
        vwap_series = []

        for candle in candles:
            if isinstance(candle, list) and len(candle) >= 6:
                typical_price = (candle[2] + candle[3] + candle[4]) / 3  # (H+L+C)/3
                volume = candle[5]

                cumulative_tp_vol += typical_price * volume
                cumulative_vol += volume

                if cumulative_vol > 0:
                    vwap = cumulative_tp_vol / cumulative_vol
                    vwap_series.append(round(vwap, 2))

        if not vwap_series:
            return create_response(False, error="Could not calculate VWAP")

        current_vwap = vwap_series[-1]
        current_price = candles[-1][4]

        # Standard deviation for bands
        squared_diffs = []
        for candle in candles:
            if isinstance(candle, list) and len(candle) >= 6:
                tp = (candle[2] + candle[3] + candle[4]) / 3
                squared_diffs.append((tp - current_vwap) ** 2)

        std_dev = math.sqrt(sum(squared_diffs) / len(squared_diffs)) if squared_diffs else 0

        return create_response(
            True,
            data={
                "symbol": symbol,
                "vwap": current_vwap,
                "current_price": current_price,
                "position": "Above VWAP (Bullish)" if current_price > current_vwap else "Below VWAP (Bearish)",
                "upper_band_1sd": round(current_vwap + std_dev, 2),
                "lower_band_1sd": round(current_vwap - std_dev, 2),
                "upper_band_2sd": round(current_vwap + 2 * std_dev, 2),
                "lower_band_2sd": round(current_vwap - 2 * std_dev, 2),
                "total_volume": int(cumulative_vol),
                "data_points": len(candles),
            },
            message="VWAP calculated successfully",
        )

    except Exception as e:
        return create_response(False, error=f"Error calculating VWAP: {str(e)}")


# ============================================================================
# CANDLESTICK PATTERN RECOGNITION
# ============================================================================

@mcp.tool()
def candlestick_patterns(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")],
    timeframe: Annotated[str, Field(description="Resolution ('D', '60', '15', etc.)")] = "D"
) -> str:
    """Detect candlestick patterns on recent price data.

    Uses fyers.history() and identifies: Doji, Hammer, Inverted Hammer,
    Bullish/Bearish Engulfing, Morning/Evening Star, Three White Soldiers,
    Three Black Crows, Shooting Star.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        data = {
            "symbol": symbol,
            "resolution": timeframe,
            "date_format": "0",
            "range_from": str(int((datetime.now() - timedelta(days=30)).timestamp())),
            "range_to": str(int(datetime.now().timestamp())),
            "cont_flag": "1",
        }

        response = client.history(data)

        if response.get("code") != 200 and response.get("s") != "ok":
            return create_response(False, error="Failed to get historical data")

        candles = response.get("candles", [])
        if len(candles) < 3:
            return create_response(False, error="Insufficient data for pattern detection")

        patterns_found = []

        for i in range(len(candles)):
            c = candles[i]
            if not isinstance(c, list) or len(c) < 6:
                continue

            o, h, l, cl = c[1], c[2], c[3], c[4]
            body = abs(cl - o)
            full_range = h - l if h - l > 0 else 0.01
            upper_shadow = h - max(o, cl)
            lower_shadow = min(o, cl) - l
            is_bullish = cl > o
            body_ratio = body / full_range

            ts = c[0]

            # Doji: very small body
            if body_ratio < 0.1 and full_range > 0:
                patterns_found.append({"pattern": "Doji", "datetime": ts, "signal": "Reversal/Indecision", "type": "neutral"})

            # Hammer: small body at top, long lower shadow
            if lower_shadow > 2 * body and upper_shadow < body * 0.5 and body > 0:
                patterns_found.append({"pattern": "Hammer", "datetime": ts, "signal": "Bullish reversal", "type": "bullish"})

            # Shooting Star: small body at bottom, long upper shadow
            if upper_shadow > 2 * body and lower_shadow < body * 0.5 and body > 0:
                patterns_found.append({"pattern": "Shooting Star", "datetime": ts, "signal": "Bearish reversal", "type": "bearish"})

            # Inverted Hammer
            if upper_shadow > 2 * body and lower_shadow < body * 0.3 and is_bullish and body > 0:
                if i > 0 and candles[i-1][4] < candles[i-1][1]:  # previous was bearish
                    patterns_found.append({"pattern": "Inverted Hammer", "datetime": ts, "signal": "Potential bullish reversal", "type": "bullish"})

            # Engulfing patterns (need previous candle)
            if i > 0:
                prev = candles[i - 1]
                po, ph, pl_prev, pcl = prev[1], prev[2], prev[3], prev[4]
                prev_body = abs(pcl - po)

                # Bullish Engulfing
                if is_bullish and pcl < po and body > prev_body and o <= pcl and cl >= po:
                    patterns_found.append({"pattern": "Bullish Engulfing", "datetime": ts, "signal": "Strong bullish reversal", "type": "bullish"})

                # Bearish Engulfing
                if not is_bullish and pcl > po and body > prev_body and o >= pcl and cl <= po:
                    patterns_found.append({"pattern": "Bearish Engulfing", "datetime": ts, "signal": "Strong bearish reversal", "type": "bearish"})

            # Three White Soldiers / Three Black Crows (need 2 previous candles)
            if i >= 2:
                c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
                if all(isinstance(x, list) and len(x) >= 6 for x in [c1, c2, c3]):
                    # Three White Soldiers
                    if (c1[4] > c1[1] and c2[4] > c2[1] and c3[4] > c3[1] and
                        c2[4] > c1[4] and c3[4] > c2[4] and
                        c2[1] > c1[1] and c3[1] > c2[1]):
                        patterns_found.append({"pattern": "Three White Soldiers", "datetime": ts, "signal": "Strong bullish continuation", "type": "bullish"})

                    # Three Black Crows
                    if (c1[4] < c1[1] and c2[4] < c2[1] and c3[4] < c3[1] and
                        c2[4] < c1[4] and c3[4] < c2[4] and
                        c2[1] < c1[1] and c3[1] < c2[1]):
                        patterns_found.append({"pattern": "Three Black Crows", "datetime": ts, "signal": "Strong bearish continuation", "type": "bearish"})

        # Return only the last 10 patterns found
        recent_patterns = patterns_found[-10:]

        return create_response(
            True,
            data={
                "symbol": symbol,
                "timeframe": timeframe,
                "patterns": recent_patterns,
                "total_detected": len(patterns_found),
                "candles_analyzed": len(candles),
            },
            message=f"Detected {len(patterns_found)} candlestick patterns",
        )

    except Exception as e:
        return create_response(False, error=f"Error detecting candlestick patterns: {str(e)}")


# ============================================================================
# OPEN INTEREST ANALYSIS
# ============================================================================

@mcp.tool()
def oi_analysis(
    symbol: Annotated[str, Field(description="Index/stock symbol (e.g. 'NSE:NIFTY50-INDEX')")],
    strike_count: Annotated[int, Field(description="Number of strikes around ATM")] = 10
) -> str:
    """Analyze Open Interest data from the option chain.

    Uses fyers.optionchain() to calculate PCR ratio, max pain, and
    OI concentration at each strike.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        data = {"symbol": symbol, "strikecount": strike_count}
        response = client.optionchain(data)

        if response.get("code") != 200:
            return create_response(False, error=f"Failed to get option chain: {response}")

        oc_data = response.get("data", {})

        if not oc_data:
            return create_response(False, error="No option chain data available")

        # Parse option chain strikes
        options_list = oc_data if isinstance(oc_data, list) else oc_data.get("optionsChain", [])

        total_call_oi = 0
        total_put_oi = 0
        total_call_volume = 0
        total_put_volume = 0
        call_oi_by_strike = {}
        put_oi_by_strike = {}

        for opt in options_list:
            if not isinstance(opt, dict):
                continue

            strike = opt.get("strikePrice", opt.get("strike_price", 0))
            option_type = opt.get("option_type", opt.get("optionType", ""))
            oi = opt.get("oi", opt.get("openInterest", 0))
            volume = opt.get("volume", 0)
            ltp = opt.get("ltp", 0)
            change_oi = opt.get("oiChange", opt.get("change_oi", 0))

            if option_type in ["CE", "CALL", "call"]:
                total_call_oi += oi
                total_call_volume += volume
                call_oi_by_strike[strike] = {"oi": oi, "volume": volume, "ltp": ltp, "change_oi": change_oi}
            elif option_type in ["PE", "PUT", "put"]:
                total_put_oi += oi
                total_put_volume += volume
                put_oi_by_strike[strike] = {"oi": oi, "volume": volume, "ltp": ltp, "change_oi": change_oi}

        # PCR (Put-Call Ratio)
        pcr_oi = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0
        pcr_vol = round(total_put_volume / total_call_volume, 2) if total_call_volume > 0 else 0

        # Max Pain calculation
        all_strikes = sorted(set(list(call_oi_by_strike.keys()) + list(put_oi_by_strike.keys())))
        max_pain_strike = 0
        min_pain_value = float("inf")

        for strike in all_strikes:
            pain = 0
            for s in all_strikes:
                call_oi = call_oi_by_strike.get(s, {}).get("oi", 0)
                put_oi = put_oi_by_strike.get(s, {}).get("oi", 0)

                if s > strike:
                    pain += call_oi * (s - strike)
                elif s < strike:
                    pain += put_oi * (strike - s)

            if pain < min_pain_value:
                min_pain_value = pain
                max_pain_strike = strike

        # Top OI concentrations
        top_call_oi = sorted(call_oi_by_strike.items(), key=lambda x: x[1]["oi"], reverse=True)[:5]
        top_put_oi = sorted(put_oi_by_strike.items(), key=lambda x: x[1]["oi"], reverse=True)[:5]

        # Market sentiment
        if pcr_oi > 1.2:
            sentiment = "Bullish (High PCR — more put writing)"
        elif pcr_oi < 0.8:
            sentiment = "Bearish (Low PCR — more call writing)"
        else:
            sentiment = "Neutral"

        return create_response(
            True,
            data={
                "symbol": symbol,
                "pcr_oi": pcr_oi,
                "pcr_volume": pcr_vol,
                "max_pain": max_pain_strike,
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "sentiment": sentiment,
                "top_call_oi_strikes": [
                    {"strike": s, **d} for s, d in top_call_oi
                ],
                "top_put_oi_strikes": [
                    {"strike": s, **d} for s, d in top_put_oi
                ],
            },
            message="OI analysis completed successfully",
        )

    except Exception as e:
        return create_response(False, error=f"Error analyzing open interest: {str(e)}")
