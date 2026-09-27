"""Minimal Bybit V5 client — only what the guard needs.

Use an API key WITHOUT withdrawal permission. The guard needs: read wallet, read
positions, cancel orders, place reduce-only market orders.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse

import requests

MAINNET = "https://api.bybit.com"
TESTNET = "https://api-testnet.bybit.com"


class Bybit:
    def __init__(self, key: str, secret: str, base: str = MAINNET, recv_window: int = 5000):
        if not key or not secret:
            raise ValueError("API key/secret missing (set PROPGUARD_BYBIT_KEY / PROPGUARD_BYBIT_SECRET)")
        self.key, self.secret, self.base, self.rw = key, secret, base.rstrip("/"), str(recv_window)
        self.s = requests.Session()

    def _headers(self, payload: str) -> dict:
        ts = str(int(time.time() * 1000))
        sig = hmac.new(self.secret.encode(), (ts + self.key + self.rw + payload).encode(), hashlib.sha256).hexdigest()
        return {"X-BAPI-API-KEY": self.key, "X-BAPI-TIMESTAMP": ts, "X-BAPI-RECV-WINDOW": self.rw,
                "X-BAPI-SIGN": sig, "Content-Type": "application/json"}

    def _get(self, path: str, params: dict) -> dict:
        q = urllib.parse.urlencode(params)
        r = self.s.get(f"{self.base}{path}?{q}", headers=self._headers(q), timeout=10)
        return self._check(r.json())

    def _post(self, path: str, body: dict) -> dict:
        b = json.dumps(body, separators=(",", ":"))
        r = self.s.post(f"{self.base}{path}", data=b, headers=self._headers(b), timeout=10)
        return self._check(r.json())

    @staticmethod
    def _check(j: dict) -> dict:
        if j.get("retCode") != 0:
            raise RuntimeError(f"Bybit error {j.get('retCode')}: {j.get('retMsg')}")
        return j["result"]

    # ── read ──
    def equity(self) -> tuple[float, float]:
        """(total equity, total wallet balance) in USD for the unified account."""
        a = self._get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})["list"][0]
        return float(a["totalEquity"]), float(a["totalWalletBalance"])

    def positions(self) -> list[dict]:
        out, cursor = [], ""
        while True:
            p = {"category": "linear", "settleCoin": "USDT", "limit": 200}
            if cursor:
                p["cursor"] = cursor
            res = self._get("/v5/position/list", p)
            out += [x for x in res["list"] if float(x.get("size") or 0) > 0]
            cursor = res.get("nextPageCursor") or ""
            if not cursor:
                return out

    # ── act ──
    def cancel_all(self) -> None:
        self._post("/v5/order/cancel-all", {"category": "linear", "settleCoin": "USDT"})

    def close(self, pos: dict) -> None:
        side = "Sell" if pos["side"] == "Buy" else "Buy"
        self._post("/v5/order/create", {"category": "linear", "symbol": pos["symbol"], "side": side,
                                        "orderType": "Market", "qty": pos["size"], "reduceOnly": True,
                                        "positionIdx": int(pos.get("positionIdx") or 0)})
