import discord
from discord.ext import commands
from discord import app_commands, ui
import random
import time
import json
with open("cards.json", "r") as f:
    CARD_POOL = json.load(f)
import os
import asyncio
from typing import List, Dict, Any, Tuple, Optional
last_bulk_sells = {}
import uuid

# --- CONFIG ---
DATA_FILE = "users.json"
CONFIG_FILE = "config.json"
ADMINS = [
    1154506207122444339,
    1072043412779433994,
    949756015644123196,
    1040272732224503959
]
AUCTION_FILE = "auctions.json"
AUCTION_DURATION = 72 * 3600  # 72 hours in seconds
BATTLE_BLACKLIST = ["pp tree xd"]
# Global variables for shop data
SHOP_LAST_REFRESH = 0  # Timestamp of last refresh
SHOP_CARDS = []        # List of cards in the shop



# --- GAME CONSTANTS ---
RARITY_WEIGHTS = {"Common": 100, "Uncommon": 75, "Rare": 40, "Epic": 10, "Legendary": 2.69696969, "Mythical": 0.02, "Nightmare": 0.0001, "Unobtainable": 0, "Event": 0}

def roll_card():
    return random.choices(
        CARD_POOL,
        weights=[RARITY_WEIGHTS.get(card["rarity"], 1) for card in CARD_POOL],
        k=1
    )[0]

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

ACHIEVEMENTS = [
    {"id": "first_blood", "name": "First Blood", "desc": "Win your first battle", "emoji": "⚔️"},
    {"id": "collector", "name": "Collector", "desc": "Own 50 cards", "emoji": "🃏"},
    {"id": "powerful", "name": "Powerful", "desc": "Reach 5000 total power", "emoji": "💪"},
    {"id": "mythic_pull", "name": "Mythic Pull", "desc": "Obtain a Mythical card", "emoji": "🔮"},
    {"id": "rich", "name": "Rich!", "desc": "Hold 10,000 coins", "emoji": "💰"},
    {"id": "battle_master", "name": "Battle Master", "desc": "Win 5 battles", "emoji": "👑"}
]


# Load the card list
with open("cards.json", "r") as f:
    CARD_POOL = json.load(f)

# Assign randomized power based on rarity
for card in CARD_POOL:
    rarity = card.get("rarity")
    if rarity in RARITY_POWER_RANGE:
        min_p, max_p = RARITY_POWER_RANGE[rarity]
        card["power"] = random.randint(min_p, max_p)

# Load card pool from file
with open("cards.json", "r") as f:
    CARD_POOL = json.load(f)

# Use globally in a roll function
    if card["rarity"] in RARITY_POWER_RANGE:
        min_p, max_p = RARITY_POWER_RANGE[card["rarity"]]
        card["power"] = random.randint(min_p, max_p)
    def draw_card():
        return random.choice(CARD_POOL)




# --- DATABASE FUNCTIONS ---
def load_data() -> Dict[str, Any]:
    """Load user data from JSON file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    except json.JSONDecodeError:
        print(f"Error: {DATA_FILE} is corrupted, creating new data file")
        return {}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}

def save_data(data: Dict[str, Any]) -> None:
    """Save user data to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

