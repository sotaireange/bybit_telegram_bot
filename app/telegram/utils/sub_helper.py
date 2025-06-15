from datetime import datetime,timezone,timedelta


from app.db.models import User


def get_sub_days(user:User) -> timedelta:
    return (user.sub_until-datetime.now(timezone.utc))