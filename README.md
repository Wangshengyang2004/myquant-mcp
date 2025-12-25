# MyQuant Financial Agent MCP Server

A comprehensive Model Context Protocol (MCP) server for financial operations using 掘金量化 (MyQuant) GM API. This server enables Claude Code and other MCP clients to interact with Chinese stock market data, perform financial analysis, and execute trading operations with built-in security controls.

## Features

### Market Data Tools 📊
- **Real-time & Historical Price Data**: Query stock prices with various frequencies (tick, daily, minute-level)
- **Fundamental Analysis**: Access PE ratio, market cap, EPS, ROE, and other financial metrics
- **Market Value Indicators**: Total market value, A-share market value, valuation ratios
- **Stock Search**: Find stocks by name or symbol pattern
- **Dragon Tiger List**: Track stocks with unusual trading activity (异动股)
- **Return Analysis**: Analyze historical returns and predict future performance

### Trading Operations 💰 (Optional)
- **Order Placement**: Place buy/sell orders with safety limits
- **Position Management**: Query current holdings
- **Order History**: Track executed trades
- **Multi-level Security**: Authentication tokens, trading limits, and safeguards

### Security Features 🔒
- **Authentication Required**: Mandatory tokens for trading operations
- **Trading Limits**: Configurable maximum order value and position percentage
- **Read-only Mode**: Disable trading completely for data analysis only
- **GM Token Protection**: Separate token management for MyQuant platform access

## Installation

### Prerequisites
- Python 3.10+
- 掘金量化 (MyQuant) account with API token
- Access to a machine running 掘金量化 GUI (for data access)

### Setup Steps

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd myquant-mcp
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Configure .env file**
```bash
# Required: Your GM API token from MyQuant platform
GM_TOKEN=your_gm_token_here

# Required for trading: Generate a secure authentication token
MCP_AUTH_TOKEN=your_secure_token_here

# Optional: Trading safety settings
TRADING_ENABLED=false          # Set to true to enable trading
MAX_ORDER_VALUE=100000         # Maximum order value in CNY
MAX_POSITION_PERCENT=0.1       # Maximum 10% of portfolio per position
```

### Generate Secure Auth Token
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Usage with Claude Code

### Configuration in Claude Code

Add the following to your Claude Code MCP settings configuration file:

**For macOS/Linux** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "myquant-financial": {
      "command": "python",
      "args": ["/path/to/myquant-mcp/server.py"],
      "env": {
        "GM_TOKEN": "your_gm_token",
        "MCP_AUTH_TOKEN": "your_auth_token",
        "TRADING_ENABLED": "false",
        "MAX_ORDER_VALUE": "100000",
        "MAX_POSITION_PERCENT": "0.1"
      }
    }
  }
}
```

**For Windows** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "myquant-financial": {
      "command": "python",
      "args": ["C:\\path\\to\\myquant-mcp\\server.py"],
      "env": {
        "GM_TOKEN": "your_gm_token",
        "MCP_AUTH_TOKEN": "your_auth_token",
        "TRADING_ENABLED": "false"
      }
    }
  }
}
```

### Alternative: Using .env file
```json
{
  "mcpServers": {
    "myquant-financial": {
      "command": "python",
      "args": ["/path/to/myquant-mcp/server.py"]
    }
  }
}
```
(Make sure `.env` file is configured in the project directory)

## Example Queries

Once configured, you can interact with Claude Code using natural language:

### Market Data Queries

**Stock Price Monitoring**
```
"What is the current price of stock 000001?"
"Show me the daily price history of 茅台 (600519) for the last 30 days"
"Watch the stock price for 000001 and alert me of any changes"
```

**Fundamental Analysis**
```
"What is the PE ratio of Maotai (贵州茅台)?"
"Show me the financial metrics for 平安银行 (000001)"
"Compare the market cap and PE ratios of 工商银行 vs 建设银行"
```

**Market Analysis**
```
"Show me today's Dragon Tiger List stocks"
"Which stocks have unusual trading activity?"
"Find all stocks related to '新能源' (new energy)"
```

**Return Prediction**
```
"Help me predict the future return by holding 000002 for next month"
"Analyze the historical return pattern of 600519 for 30-day holding period"
```

### Trading Operations (when TRADING_ENABLED=true)

**Placing Orders**
```
"Buy 100 shares of 600000 at 15.5 CNY" (requires auth_token)
"Sell 500 shares of 000001 at market price" (requires auth_token)
```

**Portfolio Management**
```
"Show my current positions" (requires auth_token)
"What orders have I placed today?" (requires auth_token)
```

## Available Tools

### Market Data Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_stock_price` | Get current/historical price data | symbol, frequency, count, end_time, adjust |
| `get_stock_fundamentals` | Get fundamental metrics (PE, EPS, ROE, etc.) | symbols, fields, date |
| `get_market_value_indicators` | Get market value indicators | symbols, fields, trade_date |
| `search_stocks` | Search stocks by name/code | query, exchanges |
| `get_dragon_tiger_list` | Get unusual trading activity stocks | symbols, change_types, trade_date |
| `analyze_stock_return` | Analyze returns and predict | symbol, holding_days, history_days |

