# Security Policy

## Supported usage

This project can expose account data and optional trading operations. Treat deployments as sensitive.

## Safe defaults

- Keep `TRADING_ENABLED=false` unless you explicitly need live trading.
- Set a strong `MCP_AUTH_TOKEN` before enabling protected account or trading tools.
- Do not commit `.env`, tokens, account ids, or generated audit logs.
- Prefer running against a dedicated MyQuant account for testing.

## Reporting a vulnerability

Please report suspected security issues privately to the maintainers before opening a public issue. Include:

1. A short description of the issue.
2. Reproduction steps.
3. Impact assessment.
4. Any suggested mitigation.

If a private reporting channel has not been set up yet, avoid posting exploit details publicly until a fix is available.
