def add_coins(user_data, amount):
    user_data["coins"] = user_data.get("coins", 0) + amount

def subtract_coins(user_data, amount):
    if user_data.get("coins", 0) >= amount:
        user_data["coins"] -= amount
        return True
    return False

def remove_coins(user_data, amount):
    user_data["coins"] = max(0, user_data.get("coins", 0) - amount)