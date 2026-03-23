"""SheerID API client."""
import httpx
from config import SHEERID_ACCESS_TOKEN, SHEERID_BASE_URL, SHEERID_PROGRAM_IDS


HEADERS = {
    "Authorization": f"Bearer {SHEERID_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

SEGMENT_MAP = {
    "student": "STUDENT",
    "military": "MILITARY",
    "teacher": "TEACHER",
    "first_responder": "FIRST_RESPONDER",
}


def _build_person_info(verification_type: str, user_data: dict) -> dict:
    """Build personInfo payload for SheerID API."""
    info = {
        "firstName": user_data.get("first_name", ""),
        "lastName": user_data.get("last_name", ""),
        "birthDate": user_data.get("birth_date", ""),
    }
    if verification_type in ("student", "teacher"):
        info["email"] = user_data.get("email", "")
        info["organization"] = {"name": user_data.get("school_name", "")}
    elif verification_type == "military":
        info["status"] = user_data.get("status", "ACTIVE_DUTY")
    elif verification_type == "first_responder":
        info["organization"] = {"name": user_data.get("organization", "")}
    return info


async def create_verification(verification_type: str, user_data: dict) -> dict:
    """Start a new SheerID verification. Returns the API response dict."""
    program_id = SHEERID_PROGRAM_IDS.get(verification_type, "")
    if not program_id:
        return {"error": f"No program ID configured for type '{verification_type}'"}

    payload = {
        "programId": program_id,
        "segment": SEGMENT_MAP[verification_type],
        "personInfo": _build_person_info(verification_type, user_data),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{SHEERID_BASE_URL}/verification",
                json=payload,
                headers=HEADERS,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


async def get_verification_status(verification_id: str) -> dict:
    """Get current status of a verification."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{SHEERID_BASE_URL}/verification/{verification_id}",
                headers=HEADERS,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


async def upload_document(verification_id: str, file_bytes: bytes, filename: str = "document.jpg") -> dict:
    """Upload a document for manual review."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{SHEERID_BASE_URL}/verification/{verification_id}/documents",
                headers={"Authorization": f"Bearer {SHEERID_ACCESS_TOKEN}"},
                files={"file": (filename, file_bytes, "application/octet-stream")},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


def parse_result_step(response: dict) -> str:
    """Return human-readable status from SheerID response."""
    step = response.get("currentStep", "")
    if step == "success":
        return "success"
    elif step == "docUpload":
        return "pending_doc"
    elif step in ("error", "rejected"):
        return "denied"
    elif "error" in response:
        return "error"
    else:
        return "unknown"
