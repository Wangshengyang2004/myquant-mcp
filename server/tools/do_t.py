"""
Advanced intraday T+0 style trading helpers.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, time as dt_time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Optional

from gm.api import (
    OrderSide_Buy,
    OrderSide_Sell,
    OrderStatus_Canceled,
    OrderStatus_Expired,
    OrderStatus_Filled,
    OrderStatus_PartiallyFilled,
    OrderStatus_Rejected,
    OrderType_Limit,
    PositionEffect_Close,
    PositionEffect_Open,
    PositionSide_Long,
    current_price as gm_current_price,
    get_cash as gm_get_cash,
    get_execution_reports as gm_get_execution_reports,
    get_orders as gm_get_orders,
    get_position as gm_get_position,
    order_cancel as gm_order_cancel,
    order_volume as gm_order_volume,
    set_account_id as gm_set_account_id,
)

from server.config import BASE_DIR, DEFAULT_ACCOUNT_ID, audit_wrapper, validate_auth
from server.mcp_server import mcp
from server.tools import tool_registry

BUY_THEN_SELL = "buy_then_sell"
SELL_THEN_BUY = "sell_then_buy"
DONE_STATES = {"done", "failed", "canceled"}
FORCE_SETTLEMENT_TIME = dt_time(hour=14, minute=55)
DO_T_SQLITE_PATH = BASE_DIR / ".local" / "do_t_state.sqlite3"
_STATE_DATETIME_FIELDS = {
    "created_at",
    "updated_at",
    "active_order_submitted_at",
}

_DO_T_RUNTIME = {
    "states": {},
    "order_index": {},
    "exec_ids": set(),
    "loaded": False,
}


def _get_field(data: Any, field: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(field, default)
    return getattr(data, field, default)


def _as_items(data: Any) -> list:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def _round_price(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _normalize_pct(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if value <= 0:
        raise ValueError("百分比必须大于 0")
    return value / 100.0 if value >= 1 else value


def _event_time(market_data: Optional[Any] = None) -> datetime:
    created_at = _get_field(market_data, "created_at") if market_data is not None else None
    if isinstance(created_at, datetime):
        return created_at
    return datetime.now()


def _state_key(symbol: str, direction: str, now: datetime) -> str:
    return f"{symbol}:{direction}:{now.strftime('%Y-%m-%d')}"


def _reset_runtime_state() -> None:
    _DO_T_RUNTIME.setdefault("states", {})
    _DO_T_RUNTIME.setdefault("order_index", {})
    _DO_T_RUNTIME.setdefault("exec_ids", set())
    if not _DO_T_RUNTIME.get("loaded"):
        _load_runtime_state()


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return value


def _normalize_sqlite_path(path: Path | str) -> Path:
    return path if isinstance(path, Path) else Path(path)


def _connect_db() -> sqlite3.Connection:
    db_path = _normalize_sqlite_path(DO_T_SQLITE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _db_connection():
    conn = _connect_db()
    try:
        yield conn
    finally:
        conn.close()


def _ensure_db_schema() -> None:
    with _db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS do_t_states (
                state_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS do_t_order_index (
                cl_ord_id TEXT PRIMARY KEY,
                state_key TEXT NOT NULL,
                leg TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS do_t_exec_ids (
                exec_id TEXT PRIMARY KEY
            )
            """
        )
        conn.commit()


def _deserialize_state(payload: str) -> dict:
    state = json.loads(payload)
    for field in _STATE_DATETIME_FIELDS:
        value = state.get(field)
        if isinstance(value, str):
            with_value = value.replace("T", " ")
            state[field] = datetime.fromisoformat(with_value)
    return state


def _load_runtime_state() -> None:
    _ensure_db_schema()

    with _db_connection() as conn:
        states = {
            row["state_key"]: _deserialize_state(row["payload"])
            for row in conn.execute("SELECT state_key, payload FROM do_t_states")
        }
        order_index = {
            row["cl_ord_id"]: {"state_key": row["state_key"], "leg": row["leg"]}
            for row in conn.execute("SELECT cl_ord_id, state_key, leg FROM do_t_order_index")
        }
        exec_ids = {
            row["exec_id"]
            for row in conn.execute("SELECT exec_id FROM do_t_exec_ids")
        }

    _DO_T_RUNTIME["states"] = states
    _DO_T_RUNTIME["order_index"] = order_index
    _DO_T_RUNTIME["exec_ids"] = exec_ids
    _DO_T_RUNTIME["loaded"] = True


def _persist_state(state: dict) -> None:
    _ensure_db_schema()
    payload = json.dumps(state, ensure_ascii=False, default=_json_default)
    with _db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO do_t_states(state_key, payload) VALUES(?, ?)",
            (state["state_key"], payload),
        )
        conn.commit()


