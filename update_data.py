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
    data["robot_status"] = robot.status.value
    
    for pet in pets:
        data["cats"][pet.name] = {
            "weight": round(pet.weight * 0.453592, 2),
            "birthday": str(pet.birthday) if pet.birthday else "Unknown",
            "age": pet.age if pet.age else "Unknown"
        }

    # 5. Get today's activity history (Mock logic for extracting pet visits)
    # Note: pylitterbot's activity history structure varies, you may need to tweak property names.
    activities = await robot.get_activity_history(limit=50)
    
    daily_stats = {
        "date": today_str,
        "cats": {pet.name: {"visits": 0, "times": [], "weight": round(pet.weight * 0.453592, 2)} for pet in pets}
    }

    for act in activities:
        act_date = act.timestamp.strftime("%Y-%m-%d")
        act_time = act.timestamp.strftime("%H:%M")
        
        # Look at all of today's events
        if act_date == today_str:
            
            # --- DIAGNOSTIC PRINT ---
            # This prints the raw data to your GitHub Actions log so we can see its exact structure
            print(f"DEBUG ACTIVITY: Action={act.action} | Vars={vars(act)}")
            
            pet_name = None
            
            # Method 1: Check for direct pet_name attribute
            if getattr(act, 'pet_name', None):
                pet_name = act.pet_name
                
            # Method 2: Check if it's stored under a 'pet' attribute
            elif getattr(act, 'pet', None):
                pet_val = act.pet
                if hasattr(pet_val, 'name'):
                    pet_name = pet_val.name
                elif isinstance(pet_val, str):
                    pet_name = pet_val
                    
            # Method 3: Check if it's stored by pet_id, and match it to our cat profiles
            elif getattr(act, 'pet_id', None) or getattr(act, 'petId', None):
                pet_id = getattr(act, 'pet_id', getattr(act, 'petId', None))
                for p in pets:
                    if p.id == pet_id:
                        pet_name = p.name
                        break
            
            # If we successfully found a cat's name, log it!
            if pet_name and pet_name in daily_stats["cats"]:
                daily_stats["cats"][pet_name]["visits"] += 1
                if act_time not in daily_stats["cats"][pet_name]["times"]:
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
