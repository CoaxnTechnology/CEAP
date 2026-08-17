"""Check get_spreadsheet_stats returns exact counts, not RAG guesses."""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from app.db import SessionLocal
from app.models import Document
from app.services.tool_executor import TOOL_EXECUTORS


def _make_xlsx(path: str):
    pd.DataFrame(
        {
            "Status": ["On Going Flow"] * 3 + ["Done"] * 2 + ["To Do"],
            "Department": ["HR", "HR", "Finance", "HR", "Finance", "Finance"],
        }
    ).to_excel(path, index=False)


def test_spreadsheet_counts():
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    _make_xlsx(path)
    db = SessionLocal()
    try:
        doc = Document(
            file_id="test-sheet-1",
            name="test.xlsx",
            source_name="test.xlsx",
            size=os.path.getsize(path),
            chunks=1,
            uploaded_at=time.time(),
            source="local",
            user_key="test",
            file_path=path,
        )
        db.add(doc)
        db.commit()
    finally:
        db.close()

    run = TOOL_EXECUTORS["get_spreadsheet_stats"]
    try:
        cols = run({"file_id": "test-sheet-1"}, "test")
        assert cols["total_rows"] == 6, cols
        assert "Status" in cols["columns"], cols

        counts = run({"file_id": "test-sheet-1", "column": "Status"}, "test")
        assert counts["counts"] == {"On Going Flow": 3, "Done": 2, "To Do": 1}, counts

        by_dept = run({"file_id": "test-sheet-1", "column": "Department"}, "test")
        assert by_dept["counts"] == {"HR": 3, "Finance": 3}, by_dept

        missing = run({"file_id": "test-sheet-1", "column": "Nope"}, "test")
        assert "error" in missing, missing
    finally:
        db = SessionLocal()
        try:
            db.query(Document).filter(Document.file_id == "test-sheet-1").delete()
            db.commit()
        finally:
            db.close()
        os.unlink(path)

    print("OK: exact spreadsheet counts work")


if __name__ == "__main__":
    test_spreadsheet_counts()
