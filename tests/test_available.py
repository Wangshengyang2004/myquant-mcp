import os
import pytest

if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    pytest.skip("Integration test requires a live GM/MyQuant environment", allow_module_level=True)

from common import init_gm, safe_run
from gm.api import (
    get_symbol_infos, 
    fut_get_continuous_contracts,
    # Add other potentially available functions if I verified them
)

def test_available():
    init_gm()
    
    print("\n=== Available APIs ===")
    
    # 1. Futures Basic Info
    safe_run(lambda: get_symbol_infos(sec_type1=1040, exchanges='CFFEX'), "get_symbol_infos(Futures)")
    safe_run(lambda: fut_get_continuous_contracts('CFFEX.IF'), "fut_get_continuous_contracts")
    
    # 2. Funds Basic Info
    safe_run(lambda: get_symbol_infos(sec_type1=1020, exchanges='SHSE', symbols='SHSE.510050'), "get_symbol_infos(Funds)")
    
    # 3. Bonds Basic Info
    safe_run(lambda: get_symbol_infos(sec_type1=1030, exchanges='SHSE'), "get_symbol_infos(Bonds)")
    
    # 4. Options Basic Info (Assuming it passes if options exist)
    safe_run(lambda: get_symbol_infos(sec_type1=1050, exchanges='SHSE'), "get_symbol_infos(Options)")

if __name__ == "__main__":
    test_available()
