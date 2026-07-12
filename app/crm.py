import logging
import os

import httpx

logger = logging.getLogger(__name__)
CRM_API_URL = os.getenv("CRM_API_URL", "https://dxcrm.doxaxsolutions.com/api/v1/public/consultation-intake")
CRM_CONSULTATION_TOKEN = os.getenv("CRM_CONSULTATION_TOKEN", "")
CRM_TIMEOUT_SECONDS = float(os.getenv("CRM_TIMEOUT_SECONDS", "15"))


def submit_consultation_request(payload: dict[str, str]) -> tuple[bool, str]:
    headers = {"Accept": "application/json"}
    if CRM_CONSULTATION_TOKEN:
        headers["X-Consultation-Token"] = CRM_CONSULTATION_TOKEN
    try:
        response = httpx.post(CRM_API_URL, json=payload, headers=headers, timeout=CRM_TIMEOUT_SECONDS)
        response.raise_for_status()
        return True, ""
    except httpx.HTTPStatusError as exc:
        logger.warning("CRM consultation request rejected with status %s", exc.response.status_code)
        return False, "CRM rejected the request. Please try again later."
    except httpx.HTTPError:
        logger.exception("CRM consultation request failed")
        return False, "The request service is temporarily unavailable. Please try again later."
