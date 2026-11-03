"""Configuration locale et variables de l’hébergement."""
import os
from dotenv import load_dotenv

load_dotenv()
COOKIE_NAME = "csv_check_session"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
SESSION_DAYS = 7


def email_config() -> tuple[str, str, str]:
    return (
        os.getenv("RESEND_API_KEY", ""),
        os.getenv("EMAIL_FROM", ""),
        os.getenv("APP_URL", "").rstrip("/"),
    )
