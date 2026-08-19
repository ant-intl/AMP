"""TravelIntent — structured travel delegation model and template parser.

P0 scope: parse controlled natural language travel intent text into a
structured TravelIntent dataclass. Supports minor wording variations
(e.g. 'leaving on' / 'departing on', 'budget of no more than' / 'budget under').
Does NOT promise to understand arbitrary free-form expressions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TravelIntent:
    """Structured travel delegation intent submitted by the user."""

    origin: str
    destination: str
    departure_date: str  # ISO format "2026-10-01"
    duration_days: int
    budget_max: float
    currency: str = "USD"
    services: list[str] = field(default_factory=lambda: ["flight", "hotel"])
    # Authorization expiry stated by the user (ISO 8601 UTC, e.g.
    # "2026-10-10T23:59:59Z"). Empty when the user stated none: the mandate
    # expiry is never invented on the user's behalf.
    expiry_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Controlled natural language parser
# ---------------------------------------------------------------------------

# Month name → number mapping (full + abbreviated)
_MONTH_MAP: dict[str, int] = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Main travel intent pattern (controlled natural language).
# Captures: duration, origin, destination, departure date text, budget amount.
# Supports variations: "I'm planning" / "I'd like to plan" / "planning" / "plan"
#   "leaving on" / "departing on"
#   "budget of no more than $N" / "budget under $N" / "budget below $N" / "within $N"
_TRAVEL_PATTERN = re.compile(
    r"(?:i'm|i\s+am|i'd\s+like\s+to|planning|plan)\s+"
    r"(?:a\s+)?(\d+)[\s-]*day\s+trip\s+"
    r"from\s+(.+?)\s+to\s+(.+?),?\s+"
    r"(?:leaving|departing)\s+on\s+"
    r"([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?)\.?\s+"
    r".*?"
    r"(?:budget\s+of\s+(?:no\s+more\s+than\s+)?|budget\s+(?:under|below|within)\s+|under\s+|below\s+|within\s+)"
    r"\$?\s*([\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Service extraction patterns
_SERVICE_KEYWORDS: dict[str, str] = {
    "flight": "flight",
    "flights": "flight",
    "hotel": "hotel",
    "hotels": "hotel",
    "accommodation": "hotel",
    "airbnb": "hotel",
}


def _parse_departure_date(date_text: str) -> Optional[str]:
    """Parse a natural language date like 'October 1' or 'Oct 1st' into ISO format.

    Uses the next occurrence year (current year if date is in the future,
    otherwise next year).
    Returns ISO date string or None if parsing fails.
    """
    date_text = date_text.strip().rstrip(".")

    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th...)
    cleaned = re.sub(r"(\d+)(?:st|nd|rd|th)", r"\1", date_text)

    # Pattern: "Month Day" or "Month Day, Year"
    m = re.match(
        r"([A-Za-z]+)\s+(\d{1,2})(?:,?\s*(\d{4}))?", cleaned
    )
    if not m:
        return None

    month_str = m.group(1).lower()
    day = int(m.group(2))
    year = int(m.group(3)) if m.group(3) else None

    month = _MONTH_MAP.get(month_str)
    if month is None:
        return None

    # Determine year: use provided year, or next occurrence
    if year is None:
        now = datetime.now()
        year = now.year
        # If the date has already passed this year, use next year
        try:
            candidate = datetime(year, month, day)
            if candidate < now:
                year += 1
        except ValueError:
            return None

    # Validate date
    try:
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# Authorization expiry (human-not-present mandate lifetime)
# ---------------------------------------------------------------------------

# The words that mark an expiry statement, so a plain trip date
# ("leaving on October 1") is never mistaken for the authorization window.
_EXPIRY_SUBJECT = r"(?:valid|valid\s+until|authoriz\w+|authoris\w+|mandate|delegation|expir\w+|授权|有效期)"

# "the authorization is valid until 2026-10-10"
_EXPIRY_ISO_PATTERN = re.compile(
    rf"{_EXPIRY_SUBJECT}[^.;\n]*?(\d{{4}}-\d{{2}}-\d{{2}})",
    re.IGNORECASE,
)

# "the authorization is valid until October 10" / "expires on Oct 10th, 2026"
_EXPIRY_DATE_PATTERN = re.compile(
    rf"{_EXPIRY_SUBJECT}[^.;\n]*?"
    r"(?:until|through|till|by|on)\s+"
    r"([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?)",
    re.IGNORECASE,
)

# "this authorization is valid for 7 days" / "授权有效期 7 天"
_EXPIRY_DAYS_PATTERN = re.compile(
    rf"{_EXPIRY_SUBJECT}[^.;\n]*?(?:for\s+)?(\d+)\s*(?:days?|天)",
    re.IGNORECASE,
)


def _end_of_day(iso_date: Optional[str]) -> Optional[str]:
    """Turn an ISO date into an end-of-day UTC timestamp (a date-only expiry
    means the user is authorized through the whole of that day)."""
    return f"{iso_date}T23:59:59Z" if iso_date else None


def _days_from_now(days: int) -> Optional[str]:
    """Turn a relative validity period in days into a UTC timestamp."""
    if days <= 0:
        return None
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


# Ordered rules: absolute dates win over a relative number of days.
_EXPIRY_RULES: list[tuple[re.Pattern[str], Callable[[re.Match[str]], Optional[str]]]] = [
    (_EXPIRY_ISO_PATTERN, lambda m: _end_of_day(m.group(1))),
    (_EXPIRY_DATE_PATTERN, lambda m: _end_of_day(_parse_departure_date(m.group(1)))),
    (_EXPIRY_DAYS_PATTERN, lambda m: _days_from_now(int(m.group(1)))),
]


def extract_expiry_time(text: str) -> tuple[Optional[str], str]:
    """Extract the authorization expiry stated by the user.

    Recognizes "valid until October 10", "valid until 2026-10-10",
    "the authorization expires on Oct 10, 2026" and "valid for 7 days".

    Returns:
        (expiry_time, cleaned_text) where expiry_time is an ISO 8601 UTC
        timestamp, or (None, text) when the user stated no expiry — callers
        must ask the user instead of inventing a default.
        The cleaned_text has the expiry phrase removed so it does not pollute
        downstream keyword search.
    """
    for pattern, to_timestamp in _EXPIRY_RULES:
        m = pattern.search(text)
        if not m:
            continue
        expiry_time = to_timestamp(m)
        if expiry_time is None:
            continue
        cleaned = (text[:m.start()] + text[m.end():]).strip()
        return expiry_time, cleaned
    return None, text


def _extract_services(text: str) -> list[str]:
    """Extract requested service types from the travel intent text."""
    text_lower = text.lower()
    services: list[str] = []
    for keyword, service in _SERVICE_KEYWORDS.items():
        if keyword in text_lower and service not in services:
            services.append(service)
    # Default to flight + hotel if nothing detected
    return services if services else ["flight", "hotel"]


def parse_travel_template(text: str) -> Optional[TravelIntent]:
    """Parse controlled natural language travel intent text into a TravelIntent.

    Supports minor wording variations but does NOT promise to understand
    arbitrary free-form expressions.

    Args:
        text: raw user input text

    Returns:
        TravelIntent instance, or None if the text does not match.
    """
    m = _TRAVEL_PATTERN.search(text)
    if not m:
        return None

    duration_days = int(m.group(1))
    origin = m.group(2).strip()
    destination = m.group(3).strip()
    date_text = m.group(4).strip()
    budget_str = m.group(5).replace(",", "")

    # Parse departure date
    departure_date = _parse_departure_date(date_text)
    if departure_date is None:
        return None

    # Parse budget
    try:
        budget_max = float(budget_str)
    except ValueError:
        return None

    # Extract services from the full text
    services = _extract_services(text)

    # Authorization expiry: empty when the user stated none (the caller then
    # asks for it — the mandate lifetime is never defaulted).
    expiry_time, _ = extract_expiry_time(text)

    return TravelIntent(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        duration_days=duration_days,
        budget_max=budget_max,
        currency="USD",
        services=services,
        expiry_time=expiry_time or "",
    )
