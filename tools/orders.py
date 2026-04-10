"""
Order management tools — basic, basket, multileg, and GTT orders.

Tools: get_orders, get_order_by_id, get_trade_book,
       place_order, modify_order, cancel_order,
       place_basket_orders, modify_basket_orders, cancel_basket_orders,
       place_multileg_order,
       place_gtt_order, modify_gtt_order, cancel_gtt_order, get_gtt_orderbook
"""

import json
from typing import Annotated, Optional
from pydantic import Field

from .core import mcp, create_response, get_fyers_client


# ============================================================================
# ORDERS - BASIC
# ============================================================================

@mcp.tool()
def get_orders() -> str:
    """Get full order book using fyers.orderbook()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.orderbook()

        if response.get("code") == 200:
            orders = response.get("orderBook", [])

            if not orders:
                return create_response(True, data={"orders": []}, message="No orders found")

            orders_list = []
            for order in orders:
                orders_list.append({
                    "id": order.get("id", "N/A"),
                    "symbol": order.get("symbol", "N/A"),
                    "side": order.get("side", 0),
                    "qty": order.get("qty", 0),
                    "filledQty": order.get("filledQty", 0),
                    "type": order.get("type", 0),
                    "limitPrice": order.get("limitPrice", 0),
                    "stopPrice": order.get("stopPrice", 0),
                    "productType": order.get("productType", "N/A"),
                    "status": order.get("status", 0),
                    "validity": order.get("validity", "N/A"),
                    "orderDateTime": order.get("orderDateTime", "N/A"),
                    "message": order.get("message", ""),
                })

            return create_response(
                True,
                data={"orders": orders_list, "count": len(orders_list)},
                message="Orders retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get orders: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting orders: {str(e)}")


@mcp.tool()
def get_order_by_id(order_id: Annotated[str, Field(description="Order ID (or comma-separated IDs) to look up")]) -> str:
    """Get specific order details by ID using fyers.get_orders()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        data = {"id": order_id}
        response = client.get_orders(data)

        if response.get("code") == 200:
            orders = response.get("orderBook", [])
            return create_response(
                True,
                data={"orders": orders},
                message="Order details retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get order: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting order: {str(e)}")


@mcp.tool()
def get_trade_book() -> str:
    """Get complete trade history (executed trades) using fyers.tradebook()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.tradebook()

        if response.get("code") == 200:
            trades = response.get("tradeBook", [])

            if not trades:
                return create_response(True, data={"trades": []}, message="No trades found")

            trades_list = []
            for trade in trades:
                trades_list.append({
                    "symbol": trade.get("symbol", "N/A"),
                    "qty": trade.get("qty", 0),
                    "tradePrice": trade.get("tradePrice", 0),
                    "side": trade.get("side", 0),
                    "productType": trade.get("productType", "N/A"),
                    "orderDateTime": trade.get("orderDateTime", "N/A"),
                    "tradeNumber": trade.get("tradeNumber", "N/A"),
                    "orderNumber": trade.get("orderNumber", "N/A"),
                    "id": trade.get("id", "N/A"),
                })

            return create_response(
                True,
                data={"trades": trades_list, "total_trades": len(trades_list)},
                message="Trade book retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get trade book: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting trade book: {str(e)}")


@mcp.tool()
def place_order(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")],
    quantity: Annotated[int, Field(description="Number of shares/contracts to trade")],
    order_type: Annotated[str, Field(description="MARKET, LIMIT, STOP, or STOPLIMIT")],
    side: Annotated[str, Field(description="BUY or SELL")],
    product_type: Annotated[str, Field(description="CNC, INTRADAY, MARGIN, CO, or BO")] = "INTRADAY",
    limit_price: Annotated[float, Field(description="Price for LIMIT/STOPLIMIT orders")] = 0,
    stop_price: Annotated[float, Field(description="Trigger price for STOP/STOPLIMIT orders")] = 0,
    validity: Annotated[str, Field(description="'DAY' or 'IOC'")] = "DAY",
    disclosed_qty: Annotated[int, Field(description="Disclosed quantity (equity only)")] = 0,
    offline_order: Annotated[bool, Field(description="True for AMO (After Market Order)")] = False,
    stop_loss: Annotated[float, Field(description="Stop loss relative points (CO/BO)")] = 0,
    take_profit: Annotated[float, Field(description="Take profit relative points (BO)")] = 0,
) -> str:
    """Place a new order using fyers.place_order()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        type_map = {"MARKET": 1, "LIMIT": 2, "STOP": 3, "STOPLIMIT": 4}
        side_map = {"BUY": 1, "SELL": -1}

        order_data = {
            "symbol": symbol,
            "qty": quantity,
            "type": type_map.get(order_type.upper(), 2),
            "side": side_map.get(side.upper(), 1),
            "productType": product_type,
            "limitPrice": limit_price,
            "stopPrice": stop_price,
            "validity": validity,
            "disclosedQty": disclosed_qty,
            "offlineOrder": offline_order,
            "stopLoss": stop_loss,
            "takeProfit": take_profit,
        }

        response = client.place_order(order_data)

        if response.get("code") == 200 or response.get("id"):
            order_id = response.get("id", "Unknown")
            return create_response(
                True,
                data={
                    "order_id": order_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "side": side,
                    "order_type": order_type,
                },
                message="Order placed successfully",
            )
        else:
            return create_response(
                False,
                error=f"Order placement failed: {response.get('message', response)}",
            )

    except Exception as e:
        return create_response(False, error=f"Error placing order: {str(e)}")


