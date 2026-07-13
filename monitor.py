#!/usr/bin/env python3
"""
Realtime terminal monitor untuk scraping task.
Usage: python monitor.py [task_id]
   Atau: python monitor.py  (akan listen semua tasks)
"""
import sys
import json
import time
import redis
from datetime import datetime
from collections import defaultdict

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.live import Live
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


console = Console() if HAS_RICH else None

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

LEVEL_COLORS = {
    "info": BLUE,
    "success": GREEN,
    "warning": YELLOW,
    "error": RED,
    "data": CYAN,
}

LEVEL_ICONS = {
    "info": "ℹ",
    "success": "✓",
    "warning": "⚠",
    "error": "✗",
    "data": "►",
}


class TaskState:
    def __init__(self, task_id):
        self.task_id = task_id
        self.keyword = ""
        self.location = ""
        self.category = ""
        self.status = "unknown"
        self.progress = 0
        self.total_found = 0
        self.scraped_results = 0
        self.error_message = ""
        self.logs = []
        self.businesses = []
        self.started_at = None
        self.completed_at = None

    def update_from_dict(self, d):
        self.keyword = d.get("keyword", self.keyword)
        self.location = d.get("location", self.location)
        self.category = d.get("category", self.category)
        self.status = d.get("status", self.status)
        self.progress = d.get("progress_percent", self.progress)
        self.total_found = d.get("total_results", self.total_found)
        self.scraped_results = d.get("scraped_results", self.scraped_results)
        self.error_message = d.get("error_message", self.error_message)
        if d.get("started_at"):
            self.started_at = d["started_at"]
        if d.get("completed_at"):
            self.completed_at = d["completed_at"]


def parse_log_message(message):
    """Parse log message like '[1/7] RSUD dr. Soeselo | ☎ 0283-491016 | ⭐ 4.5'"""
    data = {"name": "", "phone": "", "rating": "", "address": ""}
    try:
        parts = message.split("|")
        for part in parts:
            part = part.strip()
            if "☎" in part:
                data["phone"] = part.replace("☎", "").strip()
            elif "⭐" in part:
                data["rating"] = part.replace("⭐", "").strip()
            elif part.startswith("["):
                idx_end = part.find("]")
                if idx_end > 0:
                    data["name"] = part[idx_end + 1:].strip()
            else:
                if not data["name"]:
                    data["name"] = part.strip()
    except Exception:
        data["name"] = message
    return data


def progress_bar(pct, width=30):
    filled = int(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct:.0f}%"


def print_plain(tasks):
    """Plain text output (no rich)"""
    print("\033[2J\033[H", end="")
    for task_id, state in tasks.items():
        print(f"{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}Task #{state.task_id}{RESET} | {state.status.upper()}")
        print(f"  Keyword : {state.keyword}")
        print(f"  Lokasi  : {state.location}")
        print(f"  Kategori: {state.category}")
        print(f"  Progress: {progress_bar(state.progress)}")
        print(f"  Data    : {state.scraped_results} tersimpan / {state.total_found} ditemukan")
        if state.error_message:
            print(f"  Error   : {RED}{state.error_message}{RESET}")
        print(f"  {'-'*56}")
        for log in state.logs[-20:]:
            ts = log.get("ts", "")
            level = log.get("level", "info")
            msg = log.get("message", "")
            color = LEVEL_COLORS.get(level, "")
            icon = LEVEL_ICONS.get(level, "·")
            print(f"  {DIM}{ts}{RESET} {color}{icon} {msg}{RESET}")
        if state.status in ("completed", "failed"):
            print(f"\n  {GREEN if state.status == 'completed' else RED}{'SELESAI' if state.status == 'completed' else 'GAGAL'}{RESET}")
    print(f"\n{DIM}Tekan Ctrl+C untuk keluar{RESET}", end="", flush=True)


