import os
import json
import asyncio
from datetime import datetime
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
    except: pass

    # Load existing logs to avoid duplication
    existing_logs = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try: existing_logs = json.load(f).get("logs", [])
            except: pass

    robot_metadata = {}
    new_logs = existing_logs

    for robot in account.robots:
        # Capture Meta
        robot_metadata = {
            "name": str(robot.name),
            "is_online": robot.is_online,
            "litter_level": robot.litter_level,
            "waste_level": robot.waste_drawer_level,
            "cycle_count": robot.cycle_count
        }
        
        # Capture History
        history = await robot.get_activity_history()
        existing_timestamps = {log['timestamp'] for log in new_logs}
        
        for event in history:
            ts = str(event.timestamp)
            if ts not in existing_timestamps:
                # Robust extraction: Check pet_weight, then weight, then fall back to None
                weight = getattr(event, 'pet_weight', None)
                if weight is None:
                    weight = getattr(event, 'weight', None)
                
                # Only log if there is a weight, otherwise it creates messy nulls in the graph
                if weight is not None:
                    new_logs.append({
                        "timestamp": ts,
                        "event": str(event.action),
                        "weight": round(float(weight) / 2.20462, 2), # Convert to KG
                        "pet_name": getattr(event, 'pet', 'Unknown')
                    })

    # Save
    with open(DATA_FILE, "w") as f:
        json.dump({"robot_metadata": robot_metadata, "logs": new_logs, "pet_profiles": []}, f, indent=2)

    await account.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
    
