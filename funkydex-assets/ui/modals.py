import discord
from .card_select import CardSelectView

class CardSearchModal(discord.ui.Modal):
    def __init__(self, battle_view, cards, is_challenger):
        super().__init__(title="Search Your Cards")
        self.battle_view = battle_view
        self.cards = cards
        self.is_challenger = is_challenger

        self.search_input = discord.ui.TextInput(
            label="Search by card name",
            placeholder="Enter card name or part of name...",
            required=True
        )
        self.add_item(self.search_input)

    async def on_submit(self, interaction: discord.Interaction):
        search_term = self.search_input.value.lower()
        filtered_cards = [card for card in self.cards if search_term in card['name'].lower()]

        if not filtered_cards:
            await interaction.response.send_message(
                f"No cards found matching '{self.search_input.value}'", ephemeral=True
            )
            return

        view = CardSelectView(self.battle_view, filtered_cards, self.is_challenger)
        await interaction.response.send_message(
            f"Found {len(filtered_cards)} card(s):", view=view, ephemeral=True
        )
        