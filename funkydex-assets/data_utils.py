import json
import os
from typing import Dict, Any
from config import DATA_FILE



def load_data() -> Dict[str, Any]:
    """Load user data from JSON file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    except json.JSONDecodeError:
        print(f"Error: {DATA_FILE} is corrupted, creating new data file")
        return {}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}



def save_data(data: Dict[str, Any]) -> None:
    """Save user data to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")



def get_user_data(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get or create user data"""
    if user_id not in data:
        data[user_id] = {
            "cards": [], 
            "trades": [], 
            "battles": 0, 
            "wins": 0, 
            "last_daily": 0,
            "coins": 0,
            "last_earn": 0
        }
    return data[user_id]