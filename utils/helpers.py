from datetime import datetime
from config import ISRAEL_TZ

def is_work_hours() -> bool:
    now = datetime.now(ISRAEL_TZ)
    return 8 <= now.hour < 20
