from typing import List,Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr




class Settings(BaseSettings):
    BOT_TOKEN: str = '7748113385:AAHFjheEl1HCZw3I_lyMpERXnFvEwBDoyvw'
    ADMIN_IDS: List[int] =[6422309975]
    DEV_ID: int = 6422309975


    BOT_MODE: str = "polling"
    WEBHOOK_URL: str = 'https://fbd7-193-34-225-69.ngrok-free.app'
    WEBHOOK_HOST: str ='0.0.0.0'
    WEBHOOK_PATH: str ='/webhook'
    WEBHOOK_PORT: int =8080

    URL_NOTIFICATION_PK: str = ''
    API_PASSWORD_PK: str = ''
    API_ID_PK :int =0
    SHOP_PK:int=0
    SHOP_PASSWORD_PK:str=''

    URL_NOTIFICATION_FK: str= 'http://127.0.0.1:8000'
    FK_API: str = ''
    FK_SECRET_1: str = ''
    FK_SECRET_2: str = ''
    FK_ID: int = 0
    FK_CURRENCY:str ='USD'
    #PAYMENT_API: List[str]

    API_RETRY: int = 1

    FORMAT_CONSOLE_LOG: str = "%(name)s|%(module)s | %(funcName)s(%(lineno)d) | %(message)s"
    FORMAT_FILE: str = "%(asctime)s %(levelname)s %(name)s [%(module)s.%(funcName)s(%(lineno)d)] | %(message)s"
    TIME_FORMAT:str='[%X %d-%m-%Y]'
    LOG_DIR:str='/logs'
    LOG_LEVEL:str='DEBUG'


    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: SecretStr ='0880'
    POSTGRES_DB: str = "bybit_test"


    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    REDIS_PASSWORD: SecretStr | None = None


    SERVICE_NAME: str='TELEGRAM'
    PROJECT_NAME:str='Bybit Telegram Trading'
    USE_BROKER: bool=True
    DROP_TABLES: bool=True




    model_config = SettingsConfigDict(env_file_encoding="utf-8")



    @property
    def DB_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_HOST
        }:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self) -> str:
        password = f":{self.REDIS_PASSWORD.get_secret_value()}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()