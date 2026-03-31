# MyQuant MCP integration notes

## Direct MCP path

- Cursor reads `.cursor/mcp.json` and should point `url` at `http://127.0.0.1:8001/mcp/` or your deployed endpoint.
- Claude Code can read the project `.mcp.json`, using `type: "http"` plus the MCP endpoint URL.
- OpenClaw can import this repository as a Claude-compatible bundle because the repo includes `skills/` and `.mcp.json`.

## Skill path

Use `scripts/client.py` when the model should query read-only HTTP data tools without configuring MCP directly.

## Important limitation

`scripts/client.py` talks to the REST API only, so it cannot access protected account or trading tools.
