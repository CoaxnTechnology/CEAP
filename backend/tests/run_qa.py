import sys
import time

sys.path.insert(0, ".")
from app import create_app

app = create_app()

QUESTIONS = {
    "BeTogather Feature Suggestion.xlsx": [
        "What features are currently in the On Going Flow?",
        "Which features have a status of Done or In Progress?",
        "List the bugs mentioned and their status.",
        "What feature suggestions are in the sheet?",
        "Show me the date when the 'Points' feature was added.",
    ],
    "EInvoicify Notes.xlsx": [
        "What companies are pending migration?",
        "How many companies have migrated successfully?",
        "What migration statuses are there?",
        "Which company uses this email: mgwong@einvoicify.my?",
    ],
    "Logistics_Testing_Data.xlsx": [
        "How many orders are in the dataset?",
        "How many orders were delivered on time vs late?",
        "How many orders are still pending or in transit?",
        "Which destinations have the most shipments?",
        "What's the average delivery delay?",
        "Which carrier handles the most orders?",
    ],
    "Medical_Testing_Data.xlsx": [
        "How many patient records are there?",
        "How many patients visited the Cardiology department?",
        "List the diagnosis categories and their counts.",
        "How many emergency visits were recorded?",
        "Which medication is prescribed most often?",
    ],
}

with app.test_client() as c:
    with c.session_transaction() as s:
        s["user"] = "raza@123.com"
    files = c.get("/api/files").get_json()["files"]

    for fname, qs in QUESTIONS.items():
        fid = next(fid for fid, f in files.items() if f["name"] == fname)
        print("=" * 70)
        print("FILE:", fname)
        for q in qs:
            r = c.post("/api/chat", json={"question": q, "file_ids": [fid]})
            b = r.get_json()
            tools = [t.get("name") for t in (b or {}).get("tool_calls", [])]
            srcs = sorted(set(s.get("name", "") for s in (b or {}).get("sources", [])))
            print("-" * 60)
            print("Q:", q)
            print("  tools:", tools)
            print("  sources:", srcs)
            print("  A:", (b or {}).get("response", "")[:280].replace("\n", " "))
            time.sleep(3)