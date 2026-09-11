#!/usr/bin/env python3
"""Desktop widget: small always-on-top window with the latest Robinhood trending crypto.

Reads data/robinhood_trending_crypto/latest.json (written hourly by
scripts/robinhood_trending_crypto.py) and refreshes itself in place.
Stdlib only (tkinter).

Usage:
  python scripts/crypto_widget.py [--refresh-min 5] [--top 10] [--no-topmost]
  python scripts/crypto_widget.py --check   # headless: print rows, no window
"""
from __future__ import annotations

import argparse
import json
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LATEST = ROOT / "data" / "robinhood_trending_crypto" / "latest.json"

BG, FG = "#161616", "#eeeeee"
GREEN, RED, DIM = "#4caf50", "#ef5350", "#9e9e9e"


def load_latest(path: Path = LATEST) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def fmt_price(x: float | None) -> str:
    if x is None:
        return "—"
    if x == 0:
        return "0"
    if abs(x) >= 1000:
        return f"{x:,.2f}"
    if abs(x) >= 1:
        return f"{x:,.4f}"
    return f"{x:.6f}".rstrip("0").rstrip(".")


def fmt_pct(x: float | None) -> str:
    return f"{x:+.2f}%" if x is not None else "—"


def pct_fg(x: float | None) -> str:
    if x is None:
        return DIM
    return GREEN if x >= 0 else RED


def rows_for_display(data: dict, top: int) -> list[tuple[str, str, str, str]]:
    """Return (symbol, price_str, pct_str, color) rows. Pure function, headless-safe."""
    rows = []
    for t in (data.get("trending_top") or [])[:top]:
        pct = t.get("change_pct_vs_open")
        rows.append((t.get("symbol", "?"), fmt_price(t.get("mark_price")), fmt_pct(pct), pct_fg(pct)))
    return rows


def run_check(top: int) -> int:
    data = load_latest()
    if not data:
        print(f"No data yet at {LATEST} (hourly job hasn't written latest.json).")
        return 1
    print(f"as of {data.get('timestamp_utc')}  ({data.get('quoted_count')}/{data.get('tradable_count')} quoted)")
    for sym, price, pct, _ in rows_for_display(data, top):
        print(f"  {sym:12s} {price:>14s}  {pct:>8s}")
    return 0


class Widget:
    def __init__(self, root: tk.Tk, top: int, refresh_ms: int, topmost: bool) -> None:
        self.top, self.refresh_ms = top, refresh_ms
        self.root = root
        root.title("RH Trending Crypto")
        root.configure(bg=BG)
        root.attributes("-topmost", topmost)
        root.geometry("330x470")
        root.resizable(False, False)

        self.header = tk.Label(root, bg=BG, fg=DIM, font=("Segoe UI", 8), anchor="w")
        self.header.pack(fill="x", padx=10, pady=(8, 2))

        self.rows_frame = tk.Frame(root, bg=BG)
        self.rows_frame.pack(fill="both", expand=True, padx=10)
        self.row_labels: list[tuple[tk.Label, tk.Label, tk.Label]] = []
        for _ in range(top):
            f = tk.Frame(self.rows_frame, bg=BG)
            f.pack(fill="x", pady=1)
            sym = tk.Label(f, bg=BG, fg=FG, font=("Segoe UI", 10, "bold"), width=11, anchor="w")
            price = tk.Label(f, bg=BG, fg=FG, font=("Segoe UI", 10), width=13, anchor="e")
            pct = tk.Label(f, bg=BG, font=("Segoe UI", 10, "bold"), width=8, anchor="e")
            sym.pack(side="left")
            pct.pack(side="right")
            price.pack(side="right")
            self.row_labels.append((sym, price, pct))

        self.footer = tk.Label(root, bg=BG, fg=DIM, font=("Segoe UI", 8), anchor="w", justify="left")
        self.footer.pack(fill="x", padx=10, pady=(2, 4))

        bar = tk.Frame(root, bg=BG)
        bar.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(bar, text="Refresh", command=self.refresh).pack(side="left")
        self.pin = tk.BooleanVar(value=topmost)
        tk.Checkbutton(
            bar, text="On top", variable=self.pin, bg=BG, fg=DIM,
            selectcolor=BG, activebackground=BG,
            command=lambda: root.attributes("-topmost", self.pin.get()),
        ).pack(side="right")

        self.refresh()
        root.after(self.refresh_ms, self._tick)

    def _tick(self) -> None:
        self.refresh()
        self.root.after(self.refresh_ms, self._tick)

    def refresh(self) -> None:
        data = load_latest()
        if not data:
            self.header.config(text="waiting for first hourly run…")
            for sym, price, pct in self.row_labels:
                sym.config(text="—"); price.config(text=""); pct.config(text="", fg=DIM)
            self.footer.config(text=str(LATEST))
            return
        self.header.config(text=f"as of {data.get('timestamp_utc', '?')}")
        rows = rows_for_display(data, self.top)
        for (sym, price, pct, color), (sym_l, price_l, pct_l) in zip(rows, self.row_labels):
            sym_l.config(text=sym)
            price_l.config(text=price)
            pct_l.config(text=pct, fg=color)
        for sym_l, price_l, pct_l in self.row_labels[len(rows):]:
            sym_l.config(text="—"); price_l.config(text=""); pct_l.config(text="", fg=DIM)
        gainers = data.get("top_gainers_5") or []
        losers = data.get("top_losers_5") or []
        g = ", ".join(f"{x['symbol'].split('-')[0]} {x['change_pct']:+.1f}%" for x in gainers[:3])
        lo = ", ".join(f"{x['symbol'].split('-')[0]} {x['change_pct']:+.1f}%" for x in losers[:3])
        self.footer.config(text=f"▲ {g}\n▼ {lo}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-min", type=float, default=5)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--no-topmost", action="store_true")
    ap.add_argument("--check", action="store_true", help="headless: print rows, no window")
    args = ap.parse_args()

    if args.check:
        return run_check(args.top)

    root = tk.Tk()
    Widget(root, top=args.top, refresh_ms=max(1, int(args.refresh_min * 60_000)),
           topmost=not args.no_topmost)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