@mcp.tool()
def modify_order(
    order_id: Annotated[str, Field(description="Order ID to modify")],
    order_type: Annotated[Optional[int], Field(description="New order type (1=Limit, 2=Market, 3=Stop, 4=Stoplimit)")] = None,
    quantity: Annotated[Optional[int], Field(description="New quantity")] = None,
    limit_price: Annotated[Optional[float], Field(description="New limit price")] = None,
    stop_price: Annotated[Optional[float], Field(description="New stop trigger price")] = None,
) -> str:
    """Modify an existing pending order using fyers.modify_order()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        modify_data = {"id": order_id}

        if order_type is not None:
            modify_data["type"] = order_type
        if quantity is not None:
            modify_data["qty"] = quantity
        if limit_price is not None:
            modify_data["limitPrice"] = limit_price
        if stop_price is not None:
            modify_data["stopPrice"] = stop_price

        response = client.modify_order(modify_data)

        if response.get("code") == 200:
            return create_response(
                True, data={"order_id": order_id}, message="Order modified successfully"
            )
        else:
            return create_response(
                False,
                error=f"Order modification failed: {response.get('message', response)}",
            )

    except Exception as e:
        return create_response(False, error=f"Error modifying order: {str(e)}")


@mcp.tool()
def cancel_order(order_id: Annotated[str, Field(description="Order ID to cancel")]) -> str:
    """Cancel an existing order using fyers.cancel_order()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        cancel_data = {"id": order_id}

        response = client.cancel_order(cancel_data)

        if response.get("code") == 200:
            return create_response(
                True,
                data={"order_id": order_id},
                message="Order cancelled successfully",
            )
        else:
            return create_response(
                False,
                error=f"Order cancellation failed: {response.get('message', response)}",
            )

    except Exception as e:
        return create_response(False, error=f"Error cancelling order: {str(e)}")


# ============================================================================
# ORDERS - BASKET (Multiple orders at once)
# ============================================================================

@mcp.tool()
def place_basket_orders(orders: Annotated[str, Field(description="JSON string of orders array. E.g. [{\"symbol\":\"NSE:SBIN-EQ\",\"qty\":1,\"type\":1,\"side\":1,\"productType\":\"INTRADAY\"...}]")]) -> str:
    """Place multiple orders at once using fyers.place_basket_orders(). Max 10 orders."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        import json as json_lib
        orders_list = json_lib.loads(orders)

        if len(orders_list) > 10:
            return create_response(False, error="Maximum 10 orders allowed in basket")

        response = client.place_basket_orders(orders_list)

        return create_response(
            True,
            data={"response": response},
            message=f"Basket orders submitted ({len(orders_list)} orders)",
        )

    except json.JSONDecodeError as e:
        return create_response(False, error=f"Invalid JSON in orders: {str(e)}")
    except Exception as e:
        return create_response(False, error=f"Error placing basket orders: {str(e)}")


@mcp.tool()
def modify_basket_orders(orders: Annotated[str, Field(description="JSON string of orders to modify. E.g. [{\"id\":\"...\",\"type\":1,\"limitPrice\":61049,\"qty\":1}]")]) -> str:
    """Modify multiple orders at once using fyers.modify_basket_orders()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        import json as json_lib
        orders_list = json_lib.loads(orders)

        response = client.modify_basket_orders(orders_list)

        return create_response(
            True,
            data={"response": response},
            message="Basket orders modified",
        )

    except json.JSONDecodeError as e:
        return create_response(False, error=f"Invalid JSON in orders: {str(e)}")
    except Exception as e:
        return create_response(False, error=f"Error modifying basket orders: {str(e)}")


