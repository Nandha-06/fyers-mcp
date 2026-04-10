"""
Utility tools — symbol search, portfolio summary, position sizer, stock comparison, mutual funds.

Tools: symbol_search, portfolio_summary, position_sizer, compare_stocks, get_mutual_fund_holdings
"""

from typing import Annotated
from pydantic import Field
from datetime import datetime, timedelta

from .core import mcp, create_response, get_fyers_client
from .analysis import _calculate_rsi, _calculate_sma


# ============================================================================
# SYMBOL SEARCH (Public Fyers Symbol Master CSV)
# ============================================================================

@mcp.tool()
def symbol_search(
    query: Annotated[str, Field(description="Company name or keyword (e.g., 'Reliance', 'SBIN')")],
    exchange: Annotated[str, Field(description="Exchange: 'NSE_CM', 'NSE_FO', 'BSE_CM', 'BSE_FO', 'MCX_COM', 'ALL'")] = "NSE_CM"
) -> str:
    """Search for trading symbols by company name or keyword.

    Downloads the public Fyers symbol master CSV and searches it.
    No authentication required.
    """
    try:
        import urllib.request

        exchanges = ["NSE_CM", "NSE_FO", "BSE_CM", "MCX_COM"] if exchange.upper() == "ALL" else [exchange.upper()]
        all_results = []

        for exch in exchanges:
            try:
                url = f"https://public.fyers.in/sym_details/{exch}.csv"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                resp = urllib.request.urlopen(req, timeout=10)
                data = resp.read().decode("utf-8")
                lines = data.strip().split("\n")

                query_upper = query.upper()
                for line in lines:
                    cols = line.split(",")
                    if len(cols) < 15:
                        continue

                    full_name = cols[1].upper() if len(cols) > 1 else ""
                    symbol = cols[9] if len(cols) > 9 else ""
                    short_name = cols[14] if len(cols) > 14 else ""

                    if query_upper in full_name or query_upper in symbol.upper() or query_upper in short_name.upper():
                        all_results.append({
                            "symbol": symbol,
                            "name": cols[1],
                            "short_name": short_name,
                            "isin": cols[5] if len(cols) > 5 else "",
                            "lot_size": cols[11] if len(cols) > 11 else "",
                            "tick_size": cols[4] if len(cols) > 4 else "",
                            "exchange": exch,
                        })
            except Exception:
                continue

        if not all_results:
            return create_response(True, data={"results": [], "count": 0}, message=f"No symbols found for '{query}'")

        # Limit to top 25 results
        all_results = all_results[:25]

        return create_response(
            True,
            data={"results": all_results, "count": len(all_results), "query": query},
            message=f"Found {len(all_results)} symbols matching '{query}'",
        )

    except Exception as e:
        return create_response(False, error=f"Error searching symbols: {str(e)}")


# ============================================================================
# PORTFOLIO SUMMARY (Composite: funds + holdings + positions)
# ============================================================================

