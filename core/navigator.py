import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from config.settings import SCRAPE_CONFIG
from utils.rate_limiter import RateLimiter
from utils.logger import get_logger

logger = get_logger("navigator")


class MapNavigator:
    def __init__(self, driver, rate_limiter: RateLimiter):
        self.driver = driver
        self.rate_limiter = rate_limiter

    def open_search(self, url: str) -> bool:
        try:
            logger.info(f"Opening: {url}")
            self.driver.get(url)
            self.rate_limiter.wait()
            return True
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            return False

    def wait_for_results(self, timeout: int = 30) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.Nv2PK, a.hfpxzc, div[role="feed"], div.m6QErb'))
            )
            time.sleep(5)
            logger.info("Results loaded")
            return True
        except TimeoutException:
            logger.warning("Timeout waiting for results")
            return False

    def get_result_links(self) -> list:
        links = []
        selectors = [
            'a.hfpxzc',
            'a[data-value]',
            'div.Nv2PK a',
        ]
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    href = el.get_attribute("href")
                    if href and "/maps/place/" in href:
                        links.append(href)
                if links:
                    logger.info(f"Found {len(links)} result links")
                    return list(set(links))
            except Exception:
                continue

        try:
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href")
                if href and "/maps/place/" in href:
                    links.append(href)
            if links:
                links = list(set(links))
                logger.info(f"Found {len(links)} result links (fallback)")
                return links
        except Exception:
            pass

        logger.warning("No result links found")
        return []

    def scroll_results_panel(self) -> int:
        max_scrolls = SCRAPE_CONFIG["max_scroll_attempts"]
        scroll_count = 0
        last_count = 0

        feed = None
        selectors = ['div[role="feed"]', 'div.m6QErb.DxyBCb', 'div.m6QErb']
        for sel in selectors:
            try:
                feed = self.driver.find_element(By.CSS_SELECTOR, sel)
                break
            except NoSuchElementException:
                continue

        if not feed:
            logger.warning("Feed panel not found, trying window scroll")
            return self._scroll_window()

        while scroll_count < max_scrolls:
            try:
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", feed
                )
                scroll_count += 1
                time.sleep(2)

                current_links = self.get_result_links()
                current_count = len(current_links)

                if current_count == last_count and scroll_count > 3:
                    logger.info(f"No new results after scroll {scroll_count}")
                    break

                last_count = current_count
                logger.debug(f"Scroll {scroll_count}: {current_count} links")

            except StaleElementReferenceException:
                logger.warning("Stale element during scroll, re-finding feed...")
                time.sleep(2)
                for sel in selectors:
                    try:
                        feed = self.driver.find_element(By.CSS_SELECTOR, sel)
                        break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.error(f"Scroll error: {e}")
                break

        logger.info(f"Scrolling complete: {scroll_count} scrolls, {last_count} links")
        return last_count

    def _scroll_window(self) -> int:
        max_scrolls = SCRAPE_CONFIG["max_scroll_attempts"]
        scroll_count = 0
        last_count = 0

        while scroll_count < max_scrolls:
            try:
                self.driver.execute_script("window.scrollBy(0, 500)")
                scroll_count += 1
                time.sleep(2)

                current_links = self.get_result_links()
                current_count = len(current_links)

                if current_count == last_count and scroll_count > 3:
                    break

                last_count = current_count
            except Exception as e:
                logger.error(f"Window scroll error: {e}")
                break

        return last_count

    def open_place(self, url: str) -> bool:
        try:
            self.driver.get(url)
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Failed to open place: {e}")
            return False

    def go_back_to_results(self) -> bool:
        try:
            self.driver.back()
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed to go back: {e}")
            return False

    def handle_consent_dialog(self):
        try:
            consent_selectors = [
                'button[aria-label*="Accept"]',
                'button[aria-label*="Setuju"]',
                'button[aria-label*="Agree"]',
                'button:has-text("Accept")',
                'form button',
            ]
            for sel in consent_selectors:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for btn in btns:
                        text = btn.text.lower()
                        if any(w in text for w in ["accept", "setuju", "agree", "ok"]):
                            btn.click()
                            logger.info("Consent dialog dismissed")
                            time.sleep(1)
                            return
                except Exception:
                    continue
        except Exception:
            pass
