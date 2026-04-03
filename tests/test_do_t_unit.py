import asyncio
import json
from datetime import datetime
from pathlib import Path

from server.tools import do_t

TEST_DB_DIR = Path(__file__).resolve().parent.parent / ".local"


def _reset_runtime(delete_db=False):
    do_t._DO_T_RUNTIME["states"].clear()
    do_t._DO_T_RUNTIME["order_index"].clear()
    do_t._DO_T_RUNTIME["exec_ids"].clear()
    do_t._DO_T_RUNTIME["loaded"] = False
    if delete_db:
        db_path = Path(do_t.DO_T_SQLITE_PATH)
        if db_path.exists():
            db_path.unlink()


def _use_temp_db(monkeypatch, db_name):
    monkeypatch.setattr(do_t, "DO_T_SQLITE_PATH", TEST_DB_DIR / db_name)
    _reset_runtime(delete_db=True)


def test_stock_do_t_submits_first_leg_for_buy_then_sell(monkeypatch):
    fixed_now = datetime(2026, 4, 1, 10, 0, 0)
    _use_temp_db(monkeypatch, "test_do_t_submit.sqlite3")

    monkeypatch.setattr(do_t, "validate_auth", lambda auth_token: auth_token == "secret")
    monkeypatch.setattr(do_t, "gm_get_execution_reports", lambda: [])
    monkeypatch.setattr(do_t, "gm_get_orders", lambda: [])
    monkeypatch.setattr(
        do_t,
        "gm_current_price",
        lambda symbols: [{"symbol": symbols, "price": 10.0, "created_at": fixed_now}],
    )
    monkeypatch.setattr(
        do_t,
        "gm_get_position",
        lambda account_id=None: [{"symbol": "SZSE.000001", "side": do_t.PositionSide_Long, "available": 1000}],
    )
    monkeypatch.setattr(do_t, "gm_get_cash", lambda account_id=None: {"available": 20000.0})
    monkeypatch.setattr(do_t, "gm_set_account_id", lambda account_id: None)
    monkeypatch.setattr(
        do_t,
        "gm_order_volume",
        lambda **kwargs: [{"cl_ord_id": "ORD-1", "account_id": kwargs.get("account", "ACC")}],
    )

    result = asyncio.run(
        do_t.stock_do_t(
            auth_token="secret",
            symbol="SZSE.000001",
            direction=do_t.BUY_THEN_SELL,
            volume=1000,
            expire_seconds=30,
            entry_trigger_price=10.1,
            entry_order_price=10.0,
            take_profit_pct=3,
            stop_loss_price=9.7,
        )
    )
    body = json.loads(result)

    assert body["phase"] == "leg1_submitted"
    assert body["active_order"]["cl_ord_id"] == "ORD-1"
    assert body["locked_base_volume"] == 1000


def test_stock_do_t_fails_when_buy_then_sell_lacks_base_position(monkeypatch):
    fixed_now = datetime(2026, 4, 1, 10, 5, 0)
    _use_temp_db(monkeypatch, "test_do_t_fail.sqlite3")

    monkeypatch.setattr(do_t, "validate_auth", lambda auth_token: auth_token == "secret")
    monkeypatch.setattr(do_t, "gm_get_execution_reports", lambda: [])
    monkeypatch.setattr(do_t, "gm_get_orders", lambda: [])
    monkeypatch.setattr(
        do_t,
        "gm_current_price",
        lambda symbols: [{"symbol": symbols, "price": 10.0, "created_at": fixed_now}],
    )
    monkeypatch.setattr(
        do_t,
        "gm_get_position",
        lambda account_id=None: [{"symbol": "SZSE.000001", "side": do_t.PositionSide_Long, "available": 500}],
    )
    monkeypatch.setattr(do_t, "gm_get_cash", lambda account_id=None: {"available": 20000.0})

    result = asyncio.run(
        do_t.stock_do_t(
            auth_token="secret",
            symbol="SZSE.000001",
            direction=do_t.BUY_THEN_SELL,
            volume=1000,
            expire_seconds=30,
            entry_trigger_price=10.1,
            entry_order_price=10.0,
            take_profit_pct=3,
            stop_loss_price=9.7,
        )
    )
    body = json.loads(result)

    assert body["phase"] == "failed"
    assert body["last_error"] == "buy_then_sell 需要足够底仓用于后续卖出"


def test_stock_do_t_reset_removes_target_state(monkeypatch):
    _use_temp_db(monkeypatch, "test_do_t_reset.sqlite3")
    monkeypatch.setattr(do_t, "validate_auth", lambda auth_token: auth_token == "secret")

    state_key = "SZSE.000001:buy_then_sell:2026-04-01"
    do_t._DO_T_RUNTIME["states"][state_key] = {"state_key": state_key, "phase": "waiting_entry"}
    do_t._DO_T_RUNTIME["order_index"]["ORD-1"] = {"state_key": state_key, "leg": "leg1"}
    do_t._DO_T_RUNTIME["exec_ids"].add("EX-1")
    do_t._DO_T_RUNTIME["loaded"] = True

    result = asyncio.run(
        do_t.stock_do_t_reset(
            auth_token="secret",
            symbol="SZSE.000001",
            direction="buy_then_sell",
            trade_date="2026-04-01",
        )
    )
    body = json.loads(result)

    assert body["success"] is True
    assert body["removed"] is True
    assert body["cleared_orders"] == ["ORD-1"]
    assert state_key not in do_t._DO_T_RUNTIME["states"]