def _remove_state(state_key: str) -> None:
    _ensure_db_schema()
    with _db_connection() as conn:
        conn.execute("DELETE FROM do_t_states WHERE state_key = ?", (state_key,))
        conn.commit()


def _persist_order_index(cl_ord_id: str, mapping: dict) -> None:
    _ensure_db_schema()
    with _db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO do_t_order_index(cl_ord_id, state_key, leg) VALUES(?, ?, ?)",
            (cl_ord_id, mapping["state_key"], mapping["leg"]),
        )
        conn.commit()


def _remove_order_index(cl_ord_id: str) -> None:
    _ensure_db_schema()
    with _db_connection() as conn:
        conn.execute("DELETE FROM do_t_order_index WHERE cl_ord_id = ?", (cl_ord_id,))
        conn.commit()


def _persist_exec_id(exec_id: Any) -> None:
    if exec_id is None:
        return
    _ensure_db_schema()
    with _db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO do_t_exec_ids(exec_id) VALUES(?)",
            (str(exec_id),),
        )
        conn.commit()


def _clear_persistence() -> None:
    _ensure_db_schema()
    with _db_connection() as conn:
        conn.execute("DELETE FROM do_t_states")
        conn.execute("DELETE FROM do_t_order_index")
        conn.execute("DELETE FROM do_t_exec_ids")
        conn.commit()


def _clear_state_runtime(state: dict) -> None:
    active_order = state.get("active_order") or {}
    cl_ord_id = active_order.get("cl_ord_id")
    state["active_leg"] = None
    state["active_order"] = None
    state["active_order_submitted_at"] = None
    if cl_ord_id:
        _DO_T_RUNTIME["order_index"].pop(cl_ord_id, None)
        _remove_order_index(cl_ord_id)


def _is_force_settlement_time(now: datetime) -> bool:
    return now.time() >= FORCE_SETTLEMENT_TIME


def _validate_price_or_pct(label: str, price_value: Optional[float], pct_value: Optional[float]) -> Optional[float]:
    if price_value is not None and pct_value is not None:
        raise ValueError(f"{label} 只能传价格或百分比之一")
    if price_value is not None and price_value <= 0:
        raise ValueError(f"{label} 必须大于 0")
    return _normalize_pct(pct_value)


def _validate_args(
    direction: str,
    volume: int,
    entry_trigger_price: Optional[float],
    entry_order_price: Optional[float],
    take_profit_price: Optional[float],
    take_profit_pct: Optional[float],
    stop_loss_price: Optional[float],
    stop_loss_pct: Optional[float],
) -> tuple[Optional[float], Optional[float]]:
    if direction not in {BUY_THEN_SELL, SELL_THEN_BUY}:
        raise ValueError(f"direction 只能是 {BUY_THEN_SELL} 或 {SELL_THEN_BUY}")
    if int(volume) != volume or volume <= 0:
        raise ValueError("volume 必须是正整数")
    if volume % 100 != 0:
        raise ValueError("股票买入数量必须是 100 的整数倍")
    if entry_trigger_price is not None and entry_trigger_price <= 0:
        raise ValueError("entry_trigger_price 必须大于 0")
    if entry_order_price is not None and entry_order_price <= 0:
        raise ValueError("entry_order_price 必须大于 0")

    take_profit_ratio = _validate_price_or_pct("止盈条件", take_profit_price, take_profit_pct)
    stop_loss_ratio = _validate_price_or_pct("止损条件", stop_loss_price, stop_loss_pct)

    if (
        take_profit_price is None
        and take_profit_ratio is None
        and stop_loss_price is None
        and stop_loss_ratio is None
    ):
        raise ValueError("至少提供一个止盈或止损条件")

    return take_profit_ratio, stop_loss_ratio


def _validate_exit_relationship(
    direction: str,
    reference_price: Optional[float],
    take_profit_price: Optional[float],
    stop_loss_price: Optional[float],
) -> None:
    if reference_price is None:
        return
    if direction == BUY_THEN_SELL:
        if take_profit_price is not None and take_profit_price <= reference_price:
            raise ValueError("buy_then_sell 的止盈价必须高于入场基准价")
        if stop_loss_price is not None and stop_loss_price >= reference_price:
            raise ValueError("buy_then_sell 的止损价必须低于入场基准价")
    else:
        if take_profit_price is not None and take_profit_price >= reference_price:
            raise ValueError("sell_then_buy 的止盈价必须低于入场基准价")
        if stop_loss_price is not None and stop_loss_price <= reference_price:
            raise ValueError("sell_then_buy 的止损价必须高于入场基准价")


def _resolve_account_id(account_id: Optional[str]) -> Optional[str]:
    return account_id or DEFAULT_ACCOUNT_ID or None


