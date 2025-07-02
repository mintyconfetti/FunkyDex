import discord
from .card_select import CardSelectView
from .modals import CardSearchModal

class BattleButtonView(discord.ui.View):
    def __init__(self, battle_view):
        super().__init__(timeout=300)
        self.battle_view = battle_view

    @discord.ui.button(label="Browse Cards", style=discord.ButtonStyle.primary)
    async def browse_cards(self, interaction: discord.Interaction, _):
        if interaction.user.id not in [self.battle_view.challenger.id, self.battle_view.opponent.id]:
            await interaction.response.send_message("You're not part of this battle.", ephemeral=True)
            return

        is_challenger = interaction.user.id == self.battle_view.challenger.id
        cards = self.battle_view.challenger_cards if is_challenger else self.battle_view.opponent_cards

        if not cards:
            await interaction.response.send_message("You have no cards to select!", ephemeral=True)
            return

        view = CardSelectView(self.battle_view, cards, is_challenger)
        await interaction.response.send_message("Choose your card:", view=view, ephemeral=True)

    @discord.ui.button(label="Search Cards", style=discord.ButtonStyle.success)
    async def search_cards(self, interaction: discord.Interaction, _):
        is_challenger = interaction.user.id == self.battle_view.challenger.id
        cards = self.battle_view.challenger_cards if is_challenger else self.battle_view.opponent_cards

        if not cards:
            await interaction.response.send_message("No cards to search!", ephemeral=True)
            return

        modal = CardSearchModal(self.battle_view, cards, is_challenger)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Sort by Power", style=discord.ButtonStyle.secondary)
    async def sort_by_power(self, interaction: discord.Interaction, _):
        is_challenger = interaction.user.id == self.battle_view.challenger.id
        cards = self.battle_view.challenger_cards if is_challenger else self.battle_view.opponent_cards

        sorted_cards = sorted(cards, key=lambda c: c.get("power", 0), reverse=True)
        view = CardSelectView(self.battle_view, sorted_cards, is_challenger)
        await interaction.response.send_message("Sorted by power:", view=view, ephemeral=True)
        