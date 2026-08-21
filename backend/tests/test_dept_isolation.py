import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
sys.path.insert(0, ".")

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(".") / ".env")

from app.modules.ai.routes import _is_outside_department

tests = [
    ("Which city has the highest delivery volume?", "transport", False),
    ("can you show me how many compliance are missing?", "transport", True),
    ("can you show me how many compliance are missing?", "finance", True),
    ("can you show me how many compliance are missing?", "it", True),
    ("What is the total invoice value?", "transport", True),
    ("Who approves HOD leave?", "transport", True),
    ("What does the Staff Leave Policy say about probation?", "hr", False),
    ("Summarize the fire safety circular", "compliance", False),
    ("How do I raise a ticket?", "it", False),
    ("What is the fee structure?", "sports", True),
    ("Tell me about the annual day event", "sports", False),
]

fails = 0
for q, d, exp in tests:
    got = _is_outside_department(q, d, [])
    ok = got == exp
    fails += 0 if ok else 1
    print(f"{'OK ' if ok else 'FAIL'} dept={d:10} block={got!s:5} (exp {exp!s:5})  {q[:55]}")
print("ALL PASS" if fails == 0 else f"{fails} FAILURES")
