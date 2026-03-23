"""GitHub-based persistent storage for verification records."""
import json
import base64
from datetime import datetime, timezone
import httpx
from config import GITHUB_TOKEN, GITHUB_REPO, GITHUB_DATA_FILE

GITHUB_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


async def _get_file() -> tuple[dict, str]:
    """Fetch current verifications.json from GitHub. Returns (data, sha)."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{GITHUB_DATA_FILE}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 404:
                return {}, ""
            resp.raise_for_status()
            body = resp.json()
            content = base64.b64decode(body["content"]).decode("utf-8")
            return json.loads(content), body["sha"]
    except Exception:
        return {}, ""


async def _save_file(data: dict, sha: str) -> bool:
    """Save verifications.json to GitHub."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{GITHUB_DATA_FILE}"
    content_b64 = base64.b64encode(json.dumps(data, indent=2, ensure_ascii=False).encode()).decode()
    payload: dict = {
        "message": f"Update verifications {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "content": content_b64,
    }
    if sha:
        payload["sha"] = sha
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.put(url, json=payload, headers=HEADERS)
            resp.raise_for_status()
            return True
    except Exception:
        return False


async def save_verification(
    telegram_user_id: int,
    username: str,
    verification_type: str,
    verification_id: str,
    status: str,
    user_data: dict,
) -> bool:
    """Create or update a verification record in GitHub."""
    data, sha = await _get_file()
    key = str(telegram_user_id)
    data[key] = {
        "telegram_user_id": telegram_user_id,
        "username": username,
        "verification_type": verification_type,
        "verification_id": verification_id,
        "status": status,
        "user_data": {k: v for k, v in user_data.items() if k != "email"},  # don't store email
        "created_at": data.get(key, {}).get("created_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return await _save_file(data, sha)


async def get_verification(telegram_user_id: int) -> dict | None:
    """Get verification record for a user."""
    data, _ = await _get_file()
    return data.get(str(telegram_user_id))


async def update_status(telegram_user_id: int, status: str) -> bool:
    """Update the status of an existing verification."""
    data, sha = await _get_file()
    key = str(telegram_user_id)
    if key not in data:
        return False
    data[key]["status"] = status
    data[key]["updated_at"] = datetime.now(timezone.utc).isoformat()
    return await _save_file(data, sha)
