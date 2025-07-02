import discord
from discord.ext import commands
import asyncio
from data_utils import load_data
from shop import periodic_shop_refresh
from config import TOKEN

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="", intents=intents)
bot.synced = False


# Global shared data
bot.data = load_data()
from commands import register_commands
register_commands(bot)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error):
    print(f"❌ Error in command '{interaction.command.name}': {error}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"An error occurred: {str(error)}")

# Run the Bot
bot.run(TOKEN)