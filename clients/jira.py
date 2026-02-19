import aiohttp
from typing import List, Dict
from config import JIRA_URL, JQL

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
