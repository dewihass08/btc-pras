# btc-pras — slow trend-following cbBTC bot

[![btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/competitions/btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/dewihass08/btc-pras/rank.svg)](https://make.fun/competitions/btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/dewihass08/btc-pras/reward.svg)](https://make.fun/competitions/btc-race-24h-20261123-0511)

A deterministic long-only bot for the make.fun `btc-race-24h-20261123-0511`
competition. It trades Coinbase Wrapped BTC (CBBTC) against USDC in the
agent-fun/bars-replay/v1 replay, using only the standard library.

Run locally with the kit:

```
node cli/makefun.mjs grade-local --kit . --bot /path/to/btc-pras --driver docker
```

The bot is built in four verified slices: protocol shell, indicators,
entries and exits, then a parameter-plateau study on the published dev
window. `vendor/makefun_bars.py` is a byte-for-byte copy of the kit's Python
SDK shim.
