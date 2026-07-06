import os
import json
import asyncio
from datetime import datetime
from pylitterbot import Account

DATA_FILE = "data.json"

def calculate_age(birthdate_str):
    if not birthdate_str: return "Unknown"
    try:
        birthdate = datetime.strptime(birthdate_str.split(' ')[0], '%Y-%m-%d')
        today = datetime.now()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return age
    except: return "Unknown"

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
        # Capture Waste Drawer Level (percentage)
        waste_level = getattr(robot, "waste_drawer_level", None)
        
        robot_metadata = {
            "name": str(robot.name),
            "is_online": getattr(robot, "is_online", "Unknown"),
            "litter_level": getattr(robot, "litter_level", "Unknown"),
            "cycle_count": getattr(robot, "cycle_count", "Unknown"),
            "waste_level": waste_level if waste_level is not None else "Unknown"
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
        # Convert weight to Kg (assuming API provides lbs)
        raw_weight = data.get("lastWeightReading") or data.get("weight")
        weight_kg = round(raw_weight / 2.20462, 2) if isinstance(raw_weight, (int, float)) else "Unknown"
        
        # Pull Weight History for Graph
        history = data.get("weightHistory", [])
        
        pet_profiles.append({
            "name": str(data.get("name", "Unknown")),
            "age": calculate_age(data.get("birthday")),
            "latest_weight": weight_kg,
            "profile_pic": str(data.get("s3ImageURL", "")),
            "last_visit": history[-1].get("timestamp") if history else None,
            "weight_history": history # Keeping this for the graph
        })

    compiled_payload = {
        "robot_metadata": robot_metadata,
        "pet_profiles": pet_profiles,
        "logs": existing_logs
    }

    with open(DATA_FILE, "w") as f:
        json.dump(compiled_payload, f, indent=2)
            
    await account.disconnect()
    print("Database sync complete.")

if __name__ == "__main__":
    asyncio.run(main())
    
