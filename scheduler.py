"""
scheduler.py – Time-based access control for games.

Checks whether the current day/time is within the allowed schedule
defined per game in config.json.
"""
from datetime import datetime


def is_allowed_now(game: dict) -> bool:
    """
    Return True if the current moment is within the game's allowed schedule.

    game dict fields used:
      - allowed_days:  list of int  (0=Mon, 1=Tue, … 6=Sun)
                       default: [0,1,2,3,4,5,6]
      - allowed_hours: list of [start_hour, end_hour]  (24-h, exclusive end)
                       e.g. [[9, 22]] means 09:00 ≤ now < 22:00
                       default: [[0, 24]]
    """
    now = datetime.now()
    weekday = now.weekday()   # 0=Monday … 6=Sunday
    hour = now.hour

    # Check day
    allowed_days = game.get("allowed_days", list(range(7)))
    if weekday not in allowed_days:
        return False

    # Check hour ranges (any range that contains now is OK)
    allowed_hours = game.get("allowed_hours", [[0, 24]])
    for start, end in allowed_hours:
        if start <= hour < end:
            return True

    return False


def get_next_allowed_str(game: dict) -> str:
    """
    Return a human-readable string describing when the game is next allowed.
    Used in violation popups.
    """
    allowed_days = game.get("allowed_days", list(range(7)))
    allowed_hours = game.get("allowed_hours", [[0, 24]])

    day_names = ["월", "화", "수", "목", "금", "토", "일"]

    days_str = ""
    if len(allowed_days) == 7:
        days_str = "매일"
    elif allowed_days == [5, 6]:
        days_str = "주말"
    elif allowed_days == [0, 1, 2, 3, 4]:
        days_str = "평일"
    else:
        days_str = "/".join(day_names[d] for d in sorted(allowed_days)) + "요일"

    hours_parts = []
    for start, end in allowed_hours:
        if start == 0 and end == 24:
            hours_parts.append("종일")
        else:
            hours_parts.append(f"{start:02d}:00 ~ {end:02d}:00")
    hours_str = ", ".join(hours_parts)

    return f"{days_str} {hours_str}"
