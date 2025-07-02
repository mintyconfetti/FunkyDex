RARITY_WEIGHTS = {
    "Common": 100,
    "Uncommon": 75,
    "Rare": 40,
    "Epic": 10,
    "Legendary":1, 
    "Mythical": 0.02,
    "Nightmare": 0.0001,
    "Unobtainable": 0,
    "Event": 0
}

RARITY_COLORS = {
    "Common": 0xAAAAAA, 
    "Uncommon": 0xC7FFC3, 
    "Rare": 0xB9E2FF, 
    "Epic": 0xD493FF, 
    "Legendary": 0xFFCF60, 
    "Mythical": 0x6B31FF, 
    "Nightmare": 0xA62727,
    "Event": 0xFFFF8D,
    "Unobtainable": 0xFF0000
}

RARITY_POWER_RANGE = {
    "Common": (50, 199),
    "Uncommon": (200, 399),
    "Rare": (400, 599),
    "Epic": (600, 799),
    "Legendary": (800, 999),
    "Mythical": (1000, 1299),
    "Nightmare": (1300, 1799),
    "Event": (1800, 2300)
}

RARITY_ORDER = {
    "Common": 1,
    "Uncommon": 2,
    "Rare": 3,
    "Epic": 4,
    "Legendary": 5,
    "Mythical": 6,
    "Nightmare": 7,
    "Event": 8,
    "Unobtainable": 9
}

RARITY_PRICES = {
    "Common": 50,
    "Uncommon": 150,
    "Rare": 250,
    "Epic": 700,
    "Legendary": 900,
    "Mythical": 2000
}

RARITY_EMOJIS = {
       "Common": "☁️",
       "Uncommon": "❄️",
       "Rare": "🌙", 
       "Epic": "⚡",
       "Legendary": "🔥",
       "Mythical": "⭐"
}

SELL_PRICES = {
    "Common": 50,
    "Uncommon": 75,
    "Rare": 150,
    "Epic": 230,
    "Legendary": 350,
    "Mythical": 750,
    "Nightmare": 1050,
    "Event": 2000
}

ACHIEVEMENTS = [
    {
        "id":"first_blood",
        "name": "First Blood",
        "desc": "Win your first battle",
        "emoji": ":crossed_swords:"
    },
    {
        "id": "collector",
        "name": "Collector",
        "desc": "Own 50 cards",
        "emoji": ":black_joker:"
    },
    {
        "id": "powerful",
        "name": "Powerful",
        "desc": "Reach 5000 total power",
        "emoji": ":muscle:"
    },
    {
        "id": "mythic_pull",
        "name": "Mythic Pull",
        "desc": "Obtain a Mythical card",
        "emoji": ":crystal_ball:"
    },
    {
        "id": "rich",
        "name": "Rich!",
        "desc": "Hold 10,000 coins",
        "emoji": ":moneybag:"
    },
    {
        "id": "battle_master",
        "name": "Battle Master",
        "desc": "Win 5 battles",
        "emoji": ":crown:"
    },
    {
        "id": "doki_doki",
        "name": "Doki Doki!",
        "desc": "Collect the girls from DDLC!",
        "reward_card_name": "Yuri (Markov)",
        "required_cards": ["Yuri", "Natsuki", "Monika", "Sayori"],
        "emoji": ":sparkling_heart:"
    }
]

BATTLE_BLACKLIST = ["pp tree xd"]
