from typing import Dict, Any, Optional, Tuple
import discord


def sell_card(data: Dict[str, Any], user_id: str, card_name: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Sell a card and return success status, message, and the sold card if successful"""
    user_data = data.get(user_id)
    if not user_data:
        return False, "User not found.", None

    inventory = user_data.get("cards", [])

    # Find the card in the inventory
    card_index = next((i for i, c in enumerate(inventory) if c["name"].lower() == card_name.lower()), None)

    if card_index is None:
        return False, "Card not found in your inventory.", None

    card = inventory.pop(card_index)  # Remove the card
    rarity = card["rarity"]

    price = SELL_PRICES.get(rarity, 0)
    if price == 0:
        inventory.insert(card_index, card)  # Put the card back
        return False, f"{card['name']} cannot be sold.", None

    add_coins(user_data, price)  # Ensure this modifies user_data["coins"]
    save_data(data)

    return True, f"You sold **{card['name']}** for **{price} coins**.", card