"""Layer 0 — query router. Classifies a question into domains + intent
before context is built, so RAG only runs when it's actually needed.

v1: keyword + department rules, no extra LLM call.
"""
import re

DOMAIN_KEYWORDS = {
    "hr": ["leave", "attendance", "staff", "employee", "hiring", "onboard", "payroll", "payslip", "contract", "hr ", "activities", "activity", "orientation", "bonus", "training", "hr activities"],
    "finance": ["fee", "invoice", "expense", "collection", "payment", "waiver", "scholarship", "budget", "arrears", "outstanding", "finance", "cashflow", "bank statement", "bank_statement", "cash flow"],
    "admissions": ["admission", "applicant", "application", "enroll", "interview", "inquiry", "seat", "pipeline"],
    "compliance": ["compliance", "evidence", "audit", "certificate", "regulation", "license", "inspection", "compliance readiness"],
    "executive": ["kpi", "overview", "target", "revenue", "mtd", "readiness", "high-risk", "briefing", "dashboard"],
    "academic": ["assessment", "exam", "coverage", "curriculum", "academic", "class coverage", "timetable", "report card", "syllabus"],
    "workflows": ["workflow", "approval", "approver", "stage"],
    "knowledge": ["faq", "sop", "knowledge card", "knowledge base", "how do i"],
}

POLICY_KEYWORDS = ["policy", "who approves", "approval chain", "allowed", "entitlement", "max days", "limit", "rules_json"]
DOCUMENT_KEYWORDS = ["summarize", "summarise", "summary", "what does", "what is the policy", "circular", "document", "pdf", "file", "contract", "excerpt"]
ACTION_KEYWORDS = ["apply", "create", "submit", "request", "approve", "reject", "book", "register", "schedule", "cancel"]


def classify(question: str, department: str = "") -> dict:
    """Classify a question into domains, intent, and whether RAG is needed."""
    q = (question or "").lower()
    # ponytail: alias cashflow -> bank_statement for consistent file search
    q = q.replace("cashflow", "bank_statement").replace("cash flow", "bank_statement")

    # HR activities summary should be consistent — force to HR overview, not RAG doc search
    if "hr activities" in q or "hr activity" in q:
        return {"domains": ["hr"], "intent": "status", "needs_rag": False, "needs_tools": ["hr"]}

    domains = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            domains.add(domain)

    # Department tab is a strong hint even without keywords.
    dept = (department or "").strip().lower()
    dept_map = {
        "hr": "hr",
        "finance": "finance",
        "accounting": "finance",
        "admin": "executive",
        "academic": "academic",
        "admissions": "admissions",
        "compliance": "compliance",
        "students": "academic",
        "executive": "executive",
    }
    if dept in dept_map:
        domains.add(dept_map[dept])

    if not domains:
        domains.add("general")

    is_policy = any(kw in q for kw in POLICY_KEYWORDS)
    is_doc = any(kw in q for kw in DOCUMENT_KEYWORDS)
    is_action = any(kw in q for kw in ACTION_KEYWORDS)
    is_count = bool(re.search(r"(how many|count|list|show|pending|status|today|who)", q))

    if is_policy:
        intent = "policy_lookup"
    elif is_doc:
        intent = "document"
    elif is_action:
        intent = "action"
    elif is_count:
        intent = "status"
    else:
        intent = "general"

    # RAG is the last resort: only for explicit document/policy-wording
    # questions, general questions, or count-questions that don't map to a
    # domain tool (usually they're asking about an uploaded file).
    is_general_count = intent == "status" and domains == {"general"}
    needs_rag = (
        is_doc
        or (is_policy and "who" not in q)
        or intent == "general"
        or is_general_count
    )

    needs_tools = sorted(domains - {"general"})

    return {
        "domains": sorted(domains),
        "intent": intent,
        "needs_rag": needs_rag,
        "needs_tools": needs_tools,
    }