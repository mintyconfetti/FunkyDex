
# events/trivia_event.py

import base64
from data_utils import save_data
from cards import CARD_POOL

# Trivia questions
TRIVIA_QUESTIONS = [
    ("What Pokemon can evolve into multiple type forms? (i.e fire stone, water stone, etc)", "eevee"),
    ("What is super effective against Steel?", "fire"),
    ("What does the Lum Berry do within the games?", "heal status effects"),
]

# Secret code and reward name
SECRET_CODE = "missingno"
ENCODED_MESSAGE = base64.b64encode(SECRET_CODE.encode()).decode()
EXCLUSIVE_CARD_NAME = "MissingNo"

def get_exclusive_card():
    for card in CARD_POOL:
        if card["name"].lower() == EXCLUSIVE_CARD_NAME.lower():
            return card.copy()
    return None

def check_trivia_answers(answers: list[str]):
    return all(a.strip().lower() == correct for a, (_, correct) in zip(answers, TRIVIA_QUESTIONS))

def get_encoded_message():
    return ENCODED_MESSAGE

def redeem_code(data, user_id: str, code: str):
    user_data = data.get(user_id)
    if not user_data:
        return False, "User not found."

    if code.strip().lower() != SECRET_CODE:
        return False, "Incorrect code."

    card = get_exclusive_card()
    if not card:
        return False, "Event card not found in the card pool."

    if any(c["name"].lower() == card["name"].lower() for c in user_data["cards"]):
        return False, "You've already claimed the event reward!"

    user_data["cards"].append(card)
    save_data(data)
    return True, card
