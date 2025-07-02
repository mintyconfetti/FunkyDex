import time
import asyncio
from cards import roll_card
from config import SHOP_REFRESH_INTERVAL

SHOP_LAST_REFRESH = 0
SHOP_CARDS = []

def refresh_shop():
    global SHOP_LAST_REFRESH, SHOP_CARDS
    now = int(time.time())
    if now - SHOP_LAST_REFRESH >= SHOP_REFRESH_INTERVAL or not SHOP_CARDS:
        SHOP_CARDS = [roll_card() for _ in range(5)]
        SHOP_LAST_REFRESH = now

async def periodic_shop_refresh(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        refresh_shop()
        await asyncio.sleep(3600)