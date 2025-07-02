import discord

class CardSelectView(discord.ui.View):
    def __init__(self, battle_view, cards, is_challenger):
        super().__init__(timeout=60)
        self.add_item(CardSelect(cards, battle_view, is_challenger))

class CardSelect(discord.ui.Select):
    def __init__(self, cards, battle_view, is_challenger):
        self.cards = cards
        self.battle_view = battle_view
        self.is_challenger = is_challenger

        options = [
            discord.SelectOption(
                label=f"{card['name']} ({card['power']}P)",
                description=f"Rarity: {card['rarity']}",
                value=str(i)
            )
            for i, card in enumerate(cards[:25])
        ]

        super().__init__(
            placeholder="Select a card...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        correct_user = self.battle_view.challenger if self.is_challenger else self.battle_view.opponent
        if interaction.user.id != correct_user.id:
            await interaction.response.send_message("This isn't your card selection!", ephemeral=True)
            return

        selected_card = self.cards[int(self.values[0])]
        if self.is_challenger:
            self.battle_view.challenger_selection = selected_card
        else:
            self.battle_view.opponent_selection = selected_card

        await interaction.response.send_message(
            f"You selected **{selected_card['name']}** for battle!", ephemeral=True
        )
        await self.battle_view.check_battle_complete(interaction)
        