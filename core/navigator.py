import os
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from config.settings import SCRAPE_CONFIG, LOG_DIR
from utils.rate_limiter import RateLimiter
from utils.logger import get_logger

logger = get_logger("navigator")


class MapNavigator:
    def __init__(self, driver, rate_limiter: RateLimiter):
        self.driver = driver
        self.rate_limiter = rate_limiter

    def _screenshot(self, name="debug"):
        try:
            path = LOG_DIR / f"{name}_{int(time.time())}.png"
            self.driver.save_screenshot(str(path))
            logger.info(f"Screenshot saved: {path}")
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")

    def open_search(self, url: str) -> bool:
        try:
            logger.info(f"Opening: {url}")
            self.driver.get(url)
            time.sleep(5)
            self.handle_consent_dialog()
            self._screenshot("after_load")
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
            self.handle_consent_dialog()
            time.sleep(2)
            logger.info("Results loaded")
            self._screenshot("results_loaded")
            return True
        except TimeoutException:
            logger.warning("Timeout waiting for results")
            self._screenshot("timeout")
            return False

    def get_result_links(self) -> list:
        links = []

        # Retry loop: Google Maps renders <a> tags inside Nv2PK asynchronously
        for attempt in range(4):
            links = []
            try:
                nv2pk_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.Nv2PK')
                logger.info(f"Nv2PK elements: {len(nv2pk_elements)}")
                for el in nv2pk_elements:
                    try:
                        a_tags = el.find_elements(By.TAG_NAME, 'a')
                        for a in a_tags:
                            href = a.get_attribute('href')
                            if href and '/maps/place/' in href:
                                links.append(href)
                    except Exception:
                        continue
                if links:
                    links = list(set(links))
                    logger.info(f"Found {len(links)} result links (Nv2PK, attempt {attempt + 1})")
                    return links
            except Exception:
                pass

            # Fallback: querySelectorAll across whole page
            try:
                js_links = self.driver.execute_script("""
                    var results = [];
                    var anchors = document.querySelectorAll('a[href*="/maps/place/"]');
                    anchors.forEach(function(a) { results.push(a.href); });
                    return results;
                """)
                if js_links:
                    links = list(set(js_links))
                    logger.info(f"Found {len(links)} result links (JS, attempt {attempt + 1})")
                    return links
            except Exception as e:
                logger.warning(f"JS link extraction failed: {e}")

            if attempt < 3:
                wait = 2.0 * (attempt + 1)
                logger.info(f"No links on attempt {attempt + 1}, waiting {wait}s...")
                time.sleep(wait)

        # Final fallback: all <a> tags
        try:
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Total <a> tags on page: {len(all_links)}")
            for link in all_links:
                href = link.get_attribute("href")
                if href and "/maps/place/" in href:
                    links.append(href)
            if links:
                links = list(set(links))
                logger.info(f"Found {len(links)} result links (final fallback)")
                return links
        except Exception:
            pass

        logger.warning("No result links found after retries")
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
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            visible_texts = []
            for btn in all_buttons:
                try:
                    text = (btn.text or "").strip()
                    if text and btn.is_displayed():
                        visible_texts.append(text)
                except Exception:
                    pass
            logger.info(f"Visible buttons: {visible_texts}")

            has_consent = any("tetap gunakan web" in t.lower() for t in visible_texts)
            if not has_consent:
                return

            # Try Escape key first (does not change page state)
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)
            logger.info("Pressed Escape to dismiss consent")

            # Check if consent is gone
            still_visible = False
            for btn in self.driver.find_elements(By.TAG_NAME, "button"):
                try:
                    text = (btn.text or "").strip().lower()
                    if btn.is_displayed() and "tetap gunakan web" in text:
                        still_visible = True
                        break
                except Exception:
                    pass

            if still_visible:
                # Escape didn't work — click it then reload the page
                for btn in self.driver.find_elements(By.TAG_NAME, "button"):
                    try:
                        text = (btn.text or "").strip().lower()
                        if btn.is_displayed() and "tetap gunakan web" in text:
                            current_url = self.driver.current_url
                            btn.click()
                            logger.info("Clicked 'Tetap gunakan web'")
                            time.sleep(2)
                            self.driver.get(current_url)
                            time.sleep(5)
                            logger.info("Reloaded page to restore results")
                            return
                    except Exception:
                        continue
            else:
                logger.info("Consent dismissed via Escape")
        except Exception as e:
            logger.debug(f"Consent dialog handling error: {e}")
