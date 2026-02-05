import requests
from flask import Flask, request, jsonify
import os
import json
from datetime import datetime, time
from dir_path import base_dirname

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

# File path for state persistence
STATE_FILE = os.path.join(base_dirname, 'order_state.json')

# Reset time (6 AM)
RESET_TIME = time(6, 0, 0)


def load_state():
    """Load state from file, create if doesn't exist"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Initialize default state if file doesn't exist
        default_state = {
            'last_transaction_type': None,
            'consecutive_count': 0,
            'last_reset_date': datetime.now().date().isoformat()
        }
        save_state(default_state)
        return default_state
    except json.JSONDecodeError:
        logging.error("Error decoding state file, resetting to default")
        default_state = {
            'last_transaction_type': None,
            'consecutive_count': 0,
            'last_reset_date': datetime.now().date().isoformat()
        }
        save_state(default_state)
        return default_state


def save_state(state):
    """Save state to file"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def check_and_reset_state(order_state):
    """Check if state needs to be reset based on time and date"""
    now = datetime.now()
    current_date = now.date().isoformat()
    current_time = now.time()

    last_reset_date = order_state.get('last_reset_date', current_date)

    # Check if we've crossed 6 AM boundary
    if last_reset_date != current_date and current_time >= RESET_TIME:
        logging.info(f"Resetting state - crossed 6 AM boundary. Last reset: {last_reset_date}, Current: {current_date}")
        order_state['last_transaction_type'] = None
        order_state['consecutive_count'] = 0
        order_state['last_reset_date'] = current_date
        save_state(order_state)
        return True

    # Handle case where last_reset_date is missing (backward compatibility)
    if 'last_reset_date' not in order_state:
        order_state['last_reset_date'] = current_date
        save_state(order_state)

    return False


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    transaction_type = data['transaction_type'].lower()
    multiplier = data['multiplier']
    ticker = data['ticker']

    order_state = load_state()

    # Check and reset if needed
    was_reset = check_and_reset_state(order_state)
    if was_reset:
        logging.info("State was automatically reset at 6 AM boundary")

    # Update state and calculate quantity
    if order_state['last_transaction_type'] == transaction_type:
        # Same direction, increment count
        order_state['consecutive_count'] += 1
    else:
        # Direction changed, reset to 1
        order_state['consecutive_count'] = 1
        order_state['last_transaction_type'] = transaction_type

    # Calculate quantity: consecutive_count * multiplier
    quantity = order_state['consecutive_count'] * multiplier

    # Save updated state
    save_state(order_state)

    order = {
        'symbol': ticker,
        'qty': quantity,
        'side': transaction_type,
        'type': 'market',
        'time_in_force': 'gtc'
    }

    logging.info(
        f"Transaction: {transaction_type}, Consecutive Count: {order_state['consecutive_count']}, Multiplier: {multiplier}, Quantity: {quantity}")

    if transaction_type == "buy":
        response = requests.post(ALPACA_BUY_ENDPOINT, json=order, headers={
            'APCA-API-KEY-ID': ALPACA_BUY_API_KEY,
            'APCA-API-SECRET-KEY': ALPACA_BUY_SECRET_KEY
        })
        logging.info(f"Buy order placed for quantity {quantity}")
        logging.info(response.json())
        return response.json()
    elif transaction_type == "sell":
        response = requests.post(ALPACA_SELL_ENDPOINT, json=order, headers={
            'APCA-API-KEY-ID': ALPACA_SELL_API_KEY,
            'APCA-API-SECRET-KEY': ALPACA_SELL_SECRET_KEY
        })
        logging.info(f"Sell order placed for quantity {quantity}")
        logging.info(response.json())
        return response.json()
    else:
        return {"message": "wrong transaction_type"}, 400


@app.route('/health', methods=['GET'])
def health_check():
    # Return a JSON response indicating the app is healthy
    return jsonify(status="healthy", message="API is running"), 200


if __name__ == '__main__':
    app.run(port=5000)
