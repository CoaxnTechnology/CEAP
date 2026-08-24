import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
sys.path.insert(0, ".")

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(".") / ".env")

from app.modules.ai.routes import _aggregation_doc_context, _is_aggregation_question


class StubStore:
    def __init__(self, texts):
        self._texts = texts

    def get_file_text(self, fid):
        return self._texts.get(fid, "")


REGISTRY = {
    "f1": {"name": "Invoice Register A.pdf"},
    "f2": {"name": "Invoice Register B.pdf"},
    "f3": {"name": "Shipments.xlsx"},
    "f4": {"name": "Big Book.pdf"},
}
TEXTS = {
    "f1": "invoice " * 50,
    "f2": "invoice receipt " * 40,  # higher keyword score (receipt also in q)
    "f3": "sheet data",
    "f4": "x" * 25000,  # over per-doc cap -> skipped
}

fails = 0


def check(label, got, exp):
    global fails
    ok = got == exp
    fails += 0 if ok else 1
    print(f"{'OK ' if ok else 'FAIL'} {label}: {got if not ok else ''}")


# Both selected PDFs must be injected (multi-select), not just the best scorer
ctx = _aggregation_doc_context(
    "how many invoices and receipts total?", ["f1", "f2"], REGISTRY, None,
    set(REGISTRY), StubStore(TEXTS), "", [], drop_excerpts=False,
)
check("both selected docs injected", ctx.count("COMPLETE DOCUMENT TEXT"), 2)
check("doc B present", "Invoice Register B.pdf" in ctx, True)

# All-spreadsheet selection -> no excerpts, stats tool handles it
ctx = _aggregation_doc_context(
    "how many rows?", ["f3"], REGISTRY, None, set(REGISTRY),
    StubStore(TEXTS), "", [], drop_excerpts=False,
)
check("sheets-only empty", ctx, "")

# Per-doc cap: oversized doc skipped, budget respected
ctx = _aggregation_doc_context(
    "how many invoices across both registers?", ["f4", "f1"], REGISTRY, None,
    set(REGISTRY), StubStore(TEXTS), "", [], drop_excerpts=False,
)
check("oversized doc skipped", "Big Book.pdf" not in ctx, True)
check("smaller doc kept", "Invoice Register A.pdf" in ctx, True)

# Enumeration questions must count as aggregation (full-doc injection path)
check("net pay in each -> agg", _is_aggregation_question("What is the net pay in each of these payslips?"), True)
check("list all -> agg", _is_aggregation_question("list all invoices"), True)
check("simple lookup not agg", _is_aggregation_question("who is the employee on this payslip?"), False)

print("ALL PASS" if fails == 0 else f"{fails} FAILURES")
sys.exit(1 if fails else 0)
