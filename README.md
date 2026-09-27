# propguard

**Stop your crypto prop-firm account from breaching its loss limits.**

Most prop challenges are not failed on skill — they are failed on rules. Industry data
(FPFX, 300k+ accounts) shows ~14 % pass, and the single biggest cause of failure is a
**daily drawdown breach**, usually on one bad day of revenge trading.

`propguard` runs next to your trading (manual or bot) on **Bybit API–based prop accounts**.
Every few seconds it reads your equity, compares it with your firm's daily and max loss
floors, and **before** equity reaches a floor it:

1. cancels all open orders,
2. closes every position with reduce-only market orders,
3. keeps the account flat until the daily reset (it re-closes anything you open).

Alert-only monitors already exist. `propguard` **acts**.

## Quick start

```bash
pip install requests
export PROPGUARD_BYBIT_KEY=...        # key WITHOUT withdrawal permission
export PROPGUARD_BYBIT_SECRET=...

# dry-run first (default): prints what it WOULD do
python -m propguard.guard --preset cft-2phase --size 25000 --day-start-equity 25000

# when you trust it
python -m propguard.guard --preset cft-2phase --size 25000 --live
```

Optional Telegram alerts: set `PROPGUARD_TG_TOKEN` and `PROPGUARD_TG_CHAT`.

## Presets

| preset | daily | max | max mode |
|---|---|---|---|
| `cft-2phase` | 5 % | 10 % | static |
| `cft-2phase-addons` | 6 % | 12 % | static |
| `hyrotrader` | 4 % | 6 % | static |
| `generic` | 5 % | 10 % | static |

⚠ **Presets are examples compiled from public pages. Rules change and add-ons change the
numbers. Verify every value against your own dashboard before using `--live`.**
Override anything: `--buffer 0.01`, `--reset-hour 0`.

Daily loss is measured from the larger of balance and equity at the reset by default
(conservative). If you start the guard mid-day without a state file, pass
`--day-start-equity` — otherwise today's losses are invisible to it.

## Safety

- Dry-run unless `--live`.
- Never needs withdrawal permission. Do not give it one.
- If the exchange API fails the guard keeps running and alerts you — but a guard is not
  a guarantee. Gaps, outages and slippage can still breach a limit. Keep a buffer.
- Check your firm's terms on automated tools before using it on an evaluation.

## Tests

```bash
pip install pytest && python -m pytest -q
```

## License

MIT. Not financial advice. Not affiliated with any prop firm or exchange.
