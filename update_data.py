import os
import json
import asyncio
from datetime import datetime
from pylitterbot import Account

# Constants
HISTORY_FILE = "history.json"
USERNAME = os.environ.get("WHISKER_USERNAME")
PASSWORD = os.environ.get("WHISKER_PASSWORD")

async def main():
    # 1. Connect to Whisker API
    account = Account()
    await account.connect(username=USERNAME, password=PASSWORD, load_robots=True)
    
    robot = account.robots[0] # Assuming you have 1 robot
    await account.load_pets()
    pets = account.pets

    # 2. Get today's date in YYYY-MM-DD format
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 3. Load existing history (or create empty structure)
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {"robot_status": "", "cats": {}, "history": []}

    # 4. Update static info (Robot status and Cat profiles)
    data["robot_status"] = robot.status
    
    for pet in pets:
        data["cats"][pet.name] = {
            "weight": pet.weight,
            "birthday": str(pet.birth_date) if pet.birth_date else "Unknown",
            "age": pet.age if pet.age else "Unknown"
        }

    # 5. Get today's activity history (Mock logic for extracting pet visits)
    # Note: pylitterbot's activity history structure varies, you may need to tweak property names.
    activities = await robot.get_activity_history(limit=50)
    
    daily_stats = {
        "date": today_str,
        "cats": {pet.name: {"visits": 0, "times": [], "weight": pet.weight} for pet in pets}
    }

    for act in activities:
        act_date = act.timestamp.strftime("%Y-%m-%d")
        act_time = act.timestamp.strftime("%H:%M")
        
        # Only process today's events that are pet visits
        if act_date == today_str and act.action == "pet_visit":
            pet_name = act.pet_name if hasattr(act, 'pet_name') else "Unknown"
            if pet_name in daily_stats["cats"]:
                daily_stats["cats"][pet_name]["visits"] += 1
                daily_stats["cats"][pet_name]["times"].append(act_time)

    # 6. Upsert Logic: Update today or append new day
    if len(data["history"]) > 0 and data["history"][-1]["date"] == today_str:
        data["history"][-1] = daily_stats # Overwrite today with latest hourly data
    else:
        data["history"].append(daily_stats) # Append a brand new day

    # 7. Save file
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)
        
    await account.disconnect()

if __name__ == "__main__":
    asyncio.run(main())