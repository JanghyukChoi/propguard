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
| `mubite-2step` | 5 % | 8 % | static |
| `mubite-2step-addon` | 5 % | 10 % | static |
| `generic` | 5 % | 10 % | static |

⚠ **Presets are examples compiled from public pages. Rules change and add-ons change the
numbers. Verify every value against your own dashboard before using `--live`.**
Override anything: `--buffer 0.01`, `--reset-hour 0`.

Daily loss is measured from the larger of balance and equity at the reset by default
(conservative). If you start the guard mid-day without a state file, pass
`--day-start-equity` — otherwise today's losses are invisible to it.

## Firm rules on self-hosted risk scripts

We asked support at each firm (September 2026) whether a **self-hosted** script that only
reads equity and cancels orders / closes positions with reduce-only orders is allowed.
Summary of the answers we received — **rules change, confirm with your firm**:

| Firm | Answer | Conditions mentioned |
|---|---|---|
| Crypto Fund Trader | Allowed when used for risk management / avoiding violations | — |
| HyroTrader | Allowed in challenge and funded phases | must not open trades · no copy trading or external signals · **third-party apps not supported during the challenge — your own self-hosted script is fine** |
| Mubite | No restriction stated | **never delete or change the API key** · usual challenge rules apply |

This is why `propguard` is **self-hosted only**: you run it yourself with your own key.
It never opens positions and never touches API-key settings.

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

## Support the project

`propguard` is free and MIT-licensed. If you are about to buy a Crypto Fund Trader
challenge anyway, using this link supports development at no extra cost to you, and the
coupon **`platinum5`** gives you **5 % off**:

**https://cryptofundtrader.com?_by=dk4xtp**

*Disclosure: this is an affiliate link — the maintainer receives a commission if you
purchase through it. The tool works the same whether or not you use it.*

## License

MIT. Not financial advice. Not affiliated with any prop firm or exchange.
