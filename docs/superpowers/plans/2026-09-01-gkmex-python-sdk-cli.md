# Gkmex Python SDK and CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `gkmex==1.0.0` as the official zero-dependency Python SDK and JSON CLI for Gkmex's public, zero-auth, read-only crane inventory, then expose the verified PyPI package through Gkmex's generated developer-discovery surfaces.

**Architecture:** Add an independently buildable `src`-layout Python package under `packages/gkmex-python` in `gkmex-developer-resources`. One synchronous `GkmexClient` owns REST and MCP transport through the Python standard library; the CLI delegates to that client. PyPI publication is a hard gate: the separate `gkmex-site` generator change starts only after the exact wheel installs and passes a production read-only smoke test from PyPI.

**Tech Stack:** Python 3.10+, `urllib.request`, `json`, `argparse`, `unittest`, `http.server`, PEP 517/setuptools, `build`, `twine`, GitHub CLI, Cloudflare Pages tooling.

---

## Scope, Repositories, and Safety Gates

Developer-resources files created:

- `packages/gkmex-python/pyproject.toml`
- `packages/gkmex-python/LICENSE`
- `packages/gkmex-python/README.md`
- `packages/gkmex-python/src/gkmex/__init__.py`
- `packages/gkmex-python/src/gkmex/client.py`
- `packages/gkmex-python/src/gkmex/cli.py`
- `packages/gkmex-python/tests/__init__.py`
- `packages/gkmex-python/tests/helpers.py`
- `packages/gkmex-python/tests/test_client.py`
- `packages/gkmex-python/tests/test_cli.py`
- `packages/gkmex-python/tests/test_package.py`

Post-publication site files modified in a fresh `gkmex-site` worktree:

- `build_site.py`
- `tests/test_build_site.py`
- generated discovery artifacts under `site/`

Repository constraints:

- The current `gkmex-developer-resources` local `main` contains 17 reviewed commits not yet on `origin/main`, including the already-published npm package and this design. Preserve this ancestry; never reset or rebase it onto the older remote in a way that drops those commits.
- The primary `gkmex-site` checkout contains unrelated dirty generated inventory work and is behind `origin/main`. Do not edit, clean, stash, or reset that checkout. Create a fresh worktree from the fetched `origin/main` after PyPI verification.
- Never write a PyPI token to a file, command argument, shell history, log, plan, or generated configuration. Use Twine's interactive hidden password prompt.
- All production calls in this plan are read-only until the explicit PyPI upload, GitHub merge, and Cloudflare deploy steps.
- Do not run Ora.ai as package acceptance. A new measurement is a separate follow-up after the release is live.

## Task 0: Establish a Safe Feature Baseline

**Files:** None.

- [ ] **Step 1: Read the approved design and confirm the repository graph**

Run:

```bash
cd /Users/gokmentanacar/projects/gkmex-developer-resources
git fetch origin
git status --short --branch
git log --oneline --left-right origin/main...main
git rev-parse main
```

Expected: the checkout is clean apart from the plan commit being prepared, and local `main` is strictly ahead of `origin/main`. The approved design is `docs/superpowers/specs/2026-09-01-gkmex-python-sdk-cli-design.md`.

- [ ] **Step 2: Create the implementation branch from local main**

Use the `using-git-worktrees` skill if execution needs isolation. Whether using a worktree or the current clean checkout, branch from local `main`, not `origin/main`:

```bash
git switch -c feat/python-sdk-cli main
git merge-base --is-ancestor ce9fd7e HEAD
```

Expected: exit `0`; the Python design commit and all npm-package commits remain ancestors.

- [ ] **Step 3: Record the untouched baseline**

Run:

```bash
git status --short
python3 --version
```

Expected: no output from `git status --short`; Python is 3.10 or newer.

## Task 1: Package Metadata and First REST Success Path

**Files:**

- Create: `packages/gkmex-python/pyproject.toml`
- Create: `packages/gkmex-python/LICENSE`
- Create: `packages/gkmex-python/src/gkmex/__init__.py`
- Create: `packages/gkmex-python/src/gkmex/client.py`
- Create: `packages/gkmex-python/tests/__init__.py`
- Create: `packages/gkmex-python/tests/helpers.py`
- Create: `packages/gkmex-python/tests/test_client.py`

- [ ] **Step 1: Add the independently buildable package metadata**