@mcp.tool()
def portfolio_summary() -> str:
    """Get a comprehensive portfolio summary combining funds, holdings, and positions.

    Uses fyers.funds(), fyers.holdings(), and fyers.positions() to build
    a single consolidated view of the entire account.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        summary = {}

        # Funds
        try:
            funds_resp = client.funds()
            if funds_resp.get("code") == 200:
                summary["funds"] = funds_resp.get("fund_limit", [])
        except Exception:
            summary["funds"] = "Error fetching funds"

        # Holdings
        try:
            holdings_resp = client.holdings()
            if holdings_resp.get("code") == 200:
                holdings = holdings_resp.get("holdings", [])
                overall = holdings_resp.get("overall", {})

                top_gainers = sorted(
                    [h for h in holdings if h.get("pl", 0) > 0],
                    key=lambda x: x.get("pl", 0), reverse=True
                )[:5]
                top_losers = sorted(
                    [h for h in holdings if h.get("pl", 0) < 0],
                    key=lambda x: x.get("pl", 0)
                )[:5]

                summary["holdings"] = {
                    "count": len(holdings),
                    "overall": overall,
                    "top_gainers": [
                        {"symbol": h.get("symbol"), "pl": h.get("pl", 0)}
                        for h in top_gainers
                    ],
                    "top_losers": [
                        {"symbol": h.get("symbol"), "pl": h.get("pl", 0)}
                        for h in top_losers
                    ],
                }
        except Exception:
            summary["holdings"] = "Error fetching holdings"

        # Positions
        try:
            positions_resp = client.positions()
            if positions_resp.get("code") == 200:
                positions = positions_resp.get("netPositions", [])
                overall_pos = positions_resp.get("overall", {})

                summary["positions"] = {
                    "count": len(positions),
                    "overall": overall_pos,
                    "open_positions": [
                        {
                            "symbol": p.get("symbol"),
                            "side": "LONG" if p.get("side", 0) > 0 else "SHORT",
                            "qty": p.get("netQty", p.get("qty", 0)),
                            "pl": p.get("pl", 0),
                            "productType": p.get("productType"),
                        }
                        for p in positions
                        if p.get("netQty", p.get("qty", 0)) != 0
                    ],
                }
        except Exception:
            summary["positions"] = "Error fetching positions"

        return create_response(
            True,
            data=summary,
            message="Portfolio summary retrieved successfully",
        )

    except Exception as e:
        return create_response(False, error=f"Error getting portfolio summary: {str(e)}")


# ============================================================================
# POSITION SIZER (Risk-based quantity calculator)
# ============================================================================

@mcp.tool()
def position_sizer(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")],
    risk_percent: Annotated[float, Field(description="Percentage of capital to risk per trade")] = 1.0,
    stop_loss_price: Annotated[float, Field(description="Planned stop loss price (required if entry 0)")] = 0,
    entry_price: Annotated[float, Field(description="Planned entry price (0 = use CMP)")] = 0,
) -> str:
    """Calculate optimal position size based on risk management.

    Uses fyers.funds() for available capital and fyers.quotes() for current price.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        # Get funds
        funds_resp = client.funds()
        if funds_resp.get("code") != 200:
            return create_response(False, error="Failed to get funds")

        fund_limit = funds_resp.get("fund_limit", [])
        total_capital = 0
        if isinstance(fund_limit, list):
            for item in fund_limit:
                if isinstance(item, dict):
                    total_capital = max(total_capital, item.get("equityAmount", item.get("total_balance", 0)))

        if total_capital <= 0:
            return create_response(False, error="Could not determine available capital")

        # Get current price
        quote_resp = client.quotes({"symbols": symbol})
        if quote_resp.get("code") != 200:
            return create_response(False, error="Failed to get quote")

        quote_data = quote_resp.get("d", [])
        current_price = 0
        if isinstance(quote_data, list) and len(quote_data) > 0:
            v = quote_data[0].get("v", {})
            current_price = v.get("lp", 0)

        if current_price <= 0:
            return create_response(False, error="Could not get current price")

        if entry_price <= 0:
            entry_price = current_price

        if stop_loss_price <= 0:
            return create_response(False, error="stop_loss_price is required for position sizing")

        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            return create_response(False, error="Entry price and stop loss price cannot be the same")

        max_risk_amount = total_capital * (risk_percent / 100)
        recommended_qty = int(max_risk_amount / risk_per_share)
        capital_required = recommended_qty * entry_price
        max_loss = recommended_qty * risk_per_share

        # Risk-reward scenarios
        r1_target = entry_price + (1 * risk_per_share) if entry_price > stop_loss_price else entry_price - (1 * risk_per_share)
        r2_target = entry_price + (2 * risk_per_share) if entry_price > stop_loss_price else entry_price - (2 * risk_per_share)
        r3_target = entry_price + (3 * risk_per_share) if entry_price > stop_loss_price else entry_price - (3 * risk_per_share)

        return create_response(
            True,
            data={
                "symbol": symbol,
                "current_price": current_price,
                "entry_price": entry_price,
                "stop_loss": stop_loss_price,
                "risk_per_share": round(risk_per_share, 2),
                "available_capital": round(total_capital, 2),
                "risk_percent": risk_percent,
                "max_risk_amount": round(max_risk_amount, 2),
                "recommended_qty": recommended_qty,
                "capital_required": round(capital_required, 2),
                "max_loss": round(max_loss, 2),
                "targets": {
                    "1R": round(r1_target, 2),
                    "2R": round(r2_target, 2),
                    "3R": round(r3_target, 2),
                },
                "potential_profit_1R": round(recommended_qty * risk_per_share, 2),
                "potential_profit_2R": round(recommended_qty * 2 * risk_per_share, 2),
                "potential_profit_3R": round(recommended_qty * 3 * risk_per_share, 2),
            },
            message=f"Position size: {recommended_qty} shares (risking {risk_percent}% = ₹{round(max_loss, 2)})",
        )

    except Exception as e:
        return create_response(False, error=f"Error calculating position size: {str(e)}")


