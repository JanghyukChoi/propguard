"""Example presets.

⚠ These are EXAMPLES compiled from public pages at the time of writing. Firms change
their rules and add-ons change the numbers. Verify every field against your own
account dashboard / terms before relying on it. When in doubt, the conservative
choice is daily_ref="max" and a larger buffer.
"""
from .rules import Rules


def preset(name: str, account_size: float, **override) -> Rules:
    base = PRESETS[name].copy()
    base.update(override)
    return Rules(name=name, account_size=account_size, **base)


PRESETS = {
    # Crypto Fund Trader, 2-Phase (without drawdown add-ons)
    "cft-2phase":        dict(daily_loss_pct=0.05, max_loss_pct=0.10, max_loss_mode="static", daily_ref="max"),
    # Crypto Fund Trader, 2-Phase with the daily 6 % / max 12 % add-ons
    "cft-2phase-addons": dict(daily_loss_pct=0.06, max_loss_pct=0.12, max_loss_mode="static", daily_ref="max"),
    # HyroTrader (public reviews: 4 % daily, 6 % max)
    "hyrotrader":        dict(daily_loss_pct=0.04, max_loss_pct=0.06, max_loss_mode="static", daily_ref="max"),
    # Generic conservative template
    "generic":           dict(daily_loss_pct=0.05, max_loss_pct=0.10, max_loss_mode="static", daily_ref="max"),
}
