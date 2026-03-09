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

# Live account
ALPACA_LIVE_API_KEY = os.getenv("ALPACA_LIVE_API_KEY")
ALPACA_LIVE_SECRET_KEY = os.getenv("ALPACA_LIVE_SECRET_KEY")
ALPACA_LIVE_ENDPOINT = os.getenv("ALPACA_LIVE_ENDPOINT")

# Paper account
ALPACA_PAPER_API_KEY = os.getenv("ALPACA_PAPER_API_KEY")
ALPACA_PAPER_SECRET_KEY = os.getenv("ALPACA_PAPER_SECRET_KEY")
ALPACA_PAPER_ENDPOINT = os.getenv("ALPACA_PAPER_ENDPOINT")

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


def place_order(label, endpoint, api_key, secret_key, order):
    """Send an order to a single Alpaca endpoint and return the result."""
    try:
        response = requests.post(
            endpoint,
            json=order,
            headers={
                'APCA-API-KEY-ID': api_key,
                'APCA-API-SECRET-KEY': secret_key
            }
        )
        result = response.json()
        logging.info(f"[{label}] Order response: {result}")
        return {"status": "ok", "response": result}
    except Exception as e:
        logging.error(f"[{label}] Order failed: {e}")
        return {"status": "error", "error": str(e)}


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

    logging.info(
        f"Transaction: {transaction_type}, Consecutive Count: {order_state['consecutive_count']}, "
        f"Multiplier: {multiplier}, Quantity: {quantity}"
    )

    order = {
        'symbol': ticker,
        'qty': quantity,
        'side': transaction_type,
        'type': 'market',
        'time_in_force': 'gtc'
    }

    live_result = place_order("LIVE", ALPACA_LIVE_ENDPOINT, ALPACA_LIVE_API_KEY, ALPACA_LIVE_SECRET_KEY, order)
    paper_result = place_order("PAPER", ALPACA_PAPER_ENDPOINT, ALPACA_PAPER_API_KEY, ALPACA_PAPER_SECRET_KEY, order)

    return jsonify({"live": live_result, "paper": paper_result})


@app.route('/health', methods=['GET'])
def health_check():
    # Return a JSON response indicating the app is healthy
    return jsonify(status="healthy", message="API is running"), 200


if __name__ == '__main__':
    app.run(port=5000)
