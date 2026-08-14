"""One-time: re-extract + re-index existing cloud documents with the fixed parser.

Usage: .venv/bin/python reindex_cloud_docs.py <path-to-session-file>
"""
import pickle
import sys
import requests
from run import app
from app.db import SessionLocal
from app.models import Document
from app.services.vector_store import ChromaStore
from app.services.chunker import chunk_text
from app.services.file_parser import extract_text_from_bytes
from app.services.onedrive import get_fresh_token, graph_download
from app.services.google_drive import drive_download

sid = sys.argv[1]
data = pickle.loads(open(sid, "rb").read()[4:])
user_key = data.get("user_key")

GRAPH = "https://graph.microsoft.com/v1.0"


def build_od_map(token):
    """id -> download_url by walking the drive tree. No $select: it drops downloadUrl."""
    mapping = {}
    seen = set()

    def walk(folder_id):
        if folder_id in seen:
            return
        seen.add(folder_id)
        url = (
            f"{GRAPH}/me/drive/items/{folder_id}/children"
            if folder_id != "root"
            else f"{GRAPH}/me/drive/root/children"
        )
        while url:
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
            if r.status_code != 200:
                return
            for f in r.json().get("value", []):
                if "folder" in f:
                    walk(f["id"])
                elif "file" in f and f.get("@microsoft.graph.downloadUrl"):
                    mapping[f["id"]] = f["@microsoft.graph.downloadUrl"]
            url = r.json().get("@odata.nextLink")

    walk("root")
    return mapping


with app.app_context():
    store = ChromaStore(user_key)
    db = SessionLocal()
    docs = db.query(Document).filter(
        Document.user_key == user_key,
        Document.source.in_(["onedrive", "gdrive"]),
    ).all()
    db.close()

    token, _ = get_fresh_token(data.get("od_cache"), data.get("od_token"))
    od_map = build_od_map(token) if token else {}
    print("onedrive items reachable:", len(od_map))

    fixed = 0
    for d in docs:
        try:
            if d.source == "onedrive":
                url = od_map.get(d.source_ref)
                if not url:
                    print("skip", d.name, "not reachable in drive")
                    continue
                resp = requests.get(url, timeout=60)
                data_bytes = resp.content if resp.status_code == 200 else None
            else:
                token_g = data.get("gd_token")
                data_bytes = drive_download(d.source_ref, token_g, None)
            if not data_bytes:
                print("skip", d.name, "no download")
                continue
            text = extract_text_from_bytes(data_bytes, d.name)
            if not text:
                print("skip", d.name, "no text")
                continue
            store.remove_file(d.file_id)
            chunks = chunk_text(text, d.name, d.file_id)
            store.add_chunks(chunks)
            fixed += 1
            print("reindexed", d.name, len(chunks), "chunks")
        except Exception as e:
            print("FAIL", d.name, type(e).__name__, e)
    print("done, fixed", fixed)