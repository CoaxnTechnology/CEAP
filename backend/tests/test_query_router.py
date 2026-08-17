import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.services.query_router import classify

cases = [
    ("Who approves HOD leave?", "hr", "policy_lookup", False),
    ("How many staff on leave today?", "hr", "status", False),
    ("Show pending admissions in Interview stage", "admissions", "status", False),
    ("Summarize the fire safety circular", "", "document", True),
    ("What does the child protection policy say?", "", "policy_lookup", True),
    ("What is my leave balance?", "hr", "general", True),
    ("Create an invoice for ACME", "finance", "action", False),
    ("What features are currently in the On Going Flow?", "general", "general", True),
]

for question, dept, exp_intent, exp_rag in cases:
    r = classify(question, dept)
    assert r["intent"] == exp_intent, (question, r)
    assert r["needs_rag"] is exp_rag, (question, r)

assert "compliance" in classify("compliance readiness audit status", "compliance")["domains"]
assert classify("hello there", "")["domains"] == ["general"]

print(f"{len(cases) + 2} router assertions passed")