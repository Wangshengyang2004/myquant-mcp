# Contributing

Thanks for considering a contribution.

## Development setup

1. Create a Python 3.10+ virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Add a valid `GM_TOKEN`.
5. Keep `TRADING_ENABLED=false` unless you are intentionally testing trading features.

## Before opening a pull request

1. Keep changes focused and documented.
2. Update `README.md` when behavior or setup changes.
3. Add or update tests when practical.
4. Do not commit secrets, local `.env` files, or generated logs.

## Testing notes

The current test scripts under `tests/` are integration-style checks against a live MyQuant environment. They require local credentials and access to a running 掘金量化 terminal, so they are not expected to run in public CI as-is.

If you add coverage for logic that can run offline, prefer small isolated tests that do not require live market access.
