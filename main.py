"""Slow trend-following bot for the cbBTC/USDC bars-replay race.

Slice 1: speak the protocol and answer every batch with no orders.  The
vendored shim is a byte-for-byte copy of the kit SDK, so all message checks,
fills and the final flatten are handled for us.  Later slices add indicators
and entries on top of this exact wire path.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"


def on_batch(state, batch):
    """One reply per batch; slice 1 deliberately returns an empty order list."""
    del state, batch
    return []


if __name__ == "__main__":
    makefun_bars.run(on_batch)
