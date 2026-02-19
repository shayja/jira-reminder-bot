import os
from dotenv import load_dotenv
import pytz

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
