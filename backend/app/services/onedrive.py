import os
from msal import ConfidentialClientApplication, SerializableTokenCache
import requests as http_requests
from app.config import OneDriveConfig

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def get_msal_app(cache: SerializableTokenCache | None = None):
    return ConfidentialClientApplication(
        OneDriveConfig.CLIENT_ID,
        authority=OneDriveConfig.AUTHORITY,
        client_credential=OneDriveConfig.CLIENT_SECRET,
        token_cache=cache or SerializableTokenCache(),
    )


def get_fresh_token(serialized_cache: str | None, stored_token: str | None):
    """Return (access_token, updated_cache) — refreshing via MSAL when possible."""
    cache = SerializableTokenCache()
    if serialized_cache:
        try:
            cache.deserialize(serialized_cache)
        except Exception:
            pass
    app = get_msal_app(cache)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent_with_error(OneDriveConfig.SCOPES, account=accounts[0])
        token = result.get("access_token") if result else None
        if token:
            return token, cache.serialize()
    return stored_token, serialized_cache


def graph_request(endpoint: str, token: str):
    resp = http_requests.get(
        f"{GRAPH_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    return resp.json() if resp.status_code == 200 else None


def graph_download(download_url: str, token: str):
    resp = http_requests.get(
        download_url, headers={"Authorization": f"Bearer {token}"}, timeout=60
    )
    return resp.content if resp.status_code == 200 else None


def _normalize_parent_path(path: str) -> str:
    if not path:
        return ""
    if "root:" in path:
        return path.split("root:", 1)[1].strip("/")
    if path.endswith("/root"):
        return ""
    return path.strip("/")


def list_onedrive_files(token: str, folder_id: str | None = None) -> list:
    """List immediate children for a folder, not the entire drive tree."""
    SUPPORTED = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt"}
    normalized_folder_id = None if not folder_id or folder_id == "root" else folder_id
    endpoint = (
        f"/me/drive/items/{normalized_folder_id}/children"
        if normalized_folder_id
        else "/me/drive/root/children"
    )
    url = (
        f"{GRAPH_BASE}{endpoint}"
        "?$top=200&$select=id,name,size,file,folder,parentReference,@microsoft.graph.downloadUrl"
    )
    results = []

    while url:
        resp = http_requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if resp.status_code == 404:
            return results
        if resp.status_code != 200:
            raise RuntimeError(
                f"OneDrive API {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        for item in data.get("value", []):
            name = item.get("name", "")
            parent_ref = item.get("parentReference") or {}
            parent_id = parent_ref.get("id") or "root"
            parent_path = _normalize_parent_path(parent_ref.get("path", ""))
            item_path = f"{parent_path}/{name}".strip("/") if parent_path else name

            if "folder" in item:
                results.append(
                    {
                        "id": item["id"],
                        "name": name,
                        "size": item.get("size", 0),
                        "parent_id": parent_id,
                        "parent_path": parent_path,
                        "path": item_path,
                        "isFolder": True,
                    }
                )
                continue

            if "file" not in item:
                continue

            ext = os.path.splitext(name)[1].lower()
            if ext not in SUPPORTED:
                continue

            results.append(
                {
                    "id": item["id"],
                    "name": name,
                    "size": item.get("size", 0),
                    "download_url": item.get("@microsoft.graph.downloadUrl", ""),
                    "parent_id": parent_id,
                    "parent_path": parent_path,
                    "path": item_path,
                    "ext": ext,
                    "isFolder": False,
                }
            )

        url = data.get("@odata.nextLink")

    return results
