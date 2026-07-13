import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from utils.helpers import clean_text, extract_phone, extract_rating, extract_review_count
from utils.logger import get_logger

logger = get_logger("parser")


class MapParser:
    def parse_business_detail(self, driver) -> dict:
        data = {}

        data["name"] = self._get_name(driver)
        data["category"] = self._get_category(driver)
        data["address"] = self._get_field(driver, [
            'button[data-item-id="address"]',
            'div[data-item-id="address"]',
            'div[data-tooltip*="alamat"]',
            'div[data-tooltip*="address"]',
        ])
        data["phone"] = self._get_phone(driver)
        data["website"] = self._get_website(driver)
        data["rating"] = self._get_rating(driver)
        data["review_count"] = self._get_reviews(driver)
        data["operating_hours"] = self._get_hours(driver)
        data["google_maps_url"] = driver.current_url
        data["place_id"] = self._get_place_id(driver)

        lat, lng = self._get_coords(driver)
        data["latitude"] = lat
        data["longitude"] = lng

        return data

    def _get_name(self, driver) -> str:
        selectors = [
            'h1.DUwDvf',
            'h1[class*="qBF1Pd"]',
            'h1',
            'div.lMbq3e h1',
        ]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                text = clean_text(el.text)
                if text:
                    return text
            except Exception:
                continue
        return ""

    def _get_category(self, driver) -> str:
        selectors = [
            'button[jsaction*="category"]',
            'span.DkEaL',
            'span.fontBodyMedium',
        ]
        for sel in selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    text = clean_text(el.text)
                    if text and len(text) < 100:
                        return text
            except Exception:
                continue

        try:
            meta = driver.find_element(By.CSS_SELECTOR, 'meta[itemprop="name"]')
            content = meta.get_attribute("content") or ""
            if content:
                return content
        except Exception:
            pass
        return ""

    def _get_field(self, driver, selectors: list) -> str:
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                aria = el.get_attribute("aria-label")
                if aria:
                    return clean_text(aria)
                text = clean_text(el.text)
                if text:
                    return text
            except Exception:
                continue
        return ""

    def _get_phone(self, driver) -> str:
        selectors = [
            'button[data-item-id*="phone"]',
            'div[data-item-id*="phone"]',
            'button[data-tooltip*="telepon"]',
            'button[data-tooltip*="phone"]',
        ]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                aria = el.get_attribute("aria-label") or ""
                text = clean_text(el.text)
                raw = aria if aria else text
                phone = extract_phone(raw)
                if phone:
                    return phone
            except Exception:
                continue

        try:
            all_buttons = driver.find_elements(By.CSS_SELECTOR, 'button')
            for btn in all_buttons:
                aria = btn.get_attribute("aria-label") or ""
                if "phone" in aria.lower() or "telepon" in aria.lower():
                    phone = extract_phone(aria)
                    if phone:
                        return phone
        except Exception:
            pass
        return ""

    def _get_website(self, driver) -> str:
        selectors = [
            'a[data-item-id="authority"]',
            'div[data-item-id="authority"] a',
            'a[data-tooltip*="website"]',
        ]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                href = el.get_attribute("href")
                if href and "google.com" not in href:
                    return href
            except Exception:
                continue
        return ""

    def _get_rating(self, driver) -> float:
        selectors = [
            'div.F7nice span[aria-hidden="true"]',
            'span.ZmwIEB span[aria-hidden="true"]',
            'div.fontDisplayLarge',
        ]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                return extract_rating(el.text)
            except Exception:
                continue
        return 0.0

    def _get_reviews(self, driver) -> int:
        selectors = [
            'div.F7nice span[aria-label]',
            'span.ZmwIEB span[aria-label]',
        ]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                label = el.get_attribute("aria-label") or el.text
                count = extract_review_count(label)
                if count > 0:
                    return count
            except Exception:
                continue

        try:
            els = driver.find_elements(By.CSS_SELECTOR, 'div.F7nice span')
            for el in els:
                text = el.text.strip()
                if "(" in text:
                    match = re.search(r"\(([\d.,]+)\)", text)
                    if match:
                        return extract_review_count(match.group(1))
        except Exception:
            pass
        return 0

    def _get_hours(self, driver) -> str:
        selectors = [
            'div[aria-label*="jam"]',
            'div[aria-label*="hour"]',
            'div[aria-label*="Buka"]',
            'div[aria-label*="Open"]',
            'table.eK4R0e',
        ]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                aria = el.get_attribute("aria-label")
                if aria:
                    return clean_text(aria)
                text = clean_text(el.text)
                if text:
                    return text
            except Exception:
                continue
        return ""

    def _get_place_id(self, driver) -> str:
        try:
            match = re.search(r"/maps/place/[^/]+/@.*?/data=.*?!1s(.*?)!", driver.current_url)
            if match:
                return match.group(1)
        except Exception:
            pass

        try:
            match = re.search(r"1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)", driver.current_url)
            if match:
                return match.group(1)
        except Exception:
            pass
        return ""

    def _get_coords(self, driver):
        try:
            match = re.search(r"!3d([-\d.]+)!4d([-\d.]+)", driver.current_url)
            if match:
                return float(match.group(1)), float(match.group(2))
        except Exception:
            pass
        return None, None
