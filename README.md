# ngmi

**Not gonna make it**, unless you take profits.

`ngmi` is a terminal dashboard of objective exit signals: a grid of square tiles, each
green, amber or red, with a sparkline, a plain-language rule and how long it has been in that state.
It's meant for people who are good at spotting uptrends but hold too long.

![ngmi --demo](docs/demo.png)

> Not financial advice. These are rules of thumb that you configure yourself.

## Install

Not on PyPI yet, so install from a clone. Needs [uv](https://docs.astral.sh/uv/).

```bash
git clone <this repo> ngmi && cd ngmi
uv tool install --editable .   # puts `ngmi` on your PATH; code changes apply without reinstalling
ngmi init                      # writes ~/.config/ngmi/config.toml
ngmi
```

Try it without any setup: `uv run ngmi --demo`.

## Usage

| Command        | What it does                         |
| -------------- | ------------------------------------ |
| `ngmi`         | Show all signal tiles                |
| `ngmi --json`  | Same, as JSON (pipe it anywhere)     |
| `ngmi --demo`  | Built-in mock data, no network       |
| `ngmi --cols 4`| Force tiles per row (default: fit the terminal, max 5) |
| `ngmi signals` | List signals and whether they're on  |
| `ngmi history` | Each signal's color per day, from the local log |
| `ngmi --no-log`| Don't record this run                |
| `ngmi init`    | Write a starter config               |

## Config and keys

Everything runs locally. Thresholds and positions live in `~/.config/ngmi/config.toml`.
No API keys are needed: every source has a free public endpoint.

## Signals

| Tile                    | Source         | Red when                                     |
| ----------------------- | -------------- | -------------------------------------------- |
| Profit plan (per plan)  | CoinGecko / Yahoo | one of your take-profit steps is reached  |
| Drawdown (per position) | CoinGecko / Yahoo | 20%+ below the rolling 90-day high        |
| Trend (positions + watch) | CoinGecko / Yahoo | price below the 200-day MA (amber: below the 50-day) |
| Weekly RSI (per position) | CoinGecko / Yahoo | weekly RSI above 80                     |
| BTC Pi Cycle Top        | Yahoo (BTC-USD) | 111-day MA crosses 2x the 350-day MA        |
| Crypto Fear & Greed     | alternative.me | 75+ (extreme greed)                          |
| BTC funding             | OKX            | 7-day average funding 30%+/yr                |
| Liquidity               | FRED (WALCL or M2SL) | down 2%+ over 90 days                  |
| US 10Y yield            | FRED (DGS10)   | up 50bp+ in 30 days                          |

Every threshold and window is configurable. `[positions]` are what you hold (drawdown +
trend tiles); `[watch]` is context like gold and silver (trend tiles only).

## Take-profit plans

Decide your exits while you're calm, not in the moment. Add a plan per position:

```toml
[plans.bitcoin]
entry = 40000
done = 0          # bump this after you sell a step
steps = [
  { gain = 100, sell = 20 },   # at +100%, sell 20% of the original position
  { gain = 200, sell = 25 },
  { gain = 300, sell = 25 },
]
```

The plan tile turns amber when the next step is within 10% and red when it's due,
with exactly what to sell.

## History

Each run saves the day's colors to `~/.local/share/ngmi/history.jsonl` (one entry per
day). `ngmi history` shows the last 30 days per signal, and the dashboard calls out
anything that has been red on 3+ checks in a row. Use `--no-log` to skip.

## Adding a signal

1. **Adapter** (`src/ngmi/adapters/`): fetch a source and return a daily `pandas.Series`.
   Adapters are injected through `Sources` (`sources.py`), so tests and `--demo` swap in
   the mocks from `adapters/mock.py`.
2. **Rule** (`src/ngmi/rules/`): a pure function `(series, config) -> Signal`. Use
   `rules.base.state_since` to compute how long it has been in its current status.
3. **Config**: add a thresholds model in `config.py` and defaults in `default_config.toml`.
4. **Register** it in `registry.py`, and add tests. Use synthetic data, never recorded
   API responses: add a builder to `tests/fixtures/generate.py` and rerun it.

## Development

```bash
uv sync
uv run pytest
uv run ngmi
```
# ngmi
