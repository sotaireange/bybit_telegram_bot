from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    BOT_TOKEN: str = '7426379906:AAEtlBFa6Irkz0OJjgHYK63NCw81Zud0H3w'
    #ADMIN_IDS: List[int]

    #PAYMENT_API: List[str]

    API_RETRY: int = 1

    FORMAT_CONSOLE_LOG: str = "%(name)s|%(funcName)s| | %(message)s"
    FORMAT_FILE_LOG: str = "%(asctime)s %(levelname)s %(name)s [%(module)s.%(funcName)s(%(lineno)d)] | %(message)s"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr
    DB_NAME: str = "bybit_test"


    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    REDIS_PASSWORD: SecretStr | None = None



    model_config = SettingsConfigDict(env_file_encoding="utf-8")


    @property
    def DB_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        password = f":{self.REDIS_PASSWORD.get_secret_value()}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"



settings = Settings()