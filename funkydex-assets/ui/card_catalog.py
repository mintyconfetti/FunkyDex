import discord
from cards import CARD_POOL
from constants import RARITY_COLORS

class CardInfoView(discord.ui.View):
    def __init__(self, user, cards=None):
        super().__init__(timeout=60)
        self.user = user
        self.cards = cards or CARD_POOL
        self.page = 0
        self.per_page = 5
        self.max_page = (len(self.cards) - 1) // self.per_page
        self.message = None

    def get_current_page_embed(self):
        embed = discord.Embed(title="Card Catalog", color=0x00bfff)
        start = self.page * self.per_page
        end = start + self.per_page
        for card in self.cards[start:end]:
            embed.add_field(name=card["name"], value=f"Rarity: {card['rarity']}, Power: {card['power']}", inline=False)
        embed.set_footer(text=f"Page {self.page + 1}/{self.max_page + 1}")
        return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, _):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.get_current_page_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, _):
        if self.page < self.max_page:
            self.page += 1
            await interaction.response.edit_message(embed=self.get_current_page_embed(), view=self)
        else:
            await interaction.response.defer()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass
            