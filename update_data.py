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
    data["is_online"] = robot.is_online
    data["waste_drawer_level"] = getattr(robot, 'waste_drawer_level', 'Unknown')
    data["litter_level"] = getattr(robot, 'litter_level', 'Unknown')
    data["cycle_count"] = getattr(robot, 'cycle_count', 'Unknown')
    
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
            action_str = str(act.action)
            
            # Check if this activity is a recorded pet weight
            if action_str.startswith("Pet Weight Recorded"):
                try:
                    # Extract the number from "Pet Weight Recorded: 7.21 lbs"
                    weight_text = action_str.split(":")[1].replace("lbs", "").strip()
                    recorded_weight = float(weight_text)
                    
                    # Figure out which cat this is by finding the closest profile weight
                    closest_cat = None
                    smallest_diff = 999
                    
                    for pet in pets:
                        # Compare the recorded weight to the cats' baseline profiles (in lbs)
                        diff = abs(pet.weight - recorded_weight)
                        if diff < smallest_diff:
                            smallest_diff = diff
                            closest_cat = pet.name
                    
                    # Assign the visit if we found a match within a reasonable margin (e.g., 2 lbs)
                    if closest_cat and smallest_diff < 2.0:
                        if closest_cat in daily_stats["cats"]:
                            daily_stats["cats"][closest_cat]["visits"] += 1
                            if act_time not in daily_stats["cats"][closest_cat]["times"]:
                                daily_stats["cats"][closest_cat]["times"].append(act_time)
                                
                except Exception as e:
                    print(f"Skipping unparseable weight event: {e}")

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