def _position_for_symbol(account_id: Optional[str], symbol: str):
    resolved_account_id = _resolve_account_id(account_id)
    positions = gm_get_position(account_id=resolved_account_id) if resolved_account_id else gm_get_position()
    for position in _as_items(positions):
        if _get_field(position, "symbol") == symbol and _get_field(position, "side") == PositionSide_Long:
            return position
    return None


def _available_cash(account_id: Optional[str]) -> float:
    resolved_account_id = _resolve_account_id(account_id)
    cash = gm_get_cash(account_id=resolved_account_id) if resolved_account_id else gm_get_cash()
    return float(_get_field(cash, "available", 0.0) or 0.0)


def _resolve_order_type(order_type: Any) -> Any:
    if order_type is None:
        return OrderType_Limit
    if order_type == OrderType_Limit:
        return OrderType_Limit
    if isinstance(order_type, str) and order_type.strip().lower() in {"limit", "ordertype_limit"}:
        return OrderType_Limit
    raise ValueError("当前仅支持限价单: order_type='limit'")


def _create_state(
    state_key: str,
    now: datetime,
    symbol: str,
    direction: str,
    volume: int,
    expire_seconds: int,
    entry_trigger_price: Optional[float],
    entry_order_price: Optional[float],
    take_profit_price: Optional[float],
    take_profit_ratio: Optional[float],
    stop_loss_price: Optional[float],
    stop_loss_ratio: Optional[float],
    order_type: Any,
    account_id: Optional[str],
) -> dict:
    state = {
        "state_key": state_key,
        "symbol": symbol,
        "direction": direction,
        "planned_volume": volume,
        "expire_seconds": expire_seconds,
        "entry_trigger_price": _round_price(entry_trigger_price) if entry_trigger_price is not None else None,
        "entry_order_price": _round_price(entry_order_price) if entry_order_price is not None else None,
        "take_profit_price": _round_price(take_profit_price) if take_profit_price is not None else None,
        "take_profit_ratio": take_profit_ratio,
        "stop_loss_price": _round_price(stop_loss_price) if stop_loss_price is not None else None,
        "stop_loss_ratio": stop_loss_ratio,
        "order_type": order_type,
        "account_id": account_id,
        "phase": "waiting_entry",
        "created_at": now,
        "updated_at": now,
        "active_leg": None,
        "active_order": None,
        "active_order_submitted_at": None,
        "entry_order_filled": False,
        "exit_order_filled": False,
        "entry_filled_volume": 0,
        "entry_filled_amount": 0.0,
        "entry_avg_price": None,
        "exit_target_volume": 0,
        "exit_filled_volume": 0,
        "exit_filled_amount": 0.0,
        "exit_avg_price": None,
        "armed_take_profit_price": None,
        "armed_stop_loss_price": None,
        "exit_reason": None,
        "locked_base_volume": 0,
        "last_error": None,
        "force_settlement": False,
    }
    _persist_state(state)
    return state


def _mark_failed(state: dict, now: datetime, message: str) -> None:
    state["phase"] = "failed"
    state["updated_at"] = now
    state["last_error"] = message
    _clear_state_runtime(state)
    _persist_state(state)


def _mark_canceled(state: dict, now: datetime, message: str) -> None:
    state["phase"] = "canceled"
    state["updated_at"] = now
    state["last_error"] = message
    _clear_state_runtime(state)
    _persist_state(state)


def _requeue_force_settlement(state: dict, now: datetime, message: str) -> None:
    state["phase"] = "waiting_exit"
    state["updated_at"] = now
    state["last_error"] = message
    state["force_settlement"] = True
    _clear_state_runtime(state)
    _persist_state(state)


def _submit_order(
    state: dict,
    leg: str,
    side: int,
    position_effect: int,
    volume: int,
    order_price: Optional[float],
    now: datetime,
) -> bool:
    if volume <= 0:
        _mark_failed(state, now, "下单量必须大于 0")
        return False

    resolved_account_id = _resolve_account_id(state["account_id"])
    if resolved_account_id:
        gm_set_account_id(resolved_account_id)

    if state["order_type"] == OrderType_Limit and order_price is not None:
        order_price = _round_price(order_price)

    kwargs = {
        "symbol": state["symbol"],
        "volume": volume,
        "side": side,
        "order_type": state["order_type"],
        "position_effect": position_effect,
        "price": order_price or 0,
    }
    if resolved_account_id:
        kwargs["account"] = resolved_account_id

    try:
        orders = gm_order_volume(**kwargs)
    except TypeError:
        kwargs.pop("account", None)
        orders = gm_order_volume(**kwargs)

    if not orders:
        _mark_failed(state, now, "下单返回空结果")
        return False

    order = _as_items(orders)[0]
    cl_ord_id = _get_field(order, "cl_ord_id")
    order_account_id = _get_field(order, "account_id", resolved_account_id)
    if not cl_ord_id:
        _mark_failed(state, now, "下单结果缺少 cl_ord_id")
        return False

    state["active_leg"] = leg
    state["active_order"] = {"cl_ord_id": cl_ord_id, "account_id": order_account_id}
    state["active_order_submitted_at"] = now
    state["updated_at"] = now
    state["phase"] = f"{leg}_submitted"
    _DO_T_RUNTIME["order_index"][cl_ord_id] = {"state_key": state["state_key"], "leg": leg}
    _persist_order_index(cl_ord_id, _DO_T_RUNTIME["order_index"][cl_ord_id])
    _persist_state(state)
    return True