Create `packages/gkmex-python/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "gkmex"
version = "1.0.0"
description = "Official zero-auth Python SDK and CLI for the public Gkmex used-crane inventory"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [{ name = "Gkmex Cranes", email = "info@gkmex.com" }]
keywords = ["gkmex", "cranes", "sdk", "cli", "mcp", "inventory"]
classifiers = [
  "Development Status :: 5 - Production/Stable",
  "Environment :: Console",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
  "Topic :: Software Development :: Libraries :: Python Modules",
]
dependencies = []

[project.urls]
Homepage = "https://gkmex.com/developers"
Documentation = "https://gkmex.com/developers"
Source = "https://github.com/gkmex75/gkmex-developer-resources/tree/main/packages/gkmex-python"
Issues = "https://github.com/gkmex75/gkmex-developer-resources/issues"

[project.scripts]
gkmex = "gkmex.cli:main"

[tool.setuptools]
package-dir = { "" = "src" }

[tool.setuptools.packages.find]
where = ["src"]
```

Copy the repository MIT license byte-for-byte to `packages/gkmex-python/LICENSE`. Create `tests/__init__.py` as an empty package marker so shared test helpers import consistently on Python 3.10.

- [ ] **Step 2: Add a real loopback HTTP helper**

Create `tests/helpers.py` with a `ThreadingHTTPServer` context manager, request-body reader, and JSON/SSE responders:

```python
import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


def read_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    return handler.rfile.read(length)


def _send(handler, status, media_type, payload):
    handler.send_response(status)
    handler.send_header("Content-Type", media_type)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def send_json(handler, status, payload):
    _send(
        handler,
        status,
        "application/json; charset=utf-8",
        json.dumps(payload).encode("utf-8"),
    )


def send_sse(handler, payload):
    _send(handler, 200, "text/event-stream; charset=utf-8", payload.encode("utf-8"))


@contextmanager
def serve(route):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route(self, requests)

        def do_POST(self):
            route(self, requests)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}", requests
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
```

- [ ] **Step 3: Write failing REST success tests**

Create `tests/test_client.py` with these first concrete cases:

```python
import unittest
import urllib.parse
from unittest.mock import MagicMock, patch

from gkmex import GkmexClient, GkmexError
from tests.helpers import send_json, serve


class ClientTests(unittest.TestCase):
    def test_list_cranes_maps_only_supported_non_none_filters(self):
        expected = {
            "count": 1,
            "data": [{"id": "crane-1", "price_eur": 120000}],
        }

        def route(handler, requests):
            requests.append((handler.command, handler.path, handler.headers))
            send_json(handler, 200, expected)

        with serve(route) as (base_url, requests):
            result = GkmexClient(base_url).list_cranes(
                brand="Liebherr", type="mobile", limit=2, offset=1
            )

        method, target, headers = requests[0]
        parsed = urllib.parse.urlsplit(target)
        self.assertEqual(method, "GET")
        self.assertEqual(parsed.path, "/api/v1/cranes")
        self.assertEqual(
            urllib.parse.parse_qs(parsed.query),
            {
                "brand": ["Liebherr"],
                "type": ["mobile"],
                "limit": ["2"],
                "offset": ["1"],
            },
        )
        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(result, expected)

    def test_get_crane_percent_encodes_the_id_and_preserves_poa(self):
        expected = {
            "id": "id/with space",
            "price_eur": None,
            "url": "https://gkmex.com/en/crane/id%2Fwith%20space",
        }

        def route(handler, requests):
            requests.append(handler.path)
            send_json(handler, 200, expected)

        with serve(route) as (base_url, requests):
            result = GkmexClient(base_url).get_crane("id/with space")

        self.assertEqual(requests, ["/api/v1/cranes/id%2Fwith%20space"])
        self.assertIsNone(result["price_eur"])
        self.assertEqual(result, expected)

    def test_base_url_path_and_timeout_apply_to_every_request(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"count":0,"data":[]}'
        response.headers = {"Content-Type": "application/json"}
        with patch("gkmex.client.urllib.request.urlopen", return_value=response) as open_url:
            result = GkmexClient("https://example.test/prefix", timeout=7).list_cranes()

        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.test/prefix/api/v1/cranes")
        self.assertEqual(open_url.call_args.kwargs["timeout"], 7)
        self.assertEqual(result, {"count": 0, "data": []})
```

- [ ] **Step 4: Run the tests and verify RED**

Run:

```bash
cd packages/gkmex-python
PYTHONPATH=src python3 -m unittest tests.test_client -v
```

Expected: import failure because `src/gkmex` does not exist yet.

- [ ] **Step 5: Implement the minimal public import and REST transport**

Create `src/gkmex/__init__.py`:

```python
from .client import GkmexClient, GkmexError

__all__ = ["GkmexClient", "GkmexError", "__version__"]
__version__ = "1.0.0"
```

Create `src/gkmex/client.py` with these concrete primitives:

