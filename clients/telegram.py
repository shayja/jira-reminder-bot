import aiohttp
import logging
from typing import List, Dict
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, JIRA_URL
from utils.helpers import is_work_hours

logger = logging.getLogger(__name__)

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
