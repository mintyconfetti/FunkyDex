import discord

def is_admin(user: discord.User) -> bool:
    return user.id in ADMINS
    