import os
import json
import asyncio
from datetime import datetime
from pylitterbot import Account

# Ensure you have your environment variables set:
# WHISKER_EMAIL and WHISKER_PASSWORD
DATA_FILE = "data.json"

def calculate_age(birthdate_str):
    if not birthdate_str: return "Unknown"
    try:
        # Expected format: YYYY-MM-DD
        birthdate = datetime.strptime(birthdate_str.split(' ')[0], '%Y-%m-%d')
        today = datetime.now()
        return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    except: 
        return "Unknown"

async def main():
    # Connect to account
    account = Account()
    await account.connect(
        username=os.environ["WHISKER_EMAIL"], 
        password=os.environ["WHISKER_PASSWORD"], 
        load_robots=True
    )
    
    # Load pets
    try:
        if hasattr(account, 'load_pets'): await account.load_pets()
        elif hasattr(account, 'get_pets'): await account.get_pets()
    except Exception as e:
        print(f"Error loading pets: {e}")

    # Load existing history to prevent data loss
    existing_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                existing_data = json.load(f)
        except Exception:
            pass

    existing_pet_histories = {}
    for p in existing_data.get("pet_profiles", []):
        existing_pet_histories[p.get("name")] = p.get("history", [])

    # Process Robot Metadata
    robot = account.robots[0] if account.robots else None
    robot_metadata = {}
    if robot:
        print(f"--- DEBUG: Activity History ---")
        history = robot.get_activity_history()
        if history:
            # Print the most recent 3 events
            for i, event in enumerate(history[:3]):
                print(f"Event {i}: {event}")
        else:
            print("No history returned.")

        
        raw_status = getattr(robot, 'status', 'Unknown')
        status_text = raw_status.name if hasattr(raw_status, 'name') else str(raw_status)
        clean_status = status_text.replace("_", " ").title()

        robot_metadata = {
            "name": str(robot.name),
            "is_online": robot.is_online,
            "status": clean_status,
            "litter_level": robot.litter_level,
            "waste_level": getattr(robot, 'waste_drawer_level', 0),
            "cycle_count": robot.cycle_count,
            "last_seen": str(getattr(robot, 'last_seen', 'Unknown'))
        }

    # Process Pet Profiles
    pet_profiles = []
    today_date = datetime.now().date()

    for pet in account.pets:
        data = getattr(pet, "_data", {})
        pet_name = str(data.get("name", "Unknown"))
        weight_history_raw = data.get("weightHistory", [])
        
        # Clean new history from API
        clean_history = []
        for entry in weight_history_raw:
            ts = entry.get("timestamp")
            w_lbs = entry.get("weight")
            if ts and w_lbs is not None:
                clean_history.append({
                    "timestamp": ts,
                    "weight": round(float(w_lbs) / 2.20462, 2)
                })

        # Merge with existing history
        merged_dict = {}
        for entry in existing_pet_histories.get(pet_name, []):
            if entry.get("timestamp"):
                merged_dict[entry["timestamp"]] = entry
        for entry in clean_history:
            merged_dict[entry["timestamp"]] = entry
            
        final_history = list(merged_dict.values())
        final_history.sort(key=lambda x: x["timestamp"])

        # Stats calculations
        visits_today = 0
        for entry in final_history:
            try:
                dt = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                if dt.date() == today_date: visits_today += 1
            except: pass

        avg_visits = 0
        if final_history:
            try:
                start_dt = datetime.fromisoformat(final_history[0]['timestamp'].replace('Z', '+00:00'))
                days_active = (today_date - start_dt.date()).days or 1
                avg_visits = round(len(final_history) / days_active, 1)
            except: pass

        pet_profiles.append({
            "name": pet_name,
            "age": calculate_age(data.get("birthday")),
            "latest_weight": round(float(data.get("lastWeightReading", 0)) / 2.20462, 2) if data.get("lastWeightReading") else "Unknown",
            "profile_pic": str(data.get("s3ImageURL", "")),
            "last_visit": final_history[-1]['timestamp'] if final_history else None,
            "visits_today": visits_today,
            "avg_visits": avg_visits,
            "history": final_history
        })

    # Save to file
    with open(DATA_FILE, "w") as f:
        json.dump({
            "robot_metadata": robot_metadata,
            "pet_profiles": pet_profiles
        }, f, indent=2)

    await account.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
    
