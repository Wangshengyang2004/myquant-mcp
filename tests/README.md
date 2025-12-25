# Permission Tests

This directory contains scripts to verify permissions for different GM API functions.

*   `common.py`: Initialization and helper functions.
*   `test_available.py`: Tests for functions that should be available (basic metadata for Futures, Funds, Bonds).
*   `test_unavailable.py`: Tests for functions that require specialized permissions or licenses (L2, detailed Futures/Fund/Bond data), expected to fail if permissions are missing.

Usage:
```bash
python tests/test_available.py
python tests/test_unavailable.py
```