```python
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


class GkmexClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 20):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

    def list_cranes(self, *, brand=None, type=None, limit=None, offset=None, cursor=None):
        query = urllib.parse.urlencode(
            [(key, value) for key, value in (
                ("brand", brand), ("type", type), ("limit", limit),
                ("offset", offset), ("cursor", cursor),
            ) if value is not None]
        )
        path = "api/v1/cranes" + ("?" + query if query else "")
        return self._request_json("GET", path)

    def get_crane(self, id: str):
        return self._request_json(
            "GET", "api/v1/cranes/" + urllib.parse.quote(id, safe="")
        )

    def _request_json(self, method: str, path: str, *, body=None, accept="application/json"):
        url = urllib.parse.urljoin(self.base_url, path)
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": accept}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = response.read()
            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if media_type != "application/json":
            raise GkmexError("Gkmex returned an unsupported media type")
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GkmexError("Gkmex returned invalid JSON") from exc
```

This is deliberately incomplete for error normalization and input validation; the next test task drives those changes.

- [ ] **Step 6: Run REST success tests and commit GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_client -v
git add packages/gkmex-python
git commit -m "feat: add Gkmex Python REST client"
```

Expected: the three REST success tests pass.

## Task 2: Stable Validation and Transport Errors

**Files:**

- Modify: `packages/gkmex-python/tests/test_client.py`
- Modify: `packages/gkmex-python/src/gkmex/client.py`

- [ ] **Step 1: Add failing validation tests**

Add table-driven tests for these exact local failures, and patch `urlopen` to prove it is never called:

```python
invalid_get_ids = (None, "", " crane-1", "crane-1 ", ".", "..")
invalid_comparisons = (
    [], ["one"], ["one", "one"],
    ["1", "2", "3", "4", "5", "6"],
    ["one", ""], ["one", " two"],
)
```

Also assert:

- `limit` rejects booleans, zero, negative values, and values over 100;
- `offset` rejects booleans and negative values;
- `type` rejects values other than `mobile` and `crawler`;
- `offset` and `cursor` cannot be supplied together;
- non-string or empty `brand`/`cursor` inputs are rejected locally with concise messages.

- [ ] **Step 2: Add failing HTTP, media-type, JSON, timeout, and network tests**

Test these exact mappings:

- HTTP 404 JSON `{"error":"Crane not found"}` -> `GkmexError("Crane not found", status=404, details=<dict>)`;
- HTTP 500 plain text -> status 500 and generic `Gkmex request failed with HTTP 500` without leaking markup;
- HTTP 200 text/plain -> `Gkmex returned an unsupported media type`;
- malformed UTF-8 or JSON -> `Gkmex returned invalid JSON` with exception chaining;
- `urllib.error.URLError`, `TimeoutError`, and `OSError` -> `Unable to reach Gkmex` with exception chaining.

- [ ] **Step 3: Run the focused tests and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_client -v
```

Expected: failures in local validation and normalized transport errors.

- [ ] **Step 4: Add focused validators and one guarded request path**

Implement private helpers with these contracts:

```python
def _canonical_id(value: Any, *, field: str = "id") -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or value in {".", ".."}
    ):
        raise GkmexError(f"{field} must be a canonical public crane ID")
    return value


def _decode_error_body(payload: bytes, media_type: str):
    if media_type != "application/json":
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
```

Update `_request_json` to catch `urllib.error.HTTPError` before `urllib.error.URLError`; retain the original exception with a concrete chained raise such as `raise GkmexError("Gkmex returned invalid JSON") from exc`. Read at most the public error response returned by the server, set `details` only when JSON safely decodes, and derive a message only from a string `error` or string `message` field.

Add small integer/string validators; do not introduce a schema framework or dataclass layer. Validate list arguments before URL construction.

- [ ] **Step 5: Run the full client suite and commit GREEN**

```bash
PYTHONPATH=src python3 -m unittest tests.test_client -v
git add packages/gkmex-python/src/gkmex/client.py packages/gkmex-python/tests/test_client.py
git commit -m "fix: validate Gkmex Python requests and errors"
```

Expected: all REST and error tests pass; no network call occurs for invalid inputs.

## Task 3: MCP Comparison over JSON and SSE

**Files:**

- Modify: `packages/gkmex-python/tests/test_client.py`
- Modify: `packages/gkmex-python/src/gkmex/client.py`

- [ ] **Step 1: Add failing JSON MCP contract tests**

The local server must assert this exact request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "compare_cranes",
    "arguments": {"ids": ["crane-1", "crane-2"]}
  }
}
```

Assert `POST /mcp`, `Content-Type: application/json`, and `Accept: application/json, text/event-stream`. Return a valid JSON-RPC result whose `structuredContent` is:

```json
{"count": 2, "data": [{"id": "crane-1"}, {"id": "crane-2"}]}
```

Assert that `compare_cranes` returns that dict unchanged and in caller order.

- [ ] **Step 2: Add failing SSE and malformed-envelope tests**

Add an SSE success response using:

```text
: keepalive
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"structuredContent":{"count":2,"data":[{"id":"crane-1"},{"id":"crane-2"}]},"isError":false}}

