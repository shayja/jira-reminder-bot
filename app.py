import os
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Set

import aiohttp
from dotenv import load_dotenv
import pytz

# =========================
# Config
# =========================

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "notified_state.json"
CHECK_INTERVAL_SECONDS = 1800  # 30 minutes
ISRAEL_TZ = pytz.timezone("Asia/Jerusalem")

JQL = """
status IN (
  "Ready For Development", 
  "CheckedIn-Pushed", 
  "In Development", 
  "READY FOR DEV QA", 
  "Approved In Dev Environment"
)
AND created >= startOfMonth("-12")
AND project IN ("Fizikal - EzShape")
AND assignee WAS currentUser()
AND (
  labels IS EMPTY
  OR originalEstimate IS EMPTY
  OR originalEstimate <= 0
  OR sprint IS EMPTY
  OR "Project Fizikal" IS EMPTY
)
ORDER BY updated ASC
"""

# =========================
# Logging
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# =========================
# Utilities
# =========================

def is_work_hours() -> bool:
    now = datetime.now(ISRAEL_TZ)
    return 8 <= now.hour < 20

def load_state() -> Set[str]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            logger.error(f"Failed loading state: {e}")
    return set()

def save_state(state: Set[str]) -> None:
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(list(state), f)
    except Exception as e:
        logger.error(f"Failed saving state: {e}")

# =========================
# Async Jira Client
# =========================

class JiraClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def search_issues(self) -> List[Dict]:
        url = f"{JIRA_URL}/rest/api/3/search/jql"

        async with self.session.post(
            url,
            json={
                "jql": JQL,
                "maxResults": 50,
                "fields": ["summary"]
            }
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("issues", [])

# =========================
# Async Telegram Notifier
# =========================

class TelegramNotifier:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    async def send(self, issues: List[Dict]) -> None:
        if not issues:
            return

        if not is_work_hours():
            logger.info("Outside work hours. Skipping notification.")
            return

        message = "⚠️ Jira tasks need updating:\n\n"

        for issue in issues:
            key = issue["key"]
            summary = issue["fields"].get("summary", "No summary")
            issue_url = f"{JIRA_URL}/browse/{key}"
            message += f"• {key}: {summary}\n{issue_url}\n\n"

        async with self.session.post(
            self.url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            }
        ) as response:
            response.raise_for_status()

        logger.info(f"Telegram sent ({len(issues)} issues).")

# =========================
# Monitor
# =========================

class JiraMonitor:
    def __init__(self, jira: JiraClient, notifier: TelegramNotifier):
        self.jira = jira
        self.notifier = notifier
        self.notified_tasks = load_state()

    async def check(self):
        logger.info("Checking Jira...")
        try:
            issues = await self.jira.search_issues()

            if not issues:
                logger.info("All clean.")
                self.notified_tasks.clear()
                save_state(self.notified_tasks)
                return

            current_keys = {issue["key"] for issue in issues}

            new_issues = [
                issue for issue in issues
                if issue["key"] not in self.notified_tasks
            ]

            if new_issues:
                await self.notifier.send(new_issues)
                for issue in new_issues:
                    self.notified_tasks.add(issue["key"])
                save_state(self.notified_tasks)

            self.notified_tasks.intersection_update(current_keys)
            save_state(self.notified_tasks)

        except Exception as e:
            logger.error(f"Error during check: {e}")

# =========================
# Scheduler Loop
# =========================

async def scheduler_loop(monitor: JiraMonitor):
    while True:
        await monitor.check()
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

# =========================
# Main
# =========================

async def main():
    auth = aiohttp.BasicAuth(EMAIL, API_TOKEN)

    async with aiohttp.ClientSession(auth=auth) as session:
        jira = JiraClient(session)
        notifier = TelegramNotifier(session)
        monitor = JiraMonitor(jira, notifier)

        await scheduler_loop(monitor)

if __name__ == "__main__":
    asyncio.run(main())