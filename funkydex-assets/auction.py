import json
import time
from config import AUCTION_FILE, AUCTION_DURATION

def load_auctions():
    try:
        with open(AUCTION_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        save_auctions([])
        return []

def save_auctions(data):
    with open(AUCTION_FILE, "w") as f:
        json.dump(data, f, indent=4)

def remove_expired_auctions(auctions):
    now = time.time()
    return [a for a in auctions if now - a["timestamp"] < AUCTION_DURATION]

def add_auction(seller_id, card, price):
    return {
        "auction_id": str(time.time()).replace(".", ""),
        "seller_id": str(seller_id),
        "timestamp": time.time(),
        "price": price,
        "card": card
    }
    