```

Add cases for:

- no SSE `data:` event;
- invalid JSON in an SSE data event;
- `jsonrpc` not equal to `2.0`;
- response ID not equal to request ID `1`;
- JSON-RPC `error` mapping `code` and `data` to `GkmexError`;
- `result.isError == true`;
- missing/non-dict `structuredContent`;
- non-list `data`, non-integer `count`, or `count != len(data)`.

- [ ] **Step 3: Run and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_client -v
```

Expected: `GkmexClient` has no working `compare_cranes` implementation.

- [ ] **Step 4: Implement the JSON-RPC request and SSE decoder**

Add:

```python
    def compare_cranes(self, ids):
        if not isinstance(ids, (list, tuple)):
            raise GkmexError("ids must contain two to five unique public crane IDs")
        canonical = [_canonical_id(value, field="ids") for value in ids]
        if not 2 <= len(canonical) <= 5 or len(set(canonical)) != len(canonical):
            raise GkmexError("ids must contain two to five unique public crane IDs")
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
            allowed_media_types={"application/json", "text/event-stream"},
        )
        return _validated_mcp_result(envelope, request_id=1)
```

Refactor the transport once into `_request_document`, which chooses JSON or SSE decoding by media type. `_decode_sse` must ignore comments and non-`data` fields, join consecutive `data:` lines within an event with `\n`, JSON-decode each completed data event, and return the final decoded JSON-RPC document. It must reject an empty or malformed event stream with `GkmexError` and chain JSON/Unicode errors.

`_validated_mcp_result` must validate the JSON-RPC version and request ID before inspecting `error` or `result`. For tool errors, prefer a text item from public `result.content` only when it is a non-empty string; otherwise use `Gkmex MCP tool failed`.

- [ ] **Step 5: Run all client tests and commit GREEN**

```bash
PYTHONPATH=src python3 -m unittest tests.test_client -v
git add packages/gkmex-python/src/gkmex/client.py packages/gkmex-python/tests/test_client.py
git commit -m "feat: add Gkmex Python crane comparison"
```

Expected: JSON and SSE comparison tests pass, POA remains `None`, and malformed MCP responses are normalized.

## Task 4: Deterministic JSON CLI

**Files:**

- Create: `packages/gkmex-python/src/gkmex/cli.py`
- Create: `packages/gkmex-python/tests/test_cli.py`

- [ ] **Step 1: Write subprocess-based CLI tests**

Create a helper that launches the source CLI without installing it:

```python
def run_cli(*args, base_url=None):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    if base_url is not None:
        env["GKMEX_BASE_URL"] = base_url
    return subprocess.run(
        [sys.executable, "-m", "gkmex.cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
```

Add concrete tests for:

- `list --brand Liebherr --type mobile --limit 5` -> JSON stdout, newline, exit 0;
- `get crane-1` -> one JSON record, exit 0;
- `compare crane-1 crane-2` -> MCP result JSON, exit 0;
- `--help` -> usage stdout and exit 0;
- `--version` -> exactly `gkmex 1.0.0\n` and exit 0;
- invalid type, limit 0/101, negative offset, cursor plus offset, empty brand/cursor, non-canonical ID, one comparison ID, duplicate IDs, and six IDs -> usage on stderr and exit 2;
- API/network failure -> one concise stderr line, no traceback, exit 1;
- piping a large successful result into a consumer that closes immediately -> no traceback and exit 0.

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli -v
```

Expected: `gkmex.cli` is missing.

- [ ] **Step 3: Implement one argparse adapter over the SDK**

Create `src/gkmex/cli.py` with this parser structure:

```python
def _non_empty(value):
    if not value or value != value.strip():
        raise argparse.ArgumentTypeError("value must be non-empty and unpadded")
    return value


def _public_id(value):
    value = _non_empty(value)
    if value in {".", ".."}:
        raise argparse.ArgumentTypeError("ID must be a canonical public crane ID")
    return value


def _limit(value):
    parsed = int(value)
    if not 1 <= parsed <= 100:
        raise argparse.ArgumentTypeError("limit must be between 1 and 100")
    return parsed


def _offset(value):
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("offset must be zero or greater")
    return parsed


