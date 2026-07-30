import re
from datetime import datetime, timedelta
from app.services.gemini import generate_answer, GeminiServiceError

COMPLIANCE_CATEGORIES = [
    "Safeguarding",
    "Safety",
    "Finance",
    "HR",
    "Academic",
    "Infrastructure",
    "Health",
    "Transport",
]

_CLASSIFY_PROMPT = """You are a document classifier for a school compliance system.
Read the document content below and classify it into exactly ONE of these compliance categories:

Safeguarding, Safety, Finance, HR, Academic, Infrastructure, Health, Transport

Respond with ONLY the category name. No explanation, no punctuation.

--- Content:
{text}
---"""

_STATUS_PROMPT = """You are analyzing a compliance document for a school. Determine its status based on any expiry or validity dates found in the content.

Read the document content below carefully:
1. Find any expiry date, "valid until", "valid through", or "valid for" date.
2. If a date is found, compare it to TODAY's date.
3. If the date is in the PAST (already expired), respond with ONLY: "Outdated"
4. If the date is in the future but within 6 months, respond with ONLY: "Expiring"
5. If the date is in the future and more than 6 months away, respond with ONLY: "Available"
6. If NO expiry/validity date is found at all, respond with ONLY: "Available"

Respond with ONLY one word: "Available", "Expiring", or "Outdated". No explanation, no punctuation.

--- Content:
{text}
---

Status:"""


def classify_compliance(text: str, filename: str = "") -> str | None:
    try:
        prompt = _CLASSIFY_PROMPT.format(text=text[:6000])
        category = generate_answer(prompt)
        if category and category.strip() in COMPLIANCE_CATEGORIES:
            return category.strip()
        text_lower = (text[:2000] + filename).lower()
        for c in COMPLIANCE_CATEGORIES:
            if c.lower() in text_lower:
                return c
    except GeminiServiceError:
        pass
    return None


def detect_compliance_status(text: str) -> str:
    try:
        prompt = _STATUS_PROMPT.format(text=text[:4000])
        status = generate_answer(prompt)
        if status and status.strip() in ("Available", "Expiring", "Outdated"):
            return status.strip()
    except GeminiServiceError:
        pass
    fallback = _fallback_status_detection(text)
    return fallback if fallback else "Available"


_DATE_PATTERNS = [
    r'(?:valid(?:ity)?|expir(?:y|ing)|expires?|until|till|through|valid\s+for)\s*:?\s*(\d{1,2}[\/\-\.]?\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{2,4})',
    r'(?:valid(?:ity)?|expir(?:y|ing)|expires?|until|till|through|valid\s+for)\s*:?\s*(\d{4}[\/\-\.]?(?:0[1-9]|1[0-2])[\/\-\.]?\d{1,2})',
    r'(?:date|issued|effective|from)\s*:?\s*(\d{1,2}[\/\-\.]?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{2,4})',
    r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b',
]

_MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def _parse_date(text: str) -> datetime | None:
    for pattern in _DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            for fmt in ('%d %b %Y', '%d %B %Y', '%d-%b-%Y', '%d-%B-%Y',
                        '%d/%m/%Y', '%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y',
                        '%d-%m-%Y', '%d.%m.%Y', '%b %d, %Y', '%B %d, %Y',
                        '%d %b. %Y', '%d %B %Y'):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            # Try fuzzy: "Month Year"
            m = re.match(r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})', date_str, re.IGNORECASE)
            if m:
                return datetime(int(m.group(2)), _MONTH_MAP[m.group(1)[:3].lower()], 1)
    return None


def _fallback_status_detection(text: str) -> str | None:
    text_lower = text.lower()
    now = datetime.now()
    has_expiry = any(w in text_lower for w in ['expir', 'valid unt', 'valid for', 'till', 'validity'])
    if not has_expiry:
        return None
    date = _parse_date(text)
    if date is None:
        return None
    if date < now:
        return "Outdated"
    if date < now + timedelta(days=180):
        return "Expiring"
    return "Available"
