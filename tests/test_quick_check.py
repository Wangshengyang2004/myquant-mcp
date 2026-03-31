import os
import pytest

if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    pytest.skip("Integration test requires a live GM/MyQuant environment", allow_module_level=True)

from common import init_gm, safe_run
from gm.api import (
    stk_get_fundamentals_balance_pt, 
    credit_get_collateral_instruments
)

def test_quick():
    init_gm()
    
    print("\n=== Testing Fundamentals (Balance Sheet) ===")
    # SHSE.600000, 2022-09-30
    safe_run(lambda: stk_get_fundamentals_balance_pt(symbols='SHSE.600000', fields='total_assets', trade_date='2022-09-30'), "stk_get_fundamentals_balance_pt")

    print("\n=== Testing Credit Query ===")
    safe_run(lambda: credit_get_collateral_instruments(), "credit_get_collateral_instruments")

if __name__ == "__main__":
    test_quick()
