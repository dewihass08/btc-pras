"""Slow Donchian breakout bot for the cbBTC/USDC bars-replay race.

Pivot from the EMA-cross version, which paid 10 round trips of ~26 bps in a
market whose median one-minute move is 2.76 bps.  This bot samples every
fifth one-minute close, so every indicator lives on a 5-minute clock:

  - entry: the sampled close breaks above the highest of the previous
    BREAKOUT_BARS sampled closes (a simple Donchian breakout confirmation);
  - hold: while the close stays above a trailing reference, the lowest low
    of the last TRAIL_BARS samples, ratcheted upward only;
  - exit: close below that trailing reference, or 3% under cost;
  - at most MAX_ENTRIES entries over the whole window.

Slice 5 builds and checks the sampled indicators with no orders.  Slice 6
adds the entry/hold rules; slice 7 tunes them on the dev window.  The
vendored shim is a byte-for-byte copy of the kit SDK and owns the wire, the
fills and the final flatten.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
SAMPLE_EVERY = 5
BREAKOUT_BARS = 12
TRAIL_BARS = 6
MAX_ENTRIES = 3
STAKE_PERCENT = 90
HARD_STOP_RATIO = 97
MAX_SLIPPAGE_BPS = 500


class Series:
    """Sampled Donchian state for one symbol."""

    __slots__ = ("n", "fresh", "agg_low", "closes", "lows", "breakout",
                 "trail_candidate", "trail", "pending", "entries")

    def __init__(self):
        self.n = 0
        self.fresh = False
        self.agg_low = None
        self.closes = []
        self.lows = []
        self.breakout = False
        self.trail_candidate = None
        self.trail = None
        self.pending = False
        self.entries = 0


def push(s, bar):
    """Accumulate one-minute bars; publish a sample every SAMPLE_EVERY bars."""
    close = int(bar["c"])
    low = int(bar["l"])
    s.agg_low = low if s.agg_low is None else min(s.agg_low, low)
    index = s.n
    s.n += 1
    if index % SAMPLE_EVERY:
        return s

    s.fresh = True
    s.closes.append(close)
    s.lows.append(s.agg_low)
    keep = max(BREAKOUT_BARS, TRAIL_BARS) + 1
    if len(s.closes) > keep:
        s.closes.pop(0)
        s.lows.pop(0)
    s.agg_low = None

    s.breakout = False
    if len(s.closes) > BREAKOUT_BARS:
        s.breakout = close > max(s.closes[-BREAKOUT_BARS - 1:-1])
    if len(s.lows) >= TRAIL_BARS:
        s.trail_candidate = min(s.lows[-TRAIL_BARS:])
    return s


_series = {}


def on_batch(state, batch):
    """Fold the batch's bars; slice 5 sends no orders."""
    for bar in batch["bars"]:
        symbol = bar["symbol"]
        s = _series.get(symbol)
        if s is None:
            s = _series[symbol] = Series()
        s.fresh = False
        push(s, bar)
    return []


if __name__ == "__main__":
    makefun_bars.run(on_batch)
