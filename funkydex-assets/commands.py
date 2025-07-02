# -*- coding: utf-8 -*-
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import random
import time
import uuid
import aiohttp


# Imports from logic modules
from economy import add_coins, subtract_coins, remove_coins
from cards import roll_card, CARD_POOL
from data_utils import save_data, get_user_data
from constants import (
    RARITY_COLORS, RARITY_ORDER, RARITY_PRICES, RARITY_POWER_RANGE,
    SELL_PRICES, RARITY_EMOJIS, ACHIEVEMENTS, BATTLE_BLACKLIST
)
from shop import refresh_shop, SHOP_CARDS, SHOP_LAST_REFRESH
from achievements import check_achievements, get_medals
from auction import load_auctions, save_auctions, AUCTION_DURATION

# UI Imports
from ui.inventory_view import InventoryView
from ui.card_catalog import CardInfoView
from ui.battle_views import BattleButtonView
from ui.card_select import CardSelectView
from ui.modals import CardSearchModal
from battle import BattleView

# Placeholder functions for sell/trade/etc.
from helpers.trading import start_trade, accept_trade, cancel_trade
from helpers.sell import sell_card
from helpers.collection import check_specific_card, show_collection_stats
from helpers.admin import is_admin

# Event based functions
from events.trivia_event import (
    TRIVIA_QUESTIONS, get_encoded_message, redeem_code
)


# TEMP PLACEMENT!!!
TOPGG_API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJib3QiOiJ0cnVlIiwiaWQiOiIxMzA2Mjc1MzY2MjA5NTg5MjY4IiwiaWF0IjoiMTc0OTI1NDI2MyJ9.z9tpPEAXpv8ZIdhKMgXV8G-pcwSHxxn7ZBq_2O9WOs0"  # Replace with your real Top.gg API token
BOT_ID = "1306275366209589268"  # Replace with your bot's user ID as a string