def test_stock_do_t_state_persists_to_sqlite(monkeypatch):
    fixed_now = datetime(2026, 4, 1, 10, 10, 0)
    _use_temp_db(monkeypatch, "test_do_t_persist.sqlite3")

    monkeypatch.setattr(do_t, "validate_auth", lambda auth_token: auth_token == "secret")
    monkeypatch.setattr(do_t, "gm_get_execution_reports", lambda: [])
    monkeypatch.setattr(do_t, "gm_get_orders", lambda: [])
    monkeypatch.setattr(
        do_t,
        "gm_current_price",
        lambda symbols: [{"symbol": symbols, "price": 10.0, "created_at": fixed_now}],
    )
    monkeypatch.setattr(
        do_t,
        "gm_get_position",
        lambda account_id=None: [{"symbol": "SZSE.000001", "side": do_t.PositionSide_Long, "available": 1000}],
    )
    monkeypatch.setattr(do_t, "gm_get_cash", lambda account_id=None: {"available": 20000.0})
    monkeypatch.setattr(do_t, "gm_set_account_id", lambda account_id: None)
    monkeypatch.setattr(
        do_t,
        "gm_order_volume",
        lambda **kwargs: [{"cl_ord_id": "ORD-DB", "account_id": kwargs.get("account", "ACC")}],
    )

    asyncio.run(
        do_t.stock_do_t(
            auth_token="secret",
            symbol="SZSE.000001",
            direction=do_t.BUY_THEN_SELL,
            volume=1000,
            expire_seconds=30,
            entry_trigger_price=10.1,
            entry_order_price=10.0,
            take_profit_pct=3,
            stop_loss_price=9.7,
        )
    )

    _reset_runtime(delete_db=False)

    result = asyncio.run(
        do_t.stock_do_t_get_state(
            auth_token="secret",
            symbol="SZSE.000001",
            direction=do_t.BUY_THEN_SELL,
            trade_date="2026-04-01",
        )
    )
    body = json.loads(result)

    assert body["found"] is True
    assert body["phase"] == "leg1_submitted"
    assert body["active_order"]["cl_ord_id"] == "ORD-DB"


def test_stock_do_t_forces_exit_after_1455(monkeypatch):
    fixed_now = datetime(2026, 4, 1, 14, 56, 0)
    _use_temp_db(monkeypatch, "test_do_t_force.sqlite3")

    monkeypatch.setattr(do_t, "validate_auth", lambda auth_token: auth_token == "secret")
    monkeypatch.setattr(do_t, "gm_get_execution_reports", lambda: [])
    monkeypatch.setattr(do_t, "gm_get_orders", lambda: [])
    monkeypatch.setattr(
        do_t,
        "gm_current_price",
        lambda symbols: [{"symbol": symbols, "price": 10.0, "created_at": fixed_now}],
    )
    monkeypatch.setattr(
        do_t,
        "gm_get_position",
        lambda account_id=None: [{"symbol": "SZSE.000001", "side": do_t.PositionSide_Long, "available": 1000}],
    )
    monkeypatch.setattr(do_t, "gm_get_cash", lambda account_id=None: {"available": 20000.0})
    monkeypatch.setattr(do_t, "gm_set_account_id", lambda account_id: None)

    seen = {}

    def _order_volume(**kwargs):
        seen.update(kwargs)
        return [{"cl_ord_id": "ORD-FORCE", "account_id": kwargs.get("account", "ACC")}]

    monkeypatch.setattr(do_t, "gm_order_volume", _order_volume)

    state_key = do_t._state_key("SZSE.000001", do_t.BUY_THEN_SELL, fixed_now)
    state = do_t._create_state(
        state_key=state_key,
        now=fixed_now,
        symbol="SZSE.000001",
        direction=do_t.BUY_THEN_SELL,
        volume=1000,
        expire_seconds=30,
        entry_trigger_price=10.0,
        entry_order_price=10.0,
        take_profit_price=None,
        take_profit_ratio=0.03,
        stop_loss_price=9.7,
        stop_loss_ratio=None,
        order_type=do_t.OrderType_Limit,
        account_id=None,
    )
    state.update(
        {
            "phase": "waiting_exit",
            "entry_order_filled": True,
            "entry_filled_volume": 1000,
            "entry_filled_amount": 10000.0,
            "entry_avg_price": 10.0,
            "exit_target_volume": 1000,
            "armed_take_profit_price": 10.3,
            "armed_stop_loss_price": 9.7,
            "locked_base_volume": 1000,
        }
    )
    do_t._DO_T_RUNTIME["states"][state_key] = state
    do_t._persist_state(state)

    result = asyncio.run(
        do_t.stock_do_t(
            auth_token="secret",
            symbol="SZSE.000001",
            direction=do_t.BUY_THEN_SELL,
            volume=1000,
            expire_seconds=30,
            entry_trigger_price=10.0,
            entry_order_price=10.0,
            take_profit_pct=3,
            stop_loss_price=9.7,
        )
    )
    body = json.loads(result)

    assert body["phase"] == "leg2_submitted"
    assert body["exit_reason"] == "forced_settlement"
    assert body["force_settlement"] is True
    assert seen["price"] == 10.0
    assert seen["side"] == do_t.OrderSide_Sell
