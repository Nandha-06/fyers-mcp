"""
Position Management tools.

Tools: exit_positions, convert_position
"""

from typing import Annotated
from pydantic import Field

from .core import mcp, create_response, get_fyers_client


# ============================================================================
# POSITION MANAGEMENT
# ============================================================================

@mcp.tool()
def exit_positions(position_id: Annotated[str, Field(description="Position ID to exit (e.g. 'NSE:SBIN-EQ-INTRADAY'). Leave empty to exit ALL.")] = "") -> str:
    """Exit positions using fyers.exit_positions()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        # Per SDK source: empty dict → sets exit_all=1 internally
        # With id → exits specific position
        if position_id:
            exit_data = {"id": position_id}
        else:
            exit_data = {}

        response = client.exit_positions(exit_data)

        if response.get("code") == 200:
            msg = f"Position {position_id} exited" if position_id else "All positions exited"
            return create_response(
                True,
                data={"response": response},
                message=msg,
            )
        else:
            return create_response(
                False,
                error=f"Failed to exit positions: {response}",
            )

    except Exception as e:
        return create_response(False, error=f"Error exiting positions: {str(e)}")


@mcp.tool()
def convert_position(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'MCX:SILVERMIC20NOVFUT')")],
    position_side: Annotated[str, Field(description="'LONG' or 'SHORT'")],
    convert_qty: Annotated[int, Field(description="Quantity to convert")],
    convert_from: Annotated[str, Field(description="Current product type ('INTRADAY', 'MARGIN')")],
    convert_to: Annotated[str, Field(description="Target product type ('INTRADAY', 'MARGIN', 'CNC')")],
) -> str:
    """Convert position from one product type to another using fyers.convert_position().
    Note: CNC positions cannot be converted.
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        side_map = {"LONG": 1, "SHORT": -1}

        # Per SDK docs: field names are positionSide, convertQty, convertFrom, convertTo
        convert_data = {
            "symbol": symbol,
            "positionSide": side_map.get(position_side.upper(), 1),
            "convertQty": convert_qty,
            "convertFrom": convert_from,
            "convertTo": convert_to,
        }

        response = client.convert_position(convert_data)

        if response.get("code") == 200:
            return create_response(
                True,
                data={
                    "symbol": symbol,
                    "from": convert_from,
                    "to": convert_to,
                    "quantity": convert_qty,
                },
                message="Position converted successfully",
            )
        else:
            return create_response(
                False,
                error=f"Position conversion failed: {response}",
            )

    except Exception as e:
        return create_response(False, error=f"Error converting position: {str(e)}")
