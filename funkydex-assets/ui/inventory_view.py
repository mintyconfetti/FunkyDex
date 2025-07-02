import discord
from constants import SELL_PRICES
from data_utils import save_data
from economy import add_coins

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
        for index, card in enumerate(self.cards[start:end]):
            label = f"{card['name']} ({card['power']}P)"
            self.add_item(SellButton(label=label[:80], inv_view=self, card_index=start + index))
        if self.page > 0:
            self.add_item(PageButton("◀️ Previous", self, -1))
        if self.page < (len(self.cards) - 1) // self.per_page:
            self.add_item(PageButton("▶️ Next", self, 1))

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
            embed.add_field(name=f"{card['name']} (P: {card['power']})", value=f"Rarity: {card['rarity']}", inline=False)
        return embed


class SellButton(discord.ui.Button):
    def __init__(self, label, inv_view, card_index):
        super().__init__(label=label, style=discord.ButtonStyle.red)
        self.inv_view = inv_view
        self.card_index = card_index

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.inv_view.uid:
            await interaction.response.send_message("You can't sell cards from another player's inventory!", ephemeral=True)
            return

        card = self.inv_view.cards.pop(self.card_index)
        rarity = card["rarity"]
        coins = SELL_PRICES.get(rarity, 0)
        add_coins(interaction.client.data[self.inv_view.uid], coins)

        await interaction.response.send_message(f"Sold **{card['name']}** for **{coins} coins**.", ephemeral=True)
        save_data(interaction.client.data)

        self.inv_view.update_buttons()
        await interaction.message.edit(embed=self.inv_view.get_embed(), view=self.inv_view)


class PageButton(discord.ui.Button):
    def __init__(self, label, inv_view, direction):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.inv_view = inv_view
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.inv_view.uid:
            await interaction.response.send_message("You can't change another player's page!", ephemeral=True)
            return

        self.inv_view.page += self.direction
        self.inv_view.page = max(0, min(self.inv_view.page, (len(self.inv_view.cards) - 1) // self.inv_view.per_page))
        self.inv_view.update_buttons()
        await interaction.response.edit_message(embed=self.inv_view.get_embed(), view=self.inv_view)
        