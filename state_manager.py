import json
import os
import logging
from typing import Set
from config import STATE_FILE

logger = logging.getLogger(__name__)

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
