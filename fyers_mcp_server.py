#!/usr/bin/env python3
"""
Fyers MCP Server v7.0 - Complete Fyers API v3 Integration
Entry point — imports every tool module so they register on the shared `mcp` instance.

MCP config stays unchanged:
{
  "mcpServers": {
    "fyers-mcp-server": {
      "command": "python",
      "args": ["C:\\Users\\rtnan\\Desktop\\fyers-mcp-server\\fyers_mcp_server.py"]
    }
  }
}

Available SDK methods used:
  - get_profile, funds, holdings, positions, tradebook, orderbook, get_orders
  - place_order, modify_order, cancel_order
  - place_basket_orders, modify_basket_orders, cancel_basket_orders
  - exit_positions, convert_position
  - quotes, depth, history
  - market_status, optionchain
  - place_multileg_order
  - place_gtt_order, modify_gtt_order, cancel_gtt_order, gtt_orderbook
  - logout
"""

import sys

# Import the shared MCP instance from core
from tools.core import mcp

# Import all tool modules — each module registers its @mcp.tool() functions
# on the shared `mcp` instance at import time.
import tools.auth          # authenticate, check_auth_status, get_profile, logout
import tools.account       # get_funds, get_holdings, get_positions
import tools.market_data   # get_quotes, get_market_depth, get_historical_prices, get_market_status, get_option_chain
import tools.orders        # place/modify/cancel order, basket orders, multileg, GTT orders
import tools.positions     # exit_positions, convert_position
import tools.analysis      # get_technical_indicators, pivot_points, vwap_calculator, candlestick_patterns, oi_analysis
import tools.utilities     # symbol_search, portfolio_summary, position_sizer, compare_stocks, get_mutual_fund_holdings
import tools.watchlists    # get_watchlists, create_watchlist, add/remove symbols, delete_watchlist
import tools.alerts        # get_price_alerts, create_price_alert, delete_price_alert


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Fyers MCP Server v7.0...")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)
