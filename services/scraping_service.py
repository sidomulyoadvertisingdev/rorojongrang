import time
import json
from datetime import datetime
from celery import shared_task
import redis

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


@shared_task(bind=True, name="services.scraping_service.run_scraping")
def run_scraping(self, task_id, radius=5):
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

        _publish_log(task_id, "info", "Connecting to Google Maps...")
        _publish_progress(task_id, task)

        browser = BrowserManager()
        parser = MapParser()
        rate_limiter = RateLimiter()
        navigator = None

        try:
            browser.create_driver(headless=True)
            navigator = MapNavigator(browser.driver, rate_limiter)

            url = build_search_url(task.keyword, task.location, radius)
            _publish_log(task_id, "info", f"URL: {url}")
            navigator.handle_consent_dialog()
            navigator.open_search(url)
            time.sleep(3)
            navigator.handle_consent_dialog()

            _publish_log(task_id, "success", "Connected to Google Maps")
            _publish_log(task_id, "info", f"Searching: {task.keyword} {task.location}")

            if not navigator.wait_for_results():
                _publish_log(task_id, "error", "No results found on Google Maps")
                task.status = "failed"
                task.error_message = "No results found"
                db.session.commit()
                _publish_progress(task_id, task)
                return {"error": "No results found"}

            total = navigator.scroll_results_panel()
            links = navigator.get_result_links()

            if not links:
                _publish_log(task_id, "error", "No links found after scrolling")
                task.status = "failed"
                task.error_message = "No links found"
                db.session.commit()
                _publish_progress(task_id, task)
                return {"error": "No links found"}

            task.total_results = len(links)
            db.session.commit()
            _publish_log(task_id, "success", f"Found {len(links)} results")
            _publish_progress(task_id, task)

            scraped_count = 0
            for idx, link in enumerate(links):
                task = ScrapingTask.query.get(task_id)
                if task.status == "cancelled":
                    _publish_log(task_id, "warning", "Task cancelled by user")
                    break

                try:
                    navigator.open_place(link)
                    detail = parser.parse_business_detail(browser.driver)
                    detail["source_keyword"] = task.keyword
                    detail["source_location"] = task.location
                    detail["category"] = task.category
                    detail["user_id"] = task.user_id
                    detail["task_id"] = task_id

                    if detail.get("name"):
                        existing = Business.query.filter_by(place_id=detail.get("place_id")).first() if detail.get("place_id") else None
                        if existing:
                            for key in ["phone", "website", "rating", "review_count", "operating_hours"]:
                                if detail.get(key) and not getattr(existing, key, None):
                                    setattr(existing, key, detail[key])
                        else:
                            biz = Business(**{k: v for k, v in detail.items() if hasattr(Business, k)})
                            db.session.add(biz)

                        db.session.commit()
                        scraped_count += 1

                        log_entry = f"[{scraped_count}/{len(links)}] {detail.get('name', 'Unknown')}"
                        if detail.get("phone"):
                            log_entry += f" | ☎ {detail['phone']}"
                        _publish_log(task_id, "data", log_entry)

                    task.scraped_results = scraped_count
                    task.progress_percent = (scraped_count / len(links)) * 100
                    task.current_log = f"[{scraped_count}/{len(links)}] {detail.get('name', '')}"
                    db.session.commit()
                    _publish_progress(task_id, task)

                    rate_limiter.wait()
                except Exception as e:
                    _publish_log(task_id, "warning", f"Error scraping link {idx+1}: {str(e)[:50]}")
                    continue

            task = ScrapingTask.query.get(task_id)
            if task.status != "cancelled":
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.scraped_results = scraped_count
                task.progress_percent = 100
                db.session.commit()
                _publish_log(task_id, "success", f"Scraping complete! {scraped_count} data saved.")
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
            browser.quit()

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
