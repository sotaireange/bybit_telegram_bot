from datetime import datetime,timezone


from app.db.models import User


def get_sub_days(user:User):
    return (datetime.now(timezone.utc)-user.sub_until).days