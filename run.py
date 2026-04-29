import os
from dotenv import load_dotenv
from app import create_app
from app.config import OneDriveConfig, GeminiConfig
from app.services.vector_store import CHROMA_PATH

load_dotenv()

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n🚀  DocuMind  →  http://localhost:{port}")
    print(f"    Vector DB             : ✅ ChromaDB persistent  ({CHROMA_PATH})")
    print(f"    Search mode           : ✅ Hybrid (Chroma HNSW + BM25 + RRF)")
    print(f"    Gemini API key        : {'✅ set' if GeminiConfig.API_KEY else '❌ missing'}")
    print(f"    OneDrive integration  : {'✅ configured' if OneDriveConfig.is_enabled() else '❌ not configured (set AZURE_* in .env)'}\n")
    app.run(debug=True, host="0.0.0.0", port=port)
