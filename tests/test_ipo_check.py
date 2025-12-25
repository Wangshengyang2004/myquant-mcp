from common import init_gm, safe_run
from gm.api import ipo_get_instruments, ipo_get_quota

def test_ipo():
    init_gm()
    
    print("\n=== Testing IPO Functions ===")
    # Query IPO instruments for a date range
    safe_run(lambda: ipo_get_instruments('2023-01-01', '2023-06-01'), "ipo_get_instruments")
    
    # Query IPO quota
    safe_run(lambda: ipo_get_quota(), "ipo_get_quota")

if __name__ == "__main__":
    test_ipo()