def get_user_data(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get or create user data"""
    if user_id not in data:
        data[user_id] = {
            "cards": [], 
            "trades": [], 
            "battles": 0, 
            "wins": 0, 
            "last_daily": 0,
            "coins": 0,
            "last_earn": 0
        }
    return data[user_id]

# --- ADMIN FUNCTIONS ---

def is_admin(user: discord.User) -> bool:
    return user.id in ADMINS

# --- ECONOMY FUNCTIONS ---

def add_coins(user_data: Dict[str, Any], amount: int):
    user_data["coins"] = user_data.get("coins", 0) + amount

def subtract_coins(user_data: Dict[str, Any], amount: int) -> bool:
    """Subtract coins from user account, returns True if successful"""
    current = user_data.get("coins", 0)
    if current >= amount:
        user_data["coins"] = current - amount
        return True
    return False

def remove_coins(user_data: Dict[str, Any], amount: int) -> None:
    """Remove coins from user account (for undo operations)"""
    current = user_data.get("coins", 0)
    user_data["coins"] = max(0, current - amount)


# --- MEDAL FUNCTIONS ---
def get_medals(user_data):
    medals = []
    if user_data.get("wins", 0) >= 50:
        medals.append("🏆 Veteran")
    if user_data.get("battles", 0) >= 100:
        medals.append("⚔️ Battle-Hardened")
    if sum(c["power"] for c in user_data.get("cards", [])) >= 10000:
        medals.append("💪 Powerhouse")
    if len(user_data.get("cards", [])) >= 100:
        medals.append("🃏 Collector")

    return medals or ["None"]

# --- ACHIEVEMENT FUNCTIONS ---
async def check_achievements(interaction: discord.Interaction, user_data: dict):
    uid = str(interaction.user.id)
    unlocked = user_data.get("achievements", [])

    newly_unlocked = []

    for ach in ACHIEVEMENTS:
        if ach["id"] in unlocked:
            continue

        if ach["id"] == "first_blood" and user_data.get("wins", 0) >= 1:
            newly_unlocked.append(ach)
        elif ach["id"] == "collector" and len(user_data.get("cards", [])) >= 50:
            newly_unlocked.append(ach)
        elif ach["id"] == "powerful" and sum(c["power"] for c in user_data.get("cards", [])) >= 5000:
            newly_unlocked.append(ach)
        elif ach["id"] == "mythic_pull" and any(c["rarity"] == "Mythical" for c in user_data.get("cards", [])):
            newly_unlocked.append(ach)
        elif ach["id"] == "rich" and user_data.get("coins", 0) >= 10000:
            newly_unlocked.append(ach)
        elif ach["id"] == "battle_master" and user_data.get("wins", 0) >= 5:
            newly_unlocked.append(ach)

    # Add and DM user about new achievements
    for ach in newly_unlocked:
        unlocked.append(ach["id"])
        try:
            await interaction.user.send(
                f"{ach['emoji']} **Achievement Unlocked: {ach['name']}**\n{ach['desc']}"
            )
        except:
            print(f"Could not DM {interaction.user.name}")

    user_data["achievements"] = unlocked
    save_data(data)


# --- AUCTION FUNCTIONS ---
# Load or initialize auction data
def load_auctions():
    try:
        with open("auctions.json", "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # If the file doesn't exist or is corrupted, return an empty list
        print("Auctions file was corrupted or missing. Creating new auctions file.")
        save_auctions([])  # Create a new empty auctions file
        return []

def save_auctions(auctions_data):
    with open("auctions.json", "w") as f:
        json.dump(auctions_data, f, indent=4)



# --- SHOP FUNCTIONS ---
SHOP_REFRESH_INTERVAL = 10800  # 3 hours

def initialize_shop(data: Dict[str, Any]):
    if "shop" not in data:
        data["shop"] = {"last_refresh": 0, "cards": []}

def calculate_card_price(card):
    """Calculate the price of a card based on rarity and power"""
    base_price = RARITY_PRICES.get(card["rarity"], 100)
    power_factor = card.get("power", 0) / 100  # Adjust price based on power
    
    return int(base_price * (1 + power_factor))


def refresh_shop():
    """Refresh the shop cards if 3 hours have passed since last refresh"""
    global SHOP_LAST_REFRESH
    global SHOP_CARDS
    
    current_time = int(time.time())
    three_hours_in_seconds = 3 * 60 * 60  # 3 hours in seconds
    
    # Check if enough time has passed for a refresh (or if shop is empty)
    if current_time - SHOP_LAST_REFRESH >= three_hours_in_seconds or not SHOP_CARDS:
        print("Refreshing shop cards...")
        
        # Generate new cards (exactly 5)
        SHOP_CARDS = []
        for _ in range(5):
            card = roll_card()
            SHOP_CARDS.append(card)
        
        # Update the last refresh time
        SHOP_LAST_REFRESH = current_time
        print(f"Shop refreshed with {len(SHOP_CARDS)} new cards!")
    else:
        time_left = three_hours_in_seconds - (current_time - SHOP_LAST_REFRESH)
        hours, remainder = divmod(time_left, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"Shop will refresh in: {int(hours)}h {int(minutes)}m {int(seconds)}s")


def get_shop_embed(shop_cards: List[Dict[str, Any]]) -> discord.Embed:
    embed = discord.Embed(title="Card Shop", description="Available cards for the next 3 hours", color=0xFFD700)
    for idx, card in enumerate(shop_cards):
        embed.add_field(
            name=f"{idx+1}. {card['name']}",
            value=f"Rarity: {card['rarity']} | Power: {card['power']} | Cost: {SHOP_CARD_COST} coins",
            inline=False
        )
    return embed



# --- SELL FUNCTION ---
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

def sell_card(data: Dict[str, Any], user_id: str, card_name: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Sell a card and return success status, message, and the sold card if successful"""
    user_data = data.get(user_id, {})
    inventory = user_data.get("cards", [])
    
    # Find card index
    card_index = next((i for i, c in enumerate(inventory) if c["name"].lower() == card_name.lower()), None)
    
    if card_index is None:
        return False, "Card not found in your inventory.", None
    
    # Get the card and remove it
    card = inventory.pop(card_index)
    rarity = card["rarity"]
    
    # Calculate price
    coins = SELL_PRICES.get(rarity, 0)
    if coins == 0:
        # If card cannot be sold, put it back
        inventory.append(card)
        return False, f"{card['name']} cannot be sold.", None
    
    # Add coins and save
    add_coins(user_data, coins)
    save_data(data)
    
    return True, f"You sold **{card['name']}** for **{coins} coins**.", card


# --- CARD FUNCTIONS ---
def draw_card() -> Dict[str, Any]:
    """Draw a random card from the pool (no weighting)"""
    card = random.choice(CARD_POOL).copy()
    if card["rarity"] in RARITY_POWER_RANGE:
        min_p, max_p = RARITY_POWER_RANGE[card["rarity"]]
        card["power"] = random.randint(min_p, max_p)
    return card

def roll_card() -> Dict[str, Any]:
    """Roll a card with rarity weighting and power range randomization"""
    # Filter obtainable cards
    obtainable_cards = [card for card in CARD_POOL if RARITY_WEIGHTS.get(card["rarity"], 0) > 0]
    weights = [RARITY_WEIGHTS.get(card["rarity"], 0) for card in obtainable_cards]
    
    # Select a card based on weights
    base_card = random.choices(obtainable_cards, weights=weights, k=1)[0]
    card = base_card.copy()
    
    # Randomize power within rarity range
    if card["rarity"] in RARITY_POWER_RANGE:
        power_min, power_max = RARITY_POWER_RANGE[card["rarity"]]
        card["power"] = random.randint(power_min, power_max)
    
    return card

def get_card_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Find a card by name"""
    for card in CARD_POOL:
        if card["name"].lower() == name.lower():
            return card.copy()
    return None

def get_card_embed(card: Dict[str, Any]) -> discord.Embed:
    """Create an embed for a card"""
    color = RARITY_COLORS.get(card["rarity"], 0xFFFFFF)
    embed = discord.Embed(
        title=card["name"],
        description=f"**Rarity:** {card['rarity']}\n**Power:** {card['power']}",
        color=color
    )
    embed.set_image(url=card["image"])
    return embed

# --- TRADE FUNCTIONS ---
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

def cancel_trade(data: Dict[str, Any], user: discord.User) -> str:
    """Cancel a pending trade"""
    user_id = str(user.id)
    
    # Check if user has pending trades
    trades = data.get(user_id, {}).get("trades", [])
    if not trades:
        return "No trade to cancel."
    
    data[user_id]["trades"] = []
    return "Trade canceled."

# --- UI COMPONENTS ---
class InventoryView(discord.ui.View):
    def __init__(self, cards, user_id, user_display, per_page=5, query=None):
        super().__init__(timeout=180)
        self.cards = cards
        self.uid = str(user_id)
        self.user_display = user_display
        self.per_page = per_page
        self.page = 0
        self.query = query
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()

        start = self.page * self.per_page
        end = start + self.per_page
        current_cards = self.cards[start:end]

        for index, card in enumerate(current_cards):
            label = f"{card['name']} ({card['power']}P)"
            self.add_item(SellButton(label=label[:80], inv_view=self, card_index=start + index))

        if self.page > 0:
            self.add_item(PageButton(label="◀️ Previous", inv_view=self, direction=-1))
        if self.page < (len(self.cards) - 1) // self.per_page:
            self.add_item(PageButton(label="Next ▶️", inv_view=self, direction=1))

    def get_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        embed = discord.Embed(
            title=f"{self.user_display}'s Inventory",
            description=f"Page {self.page + 1}/{(len(self.cards) - 1)//self.per_page + 1}" +
                        (f"\nFiltered by: `{self.query}`" if self.query else ""),
            color=0x00ffcc
        )
        for card in self.cards[start:end]:
            embed.add_field(
                name=f"{card['name']} (P: {card['power']})",
                value=f"Rarity: {card['rarity']}",
                inline=False
            )
        return embed

class PageButton(discord.ui.Button):
    def __init__(self, label, inv_view: InventoryView, direction: int):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.inv_view = inv_view
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.inv_view.uid:
            await interaction.response.send_message("You can't control someone else's inventory.", ephemeral=True)
            return

        self.inv_view.page += self.direction
        self.inv_view.update_buttons()
        await interaction.response.edit_message(embed=self.inv_view.get_embed(), view=self.inv_view)

class SellButton(discord.ui.Button):
    def __init__(self, label, inv_view: InventoryView, card_index: int):
        super().__init__(label=f"Sell: {label}", style=discord.ButtonStyle.red)
        self.inv_view = inv_view
        self.card_index = card_index

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.inv_view.uid:
            await interaction.response.send_message("You can't sell someone else's card.", ephemeral=True)
            return

        try:
            card = self.inv_view.cards.pop(self.card_index)
            rarity = card["rarity"]
            coins = SELL_PRICES.get(rarity, 0)
            data[self.inv_view.uid]["cards"].remove(card)
            add_coins(data[self.inv_view.uid], coins)
            save_data(data)

            await interaction.response.send_message(
                f"Sold **{card['name']}** for **{coins} coins**!", ephemeral=True
            )

            self.inv_view.update_buttons()
            await interaction.message.edit(embed=self.inv_view.get_embed(), view=self.inv_view)

        except Exception as e:
            await interaction.response.send_message("Error selling card.", ephemeral=True)
            print("Sell error:", e)


        
        # Show just one card per page with its image
        card = current_cards[0]
        embed = discord.Embed(
            title=f"{self.user.name}'s Inventory",
            description=f"Card {start_idx + 1}/{len(self.cards)}",
            color=RARITY_COLORS.get(card["rarity"], 0x3498db)
        )
        
        embed.add_field(name=card["name"], value=f"Rarity: {card['rarity']}\nPower: {card['power']}", inline=False)
        embed.set_image(url=card["image"])
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.total_pages}")
        
        return embed



class CardSearchModal(discord.ui.Modal):
    def __init__(self, battle_view, cards, is_challenger):
        super().__init__(title="Search Your Cards")
        self.battle_view = battle_view
        self.cards = cards
        self.is_challenger = is_challenger
        
        self.search_input = discord.ui.TextInput(
            label="Search by card name",
            placeholder="Enter card name or part of name...",
            required=True,
            max_length=100
        )
        self.add_item(self.search_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Filter cards based on search term
        search_term = self.search_input.value.lower()
        filtered_cards = [card for card in self.cards if search_term in card['name'].lower()]
        
        if not filtered_cards:
            await interaction.response.send_message(
                f"No cards found matching '{self.search_input.value}'", 
                ephemeral=True
            )
            return
            
        # Create select menu with filtered cards
        options = []
        for i, card in enumerate(filtered_cards[:25]):  # Discord limit of 25 options
            options.append(discord.SelectOption(
                label=f"{card['name']} ({card['power']} Power)",
                description=f"Rarity: {card['rarity']}",
                value=str(i)
            ))
        
        # Create view with the filtered cards
        view = discord.ui.View(timeout=60)
        select = CardSelect(options, self.battle_view, self.is_challenger, filtered_cards)
        view.add_item(select)
        
        await interaction.response.send_message(
            f"Found {len(filtered_cards)} cards matching '{self.search_input.value}':", 
            view=view, 
            ephemeral=True
        )

class CardSelectView(discord.ui.View):
    def __init__(self, battle_view, cards, is_challenger):
        super().__init__(timeout=60)
        self.battle_view = battle_view
        self.cards = cards
        self.is_challenger = is_challenger

        # Create the select menu
        options = []
        for i, card in enumerate(self.cards[:25]):  # Discord limit of 25 options
            options.append(discord.SelectOption(
                label=f"{card['name']} ({card['power']} Power)",
                description=f"Rarity: {card['rarity']}",
                value=str(i)
            ))
        
        if not options:
            options.append(discord.SelectOption(
                label="No cards available",
                value="0"
            ))
        
        # Add select menu to the view
        self.add_item(CardSelect(options, self.battle_view, self.is_challenger, self.cards))

class CardSelect(discord.ui.Select):
    def __init__(self, options, battle_view, is_challenger, cards):
        super().__init__(
            placeholder="Choose a card for battle...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.battle_view = battle_view
        self.is_challenger = is_challenger
        self.cards = cards
    
    async def callback(self, interaction: discord.Interaction):
        # Make sure the right user is interacting
        correct_user = self.battle_view.challenger if self.is_challenger else self.battle_view.opponent
        if interaction.user.id != correct_user.id:
            await interaction.response.send_message("This isn't your battle card selection!", ephemeral=True)
            return
        
        # Get the selected card
        index = int(self.values[0])
        selected_card = self.cards[index]
        
        # Set the selection in the battle view
        if self.is_challenger:
            self.battle_view.challenger_selection = selected_card
            await interaction.response.send_message(f"You selected **{selected_card['name']}** for battle!", ephemeral=True)
        else:
            self.battle_view.opponent_selection = selected_card
            await interaction.response.send_message(f"You selected **{selected_card['name']}** for battle!", ephemeral=True)
        
        # Check if battle is complete
        await self.battle_view.check_battle_complete(interaction)


class BattleView(discord.ui.View):
    def __init__(self, challenger, opponent, challenger_cards, opponent_cards, data):
        super().__init__(timeout=300)
        self.challenger = challenger
        self.opponent = opponent
        self.challenger_cards = challenger_cards
        self.opponent_cards = opponent_cards
        self.data = data
        self.challenger_selection = None
        self.opponent_selection = None
        self.message = None
        self.is_complete = False

    # Standard browsing option - shows all cards 
    @discord.ui.button(label="Browse Cards", style=discord.ButtonStyle.primary, row=0)
    async def browse_cards_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Browse all available cards in a dropdown"""
        # Check if it's a valid participant
        if interaction.user.id not in [self.challenger.id, self.opponent.id]:
            await interaction.response.send_message("You're not part of this battle!", ephemeral=True)
            return
            
        if self.is_complete:
            await interaction.response.send_message("This battle is already complete!", ephemeral=True)
            return
            
        # Determine whose turn it is
        is_challenger = (interaction.user.id == self.challenger.id)
        eligible_cards = self.challenger_cards if is_challenger else self.opponent_cards
        
        if not eligible_cards:
            await interaction.response.send_message("You don't have any valid cards to battle with!", ephemeral=True)
            return
            
        # Basic card selection view with all cards
        view = CardSelectView(self, eligible_cards, is_challenger)
        await interaction.response.send_message("Select your battle card:", view=view, ephemeral=True)
    
    # Search option - opens a text input modal
    @discord.ui.button(label="Search Cards", style=discord.ButtonStyle.success, row=0)
    async def search_cards_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open a search modal to find cards by name"""
        # Check if it's a valid participant
        if interaction.user.id not in [self.challenger.id, self.opponent.id]:
            await interaction.response.send_message("You're not part of this battle!", ephemeral=True)
            return
            
        if self.is_complete:
            await interaction.response.send_message("This battle is already complete!", ephemeral=True)
            return
            
        # Determine whose turn it is
        is_challenger = (interaction.user.id == self.challenger.id)
        eligible_cards = self.challenger_cards if is_challenger else self.opponent_cards
        
        if not eligible_cards:
            await interaction.response.send_message("You don't have any valid cards to battle with!", ephemeral=True)
            return
        
        # Show search modal
        modal = CardSearchModal(self, eligible_cards, is_challenger)
        await interaction.response.send_modal(modal)
    
    # Sort by power option - shows cards ranked by power
    @discord.ui.button(label="Sort By Power", style=discord.ButtonStyle.secondary, row=0)
    async def sort_power_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show cards sorted by power (highest first)"""
        # Check if it's a valid participant
        if interaction.user.id not in [self.challenger.id, self.opponent.id]:
            await interaction.response.send_message("You're not part of this battle!", ephemeral=True)
            return
            
        if self.is_complete:
            await interaction.response.send_message("This battle is already complete!", ephemeral=True)
            return
            
        # Determine whose turn it is
        is_challenger = (interaction.user.id == self.challenger.id)
        eligible_cards = self.challenger_cards if is_challenger else self.opponent_cards
        
        if not eligible_cards:
            await interaction.response.send_message("You don't have any valid cards to battle with!", ephemeral=True)
            return
            
        # Sort cards by power (highest first)
        sorted_cards = sorted(eligible_cards, key=lambda x: x.get('power', 0), reverse=True)
        
        # Card selection view with power-sorted cards
        view = CardSelectView(self, sorted_cards, is_challenger)
        await interaction.response.send_message("Cards sorted by power (highest first):", view=view, ephemeral=True)


    async def check_battle_complete(self, interaction):
        """Check if battle is complete and update results"""
        if not self.challenger_selection or not self.opponent_selection or self.is_complete:
            return  # Battle not complete yet
            
        self.is_complete = True  # Mark as complete to prevent further changes
        
        # Calculate the winner
        challenger_power = self.challenger_selection["power"]
        opponent_power = self.opponent_selection["power"]
        
        if challenger_power > opponent_power:
            winner = self.challenger
            winner_id = str(self.challenger.id)
        elif opponent_power > challenger_power:
            winner = self.opponent
            winner_id = str(self.opponent.id)
        else:
            winner = None
            winner_id = None
            
        # Create result embed
        embed = discord.Embed(title="Battle Result", color=0x00ff00)
        embed.add_field(
            name=f"{self.challenger.display_name}'s Card",
            value=f"{self.challenger_selection['name']} ({self.challenger_selection['power']} Power)",
            inline=False
        )
        embed.add_field(
            name=f"{self.opponent.display_name}'s Card",
            value=f"{self.opponent_selection['name']} ({self.opponent_selection['power']} Power)",
            inline=False
        )
        
        if winner:
            embed.add_field(name="Winner", value=f"**{winner.display_name}** wins!", inline=False)
            
            # Update stats
            self.data[winner_id]["wins"] = self.data[winner_id].get("wins", 0) + 1
        else:
            embed.add_field(name="Result", value="It's a draw!", inline=False)
        
        # Update battle count for both players
        self.data[str(self.challenger.id)]["battles"] = self.data[str(self.challenger.id)].get("battles", 0) + 1
        self.data[str(self.opponent.id)]["battles"] = self.data[str(self.opponent.id)].get("battles", 0) + 1
        
        save_data(self.data)
        
        # Disable buttons
        for child in self.children:
            child.disabled = True
            
        # Try to edit the original message
        try:
            await self.message.edit(embed=embed, view=self)
        except (discord.NotFound, AttributeError):
            # Fallback if message was deleted or not stored
            await interaction.followup.send("Battle results:", embed=embed)
            
        # Check achievements if there's a winner
        if winner_id:
            await check_achievements(interaction, self.data[winner_id])
        else:
                embed.add_field(name="Result", value="It's a draw!", inline=False)
                
                # Still update battle count for both participants
                self.data[str(self.challenger.id)]["battles"] += 1
                self.data[str(self.opponent.id)]["battles"] += 1
                save_data(self.data)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)





