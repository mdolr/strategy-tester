# Quanta mini-technical-test project

Scroll-down for implementation choices

## Setup

The project utilizes [rye](https://rye.astral.sh/guide/installation/) as the environment manager, although not mandatory to run the project, it's the easiest way to make sure there won't be any compatibility issues.

### Installation

To install packages

```bash
# with rye
rye install

# without rye
pip install -r requirements.txt
```

### Running the project

```bash
# with rye
rye run main

# without rye
python -m src.main

```

### Flags

You can set different tickers using arguments

```bash
# with rye
rye run main --tickers AAPL,HOOD,MSFT

# without rye
python -m src.main --tickers AAPL,HOOD,MSFT
```

You can set the webapp mode to access the webapp at `http://127.0.0.1:8500`

```bash
# with rye
rye run main --webapp

# without rye
python -m src.main --webapp

# example combining both flags
rye run main --tickers AAPL,HOOD,MSFT --webapp
```

## Implementation

- I chose to use Yahoo Finance API as the data source as it's free and covers most markets while giving me all the data that I need (open, close, volume)

- I assumed that when a breakout happens we buy on the close price to make sure the breakout is "confirmed" and that we are not buying what could be a fake breakout with the limited information that we would have if we were to execute that strategy in real time, but we could easily modify the script to simulate returns of buying when the stock crosses exactly 2% during the day even if it finishes higher at close.

- I assumed that we sell at open of (breakout day + 20).

## Completion time

Overall the main features were completed in 2 hours and then I added the webapp which took another 30min-1hr
