from datetime import datetime, timedelta, timezone
from typing import Dict, Optional,List

def get_month_bounds(months_ago: int, min_start: Optional[datetime] = None) -> Dict[str, datetime]:
    now = datetime.now(timezone.utc)

    year = now.year
    month = now.month - months_ago

    while month <= 0:
        month += 12
        year -= 1

    first_day = datetime(year, month, 1, tzinfo=timezone.utc)

    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)

    last_day = next_month - timedelta(seconds=1)

    # Если указан min_start и он больше чем first_day — заменяем
    if min_start and first_day < min_start:
        first_day = min_start

    return {
        "startTime": first_day,
        "endTime": last_day
    }

def filter_months(first_day_user:datetime,months: List[Dict[str, datetime]]) -> List[Dict[str, datetime]]:
    filtered_months = []
    for month in months:
        if month['endTime'] > first_day_user:
            start = max(month['startTime'], first_day_user)
            filtered_months.append({
                'startTime': start,
                'endTime': month['endTime']
            })
    return filtered_months


def split_into_weeks(month_bounds: Dict[str, datetime]) -> List[Dict[str, datetime]]:
    start = month_bounds["startTime"]
    end = month_bounds["endTime"]
    now = datetime.now(timezone.utc)

    chunks = []
    current_start = start

    while current_start <= end:
        if current_start > now:
            break

        current_end = current_start + timedelta(days=6)
        if current_end > end:
            current_end = end
        if current_end > now:
            current_end = now

        chunks.append({
            "startTime": current_start,
            "endTime": current_end
        })

        current_start = current_end + timedelta(seconds=1)

    return chunks

def split_into_days(month_bounds: Dict[str, datetime]) -> List[Dict[str, datetime]]:
    start = month_bounds["startTime"]
    end = month_bounds["endTime"]
    now = datetime.now(timezone.utc)

    chunks = []
    current_start = start

    while current_start <= end:
        if current_start > now:
            break

        current_end = current_start + timedelta(days=1) - timedelta(seconds=1)
        if current_end > end:
            current_end = end
        if current_end > now:
            current_end = now

        chunks.append({
            "startTime": current_start,
            "endTime": current_end
        })

        current_start = current_end + timedelta(seconds=1)

    return chunks