def build_parser():
    parser = argparse.ArgumentParser(prog="gkmex")
    parser.add_argument("--version", action="version", version=f"gkmex {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    listing = commands.add_parser("list", help="List published cranes")
    listing.add_argument("--brand", type=_non_empty)
    listing.add_argument("--type", choices=("mobile", "crawler"))
    listing.add_argument("--limit", type=_limit)
    pagination = listing.add_mutually_exclusive_group()
    pagination.add_argument("--offset", type=_offset)
    pagination.add_argument("--cursor", type=_non_empty)

    get = commands.add_parser("get", help="Get one published crane")
    get.add_argument("id", type=_public_id)

    compare = commands.add_parser("compare", help="Compare two to five cranes")
    compare.add_argument("ids", nargs="+", type=_public_id)
    return parser
```

`main(argv=None)` must:

1. parse arguments and call `parser.error` if comparison length is outside two-to-five or contains duplicate IDs;
2. construct `GkmexClient(base_url=os.environ.get("GKMEX_BASE_URL", DEFAULT_BASE_URL))`;
3. delegate to exactly one client method;
4. write `json.dump(result, sys.stdout, ensure_ascii=False, indent=2)` plus `\n`;
5. catch only `GkmexError` for exit 1 and `BrokenPipeError` for exit 0, closing stdout inside a nested guarded `try` so interpreter shutdown cannot emit a second broken-pipe error;
6. print ordinary errors as `gkmex: <message>\n` to stderr without a traceback.

End the module with:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI and client suites and commit GREEN**

```bash
PYTHONPATH=src python3 -m unittest tests.test_client tests.test_cli -v
git add packages/gkmex-python/src/gkmex/cli.py packages/gkmex-python/tests/test_cli.py
git commit -m "feat: add Gkmex Python JSON CLI"
```

Expected: all SDK/CLI tests pass; no CLI failure prints a traceback.

## Task 5: README and Artifact Acceptance

**Files:**

- Create: `packages/gkmex-python/README.md`
- Create: `packages/gkmex-python/tests/test_package.py`
- Modify if tests expose an issue: `packages/gkmex-python/pyproject.toml`

- [ ] **Step 1: Write failing package-contract tests**

Using only `unittest`, `tomllib`, `pathlib`, and `subprocess`, assert:

- distribution name, version, Python floor, console script, source layout, and empty runtime dependency list;
- `README.md` and `LICENSE` exist;
- README contains `pip install gkmex`, SDK examples for all three methods, all three CLI commands, `zero-auth`, `read-only`, `price_eur`, `None`, `POA`, and a final-availability confirmation boundary;
- the README does not claim reservation, guaranteed availability, authenticated access, or a write API;
- `from gkmex import GkmexClient, GkmexError, __version__` works and reports `1.0.0`.

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=src python3 -m unittest tests.test_package -v
```

Expected: README-related assertions fail.

- [ ] **Step 3: Write the package README**

The README must include these executable examples verbatim:

```bash
pip install gkmex
gkmex list --brand Liebherr --limit 5
gkmex get PUBLIC_ID
gkmex compare PUBLIC_ID PUBLIC_ID
```

```python
from gkmex import GkmexClient

client = GkmexClient()
inventory = client.list_cranes(brand="Liebherr", limit=5)
crane = client.get_crane(inventory["data"][0]["id"])
comparison = client.compare_cranes([
    inventory["data"][0]["id"],
    inventory["data"][1]["id"],
])
```

State clearly that no token/account is required, all methods are read-only, `price_eur: null` becomes `None` and means POA rather than zero, a listing is not a reservation, and final specifications/availability require direct Gkmex confirmation. Link every example crane through the public `url` field rather than inventing a URL.

- [ ] **Step 4: Run the complete source suite and commit GREEN**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
git add packages/gkmex-python
git commit -m "docs: prepare Gkmex Python package"
```

Expected: all tests pass.

- [ ] **Step 5: Build and inspect wheel and source distribution**

Create an isolated release-tool environment and output directory outside the package tree:

```bash
python3 -m venv /tmp/gkmex-python-release-tools
/tmp/gkmex-python-release-tools/bin/python -m pip install --upgrade pip build twine
cd packages/gkmex-python
/tmp/gkmex-python-release-tools/bin/python -m build --outdir /tmp/gkmex-python-dist-1.0.0-unpublished
/tmp/gkmex-python-release-tools/bin/python -m twine check /tmp/gkmex-python-dist-1.0.0-unpublished/*
tar -tzf /tmp/gkmex-python-dist-1.0.0-unpublished/gkmex-1.0.0.tar.gz
/tmp/gkmex-python-release-tools/bin/python -m zipfile -l /tmp/gkmex-python-dist-1.0.0-unpublished/gkmex-1.0.0-py3-none-any.whl
```

Expected: one sdist and one universal wheel; Twine reports both `PASSED`. Archive listings contain only metadata, README, LICENSE, and `gkmex/__init__.py`, `client.py`, `cli.py` plus source tests in the sdist. They contain no token, `.env`, build cache, unrelated npm package, or developer machine path.

- [ ] **Step 6: Install the exact wheel into a clean environment**

```bash
python3 -m venv /tmp/gkmex-python-wheel-smoke
/tmp/gkmex-python-wheel-smoke/bin/python -m pip install --no-deps /tmp/gkmex-python-dist-1.0.0-unpublished/gkmex-1.0.0-py3-none-any.whl
/tmp/gkmex-python-wheel-smoke/bin/python -c 'from gkmex import GkmexClient, GkmexError, __version__; assert __version__ == "1.0.0"'
/tmp/gkmex-python-wheel-smoke/bin/gkmex --version
/tmp/gkmex-python-wheel-smoke/bin/gkmex list --limit 1
```

Expected: version is `gkmex 1.0.0`; the production list command returns JSON with `count`, `data`, and a real public crane `url`. This is read-only.

## Task 6: Adversarial Review and Developer-Resources Merge

**Files:** Only fixes proven necessary by review.

- [ ] **Step 1: Run a focused contract audit**

Run:

```bash
cd /Users/gokmentanacar/projects/gkmex-developer-resources
rg -n "TODO|FIXME|TBD|placeholder|example\.com|API[_ -]?KEY|TOKEN|PASSWORD" packages/gkmex-python
rg -n "reservation|guaranteed availability|final availability" packages/gkmex-python
PYTHONPATH=packages/gkmex-python/src python3 -m unittest discover -s packages/gkmex-python/tests -v
git diff --check
git status --short
```

Expected: no placeholder or credential material; only the explicit statement that listings are not reservations and final availability needs confirmation; tests pass; diff check is clean.

- [ ] **Step 2: Request code review and fix only verified findings**

Use the `requesting-code-review` skill. Review against the approved design, AGENTS rules, Python 3.10 compatibility, URL joining/encoding, HTTP exception order, JSON/SSE envelope validation, CLI exit codes, artifact allowlist, and credential hygiene.

For every accepted finding, first add or tighten a failing test, then implement the smallest fix and rerun the focused suite. Commit each coherent fix separately.

- [ ] **Step 3: Rebuild from a clean tree after review**

Build into a new `mktemp -d` output directory, run Twine check, reinstall the exact wheel into a new temporary virtual environment, and repeat the read-only production smoke from Task 5. Do not reuse or delete a pre-review wheel.

- [ ] **Step 4: Publish the accumulated local history through one reviewed PR**

Run:

```bash
git status --short
git push -u origin feat/python-sdk-cli
gh pr create --base main --head feat/python-sdk-cli --title "Publish Gkmex Python SDK and CLI" --body-file /tmp/gkmex-python-pr-body.md
gh pr checks --watch
```

The PR body must disclose that the branch also contains the previously completed local npm package history absent from `origin/main`; summarize both package test suites and the exact wheel smoke. Review the full `origin/main...HEAD` diff before merge so none of those 17 commits are accidentally omitted.

Merge only after checks and review pass:

```bash
gh pr merge --merge --delete-branch
git fetch origin
git log --oneline --decorate origin/main -5
```

Record the developer-resources merge SHA. PyPI artifacts in the next task must be rebuilt from that merged source state, not from the pre-merge branch.

## Task 7: PyPI Name Gate, Upload, and Public Install

**Files:** None.

- [ ] **Step 1: Recheck the exact PyPI name immediately before upload**

Run:

```bash
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://pypi.org/pypi/gkmex/json
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://pypi.org/simple/gkmex/
```

Expected before first publication: both return HTTP 404. If either resolves to a project not owned by Gkmex, stop. Do not rename or publish a lookalike package without a new owner decision.

- [ ] **Step 2: Check out the exact merged developer-resources commit and rebuild**

In a clean checkout/worktree at the recorded merge SHA:

```bash
cd packages/gkmex-python
python3 -m venv /tmp/gkmex-python-final-release
/tmp/gkmex-python-final-release/bin/python -m pip install --upgrade pip build twine
PYTHONPATH=src /tmp/gkmex-python-final-release/bin/python -m unittest discover -s tests -v
/tmp/gkmex-python-final-release/bin/python -m build --outdir /tmp/gkmex-python-final-dist-1.0.0
/tmp/gkmex-python-final-release/bin/python -m twine check /tmp/gkmex-python-final-dist-1.0.0/*
```

Inspect both archive listings again and install the exact final wheel with `--no-deps` in a separate empty venv. Expected: all acceptance checks from Task 5 pass.

- [ ] **Step 3: Upload with Twine's interactive hidden prompt**

Run:

```bash
/tmp/gkmex-python-final-release/bin/python -m twine upload /tmp/gkmex-python-final-dist-1.0.0/*
```

At Twine's prompt, enter username `__token__` and paste the PyPI token as the hidden password. Do not place the token in the command, environment file, `.pypirc`, clipboard transcript, or chat. If authentication is unavailable or rejected, stop here and leave the website unchanged.

Expected: both `gkmex-1.0.0.tar.gz` and `gkmex-1.0.0-py3-none-any.whl` upload successfully.

- [ ] **Step 4: Verify registry metadata and a clean public install**

Wait only for PyPI's normal index propagation, then run:

```bash
curl --fail --silent --show-error https://pypi.org/pypi/gkmex/1.0.0/json > /tmp/gkmex-pypi-1.0.0.json
python3 -c 'import json; p=json.load(open("/tmp/gkmex-pypi-1.0.0.json")); assert p["info"]["name"] == "gkmex"; assert p["info"]["version"] == "1.0.0"; assert p["info"]["requires_dist"] in (None, [])'
python3 -m venv /tmp/gkmex-python-public-smoke
/tmp/gkmex-python-public-smoke/bin/python -m pip install --no-cache-dir gkmex==1.0.0
/tmp/gkmex-python-public-smoke/bin/python -c 'from gkmex import GkmexClient; r=GkmexClient().list_cranes(limit=1); assert r["data"][0]["url"].startswith("https://gkmex.com/")'
/tmp/gkmex-python-public-smoke/bin/gkmex --version
```

Expected: public JSON metadata matches, the wheel installs without runtime dependencies, import succeeds, production read returns a canonical Gkmex URL, and the CLI prints `gkmex 1.0.0`.

## Task 8: Post-Publication Website Discovery PR

**Files in `gkmex-site`:**

- Modify: `build_site.py`
- Modify: `tests/test_build_site.py`
- Regenerate: `site/developers/index.html`
- Regenerate: `site/developers.md`
- Regenerate: `site/llms.txt`
- Regenerate: `site/.well-known/llms.txt`
- Regenerate: `site/llms-full.txt`
- Regenerate: `site/index.md`
- Regenerate: `site/agents.md`
- Regenerate: `site/inventory/llms.txt`
- Regenerate: `site/developers/llms.txt`
- Regenerate: `site/api/llms.txt`
- Regenerate: `site/.well-known/api-catalog`

- [ ] **Step 1: Create a clean site worktree without touching the dirty primary checkout**

```bash
git -C /Users/gokmentanacar/projects/gkmex-site fetch origin
git -C /Users/gokmentanacar/projects/gkmex-site worktree add /Users/gokmentanacar/projects/gkmex-site-python-sdk-1.0.0 -b feat/python-sdk-discovery origin/main
cd /Users/gokmentanacar/projects/gkmex-site-python-sdk-1.0.0
git status --short
```

Expected: empty status. Do not use `/Users/gokmentanacar/projects/gkmex-site` for edits or generation.

- [ ] **Step 2: Extend the existing discovery acceptance test and verify RED**

Rename `test_npm_sdk_and_cli_are_consistently_discoverable` to `test_official_sdks_and_clis_are_consistently_discoverable`. Keep all npm assertions and add:

```python
python_package = "gkmex"
python_package_url = "https://pypi.org/project/gkmex/"
python_fragments = (
    python_package_url,
    "pip install gkmex",
    "from gkmex import GkmexClient",
    "GkmexClient().list_cranes(limit=5)",
    "gkmex list --limit 5",
    "zero-auth",
    "read-only",
)
```

Assert every fragment in both `developers/index.html` and `developers.md`. Assert the package URL and `Python SDK and CLI` in:

```python
(
    "llms.txt", ".well-known/llms.txt", "llms-full.txt",
    "index.md", "agents.md", "inventory/llms.txt",
    "developers/llms.txt", "api/llms.txt",
)
```

Extend the exact API catalog `service-doc` expectation with:

```python
{
    "href": "https://pypi.org/project/gkmex/",
    "type": "text/html",
    "title": "Gkmex Python SDK and CLI",
}
```

Run:

```bash
python3 -m unittest tests.test_build_site.SeoAcceptanceTests.test_official_sdks_and_clis_are_consistently_discoverable -v
```

Expected: FAIL because no PyPI discovery content exists.

- [ ] **Step 3: Add the smallest generator change**

Add constants beside the npm constants:

```python
PYPI_PACKAGE = "gkmex"
PYPI_PACKAGE_URL = "https://pypi.org/project/gkmex/"
```

Add the Python service-document object after the npm object in `api_catalog["linkset"][0]["service-doc"]`.

Add one Python route line to the shared `llms` body:

```markdown
- [Python SDK and CLI (`{PYPI_PACKAGE}`)]({PYPI_PACKAGE_URL}): install with `pip install gkmex` to read public, zero-auth, read-only inventory from Python or the `gkmex` command
```

Add this sentence to the generated `inventory/llms.txt`, `developers/llms.txt`, and `api/llms.txt` bodies so every sectional guide exposes the same official Python entry point:

```markdown
The official [`gkmex` Python SDK and CLI]({PYPI_PACKAGE_URL}) installs with `pip install gkmex` and reads the same public, zero-auth, read-only inventory.
```

Add matching HTML and Markdown sections after the Node.js sections:

```html
<h2>Python SDK and CLI</h2><p>Install the official <a href="{PYPI_PACKAGE_URL}"><code>{PYPI_PACKAGE}</code></a> package for programmatic or command-line access to the same public, zero-auth, read-only inventory.</p>
<pre><code>pip install {PYPI_PACKAGE}</code></pre>
<pre><code>from gkmex import GkmexClient
cranes = GkmexClient().list_cranes(limit=5)</code></pre>
<pre><code>gkmex list --limit 5</code></pre>
```

~~~~markdown
## Python SDK and CLI

Install the official [`gkmex` package]({PYPI_PACKAGE_URL}) for programmatic or command-line access to the same public, zero-auth, read-only inventory.

```bash
pip install gkmex
```

```python
from gkmex import GkmexClient

cranes = GkmexClient().list_cranes(limit=5)
```

```bash
gkmex list --limit 5
```
~~~~

Do not hand-edit generated `site/` files; update the generator and regenerate them.

- [ ] **Step 4: Regenerate from the committed inventory fixture and run both suites**

Install the pinned test dependency in an isolated environment, then build without external inventory or image writes:

```bash
python3 -m venv /tmp/gkmex-site-python-tests
/tmp/gkmex-site-python-tests/bin/python -m pip install -r requirements-test.txt
/tmp/gkmex-site-python-tests/bin/python build_site.py --from-json data/inventory-sync.json --skip-image-download
/tmp/gkmex-site-python-tests/bin/python -m unittest tests.test_build_site -v
node --test tests/test_worker.mjs
git diff --check
```

Expected: all Python and Worker tests pass. The diff contains only `build_site.py`, its test, and generated discovery files whose content actually changed; no inventory record or image churn is accepted.

- [ ] **Step 5: Commit, review, open PR, and merge**

```bash
git add build_site.py tests/test_build_site.py site/developers/index.html site/developers.md site/llms.txt site/.well-known/llms.txt site/llms-full.txt site/index.md site/agents.md site/inventory/llms.txt site/developers/llms.txt site/api/llms.txt site/.well-known/api-catalog
git commit -m "Publish Gkmex Python SDK and CLI discovery"
git push -u origin feat/python-sdk-discovery
gh pr create --base main --head feat/python-sdk-discovery --title "Publish Gkmex Python SDK and CLI discovery" --body-file /tmp/gkmex-python-site-pr-body.md
gh pr checks --watch
gh pr merge --merge --delete-branch
git fetch origin
```

Use `requesting-code-review` before merge. Record the exact site merge SHA from `origin/main`.

- [ ] **Step 6: Verify the exact merge commit is deployed**

Use the repository's configured Cloudflare Pages deployment path or Git integration. Do not deploy the dirty primary checkout. Confirm the production deployment metadata reports the exact site merge SHA, then verify these live URLs return HTTP 200:

```text
https://gkmex.com/developers
https://gkmex.com/developers.md
https://gkmex.com/llms.txt
https://gkmex.com/.well-known/llms.txt
https://gkmex.com/llms-full.txt
https://gkmex.com/index.md
https://gkmex.com/agents.md
https://gkmex.com/inventory/llms.txt
https://gkmex.com/developers/llms.txt
https://gkmex.com/api/llms.txt
https://gkmex.com/.well-known/api-catalog
https://pypi.org/project/gkmex/
```

For the generated documents, assert the live body contains the PyPI URL, `pip install gkmex`, and the correct Python SDK/CLI labels wherever the tests require them.

## Task 9: Final Release Verification

**Files:** None unless a verified defect requires a test-first fix.

- [ ] **Step 1: Run package checks from public infrastructure**

From a new empty virtual environment, repeat `pip install --no-cache-dir gkmex==1.0.0`, the import, `gkmex --version`, `gkmex list --limit 1`, and one `get` using the returned public ID. Run `compare` with two real IDs only when the production inventory supplies at least two records.

- [ ] **Step 2: Verify public links and truth boundaries**

Confirm:

- PyPI JSON, project page, source link, documentation link, and issues link resolve;
- developer pages link to the exact PyPI project;
- `price_eur: null` is shown as Python `None`/POA, never zero;
- no package/site text promises reservation or final availability;
- all example crane links use live `https://gkmex.com/...` URLs.

- [ ] **Step 3: Record evidence and stop before Ora**

Report the developer-resources merge SHA, PyPI version and artifact filenames, clean-install output, site merge SHA, Cloudflare deployment ID/URL, test counts, and live URL status. Do not claim completion if PyPI or the exact site commit is not live. Do not start a new Ora.ai measurement in this plan.
