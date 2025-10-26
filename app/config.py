from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent
DB_PATH = DATA_DIR / "bot.db"

class Settings(BaseModel):
    token: str
    admin_id: int = int(os.getenv("ADMIN_ID", 0))
    env: str = os.getenv("ENV", "dev")
    owm_key: str | None = os.getenv("OWM_API_KEY")
    ninjas_key: str | None = os.getenv("NINJAS_API_KEY")

settings = Settings(token=os.environ["TELEGRAM_TOKEN"]) # fail fast, як і було