async def check_specific_card(interaction: discord.Interaction, card_name: str, user_cards: list):
    """Check if user has a specific card in their collection"""
    # Find the card in the global card pool
    target_card = next((card for card in CARD_POOL if card["name"].lower() == card_name.lower()), None)
    
    if not target_card:
        await interaction.response.send_message(f"Card '{card_name}' doesn't exist in the card database.", ephemeral=True)
        return
    
    # Check if user has this card
    owned_cards = [card for card in user_cards if card["name"].lower() == card_name.lower()]
    count = len(owned_cards)
    
    embed = discord.Embed(
        title=f"Card: {target_card['name']}",
        color=RARITY_COLORS.get(target_card["rarity"], 0xFFFFFF)
    )
    
    if count > 0:
        # User has the card
        embed.description = f"**Status**: Owned ({count} copies)"
        
        # If they have multiple copies with different powers, show the range
        if count > 1:
            powers = [card.get("power", 0) for card in owned_cards]
            embed.add_field(name="Powers", value=f"Min: {min(powers)}, Max: {max(powers)}")
        else:
            embed.add_field(name="Power", value=str(owned_cards[0].get("power", "N/A")))
    else:
        # User doesn't have the card
        embed.description = "**Status**: Not owned yet"
    
    embed.add_field(name="Rarity", value=target_card["rarity"])
    embed.set_image(url=target_card["image"])
    
    await interaction.response.send_message(embed=embed)

async def show_collection_stats(interaction: discord.Interaction, user_cards: list):
    """Show overall collection statistics"""
    uid = str(interaction.user.id)
    
    # Get total number of unique cards in the pool
    total_cards = len(CARD_POOL)
    
    # Count unique cards the user has
    unique_collected = len(set(card["name"].lower() for card in user_cards))
    
    # Calculate completion percentage
    completion = (unique_collected / total_cards) * 100 if total_cards > 0 else 0
    
    # Count cards by rarity
    rarity_counts = {}
    for card in user_cards:
        rarity = card.get("rarity", "Unknown")
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
    
    # Count cards by rarity in the total pool
    pool_rarity_counts = {}
    for card in CARD_POOL:
        rarity = card.get("rarity", "Unknown")
        pool_rarity_counts[rarity] = pool_rarity_counts.get(rarity, 0) + 1
    
    # Create the embed
    embed = discord.Embed(
        title="🎴 Card Collection Stats",
        description=f"You've collected **{unique_collected}/{total_cards}** unique cards (**{completion:.1f}%** complete)",
        color=0x9370DB  # Medium purple color
    )
    
    # Add total cards count
    embed.add_field(name="Total Cards Owned", value=str(len(user_cards)), inline=False)
    
    # Add rarity breakdown
    rarity_breakdown = ""
    for rarity in sorted(pool_rarity_counts.keys(), key=lambda r: RARITY_ORDER.get(r, 999)):
        collected = rarity_counts.get(rarity, 0)
        total = pool_rarity_counts.get(rarity, 0)
        percentage = (collected / total) * 100 if total > 0 else 0
        
        # Use emoji based on completion
        if percentage >= 90:
            emoji = "✅"  # Complete
        elif percentage >= 50:
            emoji = "🔷"  # Good progress
        elif percentage > 0:
            emoji = "🔸"  # Started
        else:
            emoji = "❌"  # None collected
            
        rarity_breakdown += f"{emoji} **{rarity}**: {collected}/{total} ({percentage:.1f}%)\n"
    
    embed.add_field(name="Collection by Rarity", value=rarity_breakdown, inline=False)
    
    # Add top rarities
    if user_cards:
        top_card = max(user_cards, key=lambda c: RARITY_ORDER.get(c.get("rarity", "Common"), 0))
        embed.add_field(
            name="Rarest Card Owned", 
            value=f"{top_card['name']} ({top_card['rarity']})", 
            inline=True
        )
        
        highest_power = max(user_cards, key=lambda c: c.get("power", 0))
        embed.add_field(
            name="Highest Power Card", 
            value=f"{highest_power['name']} ({highest_power.get('power', 0)} Power)", 
            inline=True
        )
    
    # Add collection view button
    view = CollectionView(data[uid], interaction.user.id)
    
    await interaction.response.send_message(embed=embed, view=view)

