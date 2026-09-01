from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://gkmex.com"
__version__ = "1.0.0"
USER_AGENT = f"gkmex-python/{__version__}"


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


def _decode_sse(payload: bytes):
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GkmexError("Gkmex returned malformed SSE") from exc

    documents = []
    data_lines = []
    for line in text.splitlines():
        if line == "":
            if data_lines:
                event_data = "\n".join(data_lines)
                try:
                    documents.append(json.loads(event_data))
                except json.JSONDecodeError as exc:
                    raise GkmexError("Gkmex returned malformed SSE") from exc
                data_lines = []
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if separator and field == "data":
            data_lines.append(value[1:] if value.startswith(" ") else value)

    if data_lines:
        try:
            documents.append(json.loads("\n".join(data_lines)))
        except json.JSONDecodeError as exc:
            raise GkmexError("Gkmex returned malformed SSE") from exc
    if not documents:
        raise GkmexError("Gkmex returned malformed SSE")
    return documents[-1]


def _validated_mcp_result(envelope, *, request_id: int):
    if (
        not isinstance(envelope, dict)
        or envelope.get("jsonrpc") != "2.0"
        or envelope.get("id") != request_id
        or (("result" in envelope) == ("error" in envelope))
    ):
        raise GkmexError("Gkmex returned an unexpected JSON-RPC envelope")

    if "error" in envelope:
        error = envelope["error"]
        if not isinstance(error, dict):
            raise GkmexError("Gkmex returned an unexpected JSON-RPC envelope")
        code = error.get("code")
        message = error.get("message")
        if not isinstance(code, int) or isinstance(code, bool):
            raise GkmexError("Gkmex returned an unexpected JSON-RPC envelope")
        if not isinstance(message, str) or not message:
            message = "Gkmex MCP request failed"
        raise GkmexError(
            message,
            code=code,
            details=error.get("data"),
        )

    result = envelope["result"]
    if not isinstance(result, dict):
        raise GkmexError("Gkmex returned an unexpected MCP result")
    is_error = result.get("isError", False)
    if not isinstance(is_error, bool):
        raise GkmexError("Gkmex returned an unexpected MCP result")
    if is_error:
        message = "Gkmex MCP tool failed"
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "text":
                    continue
                candidate = item.get("text")
                if isinstance(candidate, str) and candidate:
                    message = candidate
                    break
        raise GkmexError(message, details=result)

    structured = result.get("structuredContent")
    if not isinstance(structured, dict):
        raise GkmexError("Gkmex returned an unexpected MCP result")
    count = structured.get("count")
    data = structured.get("data")
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or not isinstance(data, list)
        or count != len(data)
    ):
        raise GkmexError("Gkmex returned an unexpected MCP result")
    return structured


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

    def compare_cranes(self, ids):
        message = "ids must contain two to five unique public crane IDs"
        if not isinstance(ids, (list, tuple)):
            raise GkmexError(message)
        try:
            canonical = [_canonical_id(value, field="ids") for value in ids]
        except GkmexError as exc:
            raise GkmexError(message) from exc
        if not 2 <= len(canonical) <= 5 or len(set(canonical)) != len(canonical):
            raise GkmexError(message)

        envelope = self._request_document(
            "POST",
            "mcp",
            body={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "compare_cranes",
                    "arguments": {"ids": canonical},
                },
            },
            accept="application/json, text/event-stream",
            allow_sse=True,
        )
        return _validated_mcp_result(envelope, request_id=1)

    def _request_json(
        self,
        method: str,
        target: str,
        *,
        body=None,
        accept="application/json",
    ):
        return self._request_document(
            method,
            target,
            body=body,
            accept=accept,
            allow_sse=False,
        )

    def _request_document(
        self,
        method: str,
        target: str,
        *,
        body=None,
        accept="application/json",
        allow_sse: bool,
    ):
        url = urllib.parse.urljoin(self.base_url, target)
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": accept, "User-Agent": USER_AGENT}
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
        if _is_json_media_type(media_type):
            return _decode_json(payload)
        if allow_sse and media_type == "text/event-stream":
            return _decode_sse(payload)
        raise GkmexError("Gkmex returned an unsupported media type")
