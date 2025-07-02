from typing import Dict, Any
import discord


# --- START TRADE ---
def start_trade(data: Dict[str, Any], from_user: discord.User, to_user: discord.User, card_name: str) -> str:
    """Start a trade with another user"""
    from_id, to_id = str(from_user.id), str(to_user.id)
    
    # Check if user has the card
    user_cards = data.get(from_id, {}).get("cards", [])
    card = next((c for c in user_cards if c["name"].lower() == card_name.lower()), None)
    
    if not card:
        return "You don't own that card."
    
    # Create user if doesn't exist
    if to_id not in data:
        data[to_id] = {"cards": [], "trades": [], "battles": 0, "wins": 0}
    
    # Add trade to recipient's trades
    data[to_id]["trades"] = [{"from": from_id, "to": to_id, "card": card}]
    
    return f"Trade sent to {to_user.mention}: **{card['name']}**"


# --- ACCEPT TRADE ---
def accept_trade(data: Dict[str, Any], user: discord.User) -> str:
    """Accept a pending trade"""
    user_id = str(user.id)
    
    # Check if user has pending trades
    trades = data.get(user_id, {}).get("trades", [])
    if not trades:
        return "No trade to accept."
    
    trade = trades[0]
    from_id = trade["from"]
    
    # Check if sender still has the card
    if from_id not in data or not any(c["name"] == trade["card"]["name"] for c in data[from_id]["cards"]):
        data[user_id]["trades"] = []
        return "Trade failed: card no longer available."
    
    # Find the actual card in sender's inventory (not just by name)
    sender_card = next((c for c in data[from_id]["cards"] if c["name"] == trade["card"]["name"]), None)
    if not sender_card:
        data[user_id]["trades"] = []
        return "Trade failed: card not found in sender's inventory."
    
    # Transfer the card
    data[from_id]["cards"].remove(sender_card)
    data[user_id]["cards"].append(sender_card)
    data[user_id]["trades"] = []
    
    return f"Trade accepted! You received **{sender_card['name']}**."


# --- CANCEL TRADE ---
def cancel_trade(data: Dict[str, Any], user: discord.User) -> str:
    """Cancel a pending trade"""
    user_id = str(user.id)
    
    # Check if user has pending trades
    trades = data.get(user_id, {}).get("trades", [])
    if not trades:
        return "No trade to cancel."
    
    data[user_id]["trades"] = []
    return "Trade canceled."