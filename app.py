import requests
from flask import Flask, request, jsonify
import os

from log_config import configure_logging
import logging
from dotenv import load_dotenv
load_dotenv()
configure_logging()


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
    quantity = 1
    ticker = data['ticker']

    order = {
        'symbol': ticker,
        'qty': quantity,
        'side': transaction_type,
        'type': 'market',
        'time_in_force': 'gtc'
    }

    if transaction_type == "buy":
        response = requests.post(ALPACA_BUY_ENDPOINT, json=order, headers={
            'APCA-API-KEY-ID': ALPACA_BUY_API_KEY,
            'APCA-API-SECRET-KEY': ALPACA_BUY_SECRET_KEY
        })
        logging.info(f"Buy order place for quantity {quantity}")
        logging.info(response.json())
        return response.json()
    elif transaction_type == "sell":
        response = requests.post(ALPACA_SELL_ENDPOINT, json=order, headers={
            'APCA-API-KEY-ID': ALPACA_SELL_API_KEY,
            'APCA-API-SECRET-KEY': ALPACA_SELL_SECRET_KEY
        })
        logging.info(f"sell order place for quantity {quantity}")
        logging.info(response.json())
        return response.json()
    else:
        return {"message": "wrong transaction_type"}


@app.route('/health', methods=['GET'])
def health_check():
    # Return a JSON response indicating the app is healthy
    return jsonify(status="healthy", message="API is running"), 200


if __name__ == '__main__':
    app.run(port=5000)