def _maybe_cancel_expired(state: dict, now: datetime) -> None:
    active_order = state.get("active_order")
    submitted_at = state.get("active_order_submitted_at")
    if not active_order or not submitted_at:
        return
    if state["phase"] not in {"leg1_submitted", "leg1_partial", "leg2_submitted", "leg2_partial"}:
        return
    if now - submitted_at <= timedelta(seconds=state["expire_seconds"]):
        return
    gm_order_cancel(wait_cancel_orders=[active_order])
    state["updated_at"] = now
    _persist_state(state)


def _entry_triggered(direction: str, tick_price: float, entry_trigger_price: Optional[float]) -> bool:
    if entry_trigger_price is None:
        return True
    if direction == BUY_THEN_SELL:
        return tick_price <= entry_trigger_price
    return tick_price >= entry_trigger_price


def _resolve_exit_prices(state: dict) -> tuple[Optional[float], Optional[float]]:
    entry_avg_price = state["entry_avg_price"]
    if entry_avg_price is None:
        raise ValueError("缺少第一腿实际成交均价，无法计算止盈止损价格")

    take_profit_price = state["take_profit_price"]
    stop_loss_price = state["stop_loss_price"]

    if take_profit_price is None and state["take_profit_ratio"] is not None:
        if state["direction"] == BUY_THEN_SELL:
            take_profit_price = entry_avg_price * (1 + state["take_profit_ratio"])
        else:
            take_profit_price = entry_avg_price * (1 - state["take_profit_ratio"])

    if stop_loss_price is None and state["stop_loss_ratio"] is not None:
        if state["direction"] == BUY_THEN_SELL:
            stop_loss_price = entry_avg_price * (1 - state["stop_loss_ratio"])
        else:
            stop_loss_price = entry_avg_price * (1 + state["stop_loss_ratio"])

    take_profit_price = _round_price(take_profit_price) if take_profit_price is not None else None
    stop_loss_price = _round_price(stop_loss_price) if stop_loss_price is not None else None
    _validate_exit_relationship(state["direction"], entry_avg_price, take_profit_price, stop_loss_price)
    return take_profit_price, stop_loss_price


def _arm_exit(state: dict, now: datetime) -> None:
    if state["entry_filled_volume"] <= 0:
        raise ValueError("第一腿无实际成交量，无法进入结算阶段")

    state["entry_avg_price"] = state["entry_filled_amount"] / float(state["entry_filled_volume"])
    state["armed_take_profit_price"], state["armed_stop_loss_price"] = _resolve_exit_prices(state)
    if state["direction"] == BUY_THEN_SELL:
        state["exit_target_volume"] = min(state["entry_filled_volume"], state["locked_base_volume"])
    else:
        state["exit_target_volume"] = state["entry_filled_volume"]

    if state["exit_target_volume"] <= 0:
        raise ValueError("结算量必须大于 0")

    state["phase"] = "waiting_exit"
    state["force_settlement"] = False
    _clear_state_runtime(state)
    state["updated_at"] = now
    _persist_state(state)


def _finalize_entry_if_ready(state: dict, now: datetime) -> None:
    if state["entry_order_filled"] and state["entry_filled_volume"] > 0 and state["phase"] != "waiting_exit":
        _arm_exit(state, now)


def _finalize_exit_if_ready(state: dict, now: datetime) -> None:
    if state["exit_order_filled"] and state["exit_filled_volume"] >= state["exit_target_volume"] > 0:
        state["phase"] = "done"
        state["updated_at"] = now
        _clear_state_runtime(state)
        _persist_state(state)


def _exit_trigger_reason(state: dict, tick_price: float) -> Optional[str]:
    if state["direction"] == BUY_THEN_SELL:
        if state["armed_take_profit_price"] is not None and tick_price >= state["armed_take_profit_price"]:
            return "take_profit"
        if state["armed_stop_loss_price"] is not None and tick_price <= state["armed_stop_loss_price"]:
            return "stop_loss"
    else:
        if state["armed_take_profit_price"] is not None and tick_price <= state["armed_take_profit_price"]:
            return "take_profit"
        if state["armed_stop_loss_price"] is not None and tick_price >= state["armed_stop_loss_price"]:
            return "stop_loss"
    return None


