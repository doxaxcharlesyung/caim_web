import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _setting(name: str, fallback: str = "") -> str:
    return os.getenv(name, fallback).strip()


def _submit(url: str, payload: dict, token_header: str, token: str, request_name: str) -> tuple[bool, str]:
    if not url:
        logger.error("DX CRM %s URL is not configured", request_name)
        return False, "The request service is not configured. Please try again later."

    headers = {"Accept": "application/json"}
    if token:
        headers[token_header] = token
    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=float(_setting("CRM_TIMEOUT_SECONDS", "15")),
        )
        response.raise_for_status()
        return True, ""
    except httpx.HTTPStatusError as exc:
        logger.warning("DX CRM %s rejected with status %s", request_name, exc.response.status_code)
        return False, "CRM rejected the request. Please check the form and try again."
    except httpx.HTTPError:
        logger.exception("DX CRM %s failed", request_name)
        return False, "The request service is temporarily unavailable. Please try again later."


def submit_consultation_request(payload: dict[str, str]) -> tuple[bool, str]:
    return _submit(
        _setting("CRM_API_URL"),
        payload,
        "X-Consultation-Token",
        _setting("CRM_CONSULTATION_TOKEN"),
        "consultation request",
    )


def submit_activity_registration(payload: dict) -> tuple[bool, str, dict | None]:
    url = _setting("CRM_ACTIVITY_REGISTRATION_URL")
    if not url:
        logger.error("DX CRM activity registration URL is not configured")
        return False, "The registration service is not configured. Please try again later.", None

    headers = {"Accept": "application/json"}
    token = _setting("CRM_ACTIVITY_TOKEN")
    if token:
        headers["X-Activity-Token"] = token
    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=float(_setting("CRM_TIMEOUT_SECONDS", "15")),
        )
    except httpx.HTTPError:
        logger.exception("DX CRM activity registration failed")
        return False, "The registration service is temporarily unavailable. Please try again later.", None

    if response.status_code == 201:
        try:
            result = response.json()
        except ValueError:
            logger.error("DX CRM activity registration returned invalid JSON")
            return False, "The registration service returned an invalid response. Please try again later.", None
        if result.get("registration_id") is None:
            logger.error("DX CRM activity registration response omitted registration_id")
            return False, "The registration service returned an incomplete response. Please try again later.", None
        return True, "", result
    if response.status_code == 401:
        logger.warning("DX CRM activity registration rejected an invalid or missing token")
        return False, "The registration service token is invalid or missing. Please contact CAIM.", None
    if response.status_code == 422:
        logger.warning("DX CRM activity registration rejected invalid request data")
        return False, "The registration information is invalid. Please check the form and try again.", None

    logger.warning("DX CRM activity registration rejected with status %s", response.status_code)
    return False, "CRM rejected the registration. Please try again later.", None
