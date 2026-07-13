import random
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager

from config.settings import SCRAPE_CONFIG, CHROME_OPTIONS, VIEWPORT_SIZES
from utils.logger import get_logger

logger = get_logger("browser")
ua = UserAgent()


class BrowserManager:
    def __init__(self):
        self.driver = None
        self.session_count = 0

    def create_driver(self, headless: bool = None) -> webdriver.Chrome:
        options = Options()

        options.add_argument(f"--user-agent={ua.random}")

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

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

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
