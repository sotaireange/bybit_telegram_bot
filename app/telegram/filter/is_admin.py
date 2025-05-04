from aiogram.filters import BaseFilter
from aiogram.types import Message

admins=[6422309975,850052979,6507523361]

class Admin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        print(int(message.from_user.id) in admins)
        return int(message.from_user.id) in admins
