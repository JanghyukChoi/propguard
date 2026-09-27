from datetime import datetime, timedelta, timezone

from propguard.presets import preset
from propguard.rules import State, day_start, evaluate

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def test_day_start_before_and_after_reset():
    assert day_start(datetime(2026, 9, 1, 3, tzinfo=timezone.utc), 5) == datetime(2026, 8, 31, 5, tzinfo=timezone.utc)
    assert day_start(datetime(2026, 9, 1, 6, tzinfo=timezone.utc), 5) == datetime(2026, 9, 1, 5, tzinfo=timezone.utc)


def test_ok_warn_flatten_sequence():
    r = preset("cft-2phase", 25_000, buffer_pct=0.005)          # daily floor 23,750 · trigger 23,875
    st = State()
    assert evaluate(st, r, T0, 25_000, 25_000)["action"] == "ok"
    assert evaluate(st, r, T0, 23_990, 25_000)["action"] == "warn"      # room 240 ≤ 250
    d = evaluate(st, r, T0, 23_875, 25_000)
    assert d["action"] == "flatten" and st.locked_until == datetime(2026, 9, 2, 0, tzinfo=timezone.utc)
    assert evaluate(st, r, T0 + timedelta(hours=1), 24_500, 25_000)["action"] == "locked"


def test_lock_released_after_reset():
    r = preset("cft-2phase", 25_000)
    st = State()
    evaluate(st, r, T0, 25_000, 25_000)
    evaluate(st, r, T0, 23_800, 25_000)
    assert evaluate(st, r, T0 + timedelta(hours=13), 23_800, 23_800)["action"] in ("ok", "warn")


def test_daily_ref_max_uses_larger_of_balance_and_equity():
    r = preset("cft-2phase", 25_000)                            # daily_ref = max
    st = State()
    d = evaluate(st, r, T0, 24_000, 26_000)                      # open loss at reset: ref = 26,000
    assert d["daily_floor"] == 26_000 - 1_250


def test_static_max_floor_binds_over_daily():
    r = preset("cft-2phase", 25_000)
    st = State(day_start=day_start(T0, 0), day_ref_equity=23_000, high_water=25_000)
    d = evaluate(st, r, T0, 23_000, 23_000)
    assert d["max_floor"] == 22_500 and d["floor"] == max(d["daily_floor"], 22_500)


def test_trailing_max_follows_high_water():
    r = preset("generic", 10_000, max_loss_mode="trailing")
    st = State()
    evaluate(st, r, T0, 11_000, 11_000)
    d = evaluate(st, r, T0, 11_000, 11_000)
    assert d["max_floor"] == 11_000 - 1_000