async def check_if_user_voted(user_id: str) -> bool:
    url = f"https://top.gg/api/bots/{BOT_ID}/check?userId={user_id}"
    headers = {
        "Authorization": TOPGG_API_TOKEN
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Top.gg vote check failed with status {response.status}")
                return False
            data = await response.json()
            return data.get("voted") == 1
            


class MultiDrawView(discord.ui.View):
    def __init__(self, cards, user):
        super().__init__(timeout=180)
        self.cards = cards
        self.user = user  # now storing the full discord.User object
        self.current_page = 0
        self.message = None

    def get_current_page_embed(self):
        card = self.cards[self.current_page]
        embed = discord.Embed(
            title=f"Card {self.current_page + 1}/{len(self.cards)}: {card['name']}",
            description=f"**Rarity**: {card.get('rarity', 'Unknown')}\n**Power**: {card.get('power', 'N/A')}",
            color=RARITY_COLORS.get(card.get("rarity", "Common"), 0xFFFFFF)
        )
        embed.set_image(url=card["image"])

        # Add special footer for rare+ cards
        if card.get("rarity") in ["Rare", "Epic", "Legendary", "Mythical"]:
            emoji = RARITY_EMOJIS.get(card.get("rarity"), "")
            embed.set_footer(text=f"{emoji} {card['rarity']} card!")

        return embed

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This isn't your draw result!", ephemeral=True)
            return
        self.current_page = (self.current_page - 1) % len(self.cards)
        await interaction.response.edit_message(embed=self.get_current_page_embed(), view=self)

    @discord.ui.button(label="Card Details", style=discord.ButtonStyle.primary)
    async def detail_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This isn't your draw result!", ephemeral=True)
            return
        card = self.cards[self.current_page]
        embed = discord.Embed(
            title=f"{card['name']} Details",
            description=f"**Rarity**: {card['rarity']}\n**Power**: {card['power']}",
            color=RARITY_COLORS.get(card["rarity"], 0xFFFFFF)
        )
        embed.set_image(url=card["image"])
        await interaction.response.send_message(embed=embed,ephemeral=False)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This isn't your draw result!", ephemeral=True)
            return
        self.current_page = (self.current_page + 1) % len(self.cards)
        await interaction.response.edit_message(embed=self.get_current_page_embed(), view=self)



def register_commands(bot):
    print("✓ Commands are being registered!")
   
    @bot.tree.command(name="testroll", description="Test Roll")
    async def roll(interaction: discord.Interaction):
        print("✅ /roll was called")
        await interaction.response.send_message("You rolled a card!")
    
    # --- ROLL ---
    ROLL_COST = 100
    @bot.tree.command(name="roll", description="Roll for a new card")
    async def roll(interaction: discord.Interaction):
        data = bot.data
        uid = str(interaction.user.id)
        if uid not in data:
            await interaction.response.send_message("Use /new_user first to create your profile.", ephemeral=True)
            return
        
        if not subtract_coins(data[uid], ROLL_COST):
            await interaction.response.send_message(f"You need {ROLL_COST} coins to roll!", ephemeral=True)
            return
        
        card = roll_card()
        data[uid]["cards"].append(card)
        save_data(data)

        embed = discord.Embed(
            title=f"You rolled: {card['name']}",
            description=f"Rarity: {card['rarity']} | Power: {card['power']}",
            color=RARITY_COLORS.get(card['rarity'], 0xFFFFFF)
    )
        embed.set_image(url=card['image'])
        await interaction.response.send_message(embed=embed)




    # --- NEW_USER ---
    @bot.tree.command(name="new_user", description="Create your profile in the card game")
    async def new_user(interaction: discord.Interaction):
        """Create a new user profile"""
        data = bot.data
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
            embed.add_field(name="/draw", value="Draw a random card (Limit 7 per day due to no rarity weighting on this command!)", inline=True)

            embed.add_field(name="/sell", value="Sell your cards!", inline=True)

            embed.add_field(name="/bulk_sell", value="Sell multiple of your cards!", inline=True)
            embed.add_field(name="/inventory", value="Check your card collection", inline=True)
            embed.add_field(name="/battle", value="Battle another player", inline=True)
            embed.add_field(name="/trade", value="Trade cards with others", inline=True)
            embed.add_field(name="/card_info", value="Learn about a specific card", inline=True)
            embed.add_field(name="/profile", value="View your stats", inline=True)
            embed.add_field(name="/daily", value="Get your daily card", inline=True)
        
        await interaction.response.send_message(embed=embed)





    # --- VOTE ---
    @bot.tree.command(name="vote",description="Vote for FunkyDex on Top.gg!")
    async def votenow(interaction: discord.Interaction):
        """Simple command that sends an ephemeral (private) message"""
        await interaction.response.send_message("Vote for FunkyDex [Here!](https://top.gg/bot/1306275366209589268/vote)",ephemeral=True)
    



    # --- CLAIM_VOTE ---
    @bot.tree.command(name="claim_vote", description="Claim your voting reward from Top.gg")
    async def claim_vote(interaction: discord.Interaction):
        data = bot.data
        uid = str(interaction.user.id)

        await interaction.response.defer(ephemeral=True)

        has_voted = await check_if_user_voted(uid)
        if not has_voted:
            await interaction.followup.send(
                "You haven’t voted yet! Vote here: https://top.gg/bot/YOUR_BOT_ID/vote",
                ephemeral=True
            )
            return

        user_data = data.get(uid)
        now = int(time.time())

        if user_data.get("last_vote_claimed", 0) > now - 43200:
            await interaction.followup.send("You've already claimed your vote reward recently!", ephemeral=True)
            return

        user_data["coins"] += 1000
        for _ in range(5):
            card = roll_card()
            user_data["cards"].append(card)

        user_data["last_vote_claimed"] = now
        save_data(data)

        await interaction.followup.send("✅ Thank you for voting! You received 5 cards and 1,000 coins!", ephemeral=True)




    # --- MULTI_ROLL ---
    @bot.tree.command(name="multi_roll", description="Roll multiple cards at once")
    @app_commands.describe(rolls="How many cards to roll (1 to 10)")
    async def multi_roll(interaction: discord.Interaction, rolls: int):
        data = bot.data
        uid = str(interaction.user.id)

    # Defer early to avoid timeout
        try:
            await interaction.response.defer(ephemeral=False)
        except Exception as e:
            print(f"multi_roll failed to defer: {e}")
            try:
                await interaction.followup.send("Something went wrong preparing the roll.", ephemeral=True)
            except:
                pass
            return

        if uid not in data:
            await interaction.followup.send("Use /new_user first to register.", ephemeral=True)
            return

        if rolls < 1 or rolls > 10:
            await interaction.followup.send("Please choose between 1 and 10 rolls.", ephemeral=True)
            return

        user_data = data[uid]
        total_cost = ROLL_COST * rolls

        if not subtract_coins(user_data, total_cost):
            await interaction.followup.send("You don't have enough coins for that many rolls.", ephemeral=True)
            return

        pulled_cards = []
        for _ in range(rolls):
            card = roll_card()
            pulled_cards.append(card)
            user_data["cards"].append(card)

        save_data(data)

        view = MultiDrawView(pulled_cards, interaction.user)
        await interaction.followup.send("Here are your rolls:",embed=view.get_current_page_embed(),view=view)

    


    # --- DRAW ---
    @bot.tree.command(name="draw", description="Draw a random card (max 7 per day)")
    async def draw(interaction: discord.Interaction):
        try:
            data = bot.data
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
                print(f"Resetting draws for user {uid}: {draws_today} 0")
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



    # --- INVENTORY ---
    @bot.tree.command(name="inventory", description="View your card collection with search, sell, and sort")
    @app_commands.describe(
        query="Search for card name (optional)",
        sort_by_rarity="Sort by rarity (Common > Mythical)"
    )
    async def inventory(
        interaction: discord.Interaction,
        query: Optional[str] = None,
        sort_by_rarity: Optional[bool] = False
    ):
        data = bot.data
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



    # --- PROFILE ---
    @bot.tree.command(name="profile", description="View your profile")
    async def profile(interaction: discord.Interaction):
        """View your profile and stats"""
        data = bot.data
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



    # --- CARD_INFO ---
    @bot.tree.command(name="card_info", description="Get information about a card")
    @app_commands.describe(card_name="The name of the card to look up")
    async def card_info(interaction: discord.Interaction, card_name: str):
        """Show detailed information about a specific card"""
        card = get_card_by_name(card_name)

        if not card:
            await interaction.response.send_message(f"Card not found: {card_name}", ephemeral=True)
            return

        embed = get_card_embed(card)
        await interaction.response.send_message(embed=embed)  # optionally add ephemeral=True




    # --- CARD_CATALOG ---
    @bot.tree.command(name="card_catalog", description="Browse all available cards")
    async def card_catalog(interaction: discord.Interaction):
        view = CardInfoView(interaction.user)
        await interaction.response.send_message(embed=view.get_current_page_embed(), view=view)
        view.message = await interaction.original_response()



    # --- TRADE ---
    @bot.tree.command(name="trade", description="Offer a card to another player")
    @app_commands.describe(
        user="The user to trade with", 
        card_name="The name of the card you want to trade"
    )
    async def trade(interaction: discord.Interaction, user: discord.User, card_name: str):
        """Trade a card with another user"""
        data = bot.data
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



    # --- ACCEPT_TRADE ---
    @bot.tree.command(name="accept_trade", description="Accept a pending trade")
    async def accept_trade_cmd(interaction: discord.Interaction):
        """Accept a pending trade offer"""
        data = bot.data
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



    # --- DECLINE_TRADE ---
    @bot.tree.command(name="decline_trade", description="Decline a pending trade")
    async def decline_trade_cmd(interaction: discord.Interaction):
        """Decline a pending trade offer"""
        data = bot.data
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



    # --- BATTLE ---
    @bot.tree.command(name="battle", description="Challenge another user to a card battle")
    @app_commands.describe(opponent="The user to battle")
    async def battle(interaction: discord.Interaction, opponent: discord.User):
        """Battle another user with your cards"""
        data = bot.data
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
            title=":black_joker: Card Battle Challenge",
            description=f"{interaction.user.mention} has challenged {opponent.mention} to a card battle!\n\nBoth players must click the 'Select Card' button to choose their card.",
            color=0xff5555
        )
    
        # Create the view
        view = BattleView(interaction.user, opponent, challenger_cards, opponent_cards, data)
    
        # Send message and store reference
        await interaction.response.send_message(embed=battle_embed, view=view)
        view.message = await interaction.original_response()

        await check_achievements(interaction, data[uid])



    # --- DEBUG_BATTLE ---
    @bot.tree.command(name="debug_battle")
    async def debug_battle(interaction: discord.Interaction):
        """Debug battle functionality"""
        data = bot.data
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



    # --- DAILY ---
    @bot.tree.command(name="daily", description="Claim your daily coins")
    async def daily(interaction: discord.Interaction):
        data = bot.data
        uid = str(interaction.user.id)

        try:
            await interaction.response.defer(ephemeral=True)
        except Exception as e:
            print(f"/daily failed to defer: {e}")
            try:
                await interaction.followup.send("Could not process your daily reward.", ephemeral=True)
            except:
                pass
            return

        if uid not in data:
            await interaction.followup.send("Please use /new_user to register first.", ephemeral=True)
            return

        user_data = data[uid]
        now = int(time.time())
        if now - user_data.get("last_daily", 0) < 86400:
            remaining = 86400 - (now - user_data["last_daily"])
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await interaction.followup.send(
                f"You've already claimed your daily! Try again in {hours}h {minutes}m.",
                ephemeral=True
            )
            return

        coins_earned = random.randint(100, 500)
        user_data["coins"] += coins_earned
        user_data["last_daily"] = now
        save_data(data)

        await interaction.followup.send(
            f"🎉 You received **{coins_earned} coins** from your daily reward!",
            ephemeral=True
        )
    



    # --- PERSONAL_STATS ---
    @bot.tree.command(name="personal_stats", description="View your own or another player's game stats")
    @app_commands.describe(user="The user whose stats you want to view (optional)")
    async def personal_stats(interaction: discord.Interaction,
        user: Optional[discord.User] = None):
        data = bot.data
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



    # --- SET_FAVORITE ---
    @bot.tree.command(name="set_favorite", description="Set your favorite card")
    @app_commands.describe(card_name="Exact name of the card you want to set as favorite")
    async def set_favorite(interaction: discord.Interaction, card_name: str):
        data = bot.data
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



    # --- ACHIEVEMENTS ---
    @bot.tree.command(name="achievements", description="View your unlocked and locked achievements")
    async def achievements(interaction: discord.Interaction):
        data = bot.data
        uid = str(interaction.user.id)
        if uid not in data:
            await interaction.response.send_message("You need to create a profile with /new_user first!", ephemeral=True)
            return

        unlocked = set(data[uid].get("achievements", []))

        embed = discord.Embed(title=f"{interaction.user.display_name}'s Achievements", color=0x44ff44)

        for ach in ACHIEVEMENTS:
            status = ":white_check_mark:" if ach["id"] in unlocked else ":x:"
            embed.add_field(
                name=f"{ach['emoji']} {ach['name']} [{status}]",
                value=ach["desc"],
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    # --- LEADERBOARD ---
    @bot.tree.command(name="leaderboard", description="View the top players")
    async def leaderboard(interaction: discord.Interaction):
        """Show the leaderboard of top players"""
        data = bot.data
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

        embed = discord.Embed(title=":crown: Card Game Leaderboards", color=0xffd700)

        embed.add_field(
            name=":muscle: Top Total Power",
            value="\n".join([f"{i+1}. **{u['name']}**: {u['total_power']} Power" for i, u in enumerate(power_leaders)]),
            inline=False
        )
        embed.add_field(
            name=":trophy: Top Winners",
            value="\n".join([f"{i+1}. **{u['name']}**: {u['wins']} Wins" for i, u in enumerate(win_leaders)]),
            inline=False
        )
        embed.add_field(
            name=":black_joker: Top Collectors",
            value="\n".join([f"{i+1}. **{u['name']}**: {u['card_count']} Cards" for i, u in enumerate(collection_leaders)]),
            inline=False
        )

        await interaction.response.send_message(embed=embed)



    # --- BALANCE ---
    @bot.tree.command(name="balance", description="Check your coin balance")
    async def balance(interaction: discord.Interaction):
        data = bot.data
        uid = str(interaction.user.id)
        if uid not in data:
            await interaction.response.send_message("Use /new_user to create your profile first.", ephemeral=True)
            return

        coins = data[uid].get("coins", 0)
        await interaction.response.send_message(f"You have **{coins} coins**.")



    # --- EARN ---
    @bot.tree.command(name="earn", description="Earn coins (hourly bonus)")
    async def earn(interaction: discord.Interaction):
        data = bot.data
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



    # --- SHOP ---
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



    # --- BUY ---
    @bot.tree.command(name="buy", description="Buy a card from the shop")
    @app_commands.describe(card_name="Name of the card to buy")
    async def buy(interaction: discord.Interaction, card_name: str):
        global SHOP_CARDS
        
        data = bot.data
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



    # --- Autocomplete Function ---
    async def sell_autocomplete(interaction: discord.Interaction, current: str):
        data = bot.data
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


    # --- SELL ---
    @bot.tree.command(name="sell", description="Sell a card from your inventory")
    @app_commands.describe(card_name="Start typing the card name to sell")
    @app_commands.autocomplete(card_name=sell_autocomplete)
    async def sell(interaction: discord.Interaction, card_name: str):
        data = bot.data
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



    # --- BULK_SELL ---
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
        data = bot.data
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



    # --- COLLECTION ---
    @bot.tree.command(name="collection", description="View your card collection progress")
    async def collection_command(interaction: discord.Interaction, card_name: Optional[str] = None):
        """View your card collection status and progress"""
        data = bot.data
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



    # --- PINGTEST ---
    @bot.tree.command(name="pingtest", description="Test if slash commands are working")
    async def pingtest(interaction: discord.Interaction):
        await interaction.response.send_message("Slash commands are working!")



    # --- AUCTION ---
    @bot.tree.command(name="auction", description="List a card for sale in the auction house")
    @app_commands.describe(card_name="Name of the card to sell", price="Price in coins")
    async def auction(interaction: discord.Interaction, card_name: str, price: int):
        data = bot.data
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



    # --- BROWSE_AUCTIONS ---
    @bot.tree.command(name="browse_auctions", description="View available cards in the auction house")
    async def browse_auctions(interaction: discord.Interaction):
        data = bot.data
        auctions = load_auctions()
        auctions = [a for a in auctions if time.time() - a["timestamp"] < AUCTION_DURATION]
        save_auctions(auctions)

        if not auctions:
            await interaction.response.send_message("No auctions currently listed.", ephemeral=True)
            return

        view = AuctionPaginationView(auctions)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)



    # --- BUY_AUCTION ---
    @bot.tree.command(name="buy_auction", description="Buy a card from the auction house")
    @app_commands.describe(auction_id="The ID of the auction to buy")
    async def buy_auction(interaction: discord.Interaction, auction_id: str):
        data = bot.data
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



    # --- MY_AUCTIONS ---
    @bot.tree.command(name="my_auctions", description="View your active auction listings")
    async def my_auctions(interaction: discord.Interaction):
        data = bot.data
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



    # --- CANCEL_AUCTION ---
    @bot.tree.command(name="cancel_auction", description="Cancel an auction and return the card to your inventory")
    @app_commands.describe(
        auction_id="The ID of the auction to cancel"
    )
    async def cancel_auction(interaction: discord.Interaction, auction_id: str):
        data = bot.data
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



    # --- HELP ---
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





