import asyncio
import logging
import aiohttp
import os
from config import EMAIL, API_TOKEN
from state_manager import load_state, save_state
from clients.jira import JiraClient
from clients.telegram import TelegramNotifier

# =========================
# Logging
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# =========================
# Monitor
# =========================

class JiraMonitor:
    def __init__(self, jira: JiraClient, notifier: TelegramNotifier):
        self.jira = jira
        self.notifier = notifier
        self.notified_tasks = load_state()

    async def check(self):
        logger.info("Starting Jira check...")
        try:
            issues = await self.jira.search_issues()

            if not issues:
                logger.info("All clean. Clearing state.")
                self.notified_tasks.clear()
                save_state(self.notified_tasks)
                return

            current_keys = {issue["key"] for issue in issues}

            new_issues = [
                issue for issue in issues
                if issue["key"] not in self.notified_tasks
            ]

            if new_issues:
                logger.info(f"Found {len(new_issues)} new issues to notify.")
                await self.notifier.send(new_issues)
                for issue in new_issues:
                    self.notified_tasks.add(issue["key"])
            else:
                logger.info(f"{len(issues)} incomplete tasks found (all previously notified).")

            # Cleanup resolved tasks from state (if they are no longer in the 'incomplete' list)
            self.notified_tasks.intersection_update(current_keys)
            save_state(self.notified_tasks)
            logger.info("Check complete and state updated.")

        except Exception as e:
            logger.error(f"Error during check: {e}")

# =========================
# Main
# =========================

async def main():
    # It is good practice to ensure sessions are closed properly in serverless environments
    auth = aiohttp.BasicAuth(EMAIL, API_TOKEN)

    async with aiohttp.ClientSession(auth=auth) as session:
        jira = JiraClient(session)
        notifier = TelegramNotifier(session)
        monitor = JiraMonitor(jira, notifier)

        # We call check() directly instead of the scheduler_loop.
        # GitHub Actions handles the "scheduling" via the cron in your YAML.
        await monitor.check()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Jira Bot shutting down...")
