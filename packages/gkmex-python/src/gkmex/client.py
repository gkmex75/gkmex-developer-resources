from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://gkmex.com"


class GkmexError(Exception):
    def __init__(self, message: str, *, status=None, code=None, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details


def _canonical_id(value: Any, *, field: str = "id") -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or value in {".", ".."}
    ):
        raise GkmexError(f"{field} must be a canonical public crane ID")
    return value


def _non_empty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise GkmexError(f"{field} must be a non-empty unpadded string")
    return value


def _integer_in_range(
    value: Any,
    *,
    field: str,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GkmexError(f"{field} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        if maximum is None:
            raise GkmexError(f"{field} must be {minimum} or greater")
        raise GkmexError(
            f"{field} must be between {minimum} and {maximum}"
        )
    return value


def _media_type(headers) -> str:
    if headers is None:
        return ""
    return headers.get("Content-Type", "").split(";", 1)[0].strip().lower()


def _is_json_media_type(value: str) -> bool:
    return value == "application/json" or (
        value.startswith("application/") and value.endswith("+json")
    )


def _decode_json(payload: bytes):
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GkmexError("Gkmex returned invalid JSON") from exc


def _decode_error_body(payload: bytes, media_type: str):
    if not _is_json_media_type(media_type):
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


class GkmexClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 20):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

    def list_cranes(
        self,
        *,
        brand=None,
        type=None,
        limit=None,
        offset=None,
        cursor=None,
    ):
        if brand is not None:
            brand = _non_empty_string(brand, field="brand")
        if type is not None and type not in {"mobile", "crawler"}:
            raise GkmexError("type must be mobile or crawler")
        if limit is not None:
            limit = _integer_in_range(
                limit,
                field="limit",
                minimum=1,
                maximum=100,
            )
        if offset is not None:
            offset = _integer_in_range(offset, field="offset", minimum=0)
        if cursor is not None:
            cursor = _non_empty_string(cursor, field="cursor")
        if offset is not None and cursor is not None:
            raise GkmexError("offset and cursor cannot be used together")
        query = urllib.parse.urlencode(
            [
                (key, value)
                for key, value in (
                    ("brand", brand),
                    ("type", type),
                    ("limit", limit),
                    ("offset", offset),
                    ("cursor", cursor),
                )
                if value is not None
            ]
        )
        target = "api/v1/cranes" + ("?" + query if query else "")
        return self._request_json("GET", target)

    def get_crane(self, id: str):
        id = _canonical_id(id)
        return self._request_json(
            "GET",
            "api/v1/cranes/" + urllib.parse.quote(id, safe=""),
        )

    def _request_json(
        self,
        method: str,
        target: str,
        *,
        body=None,
        accept="application/json",
    ):
        url = urllib.parse.urljoin(self.base_url, target)
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": accept}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
                media_type = _media_type(response.headers)
        except urllib.error.HTTPError as exc:
            error_payload = exc.read()
            details = _decode_error_body(
                error_payload,
                _media_type(exc.headers),
            )
            message = f"Gkmex request failed with HTTP {exc.code}"
            if isinstance(details, dict):
                for key in ("error", "message"):
                    candidate = details.get(key)
                    if isinstance(candidate, str) and candidate:
                        message = candidate
                        break
            raise GkmexError(
                message,
                status=exc.code,
                details=details,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise GkmexError("Unable to reach Gkmex") from exc
        if not _is_json_media_type(media_type):
            raise GkmexError("Gkmex returned an unsupported media type")
        return _decode_json(payload)