# --- MISSINGNO EVENT COMMANDS ---
# ============================
    @bot.tree.command(name="event_start", description="Begin the Pokemon Event Challenge")
    async def event_start(interaction: discord.Interaction):
        data = bot.data
        embed = discord.Embed(
            title="**The Pokemon Challenge!**",
            description="Answer these questions in order. Save your answers!",
            color=0xffd700
        )
        for i, (q, _) in enumerate(TRIVIA_QUESTIONS, 1):
            embed.add_field(name=f"Question {i}", value=q, inline=False)
        embed.set_footer(text="Once you have all 3 answers, decode the final base64 message!")

        await interaction.response.send_message(embed=embed)



    @bot.tree.command(name="event_hint", description="Get your encoded message to solve!")
    async def event_hint(interaction: discord.Interaction):
        encoded = get_encoded_message()
        await interaction.response.send_message(
            f":question_mark: Base64 Message: `{encoded}`\n\nDecode this to redeem your reward!",
            ephemeral=True
        )


    @bot.tree.command(name="event_redeem", description="Redeem your event prize by solving the code!")
    @app_commands.describe(code="The decoded base64 message (the secret code)")
    async def event_redeem(interaction: discord.Interaction, code: str):
        data = bot.data
        uid = str(interaction.user.id)
        success, result = redeem_code(bot.data, uid, code)

        if not success:
            await interaction.response.send_message(result, ephemeral=True)
            return

        card = result
        embed = discord.Embed(
            title=":white_check_mark: Event Reward Unlocked!",
            description=f"You received **{card['name']}**!",
            color=RARITY_COLORS.get(card["rarity"], 0xFFFFFF)
        )
        embed.set_image(url=card["image"])

        await interaction.response.send_message("You've successfully redeemed the event reward!", ephemeral=True)
        try:
            await interaction.user.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("Could not DM you the reward card!", ephemeral=True)





# --- ADMIN COMMANDS ---
# ============================

    # --- GIVE_CARD ---
    @bot.tree.command(name="give_card", description="Admin: Give a card to a user")
    @app_commands.describe(user="User to receive the card", card_name="Name of the card")
    async def give_card(interaction: discord.Interaction, user: discord.User, card_name: str):
        data = bot.data
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



    # --- RESET_DATA ---
    @bot.tree.command(name="reset_data", description="Admin: Reset a user's data")
    @app_commands.describe(user="User whose data will be reset")
    async def reset_data(interaction: discord.Interaction, user: discord.User):
        data = bot.data
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



    # --- GIVE_ECO ---
    @bot.tree.command(name="give_eco", description="Admin: Give coins to a user")
    @app_commands.describe(user="User to give coins to", amount="Amount of coins")
    async def give_eco(interaction: discord.Interaction, user: discord.User, amount: int):
        data = bot.data
        if not is_admin(interaction.user):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        uid = str(user.id)
        data.setdefault(uid, get_user_data(data, uid))
        add_coins(data[uid], amount)
        save_data(data)

        await interaction.response.send_message(f"Gave **{amount} coins** to {user.display_name}.")

        await interaction.response.send_message(embed=embed)