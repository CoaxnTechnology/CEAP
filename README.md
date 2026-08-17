# CEAP for Schools — Enterprise AI Platform

A centralized AI-powered knowledge platform for schools. Upload circulars, policies, student records, and fee documents — then ask questions in natural language and get grounded answers with document references.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **ChatGPT-style UI** — Dark sidebar for chat history, clean message bubbles, responsive design
- **RAG-powered answers** — Hybrid search (ChromaDB HNSW + BM25 with Reciprocal Rank Fusion) over your documents
- **Local file upload** — PDF, DOCX, XLSX, CSV, TXT with concurrent upload and indexing
- **OneDrive import** — Browse folders, select files, and import directly from Microsoft OneDrive via OAuth2
- **Multi-session chat** — Create, switch, and delete conversations; history persists across reloads
- **Source citations** — Every answer shows clickable source chips with the exact passage used
- **Automatic retry** — Gemini 503 "high demand" errors are retried with exponential backoff
- **Multi-user scoped** — Each user gets isolated ChromaDB collections and PostgreSQL records

## Architecture

```
┌─────────────────────────────────────────────┐
│                  Browser                     │
│  ai_chat.html + chat.js + chat.css (dark UI) │
└──────────────┬──────────────────────────────┘
               │  HTTP / JSON
┌──────────────▼──────────────────────────────┐
│                 Flask App                    │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │ /api/chat │  │ /api/    │  │ /onedrive│  │
│  │  (RAG)    │  │ files    │  │  (OAuth) │  │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  │
│        │              │              │        │
│  ┌─────▼──────────────▼──────────────▼─────┐  │
│  │           Services Layer                │  │
│  │  rag.py  ·  gemini.py  ·  onedrive.py   │  │
│  │  persistence.py  ·  vector_store.py     │  │
│  │  file_parser.py                         │  │
│  └──────────────────┬──────────────────────┘  │
└─────────────────────┼─────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌────────────┐  ┌──────────┐  ┌───────────┐
   │ PostgreSQL │  │ ChromaDB │  │ MS Graph  │
   │ (users,    │  │ (vectors │  │ (OneDrive │
   │ sessions,  │  │  + BM25) │  │  files)   │
   │ messages)  │  │          │  │           │
   └────────────┘  └──────────┘  └───────────┘
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Google Gemini API key ([get one here](https://aistudio.google.com/app/apikey))
- (Optional) Azure AD app for OneDrive integration

### 2. Install

```bash
git clone <repository-url>
cd OneDrive_Chatbot
pip install -r requirements.txt
```

### 3. Configure

Copy the example env file and fill in your keys:

```bash
cp .env.example backend/.env
```

```env
# Required — Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Required — Flask
FLASK_SECRET_KEY=change-me-to-a-random-secret

# Optional — OneDrive (leave out if you only need local files)
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=common
AZURE_REDIRECT_URI=http://localhost:5000/auth/callback

