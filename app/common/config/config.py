from pathlib import Path
from dotenv import load_dotenv
import os
from loguru import logger


class ApplicationConfig:
    def __init__(self):
        load_dotenv(Path().absolute() / f".env.{os.getenv('APP_ENV')}")
        logger.info("Env variables loaded")

    @staticmethod
    def get(key: str) -> str | None:
        return os.getenv(key)


config = ApplicationConfig()
