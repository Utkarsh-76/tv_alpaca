import requests
from flask import Flask, request
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

ALPACA_BUY_API_KEY = os.getenv("ALPACA_BUY_API_KEY")
ALPACA_BUY_SECRET_KEY = os.getenv("ALPACA_BUY_SECRET_KEY")
ALPACA_BUY_ENDPOINT = os.getenv("ALPACA_BUY_ENDPOINT")

ALPACA_SELL_API_KEY = os.getenv("ALPACA_SELL_API_KEY")
ALPACA_SELL_SECRET_KEY = os.getenv("ALPACA_SELL_SECRET_KEY")
ALPACA_SELL_ENDPOINT = os.getenv("ALPACA_SELL_ENDPOINT")


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    transaction_type = data['transaction_type'].lower()
    quantity = data['quantity']
    ticker = "SPY"

    order = {
        'symbol': ticker,
        'qty': quantity,
        'side': transaction_type,
        'type': 'market',
        'time_in_force': 'gtc'
    }

    if transaction_type == "buy":
        response = requests.post(ALPACA_BUY_API_KEY, json=order, headers={
            'APCA-API-KEY-ID': ALPACA_BUY_API_KEY,
            'APCA-API-SECRET-KEY': ALPACA_BUY_SECRET_KEY
        })
        return response.json()
    elif transaction_type == "sell":
        response = requests.post(ALPACA_SELL_API_KEY, json=order, headers={
            'APCA-API-KEY-ID': ALPACA_SELL_API_KEY,
            'APCA-API-SECRET-KEY': ALPACA_SELL_SECRET_KEY
        })
        return response.json()
    else:
        return {"message": "wrong transaction_type"}


@app.route('/', methods=['GET'])
def health_check():
    return {"message": "all good"}


if __name__ == '__main__':
    app.run(port=5000)
