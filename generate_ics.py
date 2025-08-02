import json
from datetime import datetime, timedelta
from pathlib import Path
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
import pytz

# File paths
ROSTER_FILE = Path("roster.txt")
SHIFT_FILE = Path("shifts.json")
OUTPUT_FILE = Path("test.ics")

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
    holiday_lines = lines[2:]  # Optional extra lines for holidays

year, month, day1 = map(int, year_month.split("-"))
day = datetime(year, month, 1)

# Parse holidays
holidays = set()
for line in holiday_lines:
    if line.startswith("AL "):
        dates = line[3:].strip()
        if "-" in dates:
            start_str, end_str = dates.split("-")
            start_date = datetime.strptime(f"{start_str}/{year}", "%d/%m/%Y").date()
            end_date = datetime.strptime(f"{end_str}/{year}", "%d/%m/%Y").date()
            current_date = start_date
            while current_date <= end_date:
                holidays.add(current_date)
                current_date += timedelta(days=1)
        else:
            holiday_date = datetime.strptime(f"{dates}/{year}", "%d/%m/%Y").date()
            holidays.add(holiday_date)

# Build events
cal = Calendar()
rostered_days = set()

for i, shift_code in enumerate(shifts):
    current_day = datetime(year, month, 1) + timedelta(days=i)

    if current_day.date() in holidays:
        continue  # Skip holidays from shift allocation

    if shift_code == "R" or shift_code.upper() not in shift_map:
        continue  # Rest day or invalid code

    start_str = shift_map[shift_code.upper()]["start"]
    end_str = shift_map[shift_code.upper()]["end"]

    start_hour, start_min = map(int, start_str.split(":"))
    end_hour, end_min = map(int, end_str.split(":"))

    # Handle overnight shift logic
    overnight = (datetime.combine(current_day, datetime.min.time()).replace(hour=end_hour, minute=end_min)
                 <= datetime.combine(current_day, datetime.min.time()).replace(hour=start_hour, minute=start_min))

    start_day = current_day
    if overnight:
        start_day = current_day - timedelta(days=1)

    start_dt = IRELAND.localize(datetime(start_day.year, start_day.month, start_day.day, start_hour, start_min))
    end_dt = IRELAND.localize(datetime(current_day.year, current_day.month, current_day.day, end_hour, end_min))

    event = Event()
    event.name = shift_code
    if shift_code.isnumeric():
        event.name = "OC" + shift_code
    if shift_code.islower():
        event.name = shift_code.upper() + " (OT)"
    event.begin = start_dt
    event.end = end_dt
    cal.events.add(event)

# Recurring Day Cycle with EXDATEs
cycle_labels = [f"Day {i}" for i in range(1, 9)]
cycle_start = datetime(year, month, day1).date()

for i, label in enumerate(cycle_labels):
    first_day = cycle_start + timedelta(days=i)
    if i <= 5:
        event = Event()
        event.name = label
        event.begin = first_day
        event.make_all_day()
        event.rrule = {
            "freq": "daily",
            "interval": 8
        }
    
        # Add EXDATEs for holidays or rostered shifts that match this cycle
        for exdate in holidays.union(rostered_days):
            if (exdate - first_day).days % 8 == 0:
                # Format: EXDATE;TZID=Europe/Dublin:YYYYMMDD
                exdate_str = exdate.strftime('%Y%m%d')
                event.extra.append(
                    ContentLine(name="EXDATE", params={"VALUE": "DATE"}, value=exdate_str)
                )
    
        cal.events.add(event)

# Save ICS
with open(OUTPUT_FILE, "w") as f:
    f.writelines(cal)
