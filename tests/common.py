import os
import sys
from gm.api import *
from dotenv import load_dotenv

def init_gm():
    # Load from parent directory .env
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    
    token = os.getenv("GM_TOKEN")
    if not token:
        print("Error: GM_TOKEN not found in .env")
        sys.exit(1)
        
    set_token(token)
    # No need to set_serv_addr for local terminal
    print("GM SDK Initialized.")

def safe_run(func, name):
    print(f"\n--- Testing {name} ---")
    try:
        res = func()
        print(f"PASS: {name} returned data type: {type(res)}")
        if isinstance(res, list):
            print(f"Count: {len(res)}")
            if len(res) > 0:
                print(f"Sample: {res[0]}")
        elif isinstance(res, dict):
            print(f"Data keys: {list(res.keys())}")
        else:
            print(f"Data: {res}")
        return True
    except Exception as e:
        print(f"FAIL: {name} Error: {e}")
        return False
