# Dev-window tuning notes

All numbers below come from `grade-local --kit . --bot /root/makefun/btc-pras-repo
--driver docker --worktree` on the kit's frozen dev window (1440 one-minute
bars), with the bot run twice per grade and the action logs compared byte for
byte. Each row is one grade, not an estimate.

## Hypothesis and design

The median one-minute move is 2.76 bps while a full-size round trip costs
about 26 bps, so scalping cannot pay. The bot samples every fifth close, so
both the EMA and the ATR live on a 5-minute clock (ATR high/low are the
extremes of the five bars ending at a sampled close). It enters on an EMA
up-cross only when 5-minute ATR/price clears a floor, stakes 90% of cash, and
exits on a three-sample-confirmed down-cross, a trailing stop from the highest
close since entry, or a 2% stop under cost.

## Chosen parameters

| Constant | Value |
| --- | --- |
| EMA fast / slow | 6 / 13 sampled bars (30 / 65 minutes) |
| ATR length | 14 sampled bars |
| ATR volatility floor | 8 bps |
| Trailing stop | 5.0 x ATR from peak close |
| Hard stop | 2% under cost |
| Reversal confirmation | 3 sampled bars |
| Stake | 90% of cash |

Chosen result: **net PnL +10.735 USDC, 9 trades, max drawdown 2.479%**.

## Neighbours of the chosen set

| Change | Net PnL (USDC) | Trades | Max drawdown |
| --- | ---: | ---: | ---: |
| chosen: EMA 6/13, trail 5, floor 8, reversal 3 | +10.735 | 9 | 2.479% |
| trail 4 | +11.527 | 9 | 2.403% |
| trail 6 | +9.559 | 9 | 2.592% |
| trail 7 | +7.063 | 9 | 2.833% |
| floor 6 | +7.796 | 11 | 2.762% |
| floor 10 | +10.735 | 9 | 2.479% |
| EMA 6/12 | +10.735 | 9 | 2.479% |
| EMA 5/13 | +6.475 | 11 | 2.890% |
| EMA 6/14 | -17.047 | 9 | 2.272% |
| EMA 7/13 | -17.047 | 9 | 2.272% |
| reversal 2 | +10.660 | 9 | 2.486% |
| reversal 5 | +10.189 | 9 | 2.532% |

The stop multiplier (4-7), volatility floor (6-10) and reversal length (2-5)
form a broad positive plateau, so the choice is not a single best spike. The
EMA span is the sensitive axis: the suggested slow references 10/20, 12/26
and 15/30 all lose on this window because the one large move is mostly over
before a 12/26 cross appears. The chosen faster pair sits with its neighbours
6/12 and 5/13 on the positive side; 6/14 and 7/13 are the boundary.

## Suggested reference settings (rejected, for the record)

| Setting | Net PnL (USDC) | Trades |
| --- | ---: | ---: |
| EMA 12/26, 5-min sample, ATR trail 1.2 | -19.687 | 10 |
| EMA 12/26, 5-min sample, ATR trail 1.5 | -19.823 | 10 |
| EMA 12/26, 5-min sample, ATR trail 2.0 | -24.773 | 10 |
| EMA 10/20, trail 5, floor 8, reversal 3 | -19.899 | 6 |
| EMA 15/30, trail 5, floor 8, reversal 3 | -24.966 | 8 |
| EMA 12/26, 1-min sample, trail 2 | -96.866 | 64 |

No randomness, clock or environment value enters the bot; client ids come
from the vendored shim in a fixed order, so the two executions of every grade
match byte for byte.