def _exit_order_price(state: dict, reason: str) -> Optional[float]:
    if reason == "take_profit":
        return state["armed_take_profit_price"]
    return state["armed_stop_loss_price"]


def _apply_order_status(order: Any) -> None:
    _reset_runtime_state()
    cl_ord_id = _get_field(order, "cl_ord_id")
    if not cl_ord_id or cl_ord_id not in _DO_T_RUNTIME["order_index"]:
        return

    mapping = _DO_T_RUNTIME["order_index"][cl_ord_id]
    state = _DO_T_RUNTIME["states"].get(mapping["state_key"])
    if state is None:
        return

    now = _event_time(order)
    status = _get_field(order, "status")
    leg = mapping["leg"]
    state["updated_at"] = now

    if leg == "leg1":
        if status == OrderStatus_PartiallyFilled:
            state["phase"] = "leg1_partial"
            _persist_state(state)
            return
        if status == OrderStatus_Filled:
            state["entry_order_filled"] = True
            try:
                _finalize_entry_if_ready(state, now)
            except ValueError as exc:
                _mark_failed(state, now, str(exc))
            return
        if status in {OrderStatus_Canceled, OrderStatus_Expired}:
            state["entry_order_filled"] = False
            if state["entry_filled_volume"] > 0:
                try:
                    _arm_exit(state, now)
                except ValueError as exc:
                    _mark_failed(state, now, str(exc))
            else:
                _mark_canceled(state, now, "第一腿未成交即被撤销/过期")
            return
        if status == OrderStatus_Rejected:
            _mark_failed(state, now, "第一腿委托被拒绝")
            return
        return

    if status == OrderStatus_PartiallyFilled:
        state["phase"] = "leg2_partial"
        _persist_state(state)
        return
    if status == OrderStatus_Filled:
        state["exit_order_filled"] = True
        _finalize_exit_if_ready(state, now)
        return
    if status in {OrderStatus_Canceled, OrderStatus_Expired}:
        if state.get("exit_reason") == "forced_settlement":
            _requeue_force_settlement(state, now, "第二腿撤销/过期，等待继续强制结算")
        else:
            _mark_failed(state, now, "第二腿撤销/过期，存在未完成结算风险")
        return
    if status == OrderStatus_Rejected:
        _mark_failed(state, now, "第二腿委托被拒绝")


def _apply_execution_report(execrpt: Any) -> None:
    _reset_runtime_state()
    if _get_field(execrpt, "exec_type") != 15:
        return

    exec_id = _get_field(execrpt, "exec_id")
    exec_id_key = str(exec_id)
    if exec_id_key in _DO_T_RUNTIME["exec_ids"]:
        return
    _DO_T_RUNTIME["exec_ids"].add(exec_id_key)
    _persist_exec_id(exec_id_key)

    cl_ord_id = _get_field(execrpt, "cl_ord_id")
    if not cl_ord_id or cl_ord_id not in _DO_T_RUNTIME["order_index"]:
        return

    mapping = _DO_T_RUNTIME["order_index"][cl_ord_id]
    state = _DO_T_RUNTIME["states"].get(mapping["state_key"])
    if state is None:
        return

    volume = int(_get_field(execrpt, "volume", 0) or 0)
    amount = float(_get_field(execrpt, "amount", 0.0) or 0.0)
    price = float(_get_field(execrpt, "price", 0.0) or 0.0)
    if amount <= 0 and volume > 0 and price > 0:
        amount = volume * price

    now = _event_time(execrpt)
    if mapping["leg"] == "leg1":
        state["entry_filled_volume"] += volume
        state["entry_filled_amount"] += amount
        if state["entry_filled_volume"] > 0:
            state["entry_avg_price"] = state["entry_filled_amount"] / float(state["entry_filled_volume"])
            _persist_state(state)
        try:
            _finalize_entry_if_ready(state, now)
        except ValueError as exc:
            _mark_failed(state, now, str(exc))
        return

    state["exit_filled_volume"] += volume
    state["exit_filled_amount"] += amount
    if state["exit_filled_volume"] > 0:
        state["exit_avg_price"] = state["exit_filled_amount"] / float(state["exit_filled_volume"])
    _persist_state(state)
    _finalize_exit_if_ready(state, now)


def _refresh_runtime_from_gm() -> None:
    _reset_runtime_state()
    try:
        reports = _as_items(gm_get_execution_reports())
    except Exception:
        reports = []
    for report in reports:
        _apply_execution_report(report)

    try:
        orders = _as_items(gm_get_orders())
    except Exception:
        orders = []
    for order in orders:
        _apply_order_status(order)


