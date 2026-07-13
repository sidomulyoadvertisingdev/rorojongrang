import random
import time
import os
import shutil
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

try:
    from fake_useragent import UserAgent
except Exception:
    UserAgent = None

from config.settings import SCRAPE_CONFIG, CHROME_OPTIONS, VIEWPORT_SIZES
from utils.logger import get_logger

logger = get_logger("browser")

STATIC_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


class BrowserManager:
    def __init__(self):
        self.driver = None
        self.session_count = 0

    def _pick_user_agent(self) -> str:
        if UserAgent is not None:
            try:
                ua = UserAgent()
                value = getattr(ua, "random", "") or ""
                if value and "<!doctype" not in value.lower():
                    return value
            except Exception as exc:
                logger.warning(f"fake_useragent unavailable, using static UA: {exc}")
        return random.choice(STATIC_USER_AGENTS)

    def _find_chrome_binary(self) -> str:
        env_path = os.getenv("CHROME_BINARY_PATH", "").strip()
        if env_path and Path(env_path).exists():
            return env_path

        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
        return ""

    def create_driver(self, headless: bool = None) -> webdriver.Chrome:
        options = Options()

        options.add_argument(f"--user-agent={self._pick_user_agent()}")

        viewport = random.choice(VIEWPORT_SIZES)
        options.add_argument(f"--window-size={viewport[0]},{viewport[1]}")

        for arg in CHROME_OPTIONS:
            options.add_argument(arg)

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        })

        use_headless = headless if headless is not None else SCRAPE_CONFIG["headless"]
        if use_headless:
            options.add_argument("--headless=new")

        chrome_binary = self._find_chrome_binary()
        if chrome_binary:
            options.binary_location = chrome_binary
            logger.info(f"Using Chrome binary: {chrome_binary}")
        else:
            logger.warning("Chrome binary not found in common macOS locations; relying on Selenium defaults")

        chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "").strip() or shutil.which("chromedriver")
        if chromedriver_path:
            logger.info(f"Using chromedriver: {chromedriver_path}")
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            logger.warning("chromedriver not found in PATH; trying Selenium Manager fallback")
            self.driver = webdriver.Chrome(options=options)

        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            },
        )

        self.session_count += 1
        logger.info(f"Browser created (session #{self.session_count})")
        return self.driver

    def quit(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None

    def restart_if_needed(self, max_requests: int = None, headless: bool = None) -> bool:
        max_req = max_requests or SCRAPE_CONFIG["browser_restart_every"]
        if self.session_count > 0 and self.session_count % max_req == 0:
            logger.info("Restarting browser session...")
            self.quit()
            time.sleep(5)
            self.create_driver(headless=headless)
            return True
        return False
