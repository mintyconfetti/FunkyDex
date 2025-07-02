from typing import Dict, Any, Optional, Tuple, List
import discord


# --- CHECK SPECIFIC CARD ---
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


# --- SHOW COLLECTION STATS ---
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
        title=":bar_chart: Card Collection Stats",
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
            emoji = ":green_circle:"  # Complete
        elif percentage >= 50:
            emoji = ":yellow_circle"  # Good progress
        elif percentage > 0:
            emoji = ":orange_circle:"  # Started
        else:
            emoji = ":red_circle:"  # None collected
            
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