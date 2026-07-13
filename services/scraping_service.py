import time
import json
from datetime import datetime
from celery import shared_task
import redis

from config.settings import REDIS_HOST, REDIS_PORT, REDIS_DB

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


@shared_task(bind=True, name="services.scraping_service.run_scraping")
def run_scraping(self, task_id, radius=5, center_lat=0, center_lng=0):
    from app import create_app
    from models import db
    from models.task import ScrapingTask
    from models.business import Business
    from core.browser import BrowserManager
    from core.navigator import MapNavigator
    from core.parser import MapParser
    from utils.rate_limiter import RateLimiter
    from utils.helpers import build_search_url

    app = create_app()
    with app.app_context():
        task = ScrapingTask.query.get(task_id)
        if not task:
            return {"error": "Task not found"}

        task.status = "running"
        task.started_at = datetime.utcnow()
        task.search_radius = radius
        db.session.commit()

        _publish_log(task_id, "info", "Menyambungkan ke Google Maps...")
        _publish_progress(task_id, task)

        browser = BrowserManager()
        parser = MapParser()
        rate_limiter = RateLimiter()
        navigator = None

        try:
            browser.create_driver(headless=True)
            navigator = MapNavigator(browser.driver, rate_limiter)

            url = build_search_url(task.keyword, task.location, radius, center_lat, center_lng)
            _publish_log(task_id, "info", f"URL: {url}")
            navigator.open_search(url)

            _publish_log(task_id, "success", "Terhubung ke Google Maps")
            _publish_log(task_id, "info", f"Mencari: {task.keyword} di {task.location}")

            if not navigator.wait_for_results():
                _publish_log(task_id, "error", "Tidak ada hasil ditemukan di Google Maps")
                task.status = "failed"
                task.error_message = "No results found"
                db.session.commit()
                _publish_progress(task_id, task)
                return {"error": "No results found"}

            _publish_log(task_id, "info", "Menggulir halaman hasil...")
            total = navigator.scroll_results_panel()
            links = navigator.get_result_links()
            use_card_fallback = False

            if not links:
                card_count = navigator.get_result_cards_count()
                if card_count:
                    use_card_fallback = True
                    total = card_count
                    _publish_log(task_id, "warning", f"Link hasil tidak ditemukan, pakai fallback klik {card_count} kartu hasil")
                else:
                    _publish_log(task_id, "error", "Tidak ada link/kartu hasil ditemukan setelah scroll")
                    task.status = "failed"
                    task.error_message = "No result links or cards found"
                    db.session.commit()
                    _publish_progress(task_id, task)
                    return {"error": "No result links or cards found"}

            total_results = total if use_card_fallback else len(links)
            task.total_results = total_results
            db.session.commit()
            _publish_log(task_id, "success", f"Ditemukan {total_results} hasil")
            _publish_progress(task_id, task)

            scraped_count = 0
            error_count = 0
            result_items = range(total_results) if use_card_fallback else links
            for idx, item in enumerate(result_items):
                task = ScrapingTask.query.get(task_id)
                if task.status == "cancelled":
                    _publish_log(task_id, "warning", "Task dibatalkan oleh user")
                    break

                try:
                    if use_card_fallback:
                        opened = navigator.open_result_card(idx)
                    else:
                        opened = navigator.open_place(item)
                    if not opened:
                        error_count += 1
                        _publish_log(task_id, "warning", f"[{idx+1}/{total_results}] Gagal membuka hasil")
                        continue

                    detail = parser.parse_business_detail(browser.driver)
                    detail["source_keyword"] = task.keyword
                    detail["source_location"] = task.location
                    detail["category"] = task.category
                    detail["user_id"] = task.user_id
                    detail["task_id"] = task_id

                    if detail.get("name"):
                        pid = detail.get("place_id", "")
                        existing = None
                        if pid:
                            existing = Business.query.filter_by(place_id=pid).first()

                        if existing:
                            for key in ["phone", "website", "rating", "review_count", "operating_hours", "address"]:
                                if detail.get(key) and not getattr(existing, key, None):
                                    setattr(existing, key, detail[key])
                            _publish_log(task_id, "info", f"[{idx+1}/{total_results}] Update: {detail.get('name', '')}")
                        else:
                            filtered = {k: v for k, v in detail.items() if hasattr(Business, k) and v is not None and v != ""}
                            biz = Business(**filtered)
                            db.session.add(biz)
                            _publish_log(task_id, "data", f"[{idx+1}/{total_results}] {detail.get('name', '')} | ☎ {detail.get('phone', '-')} | ⭐ {detail.get('rating', '-')}")

                        db.session.commit()
                        scraped_count += 1
                    else:
                        _publish_log(task_id, "warning", f"[{idx+1}/{total_results}] Nama kosong, skip")
                        error_count += 1

                    task.scraped_results = scraped_count
                    task.progress_percent = ((idx + 1) / total_results) * 100
                    task.current_log = f"[{idx+1}/{total_results}] {detail.get('name', '')}"
                    db.session.commit()
                    _publish_progress(task_id, task)

                    if use_card_fallback:
                        navigator.go_back_to_results()

                    rate_limiter.wait()
                except Exception as e:
                    error_count += 1
                    _publish_log(task_id, "warning", f"[{idx+1}/{total_results}] Error: {str(e)[:80]}")
                    try:
                        db.session.rollback()
                    except:
                        pass
                    if use_card_fallback:
                        try:
                            navigator.go_back_to_results()
                        except Exception:
                            pass
                    continue

            task = ScrapingTask.query.get(task_id)
            if task.status != "cancelled":
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.scraped_results = scraped_count
                task.progress_percent = 100
                db.session.commit()
                _publish_log(task_id, "success", f"Scraping selesai! {scraped_count} data tersimpan, {error_count} error.")
                _publish_progress(task_id, task)

        except Exception as e:
            task = ScrapingTask.query.get(task_id)
            if task:
                task.status = "failed"
                task.error_message = str(e)
                db.session.commit()
                _publish_log(task_id, "error", f"Fatal error: {str(e)[:100]}")
                _publish_progress(task_id, task)
        finally:
            try:
                browser.quit()
            except:
                pass

        return {"task_id": task_id, "scraped": scraped_count}


def _publish_progress(task_id, task):
    try:
        redis_client.publish(f"task:{task_id}", json.dumps(task.to_dict()))
    except Exception:
        pass


def _publish_log(task_id, level, message):
    try:
        log_data = json.dumps({
            "type": "log",
            "level": level,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        redis_client.publish(f"task:{task_id}:logs", log_data)
    except Exception:
        pass
