"""Slow Donchian breakout bot for the cbBTC/USDC bars-replay race.

Pivot: replace the EMA-cross version with a slow Donchian breakout hold.
Every indicator lives on a 5-minute clock: sample every fifth one-minute
close, and use the low of the five bars ending at each sample.

  - entry: the sampled close breaks above the highest of the previous
    BREAKOUT_BARS sampled closes (a simple breakout confirmation);
  - hold: while the close stays above a trailing reference, the lowest low
    of the last TRAIL_BARS samples, ratcheted upward only;
  - exit: close below that trailing reference, or 3% under cost;
  - at most MAX_ENTRIES entries over the whole window.

Slice 5 built and checked the sampler with no orders.  Slice 6 added the
entry/hold rules.  Slice 7 tuned them on the dev window and chose the centre
of a positive plateau: breakout 12 samples (60 minutes), trailing reference
8 samples (40 minutes), hard stop 3%, at most 3 entries.  The vendored shim
is a byte-for-byte copy of the kit SDK and owns the wire, the fills and the
final flatten.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
SAMPLE_EVERY = 5
BREAKOUT_BARS = 12
TRAIL_BARS = 8
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
    """Fold this batch's bars, then decide at most one order."""
    symbol = SYMBOL
    s = _series.get(symbol)
    if s is not None:
        s.fresh = False
    for bar in batch["bars"]:
        sym = bar["symbol"]
        series = _series.get(sym)
        if series is None:
            series = _series[sym] = Series()
        push(series, bar)
    if state.warming_up:
        return []
    s = _series.get(symbol)
    if s is None:
        return []

    close = state.close(symbol)
    held = state.positions.get(symbol)
    if held is not None:
        s.pending = False
        if close is None:
            return []
        if s.fresh and s.trail_candidate is not None:
            if s.trail is None or s.trail_candidate > s.trail:
                s.trail = s.trail_candidate
        value = state.value(symbol, held.qty)
        hard_hit = value * 100 <= held.cost * HARD_STOP_RATIO
        break_hit = s.trail is not None and close < s.trail
        if hard_hit or break_hit:
            s.trail = None
            return [{"side": "sell", "symbol": symbol, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []

    s.trail = None
    if s.pending or not s.fresh or not s.breakout or s.entries >= MAX_ENTRIES:
        return []
    stake = state.cash * STAKE_PERCENT // 100
    room = state.weight_room(symbol)
    if stake > room:
        stake = room
    minimum = int(state.hello["fees"]["min_notional_quote_units"])
    if stake < minimum:
        return []
    s.entries += 1
    s.pending = True
    s.trail = s.trail_candidate
    return [{"side": "buy", "symbol": symbol, "notional_quote_units": stake,
             "max_slippage_bps": MAX_SLIPPAGE_BPS}]


if __name__ == "__main__":
    makefun_bars.run(on_batch)