@mcp.tool()
def cancel_basket_orders(order_ids: Annotated[str, Field(description="Comma-separated order IDs to cancel")]) -> str:
    """Cancel multiple orders at once using fyers.cancel_basket_orders()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        order_ids_list = [oid.strip() for oid in order_ids.split(",")]
        orders_data = [{"id": oid} for oid in order_ids_list]

        response = client.cancel_basket_orders(orders_data)

        return create_response(
            True,
            data={"response": response},
            message=f"Basket cancel submitted ({len(order_ids_list)} orders)",
        )

    except Exception as e:
        return create_response(False, error=f"Error cancelling basket orders: {str(e)}")


# ============================================================================
# MULTILEG ORDERS
# ============================================================================

@mcp.tool()
def place_multileg_order(
    product_type: Annotated[str, Field(description="'INTRADAY' or 'MARGIN'")],
    order_type: Annotated[str, Field(description="'2L' for 2-leg or '3L' for 3-leg")],
    legs: Annotated[str, Field(description="JSON string of legs dict. E.g: {\"leg1\":{\"symbol\":\"...\",\"qty\":750,\"side\":1,\"type\":1,\"limitPrice\":800}}")],
    validity: Annotated[str, Field(description="Validity (default: 'IOC')")] = "IOC",
    offline_order: Annotated[bool, Field(description="True for AMO")] = False,
    order_tag: Annotated[str, Field(description="Custom order tag")] = "",
) -> str:
    """Place a multileg order (2L or 3L) using fyers.place_multileg_order()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        import json as json_lib
        legs_dict = json_lib.loads(legs)

        order_data = {
            "productType": product_type,
            "offlineOrder": offline_order,
            "orderType": order_type,
            "validity": validity,
            "legs": legs_dict,
        }
        if order_tag:
            order_data["orderTag"] = order_tag

        response = client.place_multileg_order(order_data)

        if response.get("code") == 200 or response.get("id"):
            return create_response(
                True,
                data={"response": response},
                message="Multileg order placed successfully",
            )
        else:
            return create_response(
                False,
                error=f"Multileg order failed: {response}",
            )

    except json.JSONDecodeError as e:
        return create_response(False, error=f"Invalid JSON in legs: {str(e)}")
    except Exception as e:
        return create_response(False, error=f"Error placing multileg order: {str(e)}")


# ============================================================================
# GTT (Good Till Triggered) ORDERS
# ============================================================================

