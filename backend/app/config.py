import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "jarvis.db"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Jarvis"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE.as_posix()}")
    
    # Razorpay Test Mode credentials (defaults to test mode key format)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_JarvisSandboxDemo")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "mock_secret_test_key_123")
    
    # Gemini API Key (loaded from env)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Synthetic dataset watermark
    DATASET_WATERMARK: str = "Synthetic demo dataset modelled on a small online seller’s workflow."

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
