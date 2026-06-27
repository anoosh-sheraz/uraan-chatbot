import os
from pathlib import Path
from dotenv import load_dotenv

# Use an absolute path so the server finds .env regardless of the
# working directory uvicorn was launched from.
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")
    APP_NAME: str = "URAAN Safe Voice"


settings = Settings()
