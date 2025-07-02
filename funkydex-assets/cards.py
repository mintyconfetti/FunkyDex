import random
import json
from constants import RARITY_WEIGHTS, RARITY_POWER_RANGE

with open("cards.json") as f:
    CARD_POOL = json.load(f)

def roll_card():
    cards = [c for c in CARD_POOL if RARITY_WEIGHTS.get(c["rarity"], 0) > 0]
    weights = [RARITY_WEIGHTS.get(c["rarity"], 0) for c in cards]
    base = random.choices(cards, weights=weights, k=1)[0]
    card = base.copy()
    if card["rarity"] in RARITY_POWER_RANGE:
        pmin, pmax = RARITY_POWER_RANGE[card["rarity"]]
        card["power"] = random.randint(pmin, pmax)
    return card
    