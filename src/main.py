

import os
import json
import typing
import dotenv
import argparse

import datetime
import requests

import numpy as np
import pandas as pd

import src.sheets as sheets
from flask import Flask, request, jsonify, render_template

import warnings
warnings.filterwarnings("ignore")

dotenv.load_dotenv()
DEFAULT_TICKERS = ["HOOD", "SHOP", "COIN"]

sheets.clear_sheet()

def parse_arguments():
    """
    Parses command-line arguments to load tickers.
    
    Returns:
    - tickers (list): List of tickers to simulate the strategy on.
    """
    parser = argparse.ArgumentParser(description="Simulate trading strategy on tickers.")
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers to simulate strategy on, e.g., HOOD,SHOP,COIN",
        default=",".join(DEFAULT_TICKERS)
    )

    parser.add_argument(
        "--webapp",
        action="store_true",
        help="Run the script in webapp mode"
    )

    args = parser.parse_args()
    return args

def get_historical_data(ticker: str) -> typing.Dict:
    """
    Gets stock data from the Yahoo Finance API given a stock ticker.

    Parameters:
    - ticker (str): The stock ticker to get data for.

    Returns:
    - stock_data (dict): A dictionary containing stock data.
    """

    # set the period1 timestamp to 0 to encompass all historical data
    period1 = 0

    # period2 timestamp is set to the timestamp of today's date
    period2 = datetime.datetime.now().timestamp()
    period2 = str(int(period2))

    URL = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?events=capitalGain%7Cdiv%7Csplit&formatted=true&includeAdjustedClose=true&interval=1d&period1={period1}&period2={period2}&symbol={ticker}&userYfid=true&lang=en-US&region=US'

    # the request necessitates a user agent, requests default user agent is blocked
    response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'})

    if response.status_code != 200:
        raise Exception('Failed to get stock data', response.status_code, response.text)
    
    data = response.json()

    if not data.get('chart', False) or data.get('chart', {}).get('error', False) or len(data.get('chart', {}).get('result', [])) == 0:
        raise Exception('API response error', data.get('error'))  
    
    return data.get('chart', {}).get('result', [])[0]

def format_data(data: typing.Dict) -> pd.DataFrame:
    """
    Transforms the raw data from the Yahoo Finance API into a pandas DataFrame.

    Parameters:
    - data (dict): The raw data from the Yahoo Finance API.

    Returns:
    - df (pd.DataFrame): A pandas DataFrame containing the stock data.
    """

    # we create an array of daily data by combining the timestamp, open, close, high, low, and volume into a 
    # single dictionnary per day
    days = [
        {
            'timestamp': data.get('timestamp', [])[day],
            'open': data.get('indicators', {}).get('quote', [])[0].get('open', [])[day],
            'close': data.get('indicators', {}).get('quote', [])[0].get('close', [])[day],
            'high': data.get('indicators', {}).get('quote', [])[0].get('high', [])[day],
            'low': data.get('indicators', {}).get('quote', [])[0].get('low', [])[day],
            'volume': data.get('indicators', {}).get('quote', [])[0].get('volume', [])[day],
        }
        for day in range(len(data.get('timestamp', [])))
    ]

    # we generate a dataframe from that array as it will ease the manipulation of the data
    df = pd.DataFrame(days)

    # format the date to make it easier to debug if needed :)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df['timestamp'] = df['timestamp'].dt.date

    return df

# used for benchmarking
snp_500_data = get_historical_data('%5ESPX')
snp_500_data = format_data(snp_500_data)

