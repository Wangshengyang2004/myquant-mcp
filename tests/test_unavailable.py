from common import init_gm, safe_run
from gm.api import (
    get_history_l2ticks, get_history_l2bars, get_history_l2transactions, 
    get_history_l2orders, get_history_l2orders_queue,
    fut_get_contract_info,
    fnd_get_net_value,
    bnd_get_conversion_price,
    option_get_exercise_prices
)

def test_unavailable():
    init_gm()
    
    print("\n=== Unavailable APIs (Permission/License Required) ===")
    
    # 1. Level 2 Data
    symbol = 'SHSE.600000'
    start_time = '2023-01-04 09:30:00'
    end_time = '2023-01-04 09:31:00'
    
    safe_run(lambda: get_history_l2ticks(symbol, start_time, end_time), "get_history_l2ticks")
    safe_run(lambda: get_history_l2bars(symbol, '60s', start_time, end_time), "get_history_l2bars")
    safe_run(lambda: get_history_l2transactions(symbol, start_time, end_time), "get_history_l2transactions")
    safe_run(lambda: get_history_l2orders('SZSE.000001', start_time, end_time), "get_history_l2orders")
    
    # 2. Futures Advanced Data
    safe_run(lambda: fut_get_contract_info('CFFEX.IF2306'), "fut_get_contract_info")
    
    # 3. Funds Advanced Data
    safe_run(lambda: fnd_get_net_value('SHSE.510050', '2023-01-01', '2023-01-10'), "fnd_get_net_value")
    
    # 4. Bonds Advanced Data
    safe_run(lambda: bnd_get_conversion_price('SHSE.113050', '2023-01-01', '2023-01-10'), "bnd_get_conversion_price")
    
    # 5. Options Advanced Data
    # safe_run(lambda: option_get_exercise_prices('SHSE.510050', '2023-01', 1), "option_get_exercise_prices") # 1=Call

if __name__ == "__main__":
    test_unavailable()
