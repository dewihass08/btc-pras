"""Slow trend-following bot for the cbBTC/USDC bars-replay race.

Slice 1 spoke the protocol with an empty order list.  Slice 2 added the
indicators: EMA(12)/EMA(26) on every fifth one-minute close (a 5-minute
sample, to keep the trade count low), and ATR(14) on every one-minute bar
from its high, low and previous close.  Slice 3 adds the rules: enter on a
confirmed up-cross with an ATR volatility filter, exit on the down-cross, a
1.5 ATR trailing stop from the highest close, or a 2% stop under cost.

The vendored shim is a byte-for-byte copy of the kit SDK, so all message
checks, fills and the final flatten are handled for us.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
FAST_SPAN = 12
SLOW_SPAN = 26
SAMPLE_EVERY = 5
ATR_LEN = 14
VOL_FLOOR_BPS = 2.0
STAKE_PERCENT = 90
TRAIL_MULT = 1.5
HARD_STOP_RATIO = 98
MAX_SLIPPAGE_BPS = 500


class Series:
    """Indicator state for one symbol, updated once per bar in arrival order."""

    __slots__ = ("n", "last_close", "trs", "atr", "warm_fast", "warm_slow",
                 "fast", "slow", "prev_gap", "gap", "cross_up", "cross_down", "down",
                 "peak", "pending")

    def __init__(self):
        self.n = 0
        self.last_close = None
        self.trs = []
        self.atr = None
        self.warm_fast = []
        self.warm_slow = []
        self.fast = None
        self.slow = None
        self.prev_gap = None
        self.gap = None
        self.cross_up = False
        self.cross_down = False
        self.down = False
        self.peak = None
        self.pending = False

    def atr_bps(self, close):
        """Latest ATR as basis points of the latest close (0 before warm-up)."""
        if self.atr is None or not close:
            return 0.0
        return self.atr * 10000.0 / close


def _ema(value, warm, span, close):
    """Seed with the mean of the first `span` samples, then smooth by 2/(span+1)."""
    if value is not None:
        return value + (2.0 / (span + 1)) * (close - value)
    warm.append(close)
    if len(warm) == span:
        return sum(warm) / span
    return None


def push(s, bar):
    """Fold one bar into the series. Cross flags are true only on sampled bars."""
    close = int(bar["c"])
    high = int(bar["h"])
    low = int(bar["l"])
    prev = s.last_close
    tr = high - low if prev is None else max(high - low, abs(high - prev), abs(low - prev))
    s.trs.append(tr)
    if len(s.trs) > ATR_LEN:
        s.trs.pop(0)
    if len(s.trs) == ATR_LEN:
        s.atr = sum(s.trs) / ATR_LEN
    s.last_close = close

    s.cross_up = False
    s.cross_down = False
    index = s.n
    s.n += 1
    if index % SAMPLE_EVERY:
        return s
    s.fast = _ema(s.fast, s.warm_fast, FAST_SPAN, close)
    s.slow = _ema(s.slow, s.warm_slow, SLOW_SPAN, close)
    if s.fast is None or s.slow is None:
        return s
    s.gap = s.fast - s.slow
    if s.prev_gap is not None:
        s.cross_up = s.gap > 0 and s.prev_gap <= 0
        s.cross_down = s.gap < 0 and s.prev_gap >= 0
    s.prev_gap = s.gap
    if s.gap < 0:
        s.down = True
    elif s.gap > 0:
        s.down = False
    return s


_series = {}


def on_batch(state, batch):
    """Fold this batch's bars, then decide at most one order."""
    for bar in batch["bars"]:
        symbol = bar["symbol"]
        s = _series.get(symbol)
        if s is None:
            s = _series[symbol] = Series()
        push(s, bar)
    if state.warming_up:
        return []

    symbol = SYMBOL
    s = _series.get(symbol)
    if s is None:
        return []
    held = state.positions.get(symbol)
    if held is not None:
        s.pending = False
        close = state.close(symbol)
        if close is None:
            return []
        if s.peak is None or close > s.peak:
            s.peak = close
        stop = s.peak - TRAIL_MULT * s.atr if s.atr is not None else None
        trail_hit = stop is not None and close <= stop
        value = state.value(symbol, held.qty)
        hard_hit = value * 100 <= held.cost * HARD_STOP_RATIO
        if s.down or trail_hit or hard_hit:
            s.peak = None
            return [{"side": "sell", "symbol": symbol, "qty": held.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []

    s.peak = None
    if s.pending or not s.cross_up or s.atr is None:
        return []
    close = state.close(symbol)
    if close is None or s.atr_bps(close) < VOL_FLOOR_BPS:
        return []
    stake = state.cash * STAKE_PERCENT // 100
    room = state.weight_room(symbol)
    if stake > room:
        stake = room
    minimum = int(state.hello["fees"]["min_notional_quote_units"])
    if stake < minimum:
        return []
    s.pending = True
    return [{"side": "buy", "symbol": symbol, "notional_quote_units": stake,
             "max_slippage_bps": MAX_SLIPPAGE_BPS}]


if __name__ == "__main__":
    makefun_bars.run(on_batch)
