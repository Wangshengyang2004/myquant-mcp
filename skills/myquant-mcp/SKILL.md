---
name: myquant-mcp
description: Calls this repository's MyQuant HTTP tools via bundled scripts/client.py (no direct MCP wiring); supports protected account, trading, and stock_do_t when the user passes --auth-token. Use when the user mentions MyQuant MCP, HTTP API, client.py, or skill helper scripts.
---

# MyQuant MCP

Use the bundled `scripts/client.py` helper when the user wants skill-based access to this repository's MyQuant HTTP API.

## What this skill does

- Query market data, fundamental data, account tools, trading tools, and the higher-level `stock_do_t` helpers from a running MyQuant server.
- List available tools directly from the live server.
- Explain how to pass `--url` when the server is not running on `http://localhost:8001`.
- Explain how to pass `--auth-token` explicitly for protected tools.
- Save API results to JSON or CSV through the helper script.

## HTTP 工具覆盖（与 MCP 一致）

- 服务端注册的**全部工具**（当前共 **61** 个：行情 12、基本面 31、账户/成交 4、交易 11、`stock_do_t` 系 3）都走同一 HTTP 工具接口；**任意工具名**均可作为 `client.py` 的第一个位置参数调用。
- **权威清单**：在仓库根目录执行 `python skills/myquant-mcp/scripts/client.py --list-tools`（需服务已启动），输出含 Public / Protected 分组；`--info <tool_name>` 查看该工具的参数 schema（与 MCP 相同）。
- **`scripts/client.py` 里的 `DATA_TOOLS`**：仅为**行情 + 基本面**共 43 个工具的离线说明，用于服务不可达时 `--list-tools` 的回退展示；**不包含**账户、下单、`stock_do_t*`——这些必须连上服务后用 `--list-tools` / `--info` 或查仓库 `server/tools/{execution,trading,do_t}.py`。
- **鉴权**：凡带服务端 `auth_token` 参数的工具（账户、交易、`stock_do_t*` 共 18 个）在命令行用 `--auth-token <MCP_AUTH_TOKEN>`；行情与基本面工具**无**该参数。默认 `REQUIRE_AUTH_TOKEN=true` 时，未配置或错误的 `MCP_AUTH_TOKEN` 会导致受保护工具失败；若部署改为 `REQUIRE_AUTH_TOKEN=false`，以服务端实际校验逻辑为准。
- **调用方式**：默认 **POST** JSON 到 `/api/v1/tools/{tool_name}`；需要 query 形式时用 **`--get`**（见 `client.py --help`）。

## Important limits

- This skill uses `scripts/client.py`, which talks to the HTTP REST API.
- HTTP and MCP now expose the same tool set.
- Protected account and trading tools require the same `auth_token` as MCP.
- Because the skill may be installed into another agent workspace, it should not assume it can read this repo's `.env`.
- Pass `--auth-token <MCP_AUTH_TOKEN>` explicitly on the command line for protected tools.
- Trading APIs are more sensitive than pure data APIs, so keep token handling explicit and avoid embedding tokens in the skill itself.

## Quick workflow

1. `cd` to the **repository root** (paths below assume `skills/myquant-mcp/` lives under that root).
2. Confirm the server is running with `python server.py`.
3. Use `python skills/myquant-mcp/scripts/client.py --list-tools` to inspect tools from the live server.
4. Use `python skills/myquant-mcp/scripts/client.py <tool_name> ...` to call public tools.
5. Use `python skills/myquant-mcp/scripts/client.py --auth-token <MCP_AUTH_TOKEN> <tool_name> ...` for protected account, trading, and `stock_do_t` tools.
6. Add `--url http://host:8001` if the server runs elsewhere.

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

- Read the repository root [README.md](../../README.md) for direct MCP setup in Cursor, Claude Code, and OpenClaw.
- Read [references/mcp-config.md](references/mcp-config.md) for bundled config files and when to prefer the skill path instead.
