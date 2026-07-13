import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "scraper"),
    "password": os.getenv("DB_PASSWORD", "scraper123"),
    "database": os.getenv("DB_NAME", "gmaps_scraper"),
    "charset": "utf8mb4",
}

SCRAPE_CONFIG = {
    "delay_min": int(os.getenv("SCRAPE_DELAY_MIN", 3)),
    "delay_max": int(os.getenv("SCRAPE_DELAY_MAX", 8)),
    "headless": os.getenv("HEADLESS", "false").lower() == "true",
    "max_scroll_attempts": int(os.getenv("MAX_SCROLL_ATTEMPTS", 20)),
    "browser_restart_every": int(os.getenv("BROWSER_RESTART_EVERY", 50)),
}

CHROME_OPTIONS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-extensions",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1920,1080",
]

VIEWPORT_SIZES = [
    (1920, 1080),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (1280, 720),
]

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

DATA_DIR = BASE_DIR / "data" / "output"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES_FILE = BASE_DIR / "config" / "categories.json"

GOOGLE_MAPS_BASE_URL = "https://www.google.com/maps/search"
