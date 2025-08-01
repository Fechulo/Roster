import json
from datetime import datetime, timedelta
from pathlib import Path
from ics import Calendar, Event
import pytz

# File paths
ROSTER_FILE = Path("roster.txt")
SHIFT_FILE = Path("shift_times.json")
OUTPUT_FILE = Path("calendar.ics")

# Timezone
IRELAND = pytz.timezone("Europe/Dublin")

# Read shift times
with open(SHIFT_FILE) as f:
    shift_map = json.load(f)

# Read roster
with open(ROSTER_FILE) as f:
    lines = f.read().strip().splitlines()
    year_month = lines[0]
    shifts = lines[1]

year, month = map(int, year_month.split("-"))

# Build events
cal = Calendar()
for i, shift_code in enumerate(shifts):
    if shift_code == "R" or shift_code not in shift_map:
        continue

    start_str = shift_map[shift_code]["start"]
    end_str = shift_map[shift_code]["end"]

    day = datetime(year, month, 1) + timedelta(days=i)

    start_hour, start_min = map(int, start_str.split(":"))
    end_hour, end_min = map(int, end_str.split(":"))
    
    # Check for overnight shift
    overnight = (datetime.combine(day, datetime.min.time()).replace(hour=end_hour, minute=end_min)
                 <= datetime.combine(day, datetime.min.time()).replace(hour=start_hour, minute=start_min))
    
    start_day = day
    if overnight:
        start_day = day - timedelta(days=1)
    
    start_dt = IRELAND.localize(datetime(start_day.year, start_day.month, start_day.day, start_hour, start_min))
    end_dt = IRELAND.localize(datetime(day.year, day.month, day.day, end_hour, end_min))

    event = Event()
    event.name = f"{shift_code} Shift"
    event.begin = start_dt
    event.end = end_dt
    cal.events.add(event)

# Save ICS
with open(OUTPUT_FILE, "w") as f:
    f.writelines(cal)