### Trading Tools (when enabled)

| Tool | Description | Auth Required | Parameters |
|------|-------------|---------------|------------|
| `place_order` | Place buy/sell order | ✅ | auth_token, symbol, volume, side, price, order_type |
| `get_positions` | Get current positions | ✅ | auth_token |
| `get_orders` | Get order history | ✅ | auth_token |

## Stock Symbol Format

MyQuant uses the following symbol format:
- Shanghai Stock Exchange: `SHSE.XXXXXX` (e.g., `SHSE.600519` for 贵州茅台)
- Shenzhen Stock Exchange: `SZSE.XXXXXX` (e.g., `SZSE.000001` for 平安银行)

## Data Frequencies

Supported frequency values:
- `tick` - Tick-level data
- `1d` - Daily bars
- `60s`, `1m` - 1-minute bars
- `5m` - 5-minute bars
- `15m` - 15-minute bars
- `30m` - 30-minute bars
- `1h` - Hourly bars

## Financial Fields

### Fundamental Data Fields
- `eps_basic` - Basic earnings per share
- `eps_dil2` - Diluted earnings per share
- `roe` - Return on equity
- `roa` - Return on assets
- `pe_ratio` - Price-to-earnings ratio
- `pb_ratio` - Price-to-book ratio

### Market Value Fields
- `tot_mv` - Total market value
- `a_mv` - A-share market value
- `tot_mv_csrc` - CSRC total market value
- `pe_ratio` - PE ratio (valuation)
- `pb_ratio` - PB ratio (valuation)

## Security & Safety

### Multi-layer Protection

1. **Environment Isolation**: Trading operations disabled by default
2. **Authentication**: Mandatory auth token for all trading functions
3. **Value Limits**: Maximum order value protection (default: 100,000 CNY)
4. **Position Limits**: Maximum position percentage (default: 10%)
5. **Token Security**: Separate GM token from MCP authentication

### Best Practices

- **Never commit tokens**: Use `.env` files and keep them in `.gitignore`
- **Start with read-only**: Test with `TRADING_ENABLED=false` first
- **Use strict limits**: Set conservative `MAX_ORDER_VALUE` and `MAX_POSITION_PERCENT`
- **Rotate tokens**: Regularly update your authentication tokens
- **Monitor logs**: Keep track of all trading operations

### Read-Only Mode

For maximum safety during development or analysis:
```bash
# In .env file
TRADING_ENABLED=false
```

This disables all trading tools while keeping market data access fully functional.

## Error Handling

The server provides detailed error messages:

- **GM API not available**: Install `gm-python-sdk`
- **Token not configured**: Set `GM_TOKEN` in environment
- **Invalid authentication**: Check `MCP_AUTH_TOKEN` matches
- **Order exceeds limits**: Reduce order size or increase limits
- **Invalid symbol**: Use correct format (SHSE.XXXXXX or SZSE.XXXXXX)

## Troubleshooting

### Common Issues

**1. "GM API not available"**
```bash
pip install gm-python-sdk
```

**2. "GM_TOKEN not configured"**
- Check `.env` file exists and contains `GM_TOKEN`
- Verify GM_TOKEN is valid from MyQuant platform
- Ensure 掘金量化 GUI is running on the machine

**3. "Invalid authentication token"**
- Verify `MCP_AUTH_TOKEN` in `.env` matches the token you're using
- Generate a new secure token if needed

**4. Connection issues**
- Ensure 掘金量化 GUI application is running
- Check network connectivity to MyQuant servers
- Verify your GM account is active and has API access

## Development

### Project Structure
```
myquant-mcp/
├── server.py              # Main MCP server implementation
├── requirements.txt       # Python dependencies
├── pyproject.toml        # Package configuration
├── .env.example          # Environment template
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

### Adding New Tools

To add a new tool:

1. Define the tool schema in `handle_list_tools()`
2. Implement the handler in `handle_call_tool()`
3. Add documentation to this README
4. Update the tool table above

### Testing

Test individual tools:
```python
# Test price query
python -c "from server import *; import asyncio; asyncio.run(test_price_query())"
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Disclaimer

**IMPORTANT**: This software is for educational and research purposes only.

- Not financial advice
- No warranty provided
- Use at your own risk
- Test thoroughly before live trading
- Past performance doesn't guarantee future results
- Consult a financial advisor before making investment decisions

## Support

- **Issues**: Report bugs via GitHub Issues
- **Documentation**: See [GM API Docs](https://www.myquant.cn/docs)
- **Community**: Join 掘金量化 community forums

## Acknowledgments

- Built on [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Powered by [掘金量化 (MyQuant)](https://www.myquant.cn/) GM API
- Designed for [Claude Code](https://claude.com/code)

## Changelog

### Version 0.1.0 (Initial Release)
- Market data query tools
- Fundamental analysis tools
- Trading operations (optional)
- Authentication and security features
- Return analysis and prediction
- Dragon Tiger List tracking