def _current_market_data(symbol: str, tick_price: Optional[float] = None) -> Optional[Any]:
    if tick_price is not None:
        return {"symbol": symbol, "price": float(tick_price), "created_at": datetime.now()}

    data = gm_current_price(symbols=symbol)
    if isinstance(data, list):
        if not data:
            return None
        for item in data:
            if _get_field(item, "symbol") == symbol:
                return item
        return data[0]
    if isinstance(data, dict):
        return data
    if data is None:
        return None
    return {"symbol": symbol, "price": float(data), "created_at": datetime.now()}


def _serialize_state(state: Optional[dict]) -> dict:
    if state is None:
        return {"found": False}

    result = {"found": True}
    for key, value in state.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat(sep=" ", timespec="seconds")
        else:
            result[key] = value
    return result


def _find_state(symbol: str, direction: str, trade_date: Optional[str] = None) -> Optional[dict]:
    _reset_runtime_state()
    current_date = trade_date or datetime.now().strftime("%Y-%m-%d")
    return _DO_T_RUNTIME["states"].get(f"{symbol}:{direction}:{current_date}")


def _run_stock_do_t(
    symbol: str,
    direction: str,
    volume: int,
    expire_seconds: int,
    entry_trigger_price: Optional[float] = None,
    entry_order_price: Optional[float] = None,
    take_profit_price: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    stop_loss_pct: Optional[float] = None,
    order_type: Any = OrderType_Limit,
    account_id: Optional[str] = None,
    tick_price: Optional[float] = None,
) -> dict:
    _refresh_runtime_from_gm()
    market_data = _current_market_data(symbol, tick_price=tick_price)
    if market_data is None:
        raise ValueError(f"无法获取 {symbol} 的最新价格")

    now = _event_time(market_data)
    live_tick_price = float(_get_field(market_data, "price", 0.0) or 0.0)
    if live_tick_price <= 0:
        raise ValueError("最新价格无效，无法执行做T逻辑")

    take_profit_ratio, stop_loss_ratio = _validate_args(
        direction,
        volume,
        entry_trigger_price,
        entry_order_price,
        take_profit_price,
        take_profit_pct,
        stop_loss_price,
        stop_loss_pct,
    )
    reference_price = entry_order_price or entry_trigger_price
    if reference_price is not None:
        _validate_exit_relationship(direction, reference_price, take_profit_price, stop_loss_price)

    resolved_order_type = _resolve_order_type(order_type)
    state_key = _state_key(symbol, direction, now)
    state = _DO_T_RUNTIME["states"].get(state_key)
    if state is None:
        state = _create_state(
            state_key,
            now,
            symbol,
            direction,
            volume,
            expire_seconds,
            entry_trigger_price,
            entry_order_price,
            take_profit_price,
            take_profit_ratio,
            stop_loss_price,
            stop_loss_ratio,
            resolved_order_type,
            _resolve_account_id(account_id),
        )
        _DO_T_RUNTIME["states"][state_key] = state

    if state["phase"] in DONE_STATES:
        return state

    _maybe_cancel_expired(state, now)

    if state["phase"] == "waiting_entry":
        if _is_force_settlement_time(now):
            _mark_canceled(state, now, "超过 14:55，不再开新做T单")
            return state

        if not _entry_triggered(direction, live_tick_price, state["entry_trigger_price"]):
            return state

        position = _position_for_symbol(account_id, symbol)
        available_volume = int(_get_field(position, "available", 0) or 0)
        available_cash = _available_cash(account_id)
        order_price = state["entry_order_price"] or _round_price(live_tick_price)

        if direction == BUY_THEN_SELL:
            if available_volume < volume:
                _mark_failed(state, now, "buy_then_sell 需要足够底仓用于后续卖出")
                return state
            if available_cash < volume * order_price:
                _mark_failed(state, now, "可用资金不足，无法买入第一腿")
                return state
            state["locked_base_volume"] = volume
            _submit_order(state, "leg1", OrderSide_Buy, PositionEffect_Open, volume, order_price, now)
            return state

        if available_volume < volume:
            _mark_failed(state, now, "可卖数量不足，无法执行第一腿卖出")
            return state
        state["locked_base_volume"] = volume
        _submit_order(state, "leg1", OrderSide_Sell, PositionEffect_Close, volume, order_price, now)
        return state

    if state["phase"] == "waiting_exit":
        reason = _exit_trigger_reason(state, live_tick_price)
        if reason is None and _is_force_settlement_time(now):
            reason = "forced_settlement"
        if reason is None:
            return state

        exit_volume = state["exit_target_volume"] - state["exit_filled_volume"]
        if exit_volume <= 0:
            state["phase"] = "done"
            state["updated_at"] = now
            return state

        order_price = _round_price(live_tick_price) if reason == "forced_settlement" else _exit_order_price(state, reason)
        available_cash = _available_cash(account_id)
        position = _position_for_symbol(account_id, symbol)
        available_volume = int(_get_field(position, "available", 0) or 0)

        if direction == BUY_THEN_SELL:
            if available_volume < exit_volume:
                _mark_failed(state, now, "可卖数量不足，无法完成第二腿卖出")
                return state
            if _submit_order(state, "leg2", OrderSide_Sell, PositionEffect_Close, exit_volume, order_price, now):
                state["exit_reason"] = reason
                state["force_settlement"] = reason == "forced_settlement"
                _persist_state(state)
            return state

        if available_cash < exit_volume * order_price:
            _mark_failed(state, now, "可用资金不足，无法完成第二腿买回")
            return state
        if _submit_order(state, "leg2", OrderSide_Buy, PositionEffect_Open, exit_volume, order_price, now):
            state["exit_reason"] = reason
            state["force_settlement"] = reason == "forced_settlement"
            _persist_state(state)
        return state

    return state


