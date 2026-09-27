"""Prop-firm rule engine — pure functions, no I/O.

Every prop firm words its limits slightly differently. The engine supports the
common building blocks; a preset combines them. ALWAYS verify a preset against
your firm's current rules before trusting it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class Rules:
    name: str
    account_size: float                 # starting balance of the account
    daily_loss_pct: float               # e.g. 0.05 = 5 %
    max_loss_pct: float                 # e.g. 0.10 = 10 %
    max_loss_mode: str = "static"       # "static" (vs starting balance) | "trailing" (vs equity high-water mark)
    daily_ref: str = "equity"           # daily loss measured from start-of-day "equity" | "balance" | "max" (larger of the two)
    reset_hour_utc: int = 0             # hour (UTC) at which the daily window resets
    buffer_pct: float = 0.005           # act this much BEFORE the hard limit (0.5 % of account by default)


@dataclass
class State:
    day_start: datetime | None = None
    day_ref_equity: float | None = None
    high_water: float | None = None
    locked_until: datetime | None = None
    events: list = field(default_factory=list)


def day_start(now: datetime, reset_hour_utc: int) -> datetime:
    now = now.astimezone(timezone.utc)
    start = now.replace(hour=reset_hour_utc, minute=0, second=0, microsecond=0)
    return start if now >= start else start - timedelta(days=1)


def roll_day(st: State, r: Rules, now: datetime, equity: float, balance: float) -> None:
    """Start a new daily window if the reset time has passed."""
    ds = day_start(now, r.reset_hour_utc)
    if st.day_start is None or ds > st.day_start:
        st.day_start = ds
        if r.daily_ref == "balance":
            st.day_ref_equity = balance
        elif r.daily_ref == "max":
            st.day_ref_equity = max(balance, equity)
        else:
            st.day_ref_equity = equity
        if st.locked_until and now >= st.locked_until:
            st.locked_until = None


def limits(st: State, r: Rules) -> dict:
    """Equity floors implied by the rules (below a floor = breach)."""
    daily_floor = st.day_ref_equity - r.daily_loss_pct * r.account_size
    if r.max_loss_mode == "trailing":
        max_floor = (st.high_water or r.account_size) - r.max_loss_pct * r.account_size
    else:
        max_floor = r.account_size * (1 - r.max_loss_pct)
    return dict(daily_floor=daily_floor, max_floor=max_floor, floor=max(daily_floor, max_floor))


def evaluate(st: State, r: Rules, now: datetime, equity: float, balance: float) -> dict:
    """Update state and decide. Returns dict(action=..., ...) where action is
    "ok" | "warn" | "flatten" | "locked"."""
    roll_day(st, r, now, equity, balance)
    st.high_water = max(st.high_water or r.account_size, equity)
    L = limits(st, r)
    trigger = L["floor"] + r.buffer_pct * r.account_size
    room = equity - L["floor"]
    out = dict(equity=equity, floor=L["floor"], daily_floor=L["daily_floor"], max_floor=L["max_floor"],
               trigger=trigger, room=room, room_pct=room / r.account_size)
    if st.locked_until and now < st.locked_until:
        out["action"] = "locked"
    elif equity <= trigger:
        st.locked_until = st.day_start + timedelta(days=1)
        out["action"] = "flatten"
    elif room <= 2 * r.buffer_pct * r.account_size:
        out["action"] = "warn"
    else:
        out["action"] = "ok"
    return out
