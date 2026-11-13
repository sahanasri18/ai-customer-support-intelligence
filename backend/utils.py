"""
Ticket numbering utility.
"""
import random
import string
from datetime import datetime


def generate_ticket_number() -> str:
    """Generate a unique ticket number like TKT-20261110-XXXX."""
    today = datetime.utcnow().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"TKT-{today}-{suffix}"


URGENT_KEYWORDS = [
    "urgent", "emergency", "critical", "asap", "immediately",
    "broken", "outage", "down", "not working", "data loss",
    "security breach", "hack", "compromised", "payment failed",
    "cannot login", "account locked",
]


def is_urgent_rule_based(subject: str, description: str) -> bool:
    """Rule-based urgent detection using keyword matching."""
    text = (subject + " " + description).lower()
    return any(kw in text for kw in URGENT_KEYWORDS)