@tool_registry("stock_do_t")
@mcp.tool()
@audit_wrapper
async def stock_do_t(
    auth_token: str,
    symbol: str,
    direction: str,
    volume: int,
    expire_seconds: int,
    entry_trigger_price: Optional[float] = None,
    entry_order_price: Optional[float] = None,
    take_profit_price: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    stop_loss_pct: Optional[float] = None,
    order_type: str = "limit",
    account_id: Optional[str] = None,
    tick_price: Optional[float] = None,
) -> str:
    """执行一个高阶做T状态机，适合被 agent 周期性轮询调用。

    用途:
    - `buy_then_sell`: 先买入一腿，再在止盈/止损或 14:55 后卖出完成做T。
    - `sell_then_buy`: 先卖出一腿，再在止盈/止损或 14:55 后买回完成做T。

    参数:
    - auth_token: 认证令牌，必须与服务端 `MCP_AUTH_TOKEN` 一致。
    - symbol: 标的代码，例如 `SZSE.000001`。
    - direction: `buy_then_sell` 或 `sell_then_buy`。
    - volume: 第一腿计划股数，必须为正整数且是 100 的整数倍。
    - expire_seconds: 单笔委托超时秒数，超过后会尝试撤单。
    - entry_trigger_price: 入场触发价。`buy_then_sell` 要求最新价小于等于该价格才入场；`sell_then_buy` 相反。
    - entry_order_price: 第一腿限价委托价；不传则使用当前价四舍五入到分。
    - take_profit_price / take_profit_pct: 止盈条件，二选一。百分比可传 `3` 表示 3%，也可传 `0.03`。
    - stop_loss_price / stop_loss_pct: 止损条件，二选一。百分比规则同上。
    - order_type: 当前仅支持 `limit`。
    - account_id: 可选账户 ID；不传则使用服务端默认账户。
    - tick_price: 可选当前价。测试、回放或外部轮询时可显式传入；不传则自动读取最新价。

    行为说明:
    - 该工具每次调用都会先同步最新订单状态和成交回报，再根据当前价推进状态机。
    - 第一腿完成后会进入 `waiting_exit`，等待第二腿触发。
    - 14:55 之后不再开新第一腿；如果第一腿已经完成但第二腿尚未触发，会按当前价发起强制结算。
    - 状态会持久化到本地 SQLite，服务重启后仍可通过 `stock_do_t_get_state` 查询。

    常见 phase:
    - `waiting_entry`: 等待第一腿触发。
    - `leg1_submitted` / `leg1_partial`: 第一腿已报单 / 部分成交。
    - `waiting_exit`: 第一腿完成，等待第二腿。
    - `leg2_submitted` / `leg2_partial`: 第二腿已报单 / 部分成交。
    - `done`: 两腿都完成。
    - `failed`: 出现需要人工处理的风险，例如第二腿撤销、资金不足、可卖数量不足。
    - `canceled`: 第一腿未成交即取消，或 14:55 后仍未开第一腿。

    返回:
    - JSON 字符串，包含当前 state、phase、active_order、entry/exit 成交统计、止盈止损价、错误信息等。

    调用建议:
    - agent 可以在盘中定期调用该工具，例如每 5-30 秒一次。
    - 如果返回 `failed`，应进一步调用 `get_positions`、`get_orders`、`get_unfinished_orders`、`get_execution_reports` 辅助人工处理。

    示例:
    - `stock_do_t(auth_token="secret", symbol="SZSE.000001", direction="buy_then_sell", volume=1000, expire_seconds=30, entry_trigger_price=10.00, entry_order_price=10.00, take_profit_pct=3, stop_loss_price=9.70)`
    - `stock_do_t(auth_token="secret", symbol="SZSE.000001", direction="sell_then_buy", volume=1000, expire_seconds=30, entry_trigger_price=10.50, entry_order_price=10.50, take_profit_pct=2, stop_loss_pct=1)`
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")

    state = _run_stock_do_t(
        symbol=symbol,
        direction=direction,
        volume=volume,
        expire_seconds=expire_seconds,
        entry_trigger_price=entry_trigger_price,
        entry_order_price=entry_order_price,
        take_profit_price=take_profit_price,
        take_profit_pct=take_profit_pct,
        stop_loss_price=stop_loss_price,
        stop_loss_pct=stop_loss_pct,
        order_type=order_type,
        account_id=account_id,
        tick_price=tick_price,
    )
    return json.dumps(_serialize_state(state), ensure_ascii=False, indent=2)


@tool_registry("stock_do_t_get_state")
@mcp.tool()
@audit_wrapper
async def stock_do_t_get_state(auth_token: str, symbol: str, direction: str, trade_date: Optional[str] = None) -> str:
    """查询指定标的/方向/交易日的做T状态。

    参数:
    - auth_token: 认证令牌。
    - symbol: 标的代码，例如 `SZSE.000001`。
    - direction: `buy_then_sell` 或 `sell_then_buy`。
    - trade_date: 交易日，格式 `YYYY-MM-DD`；不传则默认今天。

    返回:
    - 如果找到状态，返回 `found=true` 以及完整状态字段。
    - 如果不存在状态，返回 `found=false`。

    适用场景:
    - agent 在多轮调用之间恢复上下文。
    - 服务重启后确认 SQLite 中是否已有未完成的做T状态。
    - 收盘后检查某个交易日是否还有未结第二腿。

    示例:
    - `stock_do_t_get_state(auth_token="secret", symbol="SZSE.000001", direction="buy_then_sell")`
    - `stock_do_t_get_state(auth_token="secret", symbol="SZSE.000001", direction="buy_then_sell", trade_date="2026-04-01")`
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    _refresh_runtime_from_gm()
    return json.dumps(_serialize_state(_find_state(symbol, direction, trade_date)), ensure_ascii=False, indent=2)


