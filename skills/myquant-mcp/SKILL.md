---
name: myquant-mcp
description: Use this skill when the user wants to query this repository's MyQuant data tools through a local helper script instead of wiring MCP directly. This skill uses the bundled `scripts/client.py` client to call the repo's read-only HTTP API for market and fundamental data tasks.
---

# MyQuant MCP

Use the bundled `scripts/client.py` helper when the user wants skill-based access to this repository's MyQuant data API.

## What this skill does

- Query market and fundamental data from a running local MyQuant server.
- List available read-only tools.
- Explain how to pass `--url` when the server is not running on `http://localhost:8001`.
- Save API results to JSON or CSV through the helper script.

## Important limits

- This skill uses `scripts/client.py`, which talks to the REST API.
- The REST API intentionally blocks protected account and trading tools.
- Exposing trading APIs through a general-purpose skill is more vulnerable and increases operational risk.
- For that reason, this skill is limited to data APIs only.
- Use direct MCP integration when the user needs protected account or trading workflows.

## Quick workflow

1. Confirm the server is running with `python server.py`.
2. Use `python skills/myquant-mcp/scripts/client.py --list-tools` to inspect read-only tools.
3. Use `python skills/myquant-mcp/scripts/client.py <tool_name> ...` to call a data tool.
4. Add `--url http://host:8001` if the server runs elsewhere.

## Common examples

```bash
python skills/myquant-mcp/scripts/client.py --list-tools
python skills/myquant-mcp/scripts/client.py --info history
python skills/myquant-mcp/scripts/client.py history --symbol SHSE.600000 --frequency 1d --start-time 2024-01-01 --end-time 2024-12-31
python skills/myquant-mcp/scripts/client.py stk_get_daily_valuation --symbols SHSE.600519 --fields pe_ttm,pb_lyr
```

## References

- Read `README.md` for direct MCP setup in Cursor, Claude Code, and OpenClaw.
- Read `references/mcp-config.md` for the bundled config files and when to prefer the skill path instead.
