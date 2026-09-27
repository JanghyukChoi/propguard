import propguard.guard as G


class FakeEx:
    def __init__(self, eq):
        self.eq, self.cancelled, self.closed = eq, 0, []
        self.pos = [{"symbol": "BTCUSDT", "side": "Buy", "size": "0.1", "positionIdx": 0}]

    def equity(self):
        return self.eq, self.eq

    def positions(self):
        return [p for p in self.pos if p["symbol"] not in self.closed]

    def cancel_all(self):
        self.cancelled += 1

    def close(self, p):
        self.closed.append(p["symbol"])


def run(monkeypatch, tmp_path, eq, live):
    ex = FakeEx(eq)
    monkeypatch.setattr(G, "Bybit", lambda *a, **k: ex)
    args = ["--preset", "cft-2phase", "--size", "25000", "--day-start-equity", "25000",
            "--state", str(tmp_path / "s.json"), "--once"] + (["--live"] if live else [])
    assert G.main(args) == 0
    return ex


def test_live_flattens_at_trigger(monkeypatch, tmp_path):
    ex = run(monkeypatch, tmp_path, 23_870, live=True)
    assert ex.cancelled == 1 and ex.closed == ["BTCUSDT"]


def test_dry_run_never_acts(monkeypatch, tmp_path):
    ex = run(monkeypatch, tmp_path, 23_870, live=False)
    assert ex.cancelled == 0 and ex.closed == []


def test_no_action_when_room(monkeypatch, tmp_path):
    ex = run(monkeypatch, tmp_path, 24_900, live=True)
    assert ex.cancelled == 0 and ex.closed == []