def simulate_strategy(ticker: str):
    """
    Simulates our strategy on a given ticker.

    Parameters:
    - ticker (str): The stock ticker to simulate the strategy on.

    Returns:
    - returns (float): The average returns of the strategy for that ticker.
    """

    data = get_historical_data(ticker)
    df = format_data(data)

    # compute returns of holding the stock from IPO to now
    # to have some benchmark
    introduction_price = df['open'].iloc[0]
    final_price = df['close'].iloc[-1] 

    holding_return = (final_price - introduction_price) / introduction_price * 100

    # compute the snp_500 holding return on the same period
    introduction_date = df['timestamp'].iloc[0]
    final_date = df['timestamp'].iloc[-1]

    snp_500_introduction = snp_500_data[snp_500_data['timestamp'] == introduction_date]['open'].iloc[0]
    snp_500_final = snp_500_data[snp_500_data['timestamp'] == final_date]['close'].iloc[0]

    # in case snp500 open value is 0 (which is possible before a given date) then we assume
    # the first available value
    if snp_500_introduction == 0:
        snp_500_introduction = snp_500_data[snp_500_data['open'] > 0]['open'].iloc[0]

    snp_500_holding_return = (snp_500_final - snp_500_introduction) / snp_500_introduction * 100

    # Compute the daily change in %
    df['change'] = (df['close'] - df['open']) / df['open'] * 100

    # For each row compute the average of volume over the past 20 days
    df['20_day_avg_volume'] = df['volume'].rolling(window=20).mean()

    # we set flags to easily compute the breakout
    # set a volume_breakout flag if the current day's volume is >300% of the 20 day average
    # set a price_breakout flag if the current day change is >= 2%
    df['volume_breakout'] = df['volume'] > 3 * df['20_day_avg_volume']
    df['price_breakout'] = df['change'] >= 2
    df['breakout'] = df['volume_breakout'] & df['price_breakout']

    # we need to compute the returns of what would have happened if we had bought on close at breakout day
    # and that we had sold on open 20+ days later
    df['buy_price'] = df['close']
    df['sell_price'] = df['open'].shift(-20)
    df['sell_date'] = df['timestamp'].shift(-20)

    # in case we don't have 20 days of data left sell_price will be NaN, we need to filter those rows
    breakout_df = df[df['sell_price'].notnull()]
    breakout_df['return'] = (breakout_df['sell_price'] - breakout_df['buy_price']) / breakout_df['buy_price'] * 100

    # we filter the rows where a breakout occured
    breakout_df = breakout_df[breakout_df['breakout']]
    breakout_df['cumulated'] = (1 + breakout_df['return'] / 100).cumprod()
    
    if snp_500_holding_return == float('inf'):
        snp_500_holding_return = 'N/A'

    return {
        'Ticker': ticker,
        'Breakouts count': len(breakout_df),
        'Average returns per trade in %': breakout_df['return'].mean(),
        'Cumulated returns in %': (breakout_df['cumulated'].iloc[-1] - 1) * 100,
        'Lowest performance reached in cumulated returns in %': 100 * min(breakout_df['cumulated'].min() - 1, 0),
        'Highest performance reached in cumulated returns in %': (max(breakout_df['cumulated'].max(), 1) - 1) * 100,
        'Passive holding of the stock returns in % from IPO to now': holding_return,
        'Passive holding of the S&P 500 returns in % from IPO to now': snp_500_holding_return
    }, breakout_df.to_dict(orient='records')


# load tickers.json
args = parse_arguments()

tickers = args.tickers.split(',')
print(f'Running strategy on tickers: {tickers}')

results = [simulate_strategy(ticker) for ticker in tickers]

if os.environ.get('GOOGLE_SHEET_ID'):
    sheets.update_sheet([result[0] for result in results])
    print(f'Google sheet updated visit at https://docs.google.com/spreadsheets/d/{os.getenv("GOOGLE_SHEET_ID")}')

if args.webapp and __name__ == '__main__':
    app = Flask(__name__, template_folder='./pages')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/ticker/<string:ticker>', methods=['POST'])
    def get_ticker(ticker):
        try:
            results = simulate_strategy(ticker)
            return jsonify({"results": results[0], "trades": results[1]})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    app.run(debug=True, port=8500, host='0.0.0.0')