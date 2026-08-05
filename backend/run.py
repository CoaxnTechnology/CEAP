import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be .* leaked semaphore objects")

from app import create_app
from app.config import OneDriveConfig, GroqConfig, DBConfig
from app.services.vector_store import CHROMA_PATH

load_dotenv(Path(__file__).parent / '.env')

app = create_app()


@app.cli.command("index-repo-docs")
def index_repo_docs():
    """Batch-index all existing repository documents for RAG chat."""
    import time
    from app.db import SessionLocal
    from app.models import RepositoryDocument, DocumentVersion
    from app.services.file_parser import extract_text
    from app.services.rag import register_and_index_for_user

    db = SessionLocal()
    try:
        docs = db.query(RepositoryDocument).filter(
            RepositoryDocument.file_id.is_(None),
            RepositoryDocument.status == "active",
        ).all()
        print(f"Found {len(docs)} repo documents to index")

        for i, doc in enumerate(docs):
            version = db.query(DocumentVersion).filter(
                DocumentVersion.document_id == doc.id,
                DocumentVersion.version_number == doc.current_version,
            ).first()
            if not version or not os.path.exists(version.file_path):
                print(f"  [{i+1}/{len(docs)}] SKIP {doc.name} — file not found")
                continue

            try:
                text = extract_text(version.file_path, version.file_name)
                if not text:
                    print(f"  [{i+1}/{len(docs)}] SKIP {doc.name} — no text extracted")
                    continue
                rag_entry = register_and_index_for_user(
                    user_key=doc.user_key,
                    name=doc.name,
                    text=text,
                    size=doc.size,
                    source="repository",
                    source_ref=doc.id,
                )
                doc.file_id = rag_entry["file_id"]
                db.commit()
                print(f"  [{i+1}/{len(docs)}] OK {doc.name} -> {rag_entry['file_id']}")
            except Exception as e:
                db.rollback()
                print(f"  [{i+1}/{len(docs)}] FAIL {doc.name} — {e}")
    finally:
        db.close()


@app.cli.command("check-compliance-status")
def check_compliance_status():
    """Daily check: re-detect compliance evidence status from file content.

    Scans all items with file_path, extracts text, and auto-updates status
    if it has changed. Run daily via cron:  python run.py check-compliance-status
    """
    import tempfile
    from app.db import SessionLocal
    from app.models import ComplianceEvidence
    from app.services.compliance_classifier import detect_compliance_status
    from app.services.file_parser import extract_text

    db = SessionLocal()
    items = db.query(ComplianceEvidence).filter(
        ComplianceEvidence.file_path != "",
        ComplianceEvidence.file_path.isnot(None),
    ).all()
    print(f"Checking {len(items)} evidence items for status updates...")

    updated = 0
    for item in items:
        if not os.path.exists(item.file_path):
            print(f"  SKIP {item.title} — file not found at {item.file_path}")
            continue
        try:
            ext = os.path.splitext(item.file_path)[1].lower()
            if ext not in {'.pdf', '.docx', '.pptx', '.xlsx', '.xls', '.csv', '.txt'}:
                continue
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                with open(item.file_path, "rb") as src:
                    tmp.write(src.read())
                tmp_path = tmp.name
            text = extract_text(tmp_path, item.source_name or item.title)
            os.unlink(tmp_path)
            if not text:
                print(f"  SKIP {item.title} — no text extracted")
                continue
            new_status = detect_compliance_status(text)
            if new_status and new_status != item.status:
                old_status = item.status
                item.status = new_status
                item.last_updated = time.strftime("%Y-%m-%d")
                db.commit()
                updated += 1
                print(f"  OK {item.title}: {old_status} → {new_status}")
        except Exception as e:
            db.rollback()
            print(f"  FAIL {item.title} — {e}")

    print(f"\nDone. {updated} item(s) updated out of {len(items)} checked.")
    db.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))

    db_type = "PostgreSQL"

    print(f"\n 🏫 CEAP for Schools  →  http://localhost:{port}")
    print(f"    Database              : ✅ {db_type}  ({DBConfig.URL.split('://')[0]})")
    print(f"    Vector DB             : ✅ ChromaDB persistent  ({CHROMA_PATH})")
    print(f"    Search mode           : ✅ Hybrid (Chroma HNSW + BM25 + RRF)")
    print(f"    Groq LLM key          : {'✅ set' if GroqConfig.API_KEY else '❌ missing'} ({GroqConfig.MODEL})")
    print(f"    OneDrive integration  : {'✅ configured' if OneDriveConfig.is_enabled() else '❌ not configured (set AZURE_* in .env)'}")
    print(f"\n School Features:")
    print(f"    Staff                 : ✅ Leave mgmt, attendance, policies, approvals")
    print(f"    Finance               : ✅ Fee invoices, expenses, financial summaries")
    print(f"    Administration        : ✅ Circulars, meetings, tickets, announcements")
    print(f"\n Demo accounts:")
    print(f"    admin@ceap.school     : demo1234  (admin)")
    print(f"    user@ceap.school      : password123  (teacher)")
    print(f"\n")

    app.run(debug=True, host="0.0.0.0", port=port)