class CollectionView(discord.ui.View):
    def __init__(self, user_data, user_id):
        super().__init__(timeout=60)
        self.user_data = user_data
        self.user_id = user_id
        self.page = 0
    
    @discord.ui.button(label="Missing Cards", style=discord.ButtonStyle.primary)
    async def missing_cards(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show cards that the user doesn't own yet"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your collection!", ephemeral=True)
            return
            
        user_cards = self.user_data.get("cards", [])
        owned_names = set(card["name"].lower() for card in user_cards)
        
        # Find cards not owned
        missing_cards = [card for card in CARD_POOL if card["name"].lower() not in owned_names]
        
        if not missing_cards:
            await interaction.response.send_message("Congratulations! You've collected all available cards!", ephemeral=True)
            return
        
        # Sort by rarity (rarest first)
        missing_cards.sort(key=lambda c: RARITY_ORDER.get(c.get("rarity", "Common"), 0), reverse=True)
        
        # Create embed
        embed = discord.Embed(
            title="🔍 Cards You're Missing",
            description=f"You're missing **{len(missing_cards)}/{len(CARD_POOL)}** cards",
            color=0xE74C3C  # Red color
        )
        
        # Group by rarity
        by_rarity = {}
        for card in missing_cards:
            rarity = card.get("rarity", "Unknown")
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            by_rarity[rarity].append(card["name"])
        
        # Add each rarity group to the embed
        for rarity in sorted(by_rarity.keys(), key=lambda r: RARITY_ORDER.get(r, 999), reverse=True):
            card_list = by_rarity[rarity]
            # Truncate if too many cards
            if len(card_list) > 15:
                card_text = ", ".join(card_list[:15]) + f"\n*...and {len(card_list) - 15} more*"
            else:
                card_text = ", ".join(card_list)
                
            embed.add_field(name=f"{rarity} ({len(card_list)})", value=card_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Rarity Breakdown", style=discord.ButtonStyle.secondary)
    async def rarity_breakdown(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed breakdown by rarity"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your collection!", ephemeral=True)
            return
            
        user_cards = self.user_data.get("cards", [])
        
        # Count cards by rarity
        rarity_counts = {}
        for card in user_cards:
            rarity = card.get("rarity", "Unknown")
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        # Create embed
        embed = discord.Embed(
            title="📊 Collection Breakdown by Rarity",
            color=0x3498DB  # Blue color
        )
        
        # Add counts for each rarity
        total_count = len(user_cards)
        for rarity in sorted(rarity_counts.keys(), key=lambda r: RARITY_ORDER.get(r, 999)):
            count = rarity_counts[rarity]
            percentage = (count / total_count) * 100 if total_count > 0 else 0
            
            embed.add_field(
                name=f"{rarity}",
                value=f"{count} cards ({percentage:.1f}%)",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    @discord.ui.button(label="Duplicates", style=discord.ButtonStyle.success)
    async def duplicates(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show cards you have duplicates of"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your collection!", ephemeral=True)
            return
            
        user_cards = self.user_data.get("cards", [])
        
        # Count card names
        card_counts = {}
        for card in user_cards:
            name = card["name"].lower()
            card_counts[name] = card_counts.get(name, 0) + 1
        
        # Filter for duplicates only
        duplicates = {name: count for name, count in card_counts.items() if count > 1}
        
        if not duplicates:
            await interaction.response.send_message("You don't have any duplicate cards.", ephemeral=True)
            return
        
        # Create embed
        embed = discord.Embed(
            title="🔄 Your Duplicate Cards",
            description=f"You have **{len(duplicates)}** cards with duplicates",
            color=0x2ECC71  # Green color
        )
        
        # Get original card data for the duplicates
        duplicate_details = []
        for name, count in duplicates.items():
            # Find all instances of this card
            instances = [card for card in user_cards if card["name"].lower() == name]
            # Get the rarity from the first instance
            rarity = instances[0].get("rarity", "Unknown")
            # Get power range if applicable
            if all("power" in card for card in instances):
                powers = [card["power"] for card in instances]
                power_range = f"({min(powers)}-{max(powers)} Power)"
            else:
                power_range = ""
                
            # Create detail entry
            card_name = instances[0]["name"]  # Use proper case from the card
            duplicate_details.append((card_name, count, rarity, power_range))
        
        # Sort by count (highest first), then rarity
        duplicate_details.sort(key=lambda x: (x[1], RARITY_ORDER.get(x[2], 999)), reverse=True)
        
        # Add to embed in groups of 15
        current_group = []
        for name, count, rarity, power_range in duplicate_details:
            current_group.append(f"**{name}** x{count} ({rarity}) {power_range}")
            
            if len(current_group) >= 15:
                embed.add_field(name="Duplicates", value="\n".join(current_group), inline=False)
                current_group = []
        
        # Add any remaining cards
        if current_group:
            embed.add_field(name="Duplicates", value="\n".join(current_group), inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)



class CardInfoView(ui.View):
    """View for card collection browser"""
    def __init__(self, user: discord.User):
        super().__init__(timeout=120)
        self.user = user
        self.current_page = 0
        self.cards_per_page = 1
        self.total_pages = len(CARD_POOL)
        
    @ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This is not your card browser!", ephemeral=True)
            return
            
        self.current_page = (self.current_page - 1) % self.total_pages
        await interaction.response.edit_message(embed=self.get_current_page_embed(), view=self)
        
    @ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This is not your card browser!", ephemeral=True)
            return
            
        self.current_page = (self.current_page + 1) % self.total_pages
        await interaction.response.edit_message(embed=self.get_current_page_embed(), view=self)
    
def get_current_page_embed(self) -> discord.Embed:
    """Generate the embed for the current card"""
    if not CARD_POOL or self.current_page >= len(CARD_POOL):
        return discord.Embed(title="Error", description="No cards available")
    
    card = CARD_POOL[self.current_page]
    
    embed = discord.Embed(
        title="Card Collection",
        description=f"Card {self.current_page + 1}/{len(CARD_POOL)}",
        color=RARITY_COLORS.get(card["rarity"], 0x3498db)
    )
    
    embed.add_field(name=card["name"], value=f"Rarity: {card['rarity']}\nPower: {card.get('power', 'N/A')}", inline=False)
    embed.set_image(url=card["image"])
    embed.set_footer(text=f"Page {self.current_page + 1} of {len(CARD_POOL)}")
    
    return embed

class ConfirmBuyView(discord.ui.View):
    def __init__(self, interaction, auction, auctions):
        super().__init__(timeout=30)
        self.interaction = interaction
        self.auction = auction
        self.auctions = auctions

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("This confirmation isn't for you.", ephemeral=True)
            return

        uid = str(interaction.user.id)
        auction = self.auction
        seller_id = auction["seller_id"]

        data[uid]["coins"] -= auction["price"]
        if seller_id in data:
            data[seller_id]["coins"] += auction["price"]

        data[uid]["cards"].append(auction["card"])
        self.auctions.remove(auction)

        save_data(data)
        save_auctions(self.auctions)

        await interaction.response.edit_message(content=f"You bought **{auction['card']['name']}** for {auction['price']} coins!", embed=None, view=None)

        # DM seller
        try:
            user = await bot.fetch_user(int(seller_id))
            await user.send(f"Your card **{auction['card']['name']}** was sold for {auction['price']} coins!")
        except:
            pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("This confirmation isn't for you.", ephemeral=True)
            return

        await interaction.response.edit_message(content="Cancelled purchase.", embed=None, view=None)


class AuctionPaginationView(discord.ui.View):
    def __init__(self, auctions, page=0):
        super().__init__(timeout=60)
        self.auctions = auctions
        self.page = page
        self.max_pages = (len(auctions) - 1) // 5
        self.message = None

    async def send_page(self, interaction):
        embed = discord.Embed(title=f"Auction House - Page {self.page+1}/{self.max_pages+1}", color=0x00ffcc)
        for a in self.auctions[self.page*5:(self.page+1)*5]:
            embed.add_field(
                name=f"{a['card']['name']} ({a['card']['rarity']}) - {a['price']} coins",
                value=f"Seller ID: {a['seller_id']}\nAuction ID: `{a['auction_id']}`",
                inline=False
            )
        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            self.message = await interaction.followup.send(embed=embed, view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.send_page(interaction)
        await interaction.response.defer()

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_pages:
            self.page += 1
            await self.send_page(interaction)
        await interaction.response.defer()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)




# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.synced = False
data = load_data()

# --- BOT EVENTS ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    # Refresh shop on bot startup
    refresh_shop()

    bot.loop.create_task(periodic_shop_refresh())

async def periodic_shop_refresh():
    """Periodically check if shop needs refreshing"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        refresh_shop()  # This will only actually refresh if 3 hours have passed
        await asyncio.sleep(60 * 60)

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"An error occurred: {str(error)}")

# --- COMMANDS ---
@bot.tree.command(name="new_user", description="Create your profile in the card game")
async def new_user(interaction: discord.Interaction):
    """Create a new user profile"""
    uid = str(interaction.user.id)
    if uid in data:
        await interaction.response.send_message("You already have a profile!", ephemeral=True)
    else:
        data[uid] = {"cards": [],
        "trades": [],
        "battles": 0,
        "wins": 0,
        "last_daily": 0,
        "coins": 0,
        "last_earn": 0,
        "achievements": []}
        save_data(data)
        
        embed = discord.Embed(
            title="Profile Created!",
            description="Welcome to the Card Game FunkyDex! Here's what you can do:",
            color=0x00ff00
        )
        embed.add_field(name="/roll", value="Roll for a new card", inline=True)
        embed.add_field(name="/draw", value="Draw a random card (Limit 3 per day due to no rarity weighting on this command!)", inline=True)

        embed.add_field(name="/sell", value="Sell your cards!", inline=True)

        embed.add_field(name="/bulk_sell", value="Sell multiple of your cards!", inline=True)
        embed.add_field(name="/inventory", value="Check your card collection", inline=True)
        embed.add_field(name="/battle", value="Battle another player", inline=True)
        embed.add_field(name="/trade", value="Trade cards with others", inline=True)
        embed.add_field(name="/card_info", value="Learn about a specific card", inline=True)
        embed.add_field(name="/profile", value="View your stats", inline=True)
        embed.add_field(name="/daily", value="Get your daily card", inline=True)
        
    await interaction.response.send_message(embed=embed)


ROLL_COST = 100

@bot.tree.command(name="roll", description="Roll for a new card")
async def roll(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
        return

    if not subtract_coins(data[uid], ROLL_COST):
        await interaction.response.send_message(f"You need {ROLL_COST} coins to roll!", ephemeral=True)
        return  # Add this return statement

    card = roll_card()
    data[uid]["cards"].append(card)
    save_data(data)

    embed = discord.Embed(
        title=f"You rolled: {card['name']}",
        description=f"Rarity: {card['rarity']} | Power: {card['power']}",
        color=RARITY_COLORS.get(card['rarity'], 0xFFFFFF)
    )
    embed.set_image(url=card['image'])
    await interaction.response.send_message(embed=embed)  # Fix indentation




@bot.tree.command(name="draw", description="Draw a random card (max 7 per day)")
async def draw(interaction: discord.Interaction):
    try:
        uid = str(interaction.user.id)
        
        # Ensure user exists in data with proper initialization
        if uid not in data:
            data[uid] = {
                "name": interaction.user.display_name,
                "coins": 100,  # Starting coins
                "cards": [],
                "draws_today": 0,
                "last_draw_reset": 0,
                "wins": 0,
                "battles": 0
            }
            
        user_data = data[uid]
        
        # Ensure all required fields exist in user_data
        if "draws_today" not in user_data:
            user_data["draws_today"] = 0
        if "last_draw_reset" not in user_data:
            user_data["last_draw_reset"] = 0
        if "cards" not in user_data:
            user_data["cards"] = []
            
        current_time = int(time.time())
        last_reset = user_data.get("last_draw_reset", 0)
        draws_today = user_data.get("draws_today", 0)
        
        # Reset if more than 24h since last reset
        if current_time - last_reset >= 86400:
            print(f"Resetting draws for user {uid}: {draws_today} → 0")
            draws_today = 0
            user_data["last_draw_reset"] = current_time
            user_data["draws_today"] = draws_today  # Important: update this here too!
            
        if draws_today >= 7:
            # Calculate time until next reset
            time_until_reset = 86400 - (current_time - last_reset)
            hours, remainder = divmod(time_until_reset, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            await interaction.response.send_message(
                f"You've reached your **daily draw limit (7)**. Try again in **{int(hours)}h {int(minutes)}m**.", 
                ephemeral=True
            )
            return
            
        # Roll a card
        card = roll_card()
        user_data["cards"].append(card)
        
        # Update draw count - increment properly
        user_data["draws_today"] = draws_today + 1
        
        # Save early to prevent loss of data in case of error later
        save_data(data)
        
        # Log success for debugging
        print(f"User {uid} drew card: {card['name']}, Draws today: {user_data['draws_today']}/7")
        
        remaining = 7 - user_data["draws_today"]
        embed = discord.Embed(
            title="Card Drawn!",
            description=f"You drew: **{card['name']}**\nDraws left today: **{remaining}**",
            color=RARITY_COLORS.get(card["rarity"], 0xFFFFFF)
        )
        embed.add_field(name="Rarity", value=card["rarity"])
        embed.add_field(name="Power", value=str(card["power"]))
        embed.set_image(url=card["image"])
        
        await interaction.response.send_message(embed=embed)
        
        # Check achievements after successful draw and response
        await check_achievements(interaction, data[uid])
        
    except Exception as e:
        # Log the error for diagnosis
        print(f"Error in /draw command for user {interaction.user.id}: {str(e)}")
        

        try:
            await interaction.response.send_message(
                "An error occurred while drawing your card. Please try again later or contact the bot administrator.",
                ephemeral=True
            )
        except:

            try:
                await interaction.followup.send(
                    "An error occurred while drawing your card. Please try again later or contact the bot administrator.",
                    ephemeral=True
                )
            except:
                pass


@bot.tree.command(name="inventory", description="View your card collection with search, sell, and sort")
@app_commands.describe(
    query="Search for card name (optional)",
    sort_by_rarity="Sort by rarity (Common → Mythical)"
)
async def inventory(
    interaction: discord.Interaction,
    query: Optional[str] = None,
    sort_by_rarity: Optional[bool] = False
):
    uid = str(interaction.user.id)
    if uid not in data or not data[uid]["cards"]:
        await interaction.response.send_message("You have no cards yet!", ephemeral=True)
        return

    cards = data[uid]["cards"]

    # Filter by search query
    if query:
        query = query.lower()
        cards = [card for card in cards if query in card["name"].lower()]

    if not cards:
        await interaction.response.send_message("No matching cards found.", ephemeral=True)
        return

    # Sort by rarity if selected
    if sort_by_rarity:
        cards.sort(key=lambda c: RARITY_ORDER.get(c["rarity"], 99))

    view = InventoryView(cards, interaction.user.id, interaction.user.display_name, query=query)
    await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)



@bot.tree.command(name="profile", description="View your profile")
async def profile(interaction: discord.Interaction):
    """View your profile and stats"""
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
        return
        
    user_data = data[uid]
    embed = discord.Embed(title=f"{interaction.user.name}'s Profile", color=0x00ff00)
    
    # Basic stats
    embed.add_field(name="Cards Owned", value=str(len(user_data["cards"])))
    embed.add_field(name="Battles", value=str(user_data.get("battles", 0)))
    embed.add_field(name="Wins", value=str(user_data.get("wins", 0)))
    
    # Win rate
    battles = user_data.get("battles", 0)
    win_rate = f"{(user_data.get('wins', 0) / battles * 100):.1f}%" if battles > 0 else "N/A"
    embed.add_field(name="Win Rate", value=win_rate)
    
    # Card rarity breakdown
    rarity_counts = {}
    for card in user_data["cards"]:
        rarity = card["rarity"]
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1

    rarity_text = "\n".join([f"{rarity}: {count}" for rarity, count in rarity_counts.items()])
    embed.add_field(name="Card Rarities", value=rarity_text if rarity_text else "None", inline=False)
    
    # Strongest card
    if user_data["cards"]:
        strongest = max(user_data["cards"], key=lambda c: c["power"])
        embed.add_field(
            name="Strongest Card", 
            value=f"{strongest['name']} ({strongest['power']} Power)", 
            inline=False
        )
    
    # Set user avatar as thumbnail
    if interaction.user.avatar:
     embed.set_thumbnail(url=interaction.user.avatar.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="card_info", description="Get information about a card")
@app_commands.describe(card_name="The name of the card to look up")
async def card_info(interaction: discord.Interaction, card_name: str):
    """Show detailed information about a specific card"""
    card = get_card_by_name(card_name)
    
    if not card:
        await interaction.response.send_message(f"Card not found: {card_name}", ephemeral=True)
        return
    
    embed = get_card_embed(card)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="card_catalog", description="Browse all available cards")
async def card_catalog(interaction: discord.Interaction):
    """Browse all cards in the game"""
    view = CardInfoView(interaction.user)
    await interaction.response.send_message(embed=view.get_current_page_embed(), view=view)

@bot.tree.command(name="trade", description="Offer a card to another player")
@app_commands.describe(
    user="The user to trade with", 
    card_name="The name of the card you want to trade"
)
async def trade(interaction: discord.Interaction, user: discord.User, card_name: str):
    """Trade a card with another user"""
    uid = str(interaction.user.id)
    
    # Check for self-trade
    if user.id == interaction.user.id:
        await interaction.response.send_message("You can't trade with yourself!", ephemeral=True)
        return
        
    # Check for bot trade
    if user.bot:
        await interaction.response.send_message("You can't trade with a bot!", ephemeral=True)
        return
    
    if uid not in data:
        await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
        return
        
    result = start_trade(data, interaction.user, user, card_name)
    save_data(data)
    
    embed = discord.Embed(
        title="Trade Offer",
        description=result,
        color=0x00aaff
    )

    # Find the card for display
    card = next((c for c in data[uid]["cards"] if c["name"].lower() == card_name.lower()), None)
    if card:
        embed.add_field(name="Card Details", value=f"**{card['name']}**\nRarity: {card['rarity']}\nPower: {card['power']}")
        embed.set_image(url=card["image"])
    
    await interaction.response.send_message(embed=embed)
    
    # Notify the recipient
    try:
        recipient_embed = discord.Embed(
            title="New Trade Offer!",
            description=f"{interaction.user.name} wants to trade their **{card_name}** with you!",
            color=0x00aaff
        )
        
        recipient_embed.add_field(name="How to Accept", value="Use `/accept_trade` to accept this offer or `/decline_trade` to decline it")
        
        if card:
            recipient_embed.add_field(name="Card Details", value=f"**{card['name']}**\nRarity: {card['rarity']}\nPower: {card['power']}")
            recipient_embed.set_image(url=card["image"])

        await user.send(embed=recipient_embed)
    except discord.Forbidden:
        print(f"User {user.name} has DMs disabled.")


@bot.tree.command(name="accept_trade", description="Accept a pending trade")
async def accept_trade_cmd(interaction: discord.Interaction):
    """Accept a pending trade offer"""
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
        return
        
    result = accept_trade(data, interaction.user)
    save_data(data)
    
    embed = discord.Embed(
        title="Trade Result",
        description=result,
        color=0x00aa00 if "accepted" in result else 0xff0000
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="decline_trade", description="Decline a pending trade")
async def decline_trade_cmd(interaction: discord.Interaction):
    """Decline a pending trade offer"""
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
        return
        
    result = cancel_trade(data, interaction.user)
    save_data(data)
    
    embed = discord.Embed(
        title="Trade Declined",
        description=result,
        color=0xff5555
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="battle", description="Challenge another user to a card battle")
@app_commands.describe(opponent="The user to battle")
async def battle(interaction: discord.Interaction, opponent: discord.User):
    """Battle another user with your cards"""
    uid, oid = str(interaction.user.id), str(opponent.id)
    
    # Basic checks
    if uid == oid:
        await interaction.response.send_message("You cannot battle yourself!", ephemeral=True)
        return
    if opponent.bot:
        await interaction.response.send_message("You cannot battle a bot!", ephemeral=True)
        return
    if uid not in data:
        await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
        return
    if oid not in data:
        await interaction.response.send_message(f"{opponent.name} doesn't have a profile yet. They need to use /new_user first.", ephemeral=True)
        return
    
    # Define the card variables - make sure this exists
    challenger_cards = [card for card in data[uid].get("cards", []) if card["name"].lower() not in [name.lower() for name in BATTLE_BLACKLIST]]
    opponent_cards = [card for card in data[oid].get("cards", []) if card["name"].lower() not in [name.lower() for name in BATTLE_BLACKLIST]]
    
    if not challenger_cards:
        await interaction.response.send_message("You don't have any cards to battle with!", ephemeral=True)
        return
    if not opponent_cards:
        await interaction.response.send_message(f"{opponent.name} doesn't have any cards to battle with!", ephemeral=True)
        return
    
    battle_embed = discord.Embed(
        title="⚔️ Card Battle Challenge",
        description=f"{interaction.user.mention} has challenged {opponent.mention} to a card battle!\n\nBoth players must click the 'Select Card' button to choose their card.",
        color=0xff5555
    )
    
    # Create the view
    view = BattleView(interaction.user, opponent, challenger_cards, opponent_cards, data)
    
    # Send message and store reference
    await interaction.response.send_message(embed=battle_embed, view=view)
    view.message = await interaction.original_response()

    await check_achievements(interaction, data[uid])


@bot.tree.command(name="debug_battle")
async def debug_battle(interaction: discord.Interaction):
    """Debug battle functionality"""
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("No profile found.", ephemeral=True)
        return
        
    embed = discord.Embed(title="Battle Debug Info", color=0x00ffff)
    
    # Check card structure
    user_cards = data[uid].get("cards", [])
    sample_card = user_cards[0] if user_cards else None
    if sample_card:
        embed.add_field(
            name="Card Structure",
            value=f"Name: {sample_card.get('name', 'Missing')}\n" +
                  f"Rarity: {sample_card.get('rarity', 'Missing')}\n" +
                  f"Power: {sample_card.get('power', 'Missing')}",
            inline=False
        )
    else:
        embed.add_field(name="Cards", value="No cards found", inline=False)
        
    # Check user stats
    embed.add_field(
        name="Battle Stats",
        value=f"Battles: {data[uid].get('battles', 0)}\n" +
              f"Wins: {data[uid].get('wins', 0)}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)



@bot.tree.command(name="daily", description="Claim your daily card and coins (streak bonus)")
async def daily_card(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user to start your profile.", ephemeral=True)
        return

    current_time = int(time.time())
    last_daily = data[uid].get("last_daily", 0)

    if current_time - last_daily < 86400:
        remaining = 86400 - (current_time - last_daily)
        hours, remainder = divmod(remaining, 3600)
        minutes, seconds = divmod(remainder, 60)
        await interaction.response.send_message(
            f"You've already claimed your daily reward. Try again in {hours}h {minutes}m {seconds}s.",
            ephemeral=True
        )
        return

    # Grant a higher quality card for daily reward
    weights = {
        "Common": 15,
        "Uncommon": 30,
        "Rare": 40, 
        "Epic": 10,
        "Legendary": 4,
        "Mythical": 1
    }
    daily_cards = [card for card in CARD_POOL if card["rarity"] in weights]
    daily_weights = [weights.get(card["rarity"], 0) for card in daily_cards]
    card = random.choices(daily_cards, weights=daily_weights, k=1)[0].copy()

    if card["rarity"] in RARITY_POWER_RANGE:
        min_power, max_power = RARITY_POWER_RANGE[card["rarity"]]
        card["power"] = random.randint(min_power, max_power)

    data[uid]["cards"].append(card)

    # Streak logic
    streak = data[uid].get("daily_streak", 0)
    if current_time - last_daily <= 90000:  # within 25 hours
        streak += 1
    else:
        streak = 1

    base_reward = 500
    bonus = (streak // 7) * 50
    total_reward = base_reward + bonus

    data[uid]["daily_streak"] = streak
    data[uid]["last_daily"] = current_time
    add_coins(data[uid], total_reward)
    save_data(data)
    await check_achievements(interaction, data[uid])


    embed = discord.Embed(
        title="Daily Card Reward!",
        description=f"You received: **{card['name']}**\n+ **{total_reward} coins** (Streak: {streak} days)",
        color=RARITY_COLORS.get(card["rarity"], 0xFFFFFF)
    )
    embed.add_field(name="Rarity", value=card["rarity"])
    embed.add_field(name="Power", value=str(card["power"]))
    embed.set_image(url=card["image"])

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="personal_stats", description="View your own or another player's game stats")
@app_commands.describe(user="The user whose stats you want to view (optional)")
async def personal_stats(interaction: discord.Interaction,
    user: Optional[discord.User] = None):
    target = user or interaction.user
    uid = str(target.id)

    if uid not in data:
        msg = f"{target.display_name} hasn't created a profile yet." if user else "You don't have a profile yet. Use /new_user to get started!"
        await interaction.response.send_message(msg, ephemeral=True)
        return

    user_data = data[uid]
    cards = user_data.get("cards", [])
    coins = user_data.get("coins", 0)
    wins = user_data.get("wins", 0)
    battles = user_data.get("battles", 0)
    manual_favorite = user_data.get("favorite_card")

    total_power = sum(card["power"] for card in cards)
    card_count = len(cards)
    win_rate = f"{(wins / battles * 100):.1f}%" if battles else "N/A"

    # Find rarest card
    if cards:
        rarest_card = max(cards, key=lambda c: RARITY_ORDER.get(c["rarity"], 0))
        rarest_info = f"{rarest_card['name']} ({rarest_card['rarity']}, {rarest_card['power']}P)"
    else:
        rarest_info = "None"

    # Favorite card (manual or fallback)
    from collections import Counter
    card_names = [card["name"] for card in cards]
    card_counts = Counter(card_names)

    if manual_favorite and manual_favorite in card_names:
        fav_count = card_counts[manual_favorite]
        favorite_info = f"{manual_favorite} ({fav_count} copies)"
    elif card_counts:
        most_common_name, count = max(card_counts.items(), key=lambda x: (x[1], x[0]))
        favorite_info = f"{most_common_name} ({count} copies)"
    else:
        favorite_info = "None"

    # Medals
    medals = get_medals(user_data)

    embed = discord.Embed(title=f"{target.display_name}'s Stats", color=0x00ccff)
    embed.add_field(name="Cards", value=f"{card_count} total", inline=True)
    embed.add_field(name="Total Power", value=str(total_power), inline=True)
    embed.add_field(name="Coins", value=str(coins), inline=True)
    embed.add_field(name="Wins", value=str(wins), inline=True)
    embed.add_field(name="Battles", value=str(battles), inline=True)
    embed.add_field(name="Win Rate", value=win_rate, inline=True)
    embed.add_field(name="Rarest Card", value=rarest_info, inline=False)
    embed.add_field(name="Favorite Card", value=favorite_info, inline=False)
    embed.add_field(name="Medals", value=", ".join(medals), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=(user is None))


@bot.tree.command(name="set_favorite", description="Set your favorite card")
@app_commands.describe(card_name="Exact name of the card you want to set as favorite")
async def set_favorite(interaction: discord.Interaction, card_name: str):
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user to start playing first!", ephemeral=True)
        return

    cards = data[uid].get("cards", [])
    owned_names = [card["name"].lower() for card in cards]

    if card_name.lower() not in owned_names:
        await interaction.response.send_message(f"You don't own a card named `{card_name}`.", ephemeral=True)
        return

    data[uid]["favorite_card"] = card_name
    save_data(data)
    await interaction.response.send_message(f"Favorite card set to **{card_name}**!", ephemeral=True)



@bot.tree.command(name="achievements", description="View your unlocked and locked achievements")
async def achievements(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("You need to create a profile with /new_user first!", ephemeral=True)
        return

    unlocked = set(data[uid].get("achievements", []))

    embed = discord.Embed(title=f"{interaction.user.display_name}'s Achievements", color=0x44ff44)

    for ach in ACHIEVEMENTS:
        status = "✅" if ach["id"] in unlocked else "❌"
        embed.add_field(
            name=f"{ach['emoji']} {ach['name']} [{status}]",
            value=ach["desc"],
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)



@bot.tree.command(name="leaderboard", description="View the top players")
async def leaderboard(interaction: discord.Interaction):
    """Show the leaderboard of top players"""
    if not data:
        await interaction.response.send_message("No players found in the database.", ephemeral=True)
        return

    user_stats = []

    for user_id, user_data in data.items():
        try:
            if not user_data.get("cards"):
                continue

            total_power = sum(card["power"] for card in user_data["cards"])
            card_count = len(user_data["cards"])
            wins = user_data.get("wins", 0)

            # Fetch user safely
            try:
                user = await interaction.client.fetch_user(int(user_id))
                username = user.name
            except Exception as e:
                print(f"Could not fetch user {user_id}: {e}")
                username = f"User {user_id}"

            user_stats.append({
                "id": user_id,
                "name": username,
                "total_power": total_power,
                "card_count": card_count,
                "wins": wins
            })

        except Exception as e:
            print(f"Error processing user {user_id}: {e}")

    if not user_stats:
        await interaction.response.send_message("No players with cards found.", ephemeral=True)
        return

    # Leaderboards
    power_leaders = sorted(user_stats, key=lambda x: x["total_power"], reverse=True)[:10]
    win_leaders = sorted(user_stats, key=lambda x: x["wins"], reverse=True)[:10]
    collection_leaders = sorted(user_stats, key=lambda x: x["card_count"], reverse=True)[:10]

    embed = discord.Embed(title="🏆 Card Game Leaderboards", color=0xffd700)

    embed.add_field(
        name="💪 Top Total Power",
        value="\n".join([f"{i+1}. **{u['name']}**: {u['total_power']} Power" for i, u in enumerate(power_leaders)]),
        inline=False
    )
    embed.add_field(
        name="🎯 Top Winners",
        value="\n".join([f"{i+1}. **{u['name']}**: {u['wins']} Wins" for i, u in enumerate(win_leaders)]),
        inline=False
    )
    embed.add_field(
        name="🃏 Top Collectors",
        value="\n".join([f"{i+1}. **{u['name']}**: {u['card_count']} Cards" for i, u in enumerate(collection_leaders)]),
        inline=False
    )

    await interaction.response.send_message(embed=embed)



@bot.tree.command(name="balance", description="Check your coin balance")
async def balance(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user to create your profile first.", ephemeral=True)
        return

    coins = data[uid].get("coins", 0)
    await interaction.response.send_message(f"You have **{coins} coins**.")

@bot.tree.command(name="earn", description="Earn coins (hourly bonus)")
async def earn(interaction: discord.Interaction):
    import time
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user to create your profile first.", ephemeral=True)
        return

    current = int(time.time())
    last = data[uid].get("last_earn", 0)
    if current - last < 3600:
        wait = 3600 - (current - last)
        mins, secs = divmod(wait, 60)
        return await interaction.response.send_message(f"Try again in {mins}m {secs}s.", ephemeral=True)

    earned = random.randint(50, 150)
    add_coins(data[uid], earned)
    data[uid]["last_earn"] = current
    save_data(data)

    await interaction.response.send_message(f"You earned **{earned} coins**!")



@bot.tree.command(name="shop", description="Browse the card shop")
async def shop(interaction: discord.Interaction):
    global SHOP_LAST_REFRESH
    global SHOP_CARDS
    
    # Check if shop is empty (first run)
    if not SHOP_CARDS:
        refresh_shop()  # Force a refresh if no cards
    
    # Calculate remaining time until next refresh
    current_time = int(time.time())
    three_hours_in_seconds = 3 * 60 * 60
    time_left = three_hours_in_seconds - (current_time - SHOP_LAST_REFRESH)
    
    if time_left < 0:
        refresh_shop()  # Refresh if time has passed
        time_left = three_hours_in_seconds
    
    hours, remainder = divmod(time_left, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_display = f"{int(hours)}h {int(minutes)}m"
    
    # Create embed for shop display
    embed = discord.Embed(
        title="Card Shop",
        description=f"Next refresh in: **{time_display}**\nUse `/buy [card_name]` to purchase a card!",
        color=0x00aaff
    )
    
    # Display each card in the shop
    for i, card in enumerate(SHOP_CARDS):
        price = calculate_card_price(card)
        embed.add_field(
            name=f"{i+1}. {card['name']} ({price} coins)",
            value=f"Rarity: {card['rarity']}\nPower: {card.get('power', 'N/A')}",
            inline=(i%2==0)  # Alternate between inline and not
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy", description="Buy a card from the shop")
@app_commands.describe(card_name="Name of the card to buy")
async def buy(interaction: discord.Interaction, card_name: str):
    global SHOP_CARDS
    
    uid = str(interaction.user.id)
    if uid not in data:
        await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
        return
    
    # Find the card in the shop
    card = next((c for c in SHOP_CARDS if c["name"].lower() == card_name.lower()), None)
    
    if not card:
        await interaction.response.send_message(f"Card '{card_name}' not found in shop.", ephemeral=True)
        return
    
    # Calculate price
    price = calculate_card_price(card)
    
    # Check if user has enough coins
    if not subtract_coins(data[uid], price):
        await interaction.response.send_message(f"You need {price} coins to buy this card!", ephemeral=True)
        return
    
    # Remove from shop and add to user inventory
    SHOP_CARDS = [c for c in SHOP_CARDS if c["name"].lower() != card_name.lower()]
    data[uid]["cards"].append(card)
    
    # Save user data
    save_data(data)
    
    embed = discord.Embed(
        title="Purchase Successful!",
        description=f"You bought **{card['name']}** for **{price}** coins!",
        color=RARITY_COLORS.get(card["rarity"], 0xFFFFFF)
    )
    embed.set_image(url=card["image"])
    
    await interaction.response.send_message(embed=embed)


from discord import app_commands

# --- Autocomplete Function ---
async def sell_autocomplete(interaction: discord.Interaction, current: str):
    uid = str(interaction.user.id)
    if uid not in data:
        return []

    cards = data[uid].get("cards", [])
    matches = []

    for card in CARD_POOL:
        label = f"{card['name']} [P: {card['power']}]"
        if current.lower() in card['name'].lower():
            matches.append(app_commands.Choice(name=label, value=card["name"]))
        if len(matches) >= 25:
            break

    return matches

# --- Sell Command ---
@bot.tree.command(name="sell", description="Sell a card from your inventory")
@app_commands.describe(card_name="Start typing the card name to sell")
@app_commands.autocomplete(card_name=sell_autocomplete)
async def sell(interaction: discord.Interaction, card_name: str):
    uid = str(interaction.user.id)
    
    if uid not in data or not data[uid]["cards"]:
        await interaction.response.send_message("You have no cards to sell.", ephemeral=True)
        return
    
    # Use the consolidated sell_card function
    success, message, card = sell_card(data, uid, card_name)
    
    if not success:
        await interaction.response.send_message(message, ephemeral=True)
        return
    
    # Create embed for successful sale
    embed = discord.Embed(
        title="Card Sold!",
        description=message,
        color=0xFFA500
    )
    
    # Add card details to the embed
    embed.add_field(name="Rarity", value=card["rarity"])
    embed.add_field(name="Power", value=str(card["power"]))
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="bulk_sell", description="Sell multiple cards at once")
@app_commands.describe(
    rarity="Rarity of cards to sell (optional)",
    amount="How many cards to sell (optional)",
    duplicates="Only sell duplicate cards (same name)?"
)
async def bulk_sell(
    interaction: discord.Interaction,
    rarity: Optional[str] = None,
    amount: Optional[int] = None,
    duplicates: Optional[bool] = False
):
    uid = str(interaction.user.id)
    if uid not in data or not data[uid]["cards"]:
        await interaction.response.send_message("You have no cards to sell.", ephemeral=True)
        return

    user_cards = data[uid]["cards"]

    # Step 1: Filter cards
    filtered = user_cards.copy()

    if duplicates:
        name_counts = {}
        for card in user_cards:
            name_counts[card["name"]] = name_counts.get(card["name"], 0) + 1
        filtered = [c for c in filtered if name_counts[c["name"]] > 1]

    if rarity:
        rarity = rarity.capitalize()
        if rarity not in SELL_PRICES:
            await interaction.response.send_message("Invalid rarity.", ephemeral=True)
            return
        filtered = [c for c in filtered if c["rarity"] == rarity]

    if not filtered:
        await interaction.response.send_message("No cards matched the filters.", ephemeral=True)
        return

    to_sell = filtered if amount is None else filtered[:amount]

    # Step 2: Show preview
    preview_text = ""
    for card in to_sell[:10]:
        preview_text += f"- {card['name']} ({card['rarity']}, {card['power']}P)\n"
    if len(to_sell) > 10:
        preview_text += f"...and {len(to_sell) - 10} more."

    total_coins = sum(SELL_PRICES.get(c["rarity"], 0) for c in to_sell)

    class ConfirmSellView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=20)
            self.confirmed = None

        @discord.ui.button(label="Confirm Sell", style=discord.ButtonStyle.danger)
        async def confirm(self, i2: discord.Interaction, _):
            if i2.user.id != interaction.user.id:
                await i2.response.send_message("You can't confirm this.", ephemeral=True)
                return
            self.confirmed = True
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, i2: discord.Interaction, _):
            if i2.user.id != interaction.user.id:
                await i2.response.send_message("You can't cancel this.", ephemeral=True)
                return
            self.confirmed = False
            self.stop()

    view = ConfirmSellView()
    embed = discord.Embed(
        title="Confirm Bulk Sell",
        description=f"You are about to sell **{len(to_sell)}** card(s) for **{total_coins} coins**.",
        color=0xFFA500
    )
    embed.add_field(name="Preview", value=preview_text or "No cards shown.", inline=False)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    await view.wait()

    if not view.confirmed:
        await interaction.followup.send("Bulk sell canceled.", ephemeral=True)
        return

    # Step 3: Perform sell
    coins_earned = 0
    sold_cards = []

    for card in to_sell:
        try:
            user_cards.remove(card)
            coins = SELL_PRICES.get(card["rarity"], 0)
            add_coins(data[uid], coins)
            coins_earned += coins
            sold_cards.append(card)
        except ValueError:
            continue

    save_data(data)
    last_bulk_sells[uid] = sold_cards  # For undo

    # Step 4: Send result with undo button
    class UndoView(discord.ui.View):
        @discord.ui.button(label="Undo", style=discord.ButtonStyle.blurple)
        async def undo(self, i3: discord.Interaction, _):
            if i3.user.id != interaction.user.id:
                await i3.response.send_message("You can't undo this.", ephemeral=True)
                return

            restored = last_bulk_sells.get(uid, [])
            user_cards.extend(restored)
            remove_coins(data[uid], coins_earned)
            save_data(data)
            del last_bulk_sells[uid]
            await i3.response.edit_message(content="Undo successful. Cards restored.", view=None)

    await interaction.followup.send(
        f"Sold **{len(sold_cards)}** card(s) for **{coins_earned} coins**.",
        view=UndoView(),
        ephemeral=True
    )


@bot.tree.command(name="collection", description="View your card collection progress")
@app_commands.describe(
    card_name="Check a specific card (optional)"
)
async def collection(interaction: discord.Interaction, card_name: Optional[str] = None):
    """View your card collection status and progress"""
    uid = str(interaction.user.id)
    
    if uid not in data:
        await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
        return
    
    user_cards = data[uid].get("cards", [])
    
    if not user_cards:
        await interaction.response.send_message("You don't have any cards in your collection yet. Use /draw to get started!", ephemeral=True)
        return
    
    # If checking a specific card
    if card_name:
        await check_specific_card(interaction, card_name, user_cards)
        return
    
    # Otherwise show collection statistics
    await show_collection_stats(interaction, user_cards)



@bot.tree.command(name="auction", description="List a card for sale in the auction house")
@app_commands.describe(card_name="Name of the card to sell", price="Price in coins")
async def auction(interaction: discord.Interaction, card_name: str, price: int):
    uid = str(interaction.user.id)
    user_data = data.get(uid)

    if not user_data or not user_data.get("cards"):
        await interaction.response.send_message("You don't have any cards!", ephemeral=True)
        return

    # Limit of 3 auctions per user
    auctions = load_auctions()
    auctions = [a for a in auctions if time.time() - a["timestamp"] < AUCTION_DURATION]  # purge old
    save_auctions(auctions)

    user_listings = [a for a in auctions if a["seller_id"] == uid]
    if len(user_listings) >= 3:
        await interaction.response.send_message("You can only list up to 3 cards at once.", ephemeral=True)
        return

    # Find card
    card = next((c for c in user_data["cards"] if c["name"].lower() == card_name.lower()), None)
    if not card:
        await interaction.response.send_message("You don't own that card.", ephemeral=True)
        return

    # Remove from user inventory
    user_data["cards"].remove(card)
    save_data(data)

    # Add to auction listings
    auctions.append({
        "seller_id": uid,
        "price": price,
        "card": card,
        "auction_id": str(uuid.uuid4()),
        "timestamp": time.time()
    })
    save_auctions(auctions)

    await interaction.response.send_message(f"Listed **{card['name']}** for {price} coins!")


@bot.tree.command(name="browse_auctions", description="View available cards in the auction house")
async def browse_auctions(interaction: discord.Interaction):
    auctions = load_auctions()
    auctions = [a for a in auctions if time.time() - a["timestamp"] < AUCTION_DURATION]
    save_auctions(auctions)

    if not auctions:
        await interaction.response.send_message("No auctions currently listed.")
        return

    await interaction.response.send_message("Loading auctions...", ephemeral=True, view=AuctionPaginationView(auctions))


@bot.tree.command(name="buy_auction", description="Buy a card from the auction house")
@app_commands.describe(auction_id="The ID of the auction to buy")
async def buy_auction(interaction: discord.Interaction, auction_id: str):
    uid = str(interaction.user.id)
    user_data = data.get(uid)
    auctions = load_auctions()

    auction = next((a for a in auctions if a["auction_id"] == auction_id), None)
    if not auction:
        await interaction.response.send_message("Auction not found.", ephemeral=True)
        return

    if time.time() - auction["timestamp"] > AUCTION_DURATION:
        auctions.remove(auction)
        save_auctions(auctions)
        await interaction.response.send_message("This auction has expired.", ephemeral=True)
        return

    if user_data["coins"] < auction["price"]:
        await interaction.response.send_message("You don't have enough coins.", ephemeral=True)
        return

    # Confirm purchase
    confirm_embed = discord.Embed(
        title="Confirm Purchase",
        description=f"Buy **{auction['card']['name']}** for **{auction['price']}** coins?",
        color=0xffcc00
    )
    await interaction.response.send_message(embed=confirm_embed, ephemeral=True, view=ConfirmBuyView(interaction, auction, auctions))


@bot.tree.command(name="my_auctions", description="View your active auction listings")
async def my_auctions(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    auctions = [a for a in load_auctions() if a["seller_id"] == uid and time.time() - a["timestamp"] < AUCTION_DURATION]

    if not auctions:
        await interaction.response.send_message("You have no active listings.", ephemeral=True)
        return

    embed = discord.Embed(title="Your Auctions", color=0x99ccff)
    for a in auctions:
        embed.add_field(
            name=f"{a['card']['name']} ({a['card']['rarity']})",
            value=f"Price: {a['price']} coins\nID: `{a['auction_id']}`",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="cancel_auction", description="Cancel an auction and return the card to your inventory")
@app_commands.describe(
    auction_id="The ID of the auction to cancel"
)
async def cancel_auction(interaction: discord.Interaction, auction_id: str):
    # Verify the user is the owner of the auction
    uid = str(interaction.user.id)
    auction = next((a for a in auctions if a["id"] == auction_id and a["seller_id"] == uid), None)
    
    if not auction:
        await interaction.response.send_message("Auction not found or you don't own it.", ephemeral=True)
        return
    
    # Remove the auction and return the card
    auctions.remove(auction)
    data[uid]["cards"].append(auction["card"])  # return the card to the seller
    save_data(data)
    
    try:
        user = await bot.fetch_user(int(uid))
        await user.send(f"Your auction for **{auction['card']['name']}** was cancelled and returned to your inventory.")
    except:
        pass
    
    save_auctions(auctions)
    
    await interaction.response.send_message(f"Auction for **{auction['card']['name']}** was cancelled and returned to your inventory.")



@bot.tree.command(name="help", description="Show help information about the card game")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    embed = discord.Embed(
        title="Card Game Help",
        description="Welcome to the Card Collection Game! Here are the available commands:",
        color=0x00aaff
    )
    
    embed.add_field(name="/new_user", value="Create your profile to start playing", inline=False)
    embed.add_field(name="/roll", value="Roll for a random card with rarity weights", inline=False)
    embed.add_field(name="/sell", value="Sell a card with a provided name", inline=False)
    embed.add_field(name="/bulk_sell", value="Sell a bunch of cards", inline=False)
    embed.add_field(name="/shop", value="Open up the shop", inline=False)
    embed.add_field(name="/draw", value="Draw a random card without rarity weights", inline=False)
    embed.add_field(name="/daily", value="Claim your daily card (higher quality)", inline=False)
    embed.add_field(name="/inventory", value="View your card collection", inline=False)
    embed.add_field(name="/profile", value="View your game statistics", inline=False)
    embed.add_field(name="/card_info", value="Get information about a specific card", inline=False)
    embed.add_field(name="/card_catalog", value="Browse all available cards", inline=False)
    embed.add_field(name="/battle", value="Challenge another player to a battle", inline=False)
    embed.add_field(name="/trade", value="Offer a card to another player", inline=False)
    embed.add_field(name="/accept_trade", value="Accept a pending trade", inline=False)
    embed.add_field(name="/decline_trade", value="Decline a pending trade", inline=False)
    embed.add_field(name="/leaderboard", value="View the top players", inline=False)
    
    embed.add_field(
        name="Rarity Tiers",
        value="Common < Uncommon < Rare < Epic < Legendary < Mythical < Event",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="cmdtest", description="Test if commands are working")
async def cmdtest(interaction: discord.Interaction):
    await interaction.response.send_message("Command registration is working!", ephemeral=True)


# --- ADMIN COMMANDS ---
@bot.tree.command(name="give_card", description="Admin: Give a card to a user")
@app_commands.describe(user="User to receive the card", card_name="Name of the card")
async def give_card(interaction: discord.Interaction, user: discord.User, card_name: str):
    if not is_admin(interaction.user):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    uid = str(user.id)
    card = next((c.copy() for c in CARD_POOL if c["name"].lower() == card_name.lower()), None)
    if not card:
        await interaction.response.send_message("Card not found.", ephemeral=True)
        return

    if card["rarity"] in RARITY_POWER_RANGE:
        min_p, max_p = RARITY_POWER_RANGE[card["rarity"]]
        card["power"] = random.randint(min_p, max_p)

    data.setdefault(uid, get_user_data(data, uid))
    data[uid]["cards"].append(card)
    save_data(data)

    await interaction.response.send_message(f"Gave **{card['name']}** to {user.display_name}.")
    
@bot.tree.command(name="reset_data", description="Admin: Reset a user's data")
@app_commands.describe(user="User whose data will be reset")
async def reset_data(interaction: discord.Interaction, user: discord.User):
    if not is_admin(interaction.user):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    uid = str(user.id)
    if uid in data:
        del data[uid]
        save_data(data)
        await interaction.response.send_message(f"Data for {user.display_name} has been reset.")
    else:
        await interaction.response.send_message("User has no data.", ephemeral=True)
        
@bot.tree.command(name="give_eco", description="Admin: Give coins to a user")
@app_commands.describe(user="User to give coins to", amount="Amount of coins")
async def give_eco(interaction: discord.Interaction, user: discord.User, amount: int):
    if not is_admin(interaction.user):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    uid = str(user.id)
    data.setdefault(uid, get_user_data(data, uid))
    add_coins(data[uid], amount)
    save_data(data)

    await interaction.response.send_message(f"Gave **{amount} coins** to {user.display_name}.")


    await interaction.response.send_message(embed=embed)

# Load config.json
with open("config.json", "r") as f:
    config = json.load(f)

bot_token = config.get("BOT_TOKEN")
if not bot_token:
    raise ValueError("BOT_TOKEN is missing from config.json")

bot.run(bot_token)



# --- RUN THE BOT ---
# Replace 'YOUR_BOT_TOKEN' with your actual Discord bot token
# IMPORTANT: Don't hardcode your token in production. Use environment variables or config files.
# bot.run("YOUR_BOT_TOKEN")

# To enable the bot, uncomment the line above and add your token
# For security reasons, I've removed the token that was in the original codeimport discord