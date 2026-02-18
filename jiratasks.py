import os
import json
import logging
import requests
import schedule
import time
from datetime import datetime
from typing import List, Dict, Set
from dotenv import load_dotenv
import pytz

# =========================
# Configuration
# =========================

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
EMAIL = os.getenv("JIRA_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STATE_FILE = "notified_state.json"
CHECK_INTERVAL_MINUTES = 30
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
AND assignee = currentUser()
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
# State Management
# =========================

def load_state() -> Set[str]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            logger.error(f"Failed to load state file: {e}")
    return set()

def save_state(state: Set[str]) -> None:
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(list(state), f)
    except Exception as e:
        logger.error(f"Failed to save state file: {e}")

# =========================
# Utilities
# =========================

def is_work_hours() -> bool:
    now = datetime.now(ISRAEL_TZ)
    return 8 <= now.hour < 20

# =========================
# Jira Client
# =========================

class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url
        self.auth = (email, api_token)
        self.headers = {"Content-Type": "application/json"}

    def search_issues(self, jql: str) -> List[Dict]:
        response = requests.post(
            f"{self.base_url}/rest/api/3/search/jql",
            json={
                "jql": jql,
                "maxResults": 50,
                "fields": ["summary"]
            },
            auth=self.auth,
            headers=self.headers,
            timeout=15
        )
        response.raise_for_status()
        return response.json().get("issues", [])

# =========================
# Telegram Notifier
# =========================

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send(self, issues: List[Dict]) -> None:
        if not issues:
            return

        if not is_work_hours():
            logger.info("Outside work hours, skipping notification.")
            return

        message = "⚠️ Jira tasks need updating:\n\n"

        for issue in issues:
            key = issue["key"]
            summary = issue["fields"].get("summary", "No summary")
            issue_url = f"{JIRA_URL}/browse/{key}"
            message += f"• {key}: {summary}\n{issue_url}\n\n"

        response = requests.post(
            self.url,
            json={
                "chat_id": self.chat_id,
                "text": message
            },
            timeout=10
        )

        response.raise_for_status()
        logger.info(f"Telegram notification sent ({len(issues)} issues).")

# =========================
# Monitoring Logic
# =========================

class JiraMonitor:
    def __init__(self, jira: JiraClient, notifier: TelegramNotifier):
        self.jira = jira
        self.notifier = notifier
        self.notified_tasks = load_state()

    def check(self) -> None:
        logger.info("Checking Jira for incomplete tasks...")

        try:
            issues = self.jira.search_issues(JQL)

            if not issues:
                logger.info("All good. No incomplete tasks.")
                self.notified_tasks.clear()
                save_state(self.notified_tasks)
                return

            current_keys = {issue["key"] for issue in issues}

            new_issues = [
                issue for issue in issues
                if issue["key"] not in self.notified_tasks
            ]

            if new_issues:
                self.notifier.send(new_issues)

                for issue in new_issues:
                    self.notified_tasks.add(issue["key"])

                save_state(self.notified_tasks)
            else:
                logger.info(
                    f"{len(issues)} incomplete tasks (already notified)."
                )

            # Cleanup resolved tasks from state
            self.notified_tasks.intersection_update(current_keys)
            save_state(self.notified_tasks)

        except requests.RequestException as e:
            logger.error(f"HTTP error while checking Jira: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

# =========================
# Main
# =========================

def main():
    jira = JiraClient(JIRA_URL, EMAIL, API_TOKEN)
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    monitor = JiraMonitor(jira, notifier)

    monitor.check()  # Run immediately

    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(monitor.check)

    logger.info("Jira monitor started.")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()