import os
import json
import asyncio
from pylitterbot import Account

DATA_FILE = "data.json"

async def main():
    # 1. Connect to Whisker
    account = Account()
    await account.connect(
        username=os.environ["WHISKER_EMAIL"], 
        password=os.environ["WHISKER_PASSWORD"], 
        load_robots=True
    )

    # 2. Explicitly fetch the app's cat profiles
    try:
        await account.get_pets()
    except Exception as e:
        print(f"Warning: Could not fetch pet profiles: {e}")

    # 3. Setup internal file layout structure safely migrating old lists
    existing_logs = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                old_data = json.load(f)
                if isinstance(old_data, dict):
                    existing_logs = old_data.get("logs", [])
                elif isinstance(old_data, list):
                    existing_logs = old_data
            except (json.JSONDecodeError, TypeError):
                existing_logs = []

    existing_timestamps = {log["timestamp"] for log in existing_logs}

    # 4. Pull Current Hardware Metrics (Latest Snapshot)
    robot_metadata = {}
    for robot in account.robots:
        # Save structural details for the primary robot
        robot_metadata = {
            "name": str(robot.name),
            "is_online": getattr(robot, "is_online", "Unknown"),
            "litter_level": getattr(robot, "litter_level", "Unknown"),
            "cycle_count": getattr(robot, "cycle_count", "Unknown"),
            "status_text": str(getattr(robot, "status_text", "Normal"))
        }
        
        # Pull incoming event streams
        history = await robot.get_activity_history()
        for event in history:
            ts_str = str(event.timestamp)
            if ts_str not in existing_timestamps:
                weight = event.pet_weight if hasattr(event, 'pet_weight') and event.pet_weight else None
                existing_logs.append({
                    "timestamp": ts_str,
                    "event": str(event.action),
                    "robot": str(robot.name),
                    "weight": weight
                })

    # Sort timeline records chronologically
    existing_logs.sort(key=lambda x: x["timestamp"])

    # 5. Compile App Cat Profiles
    pet_profiles = []
    if hasattr(account, "pets") and account.pets:
        for pet in account.pets:
            pet_profiles.append({
                "name": str(getattr(pet, "name", "Unknown Cat")),
                "latest_weight": getattr(pet, "weight", "Unknown")
            })

    # 6. Package everything into unified dictionary layout
    compiled_payload = {
        "robot_metadata": robot_metadata,
        "pet_profiles": pet_profiles,
        "logs": existing_logs
    }

    with open(DATA_FILE, "w") as f:
        json.dump(compiled_payload, f, indent=2)
            
    await account.disconnect()
    print("Database sync complete with advanced telemetry and cat profiles.")

if __name__ == "__main__":
    asyncio.run(main())
    
