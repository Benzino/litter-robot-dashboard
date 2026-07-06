import os
import json
import asyncio
from datetime import datetime
from pylitterbot import Account

DATA_FILE = "data.json"

def calculate_age(birthdate_str):
    if not birthdate_str: return "Unknown"
    try:
        # Expected format from log: '2023-04-02 00:00:00.000'
        # We take just the date part before the space
        birthdate = datetime.strptime(birthdate_str.split(' ')[0], '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return age
    except:
        return "Unknown"

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

    existing_logs = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                old_data = json.load(f)
                existing_logs = old_data.get("logs", []) if isinstance(old_data, dict) else old_data
            except: existing_logs = []

    robot_metadata = {}
    for robot in account.robots:
        robot_metadata = {
            "name": str(robot.name),
            "is_online": getattr(robot, "is_online", "Unknown"),
            "litter_level": getattr(robot, "litter_level", "Unknown"),
            "cycle_count": getattr(robot, "cycle_count", "Unknown")
        }
        history = await robot.get_activity_history()
        for event in history:
            ts_str = str(event.timestamp)
            if not any(log['timestamp'] == ts_str for log in existing_logs):
                existing_logs.append({
                    "timestamp": ts_str, 
                    "event": str(event.action), 
                    "robot": str(robot.name), 
                    "weight": getattr(event, 'pet_weight', None)
                })

    existing_logs.sort(key=lambda x: x["timestamp"])

    pet_profiles = []
    for pet in account.pets:
        data = getattr(pet, "_data", {})
        history = data.get("weightHistory", [])
        last_visit = history[-1].get("timestamp") if history else None
        
        pet_profiles.append({
            "name": str(data.get("name", "Unknown")),
            "age": calculate_age(data.get("birthday")),
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
    print("Database sync complete with calculated age.")

if __name__ == "__main__":
    asyncio.run(main())
    
