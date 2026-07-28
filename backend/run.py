import os
from pathlib import Path
from dotenv import load_dotenv
from app import create_app
from app.config import OneDriveConfig, GeminiConfig, DBConfig
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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))

    db_type = "PostgreSQL"

    print(f"\n 🏫 CEAP for Schools  →  http://localhost:{port}")
    print(f"    Database              : ✅ {db_type}  ({DBConfig.URL.split('://')[0]})")
    print(f"    Vector DB             : ✅ ChromaDB persistent  ({CHROMA_PATH})")
    print(f"    Search mode           : ✅ Hybrid (Chroma HNSW + BM25 + RRF)")
    print(f"    Gemini API key        : {'✅ set' if GeminiConfig.API_KEY else '❌ missing'}")
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
