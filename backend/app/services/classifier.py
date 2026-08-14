from app.services.groq_service import generate_answer, GeminiServiceError

DEPARTMENTS = [
    "HR", "Admin", "Finance", "Academic", "Compliance",
    "Transport", "IT", "Sports",
]

_CLASSIFY_PROMPT = """You are a document classifier for a school management system.
Read the document content below and classify it into exactly ONE of these departments:

HR, Admin, Finance, Academic, Compliance, Transport, IT, Sports

Respond with ONLY the department name. No explanation, no punctuation.

--- Content:
{text}
---"""


def classify(text: str, filename: str = "") -> str | None:
    try:
        prompt = _CLASSIFY_PROMPT.format(text=text[:6000])
        dept = generate_answer(prompt)
        if dept and dept.strip() in DEPARTMENTS:
            return dept.strip()
        # Fallback: check if any department name appears in the content
        text_lower = (text[:2000] + filename).lower()
        for d in DEPARTMENTS:
            if d.lower() in text_lower:
                return d
    except GeminiServiceError:
        pass
    return None
