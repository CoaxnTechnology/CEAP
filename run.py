import os
from dotenv import load_dotenv
from app import create_app
from app.config import OneDriveConfig, GeminiConfig, DBConfig
from app.services.vector_store import CHROMA_PATH

load_dotenv()

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))

    db_type = "PostgreSQL" if "postgresql" in DBConfig.URL else "SQLite"

    print(f"\n DocuMind Office Automation  →  http://localhost:{port}")
    print(f"    Database              : ✅ {db_type}  ({DBConfig.URL.split('://')[0]})")
    print(f"    Vector DB             : ✅ ChromaDB persistent  ({CHROMA_PATH})")
    print(f"    Search mode           : ✅ Hybrid (Chroma HNSW + BM25 + RRF)")
    print(f"    Gemini API key        : {'✅ set' if GeminiConfig.API_KEY else '❌ missing'}")
    print(f"    OneDrive integration  : {'✅ configured' if OneDriveConfig.is_enabled() else '❌ not configured (set AZURE_* in .env)'}")
    print(f"\n Office Automation Features:")
    print(f"    HR                    : ✅ Leave mgmt, attendance, payslips, policies, approvals")
    print(f"    Accounting            : ✅ Invoices, expenses, PDF extraction, financial summaries")
    print(f"    Admin                 : ✅ Meetings, assets, tickets, supplies, announcements, visitors")
    print(f"\n Demo accounts:")
    print(f"    admin@documind.ai     : demo1234  (admin)")
    print(f"    user@example.com      : password123  (user)")
    print(f"\n")

    app.run(debug=True, host="0.0.0.0", port=port)
