import os
import json
import asyncio
from pylitterbot import Account

DATA_FILE = "data.json"

async def main():
    account = Account()
    await account.connect(
        username=os.environ["WHISKER_EMAIL"], 
        password=os.environ["WHISKER_PASSWORD"], 
        load_robots=True
    )

    try:
        if hasattr(account, 'load_pets'): await account.load_pets()
        elif hasattr(account, 'get_pets'): await account.get_pets()
    except Exception as e:
        print(f"Warning: Could not fetch pet profiles: {e}")

    # (Log history logic remains same as before...)
    existing_logs = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                old_data = json.load(f)
                existing_logs = old_data.get("logs", []) if isinstance(old_data, dict) else old_data
            except: existing_logs = []

    # [Robot Metadata extraction code here...]
    robot_metadata = {}
    for robot in account.robots:
        robot_metadata = {
            "name": str(robot.name),
            "is_online": getattr(robot, "is_online", "Unknown"),
            "litter_level": getattr(robot, "litter_level", "Unknown"),
            "cycle_count": getattr(robot, "cycle_count", "Unknown")
        }

    # Extract Pet Profiles (NEW: Adding Age and Last Visit)
    pet_profiles = []
    for pet in account.pets:
        data = getattr(pet, "_data", {})
        history = data.get("weightHistory", [])
        
        # Get the most recent timestamp if history exists
        last_visit = history[-1].get("timestamp") if history else None
        
        pet_profiles.append({
            "name": str(data.get("name", "Unknown")),
            "age": data.get("age", 0),
            "latest_weight": str(data.get("lastWeightReading") or data.get("weight", "Unknown")),
            "profile_pic": str(data.get("s3ImageURL", "")),
            "last_visit": last_visit
        })

    compiled_payload = {
        "robot_metadata": robot_metadata,
        "pet_profiles": pet_profiles,
        "logs": existing_logs
    }

    with open(DATA_FILE, "w") as f:
        json.dump(compiled_payload, f, indent=2)
            
    await account.disconnect()
    print("Database sync complete with detailed cat profiles.")

if __name__ == "__main__":
    asyncio.run(main())
    
