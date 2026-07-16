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

    @staticmethod
    def _dedupe_preserve_order(items: list) -> list:
        seen = set()
        ordered = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    def _extract_href_links(self) -> list:
        """Extract place URLs from <a href> anchors (older Google Maps layouts)."""
        links = []

        # Anchor-based layout: <a class="hfpxzc" href="/maps/place/...">
        try:
            js_links = self.driver.execute_script("""
                var results = [];
                var scope = document.querySelector('div[role="feed"]') || document;
                var anchors = scope.querySelectorAll('a[href*="/maps/place/"]');
                anchors.forEach(function(a) { results.push(a.href); });
                if (results.length === 0) {
                    document.querySelectorAll('a[href*="/maps/place/"]')
                        .forEach(function(a) { results.push(a.href); });
                }
                return results;
            """)
            if js_links:
                logger.info(f"JS place anchors: {len(js_links)}")
                return self._dedupe_preserve_order(js_links)
        except Exception as e:
            logger.warning(f"JS link extraction failed: {e}")

        return self._dedupe_preserve_order(links)

    def _collect_links_by_clicking(self) -> list:
        """Newer Google Maps layout: cards are <button class="hfpxzc"> without an
        href. We must click each card to reveal its /maps/place/ URL, capture it,
        then navigate back to the results feed and continue with the next card."""
        links = []
        try:
            card_count = len(self.driver.find_elements(By.CSS_SELECTOR, "button.hfpxzc"))
        except Exception:
            card_count = 0

        if not card_count:
            return links

        logger.info(f"Collecting links by clicking {card_count} result buttons")
        seen = set()

        for idx in range(card_count):
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.hfpxzc")
                if idx >= len(buttons):
                    break
                button = buttons[idx]
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", button
                )
                time.sleep(0.4)
                self.driver.execute_script("arguments[0].click();", button)

                url = None
                for _ in range(10):
                    time.sleep(0.6)
                    current = self.driver.current_url
                    if "/maps/place/" in current:
                        url = current
                        break

                if url and url not in seen:
                    seen.add(url)
                    links.append(url)

                # Return to the results feed for the next card
                self.driver.back()
                for _ in range(10):
                    time.sleep(0.5)
                    if self.driver.find_elements(By.CSS_SELECTOR, "button.hfpxzc"):
                        break
            except StaleElementReferenceException:
                time.sleep(1)
                continue
            except Exception as e:
                logger.warning(f"Click-collect failed on card #{idx + 1}: {e}")
                try:
                    self.driver.back()
                    time.sleep(1)
                except Exception:
                    pass
                continue

        logger.info(f"Collected {len(links)} links via clicking")
        return links

    def get_result_links(self) -> list:
        # First try href-based extraction (fast, older layouts)
        for attempt in range(3):
            links = self._extract_href_links()
            if links:
                logger.info(f"Found {len(links)} result links via href (attempt {attempt + 1})")
                return links
            if attempt < 2:
                wait = 2.0 * (attempt + 1)
                logger.info(f"No href links on attempt {attempt + 1}, waiting {wait}s...")
                time.sleep(wait)

        # Newer layout: buttons without href — click each card to collect URLs
        links = self._collect_links_by_clicking()
        if links:
            return links

        logger.warning("No result links found after retries")
        return []

    def get_result_cards_count(self) -> int:
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
            count = len([card for card in cards if card.is_displayed()])
            logger.info(f"Visible result cards: {count}")
            return count
        except Exception as e:
            logger.warning(f"Could not count result cards: {e}")
            return 0

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
                current_count = len(current_links) or self.get_result_cards_count()

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

        logger.info(f"Scrolling complete: {scroll_count} scrolls, {last_count} results")
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
                current_count = len(current_links) or self.get_result_cards_count()

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

    def open_result_card(self, index: int, timeout: int = 12) -> bool:
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
            visible_cards = [card for card in cards if card.is_displayed()]
            if index >= len(visible_cards):
                logger.warning(f"Result card index out of range: {index}/{len(visible_cards)}")
                return False

            card = visible_cards[index]
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
            time.sleep(0.6)

            clicked = False
            for selector in ["a.hfpxzc", "[role='button']", "[jsaction]", "div[role='article']"]:
                try:
                    target = card.find_element(By.CSS_SELECTOR, selector)
                    self.driver.execute_script("arguments[0].click();", target)
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                self.driver.execute_script("arguments[0].click();", card)

            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf, h1, button[data-item-id='address'], div[role='main']"))
            )
            time.sleep(2)
            logger.info(f"Opened result card #{index + 1}")
            return True
        except Exception as e:
            logger.warning(f"Failed to open result card #{index + 1}: {e}")
            self._screenshot("open_card_failed")
            return False

    def go_back_to_results(self) -> bool:
        try:
            self.driver.back()
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.Nv2PK, div[role='feed']"))
            )
            time.sleep(1.5)
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