# ============================================================================
# MULTI-STOCK COMPARISON
# ============================================================================

@mcp.tool()
def compare_stocks(symbols: Annotated[str, Field(description="Comma-separated symbols to compare (e.g. 'NSE:SBIN-EQ,NSE:HDFCBANK-EQ')")]) -> str:
    """Compare multiple stocks side by side with price and technical data.

    Uses fyers.quotes() and fyers.history() for each symbol.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        symbol_list = [s.strip() for s in symbols.split(",")]

        if len(symbol_list) > 10:
            return create_response(False, error="Maximum 10 symbols for comparison")

        # Get quotes for all symbols at once
        quote_resp = client.quotes({"symbols": symbols.strip()})
        quotes_map = {}
        if quote_resp.get("code") == 200:
            for item in quote_resp.get("d", []):
                name = item.get("n", "")
                v = item.get("v", {})
                quotes_map[name] = {
                    "ltp": v.get("lp", 0),
                    "change": v.get("ch", 0),
                    "change_pct": v.get("chp", 0),
                    "volume": v.get("volume", 0),
                    "high": v.get("high_price", 0),
                    "low": v.get("low_price", 0),
                    "open": v.get("open_price", 0),
                    "prev_close": v.get("prev_close_price", 0),
                }

        comparison = []
        for sym in symbol_list:
            stock_data = quotes_map.get(sym, {})

            # Fetch history for RSI calculation
            try:
                hist_data = {
                    "symbol": sym,
                    "resolution": "D",
                    "date_format": "0",
                    "range_from": str(int((datetime.now() - timedelta(days=60)).timestamp())),
                    "range_to": str(int(datetime.now().timestamp())),
                    "cont_flag": "1",
                }
                hist_resp = client.history(hist_data)
                candles = hist_resp.get("candles", [])
                close_prices = [c[4] for c in candles if isinstance(c, list) and len(c) >= 6]

                rsi = _calculate_rsi(close_prices, 14) if len(close_prices) >= 15 else None
                sma_20 = _calculate_sma(close_prices, 20)[-1] if len(close_prices) >= 20 else None
            except Exception:
                rsi = None
                sma_20 = None

            comparison.append({
                "symbol": sym,
                **stock_data,
                "rsi_14": rsi,
                "sma_20": sma_20,
            })

        # Sort by change_pct descending
        comparison.sort(key=lambda x: x.get("change_pct", 0), reverse=True)

        return create_response(
            True,
            data={"comparison": comparison, "count": len(comparison)},
            message=f"Compared {len(comparison)} stocks",
        )

    except Exception as e:
        return create_response(False, error=f"Error comparing stocks: {str(e)}")


# ============================================================================
# MUTUAL FUND HOLDINGS
# ============================================================================

@mcp.tool()
def get_mutual_fund_holdings() -> str:
    """Get mutual fund portfolio with performance details.

    Filters regular holdings to return only mutual funds.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.holdings()

        if response.get("code") == 200:
            holdings = response.get("holdings", [])

            mf_holdings = []
            for h in holdings:
                sym = h.get("symbol", "")
                h_type = str(h.get("holdingType", "")).upper()

                # Identify MFs usually by holdingType or missing -EQ suffix indicating it's not a standard stock
                if "MF" in h_type or ("-EQ" not in sym and "NSE:" not in sym):
                    mf_holdings.append(h)

            return create_response(
                True,
                data={
                    "mutual_fund_holdings": mf_holdings,
                    "count": len(mf_holdings),
                },
                message="Mutual Fund Holdings retrieved successfully" if mf_holdings else "No mutual fund holdings found",
            )
        else:
            return create_response(False, error=f"Failed to get holdings: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting mutual fund holdings: {str(e)}")