@tool_registry("stock_do_t_reset")
@mcp.tool()
@audit_wrapper
async def stock_do_t_reset(
    auth_token: str,
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    trade_date: Optional[str] = None,
    all_states: bool = False,
) -> str:
    """删除做T状态机的运行状态和持久化记录。

    参数:
    - auth_token: 认证令牌。
    - symbol: 标的代码；当 `all_states=false` 时必填。
    - direction: `buy_then_sell` 或 `sell_then_buy`；当 `all_states=false` 时必填。
    - trade_date: 交易日，格式 `YYYY-MM-DD`；不传则默认今天。
    - all_states: 传 `true` 时清空所有做T状态、订单映射和执行去重记录。

    注意:
    - 该工具只清状态机缓存和 SQLite 持久化记录，不会撤销真实委托，也不会修复真实持仓。
    - 如果存在未结委托或未结仓位，应先用 `get_orders` / `get_unfinished_orders` / `get_positions` 确认，再决定是否 reset。

    返回:
    - JSON 字符串，包含是否删除成功、删除的 state_key，以及同步清掉的订单映射列表。

    示例:
    - `stock_do_t_reset(auth_token="secret", symbol="SZSE.000001", direction="buy_then_sell")`
    - `stock_do_t_reset(auth_token="secret", all_states=true)`
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")

    _reset_runtime_state()
    if all_states:
        _DO_T_RUNTIME["states"].clear()
        _DO_T_RUNTIME["order_index"].clear()
        _DO_T_RUNTIME["exec_ids"].clear()
        _clear_persistence()
        return json.dumps({"success": True, "cleared": "all"}, ensure_ascii=False, indent=2)

    if not symbol or not direction:
        raise ValueError("不使用 all_states 时，必须提供 symbol 和 direction")

    current_date = trade_date or datetime.now().strftime("%Y-%m-%d")
    target_state_key = f"{symbol}:{direction}:{current_date}"
    removed = _DO_T_RUNTIME["states"].pop(target_state_key, None) is not None
    if removed:
        _remove_state(target_state_key)

    stale_order_ids = [
        cl_ord_id
        for cl_ord_id, mapping in _DO_T_RUNTIME["order_index"].items()
        if mapping["state_key"] == target_state_key
    ]
    for cl_ord_id in stale_order_ids:
        _DO_T_RUNTIME["order_index"].pop(cl_ord_id, None)
        _remove_order_index(cl_ord_id)

    return json.dumps(
        {"success": True, "removed": removed, "state_key": target_state_key, "cleared_orders": stale_order_ids},
        ensure_ascii=False,
        indent=2,
    )
