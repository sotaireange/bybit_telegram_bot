from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
from dateutil.relativedelta import relativedelta
from app.db.models import User

class TimeSplitter:
    def __init__(self, user: User, now: Optional[datetime] = None):
        self.first_day = user.first_day
        self.last_sub_day = user.last_sub_time
        self.now = now or datetime.now(timezone.utc)


    def get_recent_months(self, months_back: int) -> List[Dict[str, datetime]]:
        months = [self._get_month_bounds(i) for i in range(months_back)]
        return self._filter_months(months)

    def get_recent_weeks(self, months_back: int=3, use_last_sub_day: bool = False) -> List[List[Dict[str, datetime]]]:
        if use_last_sub_day:
            months = self._get_months_from_last_sub_day()
        else:
            months = self.get_recent_months(months_back)
        return [self._split_into_weeks(month) for month in months]

    def _get_month_bounds(self, months_ago: int) -> Dict[str, datetime]:
        year = self.now.year
        month = self.now.month - months_ago

        while month <= 0:
            month += 12
            year -= 1

        first_day = datetime(year, month, 1, tzinfo=timezone.utc)

        if month == 12:
            next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        last_day = next_month - timedelta(seconds=1)

        return {
            "startTime": first_day,
            "endTime": last_day
        }

    def _filter_months(self, months: List[Dict[str, datetime]]) -> List[Dict[str, datetime]]:
        return [
            {
                'startTime': max(month['startTime'], self.first_day),
                'endTime': month['endTime']
            }
            for month in months
            if month['endTime'] > self.first_day
        ]

    def _split_into_weeks(self, month_bounds: Dict[str, datetime]) -> List[Dict[str, datetime]]:
        start = month_bounds["startTime"]
        end = month_bounds["endTime"]
        chunks = []
        current_start = start

        while current_start <= end:
            if current_start > self.now:
                break

            current_end = current_start + timedelta(days=6)
            current_end = min(current_end, end, self.now)

            chunks.append({
                "startTime": current_start,
                "endTime": current_end
            })

            current_start = current_end + timedelta(seconds=1)

        return chunks


    def _get_months_from_last_sub_day(self) -> List[Dict[str, datetime]]:
        end_date = self.now
        result = []
        current_start = self.last_sub_day

        while current_start <= end_date:
            next_month = current_start + relativedelta(months=1)
            current_end = next_month - timedelta(days=1)

            if current_end > end_date:
                current_end = end_date

            result.append({
                'startTime': current_start,
                'endTime': current_end
            })

            current_start = next_month

        return result


    def get_time_one_day(self) -> List[Dict[str, datetime]]:
        msk_tz=timezone(timedelta(hours=3))
        now=datetime.now(msk_tz)
        to_date=datetime(year=now.year,month=now.month,day=now.day,hour=18,tzinfo=msk_tz)
        from_date=to_date-timedelta(days=1)
        return [{'startTime': from_date,
                 'endTime': to_date}]
