#!/usr/bin/env python3
"""Hourly automation: pull latest prices of tradable crypto on Robinhood.com.

Sources (public, no API key required):
  - Tradable list: https://nummus.robinhood.com/currency_pairs/  (filter tradability == "tradable")
  - Live quotes:   https://api.robinhood.com/marketdata/forex/quotes/?symbols=BTCUSD,ETHUSD,...

"Trending" is defined as largest absolute % move (mark vs open price) in the
current Robinhood session, which mirrors how Robinhood surfaces movers without
scraping JS-heavy pages. Output includes top movers, gainers, and losers.

Outputs (relative to repo root):
  - data/robinhood_trending_crypto/YYYY-MM-DD_HH-MM-UTC.csv
  - data/robinhood_trending_crypto/latest.json  (overwritten each run)
  - data/robinhood_trending_crypto/history.jsonl (one JSON row appended per run)

Stdlib only. Exit code 0 on success, 1 on failure.
Usage:
  python scripts/robinhood_trending_crypto.py [--top 15] [--out-dir data/robinhood_trending_crypto]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

PAIRS_URL = "https://nummus.robinhood.com/currency_pairs/"
QUOTES_URL = "https://api.robinhood.com/marketdata/forex/quotes/?symbols={symbols}"
UA = {"User-Agent": "OpenAutomations-hourly/1.0 (+https://github.com)"}
BATCH = 40
TIMEOUT = 25


def http_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def get_tradable_symbols() -> list[str]:
    data = http_json(PAIRS_URL)
    results = data.get("results", data) if isinstance(data, dict) else data
    syms = sorted(
        r["symbol"] for r in results if r.get("tradability") == "tradable" and r.get("symbol")
    )
    return syms  # e.g. ["AAVE-USD", ...]


def get_quotes(dash_symbols: list[str]) -> list[dict]:
    """Fetch quotes in batches. Robinhood wants symbols without dash: BTCUSD."""
    out: list[dict] = []
    stripped = [s.replace("-", "") for s in dash_symbols]
    for i in range(0, len(stripped), BATCH):
        chunk = stripped[i : i + BATCH]
        url = QUOTES_URL.format(symbols=",".join(chunk))
        data = http_json(url)
        out.extend(data.get("results", []))
    return out


def pct(mark: float | None, open_: float | None) -> float | None:
    try:
        if mark is None or open_ is None or open_ == 0:
            return None
        return (mark - open_) / open_ * 100.0
    except (TypeError, ValueError):
        return None


def f(x: str | None) -> float | None:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--out-dir", default="data/robinhood_trending_crypto")
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%Y-%m-%d_%H-%M-UTC")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        symbols = get_tradable_symbols()
        if not symbols:
            print("ERROR: empty tradable list", file=sys.stderr)
            return 1
        quotes = get_quotes(symbols)
        by_sym = {q.get("symbol"): q for q in quotes}

        rows: list[dict] = []
        for dash in symbols:
            flat = dash.replace("-", "")
            q = by_sym.get(flat, {})
            mark, open_ = f(q.get("mark_price")), f(q.get("open_price"))
            rows.append(
                {
                    "timestamp_utc": now.isoformat(),
                    "symbol": dash,
                    "mark_price": mark,
                    "bid_price": f(q.get("bid_price")),
                    "ask_price": f(q.get("ask_price")),
                    "open_price": open_,
                    "high_price": f(q.get("high_price")),
                    "low_price": f(q.get("low_price")),
                    "change_pct_vs_open": pct(mark, open_),
                    "updated_at": q.get("updated_at"),
                    "robinhood_url": f"https://robinhood.com/us/en/crypto/{dash.split('-')[0].lower()}",
                }
            )

        priced = [r for r in rows if r["mark_price"] is not None]
        movers = sorted(
            [r for r in priced if r["change_pct_vs_open"] is not None],
            key=lambda r: abs(r["change_pct_vs_open"]),
            reverse=True,
        )
        trending = movers[: args.top]
        gainers = sorted(movers, key=lambda r: r["change_pct_vs_open"], reverse=True)[:5]
        losers = sorted(movers, key=lambda r: r["change_pct_vs_open"])[:5]

        # CSV snapshot (all tradable, sorted by symbol)
        csv_path = out_dir / f"{stamp}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: r["symbol"]))

        payload = {
            "timestamp_utc": now.isoformat(),
            "source": "robinhood.com public marketdata (nummus + api.robinhood.com)",
            "tradable_count": len(symbols),
            "quoted_count": len(priced),
            "trending_top": [
                {
                    "symbol": r["symbol"],
                    "mark_price": r["mark_price"],
                    "change_pct_vs_open": round(r["change_pct_vs_open"], 4),
                    "url": r["robinhood_url"],
                }
                for r in trending
            ],
            "top_gainers_5": [
                {"symbol": r["symbol"], "change_pct": round(r["change_pct_vs_open"], 4)} for r in gainers
            ],
            "top_losers_5": [
                {"symbol": r["symbol"], "change_pct": round(r["change_pct_vs_open"], 4)} for r in losers
            ],
            "csv": str(csv_path.as_posix()),
        }
        (out_dir / "latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        with (out_dir / "history.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")

        print(f"[{stamp}] tradable={len(symbols)} quoted={len(priced)} csv={csv_path.name}")
        print("TRENDING (biggest |move|):")
        for t in payload["trending_top"]:
            print(f"  {t['symbol']:12s} {t['mark_price']!s:>18s}  {t['change_pct_vs_open']:+.2f}%")
        return 0
    except Exception as e:  # noqa: BLE001 - hourly job must report, not crash silently
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
