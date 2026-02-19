import asyncio
import logging
import aiohttp
from config import EMAIL, API_TOKEN, CHECK_INTERVAL_SECONDS
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
            else:
                logger.info(
                    f"{len(issues)} incomplete tasks (already notified)."
                )

            # Cleanup resolved tasks from state
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This catches the Ctrl+C at the top level
        print("\n[!] Jira Bot shutting down...")
    except SystemExit:
        pass
