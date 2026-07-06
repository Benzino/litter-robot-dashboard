import os
import json
import asyncio
from datetime import datetime
from pylitterbot import Account

# File where history will be stored inside your repository
DATA_FILE = "data.json"

async def main():
    # 1. Connect to Whisker
    account = Account()
    await account.connect(
        username=os.environ["WHISKER_EMAIL"], 
        password=os.environ["WHISKER_PASSWORD"], 
        load_robots=True
    )

    # 2. Load existing data if it exists, otherwise start fresh
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                all_logs = json.load(f)
            except json.JSONDecodeError:
                all_logs = []
    else:
        all_logs = []

    # Create a set of existing timestamps to prevent duplicate entries
    existing_timestamps = {log["timestamp"] for log in all_logs}

    # 3. Pull latest history from the robot
    for robot in account.robots:
        history = await robot.get_activity_history()
        for event in history:
            ts_str = str(event.timestamp)
            
            # If we haven't logged this specific timestamp before, add it
            if ts_str not in existing_timestamps:
                weight = event.pet_weight if hasattr(event, 'pet_weight') and event.pet_weight else None
                all_logs.append({
                    "timestamp": ts_str,
                    "event": str(event.action),
                    "robot": str(robot.name),
                    "weight": weight
                })

    # Sort everything chronological (oldest to newest)
    all_logs.sort(key=lambda x: x["timestamp"])

    # 4. Save back to the JSON file
    with open(DATA_FILE, "w") as f:
        json.dump(all_logs, f, indent=2)
            
    await account.disconnect()
    print(f"Sync complete. Total logs stored: {len(all_logs)}")

if __name__ == "__main__":
    asyncio.run(main())