@mcp.tool()
def place_gtt_order(
    symbol: Annotated[str, Field(description="Trading symbol (e.g. 'NSE:SBIN-EQ')")],
    side: Annotated[str, Field(description="'BUY' or 'SELL'")],
    product_type: Annotated[str, Field(description="'CNC', 'MARGIN', or 'MTF'")],
    leg1_price: Annotated[float, Field(description="Price for GTT leg1")],
    leg1_trigger_price: Annotated[float, Field(description="Trigger price for leg1")],
    leg1_qty: Annotated[int, Field(description="Quantity for leg1")],
    leg2_price: Annotated[float, Field(description="Price for OCO leg2 (optional, 0 = no leg2)")] = 0,
    leg2_trigger_price: Annotated[float, Field(description="Trigger price for OCO leg2 (optional)")] = 0,
    leg2_qty: Annotated[int, Field(description="Quantity for OCO leg2 (optional)")] = 0,
) -> str:
    """Place a GTT (Good Till Triggered) or OCO order using fyers.place_gtt_order().

    For a simple GTT, only leg1 is needed.
    For an OCO (One Cancels Other), both leg1 and leg2 are needed.
    (OCO Note: leg1 trigger should be ABOVE LTP and leg2 trigger BELOW LTP).
    """
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        side_map = {"BUY": 1, "SELL": -1}

        order_data = {
            "side": side_map.get(side.upper(), 1),
            "symbol": symbol,
            "productType": product_type,
            "orderInfo": {
                "leg1": {
                    "price": leg1_price,
                    "triggerPrice": leg1_trigger_price,
                    "qty": leg1_qty,
                }
            },
        }

        # Add leg2 for OCO orders
        if leg2_price > 0 and leg2_trigger_price > 0 and leg2_qty > 0:
            order_data["orderInfo"]["leg2"] = {
                "price": leg2_price,
                "triggerPrice": leg2_trigger_price,
                "qty": leg2_qty,
            }

        response = client.place_gtt_order(order_data)

        if response.get("code") == 200 or response.get("id"):
            return create_response(
                True,
                data={
                    "gtt_id": response.get("id", "Unknown"),
                    "symbol": symbol,
                    "response": response,
                },
                message="GTT order placed successfully",
            )
        else:
            return create_response(
                False,
                error=f"GTT order placement failed: {response}",
            )

    except Exception as e:
        return create_response(False, error=f"Error placing GTT order: {str(e)}")


@mcp.tool()
def modify_gtt_order(
    order_id: Annotated[str, Field(description="GTT order ID (e.g. '25010700000001')")],
    leg1_price: Annotated[float, Field(description="Updated price for leg1")],
    leg1_trigger_price: Annotated[float, Field(description="Updated trigger price for leg1")],
    leg1_qty: Annotated[int, Field(description="Updated quantity for leg1")],
    leg2_trigger_price: Annotated[float, Field(description="Updated trigger price for leg2 (OCO only)")] = 0,
    leg2_qty: Annotated[int, Field(description="Updated quantity for leg2 (OCO only)")] = 0,
) -> str:
    """Modify a pending GTT/OCO order using fyers.modify_gtt_order()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        modify_data = {
            "id": order_id,
            "orderInfo": {
                "leg1": {
                    "price": leg1_price,
                    "triggerPrice": leg1_trigger_price,
                    "qty": leg1_qty,
                }
            },
        }

        if leg2_trigger_price > 0 and leg2_qty > 0:
            modify_data["orderInfo"]["leg2"] = {
                "triggerPrice": leg2_trigger_price,
                "qty": leg2_qty,
            }

        response = client.modify_gtt_order(modify_data)

        if response.get("code") == 200:
            return create_response(
                True,
                data={"order_id": order_id},
                message="GTT order modified successfully",
            )
        else:
            return create_response(
                False,
                error=f"GTT order modification failed: {response}",
            )

    except Exception as e:
        return create_response(False, error=f"Error modifying GTT order: {str(e)}")


@mcp.tool()
def cancel_gtt_order(order_id: Annotated[str, Field(description="GTT order ID to cancel (e.g. '25010700000001')")]) -> str:
    """Cancel a GTT order using fyers.cancel_gtt_order()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.cancel_gtt_order({"id": order_id})

        if response.get("code") == 200:
            return create_response(
                True,
                data={"order_id": order_id},
                message="GTT order cancelled successfully",
            )
        else:
            return create_response(
                False,
                error=f"GTT order cancellation failed: {response}",
            )

    except Exception as e:
        return create_response(False, error=f"Error cancelling GTT order: {str(e)}")


@mcp.tool()
def get_gtt_orderbook() -> str:
    """Get GTT order book using fyers.gtt_orderbook()."""
    try:
        client = get_fyers_client()
        if not client:
            return create_response(False, error="Not authenticated")

        response = client.gtt_orderbook()

        if response.get("code") == 200:
            gtt_orders = response.get("gttOrders", response.get("data", []))
            return create_response(
                True,
                data={"gtt_orders": gtt_orders, "count": len(gtt_orders) if isinstance(gtt_orders, list) else 0},
                message="GTT orderbook retrieved successfully",
            )
        else:
            return create_response(False, error=f"Failed to get GTT orderbook: {response}")

    except Exception as e:
        return create_response(False, error=f"Error getting GTT orderbook: {str(e)}")
