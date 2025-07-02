import discord
from data_utils import save_data
from achievements import check_achievements

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

    async def check_battle_complete(self, interaction: discord.Interaction):
        if not self.challenger_selection or not self.opponent_selection or self.is_complete:
            return
        self.is_complete = True

        chal_power = self.challenger_selection["power"]
        opp_power = self.opponent_selection["power"]

        if chal_power > opp_power:
            winner = self.challenger
        elif opp_power > chal_power:
            winner = self.opponent
        else:
            winner = None

        embed = discord.Embed(title="Battle Result", color=0x00ff00)
        embed.add_field(name=f"{self.challenger.display_name}", value=f"{self.challenger_selection['name']} ({chal_power}P)", inline=False)
        embed.add_field(name=f"{self.opponent.display_name}", value=f"{self.opponent_selection['name']} ({opp_power}P)", inline=False)

        if winner:
            embed.add_field(name="Winner", value=f"**{winner.display_name}** wins!", inline=False)
            self.data[str(winner.id)]["wins"] += 1
        else:
            embed.add_field(name="Result", value="It's a draw!", inline=False)

        self.data[str(self.challenger.id)]["battles"] += 1
        self.data[str(self.opponent.id)]["battles"] += 1

        save_data(self.data)

        for child in self.children:
            child.disabled = True

        await self.message.edit(embed=embed, view=self)

        if winner:
            await check_achievements(interaction, self.data[str(winner.id)])

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)
            