import discord
from data_utils import save_data
from cards import CARD_POOL
from constants import ACHIEVEMENTS


async def check_achievements(interaction: discord.Interaction, user_data: dict, data):
    uid = str(interaction.user.id)
    unlocked = user_data.get("achievements", [])

    newly_unlocked = []

    for ach in ACHIEVEMENTS:
        if ach["id"] in unlocked:
            continue

        # Existing achievements
        if ach["id"] == "first_blood" and user_data.get("wins", 0) >= 1:
            newly_unlocked.append(ach)
        elif ach["id"] == "collector" and len(user_data.get("cards", [])) >= 50:
            newly_unlocked.append(ach)
        elif ach["id"] == "powerful" and sum(c["power"] for c in user_data.get("cards", [])) >= 5000:
            newly_unlocked.append(ach)
        elif ach["id"] == "mythic_pull" and any(c["rarity"] == "Mythical" for c in user_data.get("cards", [])):
            newly_unlocked.append(ach)
        elif ach["id"] == "rich" and user_data.get("coins", 0) >= 10000:
            newly_unlocked.append(ach)
        elif ach["id"] == "battle_master" and user_data.get("wins", 0) >= 5:
            newly_unlocked.append(ach)
        elif ach["id"] == "doki_doki":
            required_cards = ach.get("required_cards", [])
            owned_names = [c["name"] for c in user_data.get("cards", [])]
            if all(req in owned_names for req in required_cards):
                newly_unlocked.append(ach)

    # Add and DM user about new achievements
    for ach in newly_unlocked:
        unlocked.append(ach["id"])
        try:
            msg = f"{ach['emoji']} **Achievement Unlocked: {ach['name']}**\n{ach['desc']}"

            # Send achievement message
            await interaction.user.send(msg)

            # Reward special card (e.g. event card)
            reward_name = ach.get("reward_card_name")
            if reward_name:
                reward_card = next((card for card in CARD_POOL if card["name"] == reward_name), None)
                if reward_card:
                    user_data["cards"].append(reward_card)
                    reward_embed = discord.Embed(
                        title=f"You received: {reward_card['name']}",
                        description=f"Rarity: {reward_card['rarity']} | Power: {reward_card['power']}",
                        color=0xffc300
                    )
                    reward_embed.set_image(url=reward_card['image'])
                    await interaction.user.send(embed=reward_embed)

        except Exception as e:
            print(f"Could not DM {interaction.user.name}: {e}")

    user_data["achievements"] = unlocked
    save_data(data)


def get_medals(user_data):
    unlocked_ids = user_data.get("achievements", [])
    return [ach for ach in ACHIEVEMENTS if ach["id"] in unlocked_ids]
    
    