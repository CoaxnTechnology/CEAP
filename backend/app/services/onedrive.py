import os
from msal import ConfidentialClientApplication
import requests as http_requests
from app.config import OneDriveConfig

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def get_msal_app():
    return ConfidentialClientApplication(
        OneDriveConfig.CLIENT_ID,
        authority=OneDriveConfig.AUTHORITY,
        client_credential=OneDriveConfig.CLIENT_SECRET,
    )


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
        if resp.status_code != 200:
            return results

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
