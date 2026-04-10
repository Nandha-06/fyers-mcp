"""
Account & Funds tools.

Tools: get_funds, get_holdings, get_positions
"""

from .core import mcp, create_response, get_fyers_client


# ============================================================================
# ACCOUNT & FUNDS
# ============================================================================

@mcp.tool()
def get_funds() -> str:
    """Get account funds and margin details using fyers.funds().

    Returns fund_limit array with equity/commodity amounts, margins, etc.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.funds()

        if response.get("code") == 200:
            fund_limit = response.get("fund_limit", [])
            return create_response(
                True,
                data={"fund_limit": fund_limit},
                message="Funds retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get funds: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting funds: {str(e)}")


@mcp.tool()
def get_holdings() -> str:
    """Get portfolio holdings using fyers.holdings()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.holdings()

        if response.get("code") == 200:
            holdings = response.get("holdings", [])

            if not holdings:
                return create_response(True, data={"holdings": [], "overall": {}}, message="No holdings found")

            overall = response.get("overall", {})

            holdings_list = []
            for holding in holdings:
                holdings_list.append({
                    "symbol": holding.get("symbol", "N/A"),
                    "quantity": holding.get("quantity", holding.get("qty", 0)),
                    "ltp": holding.get("ltp", 0),
                    "costPrice": holding.get("costPrice", 0),
                    "marketVal": holding.get("marketVal", 0),
                    "pl": holding.get("pl", 0),
                    "holdingType": holding.get("holdingType", "N/A"),
                })

            return create_response(
                True,
                data={
                    "holdings": holdings_list,
                    "overall": overall,
                    "count": len(holdings_list),
                },
                message="Holdings retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get holdings: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting holdings: {str(e)}")


@mcp.tool()
def get_positions() -> str:
    """Get current trading positions using fyers.positions()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.positions()

        if response.get("code") == 200:
            positions = response.get("netPositions", [])

            if not positions:
                return create_response(True, data={"positions": [], "overall": {}}, message="No open positions")

            overall = response.get("overall", {})

            positions_list = []
            for pos in positions:
                positions_list.append({
                    "symbol": pos.get("symbol", "N/A"),
                    "side": pos.get("side", 0),
                    "qty": pos.get("qty", 0),
                    "netQty": pos.get("netQty", 0),
                    "avgPrice": pos.get("avgPrice", 0),
                    "ltp": pos.get("ltp", 0),
                    "pl": pos.get("pl", 0),
                    "productType": pos.get("productType", "N/A"),
                    "id": pos.get("id", "N/A"),
                })

            return create_response(
                True,
                data={"positions": positions_list, "overall": overall},
                message="Positions retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get positions: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting positions: {str(e)}")
