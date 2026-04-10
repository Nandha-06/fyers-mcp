<p align="center">
  <h1 align="center">🔗 Fyers MCP Server</h1>
  <p align="center">
    <strong>A Model Context Protocol server for complete Fyers API v3 integration</strong>
  </p>
  <p align="center">
    Trade execution&ensp;·&ensp;Live market data&ensp;·&ensp;Portfolio management&ensp;·&ensp;Technical analysis
  </p>
  <p align="center">
    <a href="#-quick-start"><img src="https://img.shields.io/badge/python-≥3.11-blue?logo=python&logoColor=white" alt="Python"></a>
    <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-compatible-8A2BE2?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBkPSJNMTIgMkw0IDdsMCA1IDggNSA4LTV2LTVMMTIgMnoiIGZpbGw9IiNGRkYiLz48L3N2Zz4=" alt="MCP"></a>
    <a href="https://github.com/Nandha-06/fyers-mcp--developement-only-/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
    <a href="https://pypi.org/project/fyers-apiv3/"><img src="https://img.shields.io/badge/Fyers_SDK-v3.1.11-orange" alt="Fyers SDK"></a>
  </p>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features at a Glance](#-features-at-a-glance)
- [Tool Reference](#-tool-reference)
- [Prerequisites](#-prerequisites)
- [Getting a Static Public IP (Required for Order Placement)](#-getting-a-static-public-ip-required-for-order-placement)
- [Fyers API Credentials Setup](#-fyers-api-credentials-setup)
- [Quick Start](#-quick-start)
- [MCP Client Configuration](#-mcp-client-configuration)
- [Authentication Flow](#-authentication-flow)
- [Usage Examples](#-usage-examples)
- [Project Structure](#-project-structure)
- [Feature Roadmap](#-feature-roadmap)
- [Contributing](#-contributing)
- [Disclaimer](#%EF%B8%8F-disclaimer)
- [License](#-license)

---

## 🧠 Overview

**Fyers MCP Server** is a [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the full [Fyers API v3](https://myapi.fyers.in/docsv3) as a set of **47 tools** consumable by any MCP-compatible AI client — Claude Desktop, Cline, OpenCode, Continue, and more.

It bridges the gap between conversational AI and programmatic trading, enabling your AI assistant to:

- **Execute trades** — place, modify, and cancel orders using natural language  
- **Fetch live data** — real-time quotes, market depth, option chains  
- **Analyze markets** — RSI, MACD, Bollinger Bands, VWAP, pivot points, candlestick patterns, OI analysis  
- **Manage portfolios** — holdings, positions, funds, consolidated summaries  
- **Automate workflows** — basket orders, multileg strategies, GTT/OCO orders, price alerts  

All through a single, unified MCP interface.

> **In simple terms:** Ask your AI assistant *"Buy 10 shares of SBIN at market price"* or *"Show me the RSI and MACD for Reliance"* — and it just works.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          MCP CLIENT (AI Assistant)                          │
│                 Claude Desktop / Cline / OpenCode / Continue                │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │  stdio transport
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        fyers_mcp_server.py (Entry Point)                    │
│                     Imports all tool modules → runs mcp.run()               │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │  registers @mcp.tool()
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        tools/core.py (Shared Kernel)                        │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────────────┐  │
│  │  FastMCP Server  │  │  Fyers Client  │  │  OAuth Handler + .env Loader │  │
│  │  (single inst.)  │  │  (lazy init)   │  │  (auto token exchange)       │  │
│  └─────────────────┘  └────────────────┘  └──────────────────────────────┘  │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
        ┌───────────┬──────────┬────┴─────┬──────────┬──────────┬──────────┐
        ▼           ▼          ▼          ▼          ▼          ▼          ▼
  ┌──────────┐ ┌─────────┐ ┌───────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────┐
  │  auth.py │ │account. │ │market │ │orders. │ │positi- │ │analy-  │ │utili │
  │          │ │  py     │ │_data. │ │  py    │ │ons.py  │ │sis.py  │ │ties. │
  │ 4 tools  │ │ 3 tools │ │py     │ │14 tools│ │ 2 tools│ │ 5 tools│ │py    │
  └──────────┘ └─────────┘ │5 tools│ └────────┘ └────────┘ └────────┘ │5 tool│
                           └───────┘                                   └──────┘
        ┌──────────────┐  ┌──────────────┐
        ▼              ▼  ▼              ▼
  ┌───────────┐  ┌───────────┐
  │watchlists │  │ alerts.py │
  │   .py     │  │           │
  │  6 tools  │  │  3 tools  │         ──────────────────────────────────────
  └─────┬─────┘  └─────┬─────┘         Fyers API v3  (api-t1.fyers.in)
        │              │               ──────────────────────────────────────
        │  local JSON  │  REST API              ▲
        ▼              └────────────────────────┘
  watchlists.json                      Fyers SDK (fyers-apiv3==3.1.11)
```

**Key design decisions:**

| Principle | Implementation |
|---|---|
| **Single MCP instance** | `tools/core.py` creates one `FastMCP` server; every module imports and decorates onto it |
| **Lazy client init** | `get_fyers_client()` reads `.env` on each call — supports runtime token refresh |
| **Module isolation** | Each `tools/*.py` file owns its domain; zero cross-module coupling (except `analysis` helpers reused by `utilities`) |
| **Schema-bound parameters** | Every tool parameter uses `Annotated[type, Field(description=...)]` for rich LLM tool schemas |
| **stdio transport** | MCP communication over stdin/stdout — no HTTP server, no port conflicts |

---

## ✨ Features at a Glance

| Category | Capabilities |
|---|---|
| 🔐 **Authentication** | Browser-based OAuth 2.0, auto token persistence, session management |
| 💰 **Account** | Funds & margin details, portfolio holdings, open positions |
| 📊 **Market Data** | Live quotes (50 symbols), L2 order book, OHLCV history, market status, option chains |
| 📝 **Order Management** | Market/Limit/Stop/SL orders, AMO, bracket orders, cover orders |
| 📦 **Basket Orders** | Place/modify/cancel up to 10 orders in a single call |
| 🔀 **Multileg Orders** | 2-leg and 3-leg spread strategies (straddles, strangles, spreads) |
| ⏰ **GTT Orders** | Good Till Triggered orders and OCO (One Cancels Other) pairs |
| 📈 **Technical Analysis** | RSI, MACD, SMA, EMA, Bollinger Bands, VWAP, Pivot Points (4 types) |
| 🕯️ **Pattern Detection** | 10 candlestick patterns — Doji, Hammer, Engulfing, Morning Star, etc. |
| 📉 **OI Analysis** | Put-Call Ratio, Max Pain, OI concentration heatmap |
| 🔍 **Utilities** | Symbol search, multi-stock comparison, position sizer, portfolio summary |
| 📋 **Watchlists** | Full CRUD with local persistence + live price enrichment |
| 🔔 **Price Alerts** | Server-synced alerts via Fyers REST API |

---

## 🛠 Tool Reference

### Authentication & Session (4 tools)

| Tool | Description |
|---|---|
| `authenticate` | Opens browser for OAuth 2.0 login, captures redirect, exchanges auth code for access token, and persists it to `.env` |
| `check_auth_status` | Validates the current access token against Fyers servers and returns the authenticated user name |
| `get_profile` | Retrieves user profile — name, email, mobile, Fyers ID |
| `logout` | Invalidates the current access token on the server side |

### Account & Portfolio (3 tools)

| Tool | Description |
|---|---|
| `get_funds` | Returns fund limits — available equity, commodity balance, used margin, etc. |
| `get_holdings` | Lists all delivery holdings with LTP, cost price, P&L, market value |
| `get_positions` | Lists all intraday/margin positions with live P&L and net quantity |

### Market Data (5 tools)

| Tool | Description |
|---|---|
| `get_quotes` | Fetches live quotes for up to 50 symbols — LTP, OHLC, change %, volume |
| `get_market_depth` | Returns Level 2 order book (top 5 bid/ask with quantities) |
| `get_historical_prices` | Retrieves OHLCV candle data with configurable timeframes (1m to monthly) and date ranges |
| `get_market_status` | Returns real-time status of NSE, BSE, MCX market segments |
| `get_option_chain` | Fetches option chain data with configurable strike count and expiry |

### Order Management (14 tools)

| Tool | Description |
|---|---|
| `get_orders` | Retrieves the full order book for the current session |
| `get_order_by_id` | Looks up specific order(s) by ID |
| `get_trade_book` | Returns all executed trades with prices and timestamps |
| `place_order` | Places a new order — supports MARKET, LIMIT, STOP, STOPLIMIT with CNC/INTRADAY/BO/CO product types |
| `modify_order` | Modifies pending order's type, quantity, or price |
| `cancel_order` | Cancels a pending order by ID |
| `place_basket_orders` | Places up to 10 orders simultaneously |
| `modify_basket_orders` | Batch-modifies multiple orders |
| `cancel_basket_orders` | Batch-cancels multiple orders by ID |
| `place_multileg_order` | Places 2-leg or 3-leg option spread strategies |
| `place_gtt_order` | Creates Good Till Triggered or OCO (One Cancels Other) orders |
| `modify_gtt_order` | Modifies pending GTT/OCO order parameters |
| `cancel_gtt_order` | Cancels a GTT order |
| `get_gtt_orderbook` | Retrieves all active GTT orders |

### Position Management (2 tools)

| Tool | Description |
|---|---|
| `exit_positions` | Exits a specific position by ID, or all open positions at once |
| `convert_position` | Converts a position between product types (INTRADAY ↔ MARGIN ↔ CNC) |

### Technical Analysis (5 tools)

| Tool | Description |
|---|---|
| `get_technical_indicators` | Calculates RSI, MACD, SMA (20/50), EMA (12/26), and Bollinger Bands from live historical data |
| `pivot_points` | Computes support/resistance levels — Standard, Fibonacci, Woodie, or Camarilla methods |
| `vwap_calculator` | Calculates real-time VWAP with ±1σ and ±2σ bands from intraday 1-minute data |
| `candlestick_patterns` | Detects 10 patterns — Doji, Hammer, Shooting Star, Engulfing, Three White Soldiers, Three Black Crows, etc. |
| `oi_analysis` | Analyzes option chain OI — Put-Call Ratio, Max Pain, OI concentration, and market sentiment |

### Utilities (5 tools)

| Tool | Description |
|---|---|
| `symbol_search` | Searches the public Fyers symbol master CSV by name/keyword — supports NSE, BSE, MCX |
| `portfolio_summary` | Generates a consolidated view combining funds, holdings (with top gainers/losers), and open positions |
| `position_sizer` | Calculates optimal quantity based on risk % of capital, entry price, and stop loss — includes 1R/2R/3R targets |
| `compare_stocks` | Side-by-side comparison of up to 10 stocks with live data, RSI, and SMA |
| `get_mutual_fund_holdings` | Filters holdings to show only mutual fund positions with performance data |

### Watchlist Management (6 tools)

| Tool | Description |
|---|---|
| `get_watchlists` | Lists all saved watchlists with symbol counts |
| `get_watchlists_by_id` | Retrieves a specific watchlist with live market data for all symbols |
| `create_watchlist` | Creates a new watchlist with an optional initial set of symbols |
| `add_symbols_to_watchlist` | Adds symbols to an existing watchlist (deduplication built-in) |
| `remove_symbols_from_watchlist` | Removes symbols from a watchlist |
| `delete_watchlist` | Permanently deletes a watchlist |

### Price Alerts (3 tools)

| Tool | Description |
|---|---|
| `get_price_alerts` | Retrieves all active price alerts from Fyers servers |
| `create_price_alert` | Creates a server-synced price alert — configurable symbol, condition (GT/LT), and target price |
| `delete_price_alert` | Deletes a price alert by ID |

---

## 📦 Prerequisites

- **Python** ≥ 3.11
- **uv** (recommended) or pip
- A **Fyers trading account** — [Sign up here](https://open-account.fyers.in/)
- A **Fyers API app** — [Create one here](https://myapi.fyers.in/dashboard/)
- A **static public IP address** — required by SEBI regulations for order placement ([details below](#-getting-a-static-public-ip-required-for-order-placement))

---

## 🌐 Getting a Static Public IP (Required for Order Placement)

> **Why is this needed?**  
> As per SEBI (Securities and Exchange Board of India) regulations, all algorithmic/API-based trading applications must whitelist a **static public IP address** in the Fyers API app dashboard. Fyers will reject any order placement requests originating from a non-whitelisted IP. Market data and account info endpoints work without this, but **you cannot place, modify, or cancel orders without a whitelisted static IP**.

### Understanding the Problem

Most home internet connections use **dynamic IPs** — your public IP changes every time your router restarts or your ISP reassigns it. API apps registered on Fyers require a **fixed IP** that never changes, so Fyers can verify that trading requests are coming from an authorized source.

Below are two practical approaches to obtain a static IP.

---

### Option 1: Request a Static IP from Your ISP

This is the simplest approach if your ISP supports it.

**Steps:**

1. **Contact your ISP** (Airtel, Jio Fiber, ACT, BSNL, etc.) via their customer support
2. **Request a static/fixed public IP address** — explain you need it for financial API access
3. ISP will assign you a permanent public IP (e.g., `49.37.xxx.xxx`)
4. **Verify** by visiting [whatismyip.com](https://whatismyip.com) — the IP should remain the same after router restarts
5. **Whitelist** this IP in your Fyers API app dashboard

**Pros:** Zero maintenance, works natively, no tunneling overhead  
**Cons:** Monthly cost varies (₹100–₹500+/month depending on ISP), not all ISPs offer this for residential plans

---

### Option 2: Oracle Cloud VPS + Tailscale (Free Forever)

This approach uses a **free cloud server as a proxy** — your traffic exits through the VPS's static IP while the MCP server runs locally on your machine. This is the recommended approach for most developers.

#### How It Works

```
Your PC (MCP Server)  ──Tailscale VPN──▶  Oracle Cloud VPS  ──▶  Fyers API
   (any dynamic IP)                      (static public IP)     (whitelisted)
                                           as Exit Node
```

Your MCP server runs locally on your machine. Tailscale creates a secure tunnel to the Oracle VPS, which acts as an **exit node** — all outbound API traffic appears to originate from the VPS's static IP.

#### Step-by-Step Setup

**1. Create a Free Oracle Cloud Account**

1. Go to [cloud.oracle.com](https://cloud.oracle.com) and sign up for an **Always Free** account
2. Select a home region close to NSE servers (e.g., **Mumbai — ap-mumbai-1**) for lowest latency
3. Complete verification (credit card required for identity but **₹0 charged**)

**2. Launch a Free-Tier VM**

1. Navigate to **Compute → Instances → Create Instance**  
2. Configure:
   - **Image:** Ubuntu 22.04 (or Oracle Linux)
   - **Shape:** `VM.Standard.A1.Flex` (ARM — 4 OCPU, 24 GB RAM free) or `VM.Standard.E2.1.Micro` (AMD — Always Free)
   - **Networking:** Assign a public IP (this will be your static IP)
3. Download the SSH key and launch the instance
4. **Note the Public IP** — this is the IP you'll whitelist in Fyers (e.g., `129.154.xxx.xxx`)

**3. Install Tailscale on the VPS**

SSH into your VPS and run:

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale and advertise as exit node
sudo tailscale up --advertise-exit-node

# Enable IP forwarding (required for exit node)
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
sudo sysctl -p /etc/sysctl.d/99-tailscale.conf
```

**4. Install Tailscale on Your Local Machine**

1. Download Tailscale from [tailscale.com/download](https://tailscale.com/download)
2. Install and sign in with the same account used on the VPS
3. Go to the [Tailscale Admin Console](https://login.tailscale.com/admin/machines) and **approve the exit node**

**5. Route Traffic Through the VPS**

On your local machine:

```bash
# Windows (PowerShell as Administrator)
tailscale set --exit-node=<VPS_TAILSCALE_HOSTNAME>

# Linux/macOS
sudo tailscale set --exit-node=<VPS_TAILSCALE_HOSTNAME>
```

**6. Verify Your IP**

```bash
curl ifconfig.me
# Should return: 129.154.xxx.xxx (your Oracle VPS IP)
```

**7. Whitelist in Fyers**

1. Go to [myapi.fyers.in/dashboard](https://myapi.fyers.in/dashboard/)
2. Edit your API app
3. Add the VPS public IP to the **Whitelisted IPs** field
4. Save

> **💡 Pro Tip:** You can selectively route only Fyers API traffic through the exit node using Tailscale's `--exit-node-allow-lan-access` flag, keeping your regular browsing on your normal connection.

**Oracle Always Free Tier Limits (more than enough):**
- 2 AMD Micro instances or 1 ARM Flex (4 cores, 24 GB) — **free forever**
- 200 GB block storage, 10 TB/month outbound bandwidth
- No credit card charges after signup verification

---

## 🔑 Fyers API Credentials Setup

### Step 1: Create a Fyers API App

1. Log in to [myapi.fyers.in/dashboard](https://myapi.fyers.in/dashboard/)
2. Click **Create App**
3. Fill in the details:
   - **App Name:** Any name (e.g., "MCP Trading Bot")
   - **Redirect URL:** `http://127.0.0.1:8080/`  ← **must match exactly**
   - **App Type:** Web
   - **Permissions:** Select all required permissions (orders, holdings, funds, etc.)
   - **Whitelisted IPs:** Add your static public IP (from the section above)
4. Click **Create** — you'll receive your **App ID** and **Secret Key**

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Fyers API Credentials
FYERS_CLIENT_ID=YOUR_APP_ID        # e.g., AB1C2D3E4F-100
FYERS_SECRET_KEY=YOUR_SECRET_KEY   # e.g., xK9mPqR2sT...
FYERS_REDIRECT_URI=http://127.0.0.1:8080/
```

> **Note:** The `FYERS_ACCESS_TOKEN` is automatically generated and saved to `.env` when you run the `authenticate` tool. You do not need to set it manually.

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Nandha-06/fyers-mcp-server.git
cd fyers-mcp-server
```

### 2. Create Virtual Environment & Install Dependencies

Using **uv** (recommended):

```bash
uv venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

uv pip install -e .
```

Using **pip**:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e .
```

### 3. Configure `.env`

Copy the example and fill in your credentials:

```bash
# Create .env with your credentials
echo "FYERS_CLIENT_ID=YOUR_APP_ID" > .env
echo "FYERS_SECRET_KEY=YOUR_SECRET_KEY" >> .env
echo "FYERS_REDIRECT_URI=http://127.0.0.1:8080/" >> .env
```

### 4. Test the Server

```bash
python fyers_mcp_server.py
```

If everything is configured correctly, you'll see:

```
🚀 Starting Fyers MCP Server v7.0...
```

The server is now waiting for MCP client connections over stdio.

---

## ⚙ MCP Client Configuration

Add the server to your MCP client's configuration file:

### Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fyers-mcp-server": {
      "command": "python",
      "args": ["C:\\path\\to\\fyers-mcp-server\\fyers_mcp_server.py"]
    }
  }
}
```

### Cline (VS Code Extension)

Add to Cline's MCP settings:

```json
{
  "mcpServers": {
    "fyers-mcp-server": {
      "command": "python",
      "args": ["C:\\path\\to\\fyers-mcp-server\\fyers_mcp_server.py"]
    }
  }
}
```

### OpenCode

```json
{
  "mcpServers": {
    "fyers-mcp-server": {
      "command": "python",
      "args": ["C:\\path\\to\\fyers-mcp-server\\fyers_mcp_server.py"]
    }
  }
}
```

> **Note:** Replace `C:\\path\\to\\` with the actual absolute path to your cloned repository.  
> On macOS/Linux, use forward slashes: `/home/user/fyers-mcp-server/fyers_mcp_server.py`

---

## 🔓 Authentication Flow

The server uses **Fyers OAuth 2.0** for secure authentication.

```
     ┌──────────┐         ┌──────────────┐         ┌──────────┐
     │ MCP Tool │         │ Local Server │         │  Fyers   │
     │  Client  │         │ (port 8080)  │         │  OAuth   │
     └────┬─────┘         └──────┬───────┘         └────┬─────┘
          │                      │                      │
          │  1. authenticate()   │                      │
          │─────────────────────▶│                      │
          │                      │  2. Start listener   │
          │                      │─────────┐            │
          │                      │◀────────┘            │
          │  3. Open browser     │                      │
          │  ──────────────────────────────────────────▶│
          │                      │                      │
          │                      │  4. User logs in     │
          │                      │  ◀────────────────── │
          │                      │                      │
          │                      │  5. Redirect with    │
          │                      │     auth_code        │
          │                      │◀─────────────────────│
          │                      │                      │
          │  6. Exchange code    │                      │
          │     for token        │─────────────────────▶│
          │                      │                      │
          │  7. Save token       │  8. Return token     │
          │     to .env          │◀─────────────────────│
          │◀─────────────────────│                      │
          │                      │                      │
          │  ✅ Authenticated    │                      │
```

**First time setup:**

1. Ask your AI: *"Authenticate with Fyers"*
2. A browser window opens → log in with your Fyers credentials
3. The token is automatically saved to `.env`
4. Subsequent sessions reuse the token until it expires (tokens are valid for one trading day)

> **Token Expiry:** Access tokens expire at the end of each trading day. Re-run `authenticate` the next morning.

---

## 💡 Usage Examples

Once connected to an MCP client, interact with the server using natural language:

### Market Data
```
"Get the current price of SBIN and Reliance"
"Show me the market depth for NIFTY 50 futures"
"Is the market open right now?"
"Get daily candle data for TCS for the last 3 months"
"Show me the NIFTY option chain with 10 strikes"
```

### Technical Analysis
```
"Calculate RSI and MACD for HDFCBANK"
"What are the pivot points for SBIN today?"
"Calculate VWAP for INFY"
"Detect candlestick patterns on RELIANCE daily chart"
"Analyze the open interest for NIFTY"
```

### Trading
```
"Place a market buy order for 10 shares of SBIN"
"Set a limit buy for 50 INFY at ₹1450"
"Cancel order ID 240410000012345"
"Place a GTT order to buy TCS if it drops to ₹3500"
"Exit all open positions"
```

### Portfolio
```
"Show my complete portfolio summary"
"What are my current holdings?"
"How much margin do I have available?"
"Calculate position size for SBIN with 1% risk and SL at ₹780"
"Compare SBIN, HDFCBANK, and ICICIBANK side by side"
```

### Watchlists & Alerts
```
"Create a watchlist called 'Banking Stocks' with SBIN, HDFCBANK, and ICICIBANK"
"Show me live prices for my Banking Stocks watchlist"
"Set a price alert for RELIANCE if it goes above ₹2500"
```

---

## 📁 Project Structure

```
fyers-mcp-server/
├── fyers_mcp_server.py      # Entry point — imports tool modules, starts MCP server
├── tools/
│   ├── __init__.py           # Package marker
│   ├── core.py               # Shared kernel — MCP instance, Fyers client, OAuth, helpers
│   ├── auth.py               # Authentication & session management (4 tools)
│   ├── account.py            # Funds, holdings, positions (3 tools)
│   ├── market_data.py        # Quotes, depth, history, market status, options (5 tools)
│   ├── orders.py             # Order CRUD, basket, multileg, GTT (14 tools)
│   ├── positions.py          # Exit & convert positions (2 tools)
│   ├── analysis.py           # Technical indicators, pivots, VWAP, patterns, OI (5 tools)
│   ├── utilities.py          # Symbol search, portfolio summary, risk calc (5 tools)
│   ├── watchlists.py         # Local watchlist CRUD with live enrichment (6 tools)
│   └── alerts.py             # Server-synced price alerts (3 tools)
├── pyproject.toml            # PEP 621 metadata, dependencies, tool config
├── .env                      # API credentials (git-ignored)
├── .gitignore                # Standard Python gitignore
└── uv.lock                   # Lockfile for reproducible installs
```

---

## 🗺 Feature Roadmap

Planned features and improvements for future releases:

### Near-Term

| Feature | Description |
|---|---|
| 🔄 **WebSocket Streaming** | Real-time tick-by-tick price streaming via Fyers WebSocket API for live alerts and monitoring |
| 📊 **Advanced Charting** | Generate chart images (PNG/SVG) from OHLCV data for visual analysis within the AI chat |
| 🧪 **Paper Trading Mode** | Simulated order execution against live prices for strategy testing without real capital |
| 📱 **Notification System** | Push notifications to Telegram/Discord/Slack on order fills, alerts, and P&L thresholds |

### Mid-Term

| Feature | Description |
|---|---|
| 🤖 **Strategy Backtesting** | Backtest trading strategies against historical data with P&L reporting and drawdown analysis |
| 📈 **Multi-Timeframe Analysis** | Composite analysis across multiple timeframes (e.g., daily trend + 15-min entry) |
| 🏦 **Multi-Account Support** | Switch between multiple Fyers accounts within a single MCP session |
| 📝 **Trade Journal** | Automatic trade logging with entry/exit reasons, screenshots, and performance stats |

### Long-Term

| Feature | Description |
|---|---|
| 🧠 **AI Strategy Builder** | Natural language → automated trading strategy generation and deployment |
| 🔗 **Multi-Broker Support** | Extend MCP tools to support Zerodha, Angel One, and Upstox alongside Fyers |
| 📊 **Portfolio Analytics** | Sharpe ratio, beta, sector allocation, and risk-adjusted return analysis |
| 🌍 **Market Screener** | Scan all NSE/BSE stocks against custom technical and fundamental filters |

> Have a suggestion? Open an [issue](https://github.com/Nandha-06/fyers-mcp-server/issues) or submit a PR!

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create a feature branch:** `git checkout -b feature/my-feature`
3. **Install dev dependencies:** `uv pip install -e ".[dev]"`
4. **Make your changes** — follow the modular `tools/*.py` pattern
5. **Lint:** `ruff check . && ruff format .`
6. **Type check:** `mypy .`
7. **Commit:** `git commit -m "feat: add my feature"`
8. **Push & open a PR**

### Development Guidelines

- Each new feature should be a separate `tools/*.py` module
- Use `Annotated[type, Field(description=...)]` for all tool parameters
- Import `mcp`, `create_response`, and `get_fyers_client` from `tools.core`
- Decorate tools with `@mcp.tool()` — they auto-register on the shared MCP instance
- Keep cross-module dependencies minimal

---

## ⚠️ Disclaimer

**This software is provided for educational and informational purposes only.**

- This is **not** financial advice. Trading in financial markets involves substantial risk of loss.
- The authors are **not** responsible for any financial losses incurred through the use of this software.
- Always test with small quantities before deploying any automated trading strategy.
- Ensure compliance with all applicable **SEBI regulations** and **Fyers terms of service**.
- API access tokens grant full trading permissions — **keep your `.env` file secure and never commit it to version control.**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Built with ❤️ for the Indian trading community
  <br>
  <sub>If this project helped you, consider giving it a ⭐</sub>
</p>