def build_rich_layout(tasks):
    """Build rich renderable for live display"""
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text

    panels = []
    for task_id, state in tasks.items():
        # Header
        status_color = {
            "running": "yellow", "completed": "green",
            "failed": "red", "cancelled": "red",
        }.get(state.status, "white")

        header = Text()
        header.append(f"Task #{state.task_id} ", style="bold")
        header.append(f"• {state.keyword} ", style="bold white")
        header.append(f"• {state.location}", style="dim")
        header.append(f"\n{state.category} ", style="dim")
        header.append(f"• {state.status.upper()}", style=f"bold {status_color}")

        # Progress
        bar = progress_bar(state.progress, 25)
        stats = f"Data: {state.scraped_results} tersimpan / {state.total_found} ditemukan"
        if state.error_message:
            stats += f"\nError: {state.error_message}"

        # Log table
        log_table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", padding=(0, 1))
        log_table.add_column("Waktu", width=8, style="dim")
        log_table.add_column("Level", width=7)
        log_table.add_column("Pesan", min_width=40)

        for log in state.logs[-15:]:
            level = log.get("level", "info")
            msg = log.get("message", "")
            ts = log.get("ts", "")[-8:]
            icon = LEVEL_ICONS.get(level, "·")
            lvl_style = {
                "info": "blue", "success": "green",
                "warning": "yellow", "error": "red", "data": "cyan",
            }.get(level, "white")
            log_table.add_row(ts, Text(f"{icon} {level}", style=lvl_style), msg)

        content = Text()
        content.append_text(header)
        content.append(f"\n\n{bar}\n{stats}\n", style="white")

        panel = Panel(
            content,
            title=f"[bold]Scraping Monitor[/bold]",
            border_style=status_color,
            padding=(1, 2),
        )
        panels.append(panel)

    if not panels:
        return Panel("[dim]Menunggu task...[/dim]", title="Scraping Monitor", border_style="blue")

    from rich.console import Group
    from rich.table import Table as RichTable

    log_table = None
    for task_id, state in tasks.items():
        if state.logs:
            log_table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", padding=(0, 1), expand=True)
            log_table.add_column("Waktu", width=8, style="dim")
            log_table.add_column("Level", width=8)
            log_table.add_column("Pesan", min_width=50, ratio=3)
            for log in state.logs[-20:]:
                level = log.get("level", "info")
                msg = log.get("message", "")
                ts = log.get("ts", "")[-8:]
                icon = LEVEL_ICONS.get(level, "·")
                lvl_style = {
                    "info": "blue", "success": "green",
                    "warning": "yellow", "error": "red", "data": "cyan",
                }.get(level, "white")
                log_table.add_row(ts, Text(f"{icon} {level}", style=lvl_style), msg)

    items = panels
    if log_table:
        items.append(log_table)

    return Group(*items)


def main():
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    target_task = int(sys.argv[1]) if len(sys.argv) > 1 else None

    tasks = {}
    pubsub = r.pubsub()

    if target_task:
        channels = [f"task:{target_task}", f"task:{target_task}:logs"]
    else:
        channels = ["task:*"]

    for ch in channels:
        pubsub.psubscribe(ch)

    if HAS_RICH:
        console.print(Panel(
            f"[bold green]Scraping Monitor[/bold green]\n"
            f"[dim]Listening to Redis pub/sub channels...[/dim]\n"
            f"[dim]Task: {'#' + str(target_task) if target_task else 'ALL'}[/dim]",
            border_style="green"
        ))
    else:
        print(f"{GREEN}{BOLD}Scraping Monitor{RESET}")
        print(f"Listening... Task: {'#' + str(target_task) if target_task else 'ALL'}")

    last_render = time.time()

    try:
        for message in pubsub.listen():
            if message["type"] not in ("message", "pmessage"):
                continue

            channel = message["channel"]
            try:
                data = json.loads(message["data"])
            except (json.JSONDecodeError, TypeError):
                continue

            # Determine task_id from channel
            if channel.startswith("task:") and ":logs" in channel:
                tid = int(channel.split(":")[1])
            elif channel.startswith("task:"):
                tid = int(channel.split(":")[1].replace(":logs", ""))
            else:
                continue

            if target_task and tid != target_task:
                continue

            if tid not in tasks:
                tasks[tid] = TaskState(tid)

            state = tasks[tid]

            # Handle progress updates
            if ":logs" not in channel:
                state.update_from_dict(data)
            else:
                # Handle log messages
                level = data.get("level", "info")
                msg = data.get("message", "")
                ts = data.get("timestamp", datetime.now().isoformat())[-19:]
                state.logs.append({"level": level, "message": msg, "ts": ts})

                # Parse business data from data-level logs
                if level == "data":
                    parsed = parse_log_message(msg)
                    if parsed["name"]:
                        state.businesses.append(parsed)

            # Throttle rendering
            now = time.time()
            if now - last_render >= 0.5:
                last_render = now
                if HAS_RICH:
                    console.clear()
                    layout = build_rich_layout(tasks)
                    console.print(layout)
                else:
                    print_plain(tasks)

    except KeyboardInterrupt:
        if HAS_RICH:
            console.print("\n[dim]Monitor stopped.[/dim]")
        else:
            print(f"\n{DIM}Monitor stopped.{RESET}")
    finally:
        pubsub.unsubscribe()
        pubsub.close()


if __name__ == "__main__":
    main()
