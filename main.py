import sys
import argparse
import signal

from core.scraper import GoogleMapsScraper
from storage.exporter import Exporter
from storage.database import Database
from utils.logger import get_logger

logger = get_logger("main")

scraper_instance = None


_stopping = False

def signal_handler(sig, frame):
    global _stopping
    if _stopping:
        return
    _stopping = True
    logger.info("\nStopping scraper...")
    if scraper_instance:
        try:
            scraper_instance.stop()
        except Exception:
            pass
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def cmd_scrape(args):
    global scraper_instance
    scraper_instance = GoogleMapsScraper()

    try:
        scraper_instance.start()

        if args.all:
            scraper_instance.scrape_from_config()
        elif args.keyword and args.location:
            scraper_instance.scrape_custom(
                keywords=[args.keyword],
                locations=[args.location],
                category=args.category or "",
            )
        else:
            logger.info("Scraping all categories from config...")
            scraper_instance.scrape_from_config()

    finally:
        scraper_instance.stop()


def cmd_export(args):
    db = Database()
    exporter = Exporter(db)

    filepath = exporter.export(args.format)
    if filepath:
        print(f"Exported to: {filepath}")
    else:
        print("No data to export")

    db.close()


def cmd_stats(args):
    db = Database()
    count = db.get_business_count()
    print(f"Total businesses in database: {count}")
    db.close()


def cmd_test(args):
    from core.browser import BrowserManager
    from core.navigator import MapNavigator
    from utils.rate_limiter import RateLimiter

    logger.info("Testing browser...")
    browser = BrowserManager()
    driver = browser.create_driver()

    logger.info("Opening Google Maps...")
    navigator = MapNavigator(driver, RateLimiter(min_delay=1, max_delay=2))
    navigator.open_search("https://www.google.com/maps")
    navigator.handle_consent_dialog()

    logger.info("Browser test successful!")
    logger.info(f"Current URL: {driver.current_url}")

    input("Press Enter to close browser...")
    browser.quit()


def main():
    parser = argparse.ArgumentParser(
        description="Google Maps Business Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scrape --all                      # Scrape all categories
  python main.py scrape -k "toko besi" -l "Kabupaten Bandung"
  python main.py export --format csv               # Export to CSV
  python main.py export --format json              # Export to JSON
  python main.py stats                             # Show database stats
  python main.py test                              # Test browser
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    scrape_parser = subparsers.add_parser("scrape", help="Run scraper")
    scrape_parser.add_argument("--all", action="store_true", help="Scrape all categories")
    scrape_parser.add_argument("-k", "--keyword", help="Search keyword")
    scrape_parser.add_argument("-l", "--location", help="Target location")
    scrape_parser.add_argument("-c", "--category", help="Category name")

    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Export format")

    subparsers.add_parser("stats", help="Show statistics")
    subparsers.add_parser("test", help="Test browser setup")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "scrape": cmd_scrape,
        "export": cmd_export,
        "stats": cmd_stats,
        "test": cmd_test,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
