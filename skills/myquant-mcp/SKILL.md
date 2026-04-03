---
name: myquant-mcp
description: Use this skill when the user wants to call this repository's MyQuant HTTP tools through a local helper script instead of wiring MCP directly. This skill uses the bundled `scripts/client.py` client to call the repo's HTTP API, including protected account and trading tools when an auth token is passed explicitly.
---

# MyQuant MCP

Use the bundled `scripts/client.py` helper when the user wants skill-based access to this repository's MyQuant HTTP API.

## What this skill does

- Query market data, fundamental data, account tools, trading tools, and the higher-level `stock_do_t` helpers from a running MyQuant server.
- List available tools directly from the live server.
- Explain how to pass `--url` when the server is not running on `http://localhost:8001`.
- Explain how to pass `--auth-token` explicitly for protected tools.
- Save API results to JSON or CSV through the helper script.

## Important limits

- This skill uses `scripts/client.py`, which talks to the HTTP REST API.
- HTTP and MCP now expose the same tool set.
- Protected account and trading tools require the same `auth_token` as MCP.
- Because the skill may be installed into another agent workspace, it should not assume it can read this repo's `.env`.
- Pass `--auth-token <MCP_AUTH_TOKEN>` explicitly on the command line for protected tools.
- Trading APIs are more sensitive than pure data APIs, so keep token handling explicit and avoid embedding tokens in the skill itself.

## Quick workflow

1. Confirm the server is running with `python server.py`.
2. Use `python skills/myquant-mcp/scripts/client.py --list-tools` to inspect tools from the live server.
3. Use `python skills/myquant-mcp/scripts/client.py <tool_name> ...` to call public tools.
4. Use `python skills/myquant-mcp/scripts/client.py --auth-token <MCP_AUTH_TOKEN> <tool_name> ...` for protected account, trading, and `stock_do_t` tools.
5. Add `--url http://host:8001` if the server runs elsewhere.

## Common examples

```bash
python skills/myquant-mcp/scripts/client.py --list-tools
python skills/myquant-mcp/scripts/client.py --info history
python skills/myquant-mcp/scripts/client.py history --symbol SHSE.600000 --frequency 1d --start-time 2024-01-01 --end-time 2024-12-31
python skills/myquant-mcp/scripts/client.py stk_get_daily_valuation --symbols SHSE.600519 --fields pe_ttm,pb_lyr
python skills/myquant-mcp/scripts/client.py --auth-token YOUR_TOKEN get_positions
python skills/myquant-mcp/scripts/client.py --auth-token YOUR_TOKEN stock_do_t --symbol SZSE.000001 --direction buy_then_sell --volume 1000 --expire-seconds 30 --entry-trigger-price 10.00 --entry-order-price 10.00 --take-profit-pct 3 --stop-loss-price 9.70
```

## References

- Read `README.md` for direct MCP setup in Cursor, Claude Code, and OpenClaw.
- Read `references/mcp-config.md` for the bundled config files and when to prefer the skill path instead.