# Optional
PORT=5000
```

### 4. Run

```bash
python run.py
```

Open **http://localhost:5000** and log in with one of the demo accounts:

| Email | Password |
|---|---|
| `admin@ceap.school` | `demo1234` |
| `user@example.com` | `password123` |

Add more users in `app/config.py` under `AuthConfig.USERS`.

## Usage

### Uploading Files

1. Click the **paperclip** icon in the composer (or the **Files** button on the top-right)
2. Select PDF, DOCX, XLSX, CSV, or TXT files
3. Files are parsed, chunked, embedded, and stored in ChromaDB automatically
4. Once indexed, click a file in the Files panel to select it for your next query

### Importing from OneDrive

1. Open the **Files** panel and switch to the **OneDrive** tab
2. Click **Connect** to sign in with Microsoft
3. Browse folders, select files, and click **Import Selected**
4. Imported files are indexed the same way as local uploads

### Asking Questions

- Type a question in the composer and press Enter
- Answers are grounded in your indexed documents with source citations
- Click any **source chip** below an answer to see the exact passage
- Use the quick-prompt chips on the welcome screen for common tasks
- Selected files are prioritized; if none are selected, all indexed files are searched

## Configuration

### RAG Settings (`app/config.py`)

| Setting | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | 800 | Characters per document chunk |
| `CHUNK_OVERLAP` | 150 | Overlap between consecutive chunks |
| `TOP_K` | 6 | Number of chunks retrieved per query |
| `RRF_K` | 60 | RRF damping factor for hybrid ranking |

### Gemini Model

Uses `gemini-2.5-flash` by default. Change `GeminiConfig.MODEL` in `app/config.py` to use a different model.

### Gemini 503 Retry

When Google's API returns a 503 ("high demand") error, the backend retries up to 3 times with exponential backoff (2s, 4s, 8s + jitter). If all retries fail, it falls back to showing the top retrieved passage directly.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/chat/session` | Get current session messages |
| `DELETE` | `/api/chat/session` | Clear current session |
| `GET` | `/api/chat/sessions` | List all sessions |
| `POST` | `/api/chat/sessions` | Create new session |
| `DELETE` | `/api/chat/sessions/<id>` | Delete a session |
| `POST` | `/api/chat` | Send a message (RAG query) |
| `GET` | `/api/files` | List indexed files |
| `POST` | `/api/upload` | Upload and index a file |
| `POST` | `/api/remove` | Remove a file |
| `GET` | `/api/onedrive/status` | OneDrive connection status |
| `GET` | `/api/onedrive/files` | List OneDrive folder contents |
| `POST` | `/api/onedrive/import` | Import selected OneDrive files |
| `GET` | `/onedrive/connect` | Start OneDrive OAuth flow |
| `POST` | `/onedrive/disconnect` | Disconnect OneDrive |

## Project Structure

```
OneDrive_Chatbot/
├── app/
│   ├── __init__.py            # Flask app factory
│   ├── config.py              # All configuration classes
│   ├── auth_helpers.py        # Login decorator
│   ├── routes/
│   │   ├── auth.py            # Login / logout
│   │   ├── chat.py            # Chat API, RAG pipeline
│   │   ├── files.py           # Upload / remove endpoints
│   │   └── onedrive.py        # OneDrive OAuth + import
│   └── services/
│       ├── file_parser.py     # PDF, DOCX, XLSX, CSV, TXT extraction
│       ├── gemini.py          # Gemini API client with retry
│       ├── onedrive.py        # MS Graph API helpers
│       ├── persistence.py     # PostgreSQL schema and queries
│       ├── rag.py             # Chunking, indexing, prompt building
│       └── vector_store.py    # ChromaDB wrapper (hybrid search)
├── static/
│   ├── css/chat.css           # Dark ChatGPT-style theme
│   └── js/chat.js             # Frontend state and DOM logic
├── templates/
│   ├── ai_chat.html            # AI Chat UI (both /chat and /ai-chat)
├── chroma_db/                 # Persistent vector store (auto-created)
├── ceap.sqlite3               # (removed — PostgreSQL only)
├── flask_session/             # Server-side session store
├── requirements.txt
├── run.py
└── .env                # backend/.env — the single config file
```

## Supported File Types

| Type | Extensions | Parser |
|---|---|---|
| PDF | `.pdf` | PyPDF2 |
| Word | `.docx`, `.doc` | python-docx |
| Excel | `.xlsx`, `.xls`, `.csv` | pandas / openpyxl / xlrd |
| Text | `.txt` | Direct read |

## Troubleshooting

**"Gemini temporarily unavailable"** — The API is experiencing high demand. The backend retries automatically; if all retries fail you'll see the top retrieved passage as a fallback.

**Files not showing after refresh** — The Files panel may need a manual refresh. Click the **Refresh** button in the Documents tab.

**OneDrive import fails** — Check that your Azure AD app has `Files.Read` and `Files.Read.All` permissions granted, and that the redirect URI matches exactly.

**"No documents indexed"** — Upload at least one file before asking questions. Answers require indexed document chunks.

## Tech Stack

- **Backend**: Flask, PostgreSQL, ChromaDB
- **AI**: Google Gemini (via `google-genai`)
- **Vector Search**: ChromaDB hybrid (HNSW dense + BM25 sparse + RRF)
- **Embeddings**: `sentence-transformers` (local, no external API)
- **OneDrive**: MSAL + Microsoft Graph API
- **Frontend**: Vanilla JS, Marked.js, DOMPurify, Font Awesome

## License

MIT
