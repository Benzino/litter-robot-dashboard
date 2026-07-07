import os
import json
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from pylitterbot import Account

DATA_FILE = "data.json"

def calculate_age(birthdate_str):
    if not birthdate_str: return "Unknown"
    try:
        birthdate = datetime.strptime(birthdate_str.split(' ')[0], '%Y-%m-%d')
        today = datetime.now()
        return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
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
    except: pass

    # Load existing to append
    existing_data = {"logs": [], "pet_profiles": [], "robot_metadata": {}}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try: existing_data = json.load(f)
            except: pass

    # 1. Process Robot
    robot = account.robots[0]
    robot_metadata = {
        "name": str(robot.name),
        "is_online": robot.is_online,
        "litter_level": robot.litter_level,
        "waste_level": robot.waste_drawer_level,
        "cycle_count": robot.cycle_count
    }

    # 2. Process Logs (Deduplicate)
    history = await robot.get_activity_history()
    existing_timestamps = {log['timestamp'] for log in existing_data.get("logs", [])}
    new_logs = existing_data.get("logs", [])
    
    for event in history:
        ts = str(event.timestamp)
        if ts not in existing_timestamps:
            new_logs.append({
                "timestamp": ts,
                "event": str(event.action),
                "robot": str(robot.name),
                "weight": getattr(event, 'pet_weight', 0) / 2.20462 if hasattr(event, 'pet_weight') else 0,
                "pet_name": getattr(event, 'pet', 'Unknown')
            })

    # 3. Process Pet Profiles
    pet_profiles = []
    today = datetime.now().date()
    
    for pet in account.pets:
        data = getattr(pet, "_data", {})
        # Stats
        pet_logs = [l for l in new_logs if l.get('pet_name') == data.get('name')]
        visits_today = len([l for l in pet_logs if datetime.fromisoformat(l['timestamp'].replace('Z', '')).date() == today])
        
        # Calculate Average
        if pet_logs:
            start_date = datetime.fromisoformat(pet_logs[0]['timestamp'].replace('Z', '')).date()
            days_active = (today - start_date).days or 1
            avg_visits = round(len(pet_logs) / days_active, 1)
        else: avg_visits = 0

        pet_profiles.append({
            "name": str(data.get("name", "Unknown")),
            "age": calculate_age(data.get("birthday")),
            "birthday": data.get("birthday"),
            "latest_weight": round((data.get("lastWeightReading") or 0) / 2.20462, 2),
            "profile_pic": str(data.get("s3ImageURL", "")),
            "last_visit": pet_logs[-1]['timestamp'] if pet_logs else None,
            "visits_today": visits_today,
            "avg_visits": avg_visits
        })

    with open(DATA_FILE, "w") as f:
        json.dump({
            "robot_metadata": robot_metadata,
            "pet_profiles": pet_profiles,
            "logs": new_logs
        }, f, indent=2)

    await account.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
    
