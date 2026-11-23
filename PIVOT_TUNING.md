# Donchian pivot — dev-window tuning notes

Every number below is one `grade-local --kit . --bot /root/makefun/btc-pras-repo
--driver docker --worktree` run on the kit's frozen dev window (1440 one-minute
bars), with two executions compared byte for byte. No estimates.

## Rule chosen

One simple rule, sampled every fifth one-minute close so all indicators share
a 5-minute clock: enter when the sampled close exceeds the highest of the
previous BREAKOUT_BARS sampled closes. Hold while the close stays above a
trailing reference: the lowest low of the last TRAIL_BARS samples, ratcheted
upward only. Exit on a close below that reference or a 3% stop under cost.
At most 3 entries; 90% of cash per entry. No EMA, no ATR, no volatility
filter, no discretion.

## Chosen parameters and result

| Constant | Value |
| --- | --- |
| Breakout lookback | 12 samples (60 minutes) |
| Trailing reference | 8 samples (40 minutes) |
| Hard stop | 3% under cost |
| Entry cap | 3 |
| Stake | 90% of cash |

Chosen grade: **net PnL +11.483 USDC, 6 trades, max drawdown 2.391%**.

## Requested 3 x 3 grid (breakout 6 / 12 / 24, trail 4 / 6 / 8)

| Breakout \ Trail | 4 | 6 | 8 |
| --- | ---: | ---: | ---: |
| 6 | -7.168 | +13.051 | +10.328 |
| 12 | +2.366 | +12.710 | +11.483 |
| 24 | -5.724 | +10.912 | +15.076 |

Entries are 6 in every cell. Trail 4 is the weak edge; trail 6 and 8 are
positive at every breakout lookback. That is the stable region we targeted.

## Neighbours of the chosen 12 / 8 point

| Change | Net PnL (USDC) | Trades | Max drawdown |
| --- | ---: | ---: | ---: |
| chosen 12 / 8 | +11.483 | 6 | 2.391% |
| trail 6 | +12.710 | 6 | 1.227% |
| trail 7 | +9.576 | 6 | 2.085% |
| trail 9 | +11.483 | 6 | 2.391% |
| trail 10 | +11.483 | 6 | 2.391% |
| breakout 8 / trail 7 | +9.390 | 6 | 2.092% |
| breakout 10 / trail 7 | +9.390 | 6 | 2.092% |
| breakout 14 / trail 7 | +8.017 | 6 | 2.190% |
| breakout 16 / trail 7 | +9.634 | 6 | 2.035% |
| breakout 20 / trail 7 | +8.809 | 6 | 2.072% |
| breakout 24 / trail 7 | +8.228 | 6 | 2.128% |
| entry cap 2 | +16.020 | 4 | 1.953% |
| entry cap 4 | +9.878 | 8 | 2.546% |
| hard stop 2% | +11.483 | 6 | 2.391% |
| hard stop 4% | +11.483 | 6 | 2.391% |

Breakout 6 through 24 at trail 7-8, trail 6 through 10 at breakout 12, the
entry cap 2-4 and the hard stop 2%-4% are all positive. The chosen 12/8 sits
inside that region rather than at the +15.076 peak of the coarse grid.

The old EMA-cross bot on the same kit scored -17.390 USDC with 10 trades and
0% win rate. The pivot pays 6 trades instead of 10 and has positive expectancy
on the dev window.
