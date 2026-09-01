from __future__ import annotations

import json
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://gkmex.com"


class GkmexError(Exception):
    def __init__(self, message: str, *, status=None, code=None, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details


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
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = response.read()
            media_type = (
                response.headers.get("Content-Type", "")
                .split(";", 1)[0]
                .lower()
            )
        if media_type != "application/json":
            raise GkmexError("Gkmex returned an unsupported media type")
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GkmexError("Gkmex returned invalid JSON") from exc
