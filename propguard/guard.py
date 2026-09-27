"""propguard — stop a prop-firm account from breaching its loss limits.

Runs next to your trading (manual or bot). Every few seconds it reads equity from
the exchange, compares it with your firm's daily / max loss floors, and when equity
gets within a buffer of a floor it cancels all orders, closes all positions with
reduce-only market orders, and keeps the account flat until the daily reset.

Dry-run by default: it only prints what it would do. Add --live to act.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import requests

from .bybit import MAINNET, TESTNET, Bybit
from .presets import PRESETS, preset
from .rules import State, evaluate


def load_state(p: Path) -> State:
    if not p.exists():
        return State()
    d = json.loads(p.read_text())
    st = State()
    for k in ("day_start", "locked_until"):
        if d.get(k):
            setattr(st, k, datetime.fromisoformat(d[k]))
    st.day_ref_equity, st.high_water = d.get("day_ref_equity"), d.get("high_water")
    return st


def save_state(p: Path, st: State) -> None:
    d = asdict(st)
    for k in ("day_start", "locked_until"):
        d[k] = d[k].isoformat() if d[k] else None
    d.pop("events", None)
    p.write_text(json.dumps(d, indent=1))


def notify(msg: str) -> None:
    print(msg, flush=True)
    tok, chat = os.getenv("PROPGUARD_TG_TOKEN"), os.getenv("PROPGUARD_TG_CHAT")
    if tok and chat:
        try:
            requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", data={"chat_id": chat, "text": msg}, timeout=10)
        except Exception:
            pass


def flatten(ex: Bybit, live: bool) -> int:
    pos = ex.positions()
    if live:
        ex.cancel_all()
        for p in pos:
            ex.close(p)
    return len(pos)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="propguard", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", required=True, choices=sorted(PRESETS))
    ap.add_argument("--size", type=float, required=True, help="account starting balance, e.g. 25000")
    ap.add_argument("--buffer", type=float, default=0.005, help="act this fraction of the account BEFORE the floor (default 0.005)")
    ap.add_argument("--reset-hour", type=int, default=0, help="daily reset hour in UTC (check your firm)")
    ap.add_argument("--day-start-equity", type=float, default=None,
                    help="equity at today's reset. REQUIRED if you start the guard mid-day with no state file")
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between checks")
    ap.add_argument("--state", default="propguard_state.json")
    ap.add_argument("--testnet", action="store_true")
    ap.add_argument("--live", action="store_true", help="actually cancel orders and close positions")
    ap.add_argument("--once", action="store_true", help="check once and exit")
    a = ap.parse_args(argv)

    r = preset(a.preset, a.size, buffer_pct=a.buffer, reset_hour_utc=a.reset_hour)
    ex = Bybit(os.getenv("PROPGUARD_BYBIT_KEY", ""), os.getenv("PROPGUARD_BYBIT_SECRET", ""), TESTNET if a.testnet else MAINNET)
    sp = Path(a.state)
    st = load_state(sp)
    if st.day_start is None:
        if a.day_start_equity is None:
            print("⚠ No state file and no --day-start-equity. Using CURRENT equity as today's reference.\n"
                  "  If you already lost money today this makes the daily limit LOOSER than your firm's. "
                  "Pass --day-start-equity to be safe.", file=sys.stderr)
        else:
            st.day_ref_equity = a.day_start_equity
            from .rules import day_start
            st.day_start = day_start(datetime.now(timezone.utc), r.reset_hour_utc)

    print(f"propguard · {r.name} · size {r.account_size:,.0f} · daily {r.daily_loss_pct:.1%} · max {r.max_loss_pct:.1%} "
          f"({r.max_loss_mode}) · buffer {r.buffer_pct:.2%} · {'LIVE' if a.live else 'DRY-RUN'}", flush=True)
    last = None
    while True:
        try:
            eq, bal = ex.equity()
            now = datetime.now(timezone.utc)
            d = evaluate(st, r, now, eq, bal)
            save_state(sp, st)
            line = (f"{now:%H:%M:%S} equity {eq:,.2f} · floor {d['floor']:,.2f} · room {d['room']:,.2f} "
                    f"({d['room_pct']:.2%}) · {d['action']}")
            if d["action"] in ("flatten", "locked"):
                n = flatten(ex, a.live) if d["action"] == "flatten" or ex.positions() else 0
                if d["action"] == "locked" and not n:
                    print(line, flush=True)
                else:
                    notify(f"🛑 propguard {'closed' if a.live else 'WOULD close'} {n} position(s) — {line} · "
                           f"locked until {st.locked_until:%Y-%m-%d %H:%M} UTC")
            elif d["action"] == "warn" and last != "warn":
                notify(f"⚠ propguard near limit — {line}")
            else:
                print(line, flush=True)
            last = d["action"]
        except Exception as e:                       # never die silently; keep guarding
            notify(f"❗ propguard error: {e}")
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())
