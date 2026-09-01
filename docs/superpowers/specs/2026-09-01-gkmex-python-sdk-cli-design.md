# Gkmex Python SDK and CLI Design

## Goal

Publish a real `gkmex` package on PyPI that gives Python developers and command-line users zero-auth, read-only access to the public Gkmex crane inventory. The package must mirror the live REST and MCP contracts, preserve public inventory fields unchanged, and create a truthful Python SDK/CLI discovery signal for Gkmex.

## Confirmed Decisions

- PyPI distribution name: `gkmex`
- Python import name: `gkmex`
- Console command: `gkmex`
- First release: `1.0.0`
- Minimum Python version: `3.10`
- Runtime dependencies: none
- Repository: the existing `gkmex-developer-resources` monorepo

The official PyPI JSON and Simple APIs returned HTTP 404 for `gkmex` on 2026-09-01. Availability must be checked again immediately before publication; implementation must stop rather than silently choose a different name if another publisher claims it first.

## Chosen Approach

Add an independently publishable Python package under `packages/gkmex-python` in the existing public developer-resources repository. The package uses only Python's standard library at runtime: `urllib.request` for HTTP, `json` for payloads, `argparse` for the CLI, and normal dictionaries for returned records.

Alternatives rejected:

- A separate Python repository adds another release and issue-management lifecycle without improving this small client.
- An OpenAPI-generated client adds generated bulk and runtime dependencies for three read-only operations.
- Placing Python files at the repository root mixes package metadata with the existing cross-client integration resources and JavaScript package.

## Package Layout

The package lives entirely under `packages/gkmex-python`:

- `pyproject.toml` defines PEP 517 build metadata, package metadata, Python `>=3.10`, the `src` layout, and the `gkmex` console script.
- `src/gkmex/__init__.py` exports the supported SDK surface and `__version__`.
- `src/gkmex/client.py` owns URL construction, REST calls, MCP calls, response validation, and `GkmexError`.
- `src/gkmex/cli.py` parses commands, calls the public client, and writes JSON or concise errors.
- `tests/test_client.py` verifies SDK behavior against a local HTTP server.
- `tests/test_cli.py` executes the CLI against a local HTTP server and verifies output and exit codes.
- `tests/test_package.py` verifies metadata, package contents, imports, and console-script configuration.
- `README.md` documents installation, SDK use, CLI use, the zero-auth/read-only contract, POA behavior, and commercial-confirmation boundaries.
- `LICENSE` copies the repository's MIT license into the independently published artifact.

The build backend may use `setuptools`, but the installed wheel must declare no runtime dependencies.

## Public SDK Contract

Consumers import the client and error type from the package root:

```python
from gkmex import GkmexClient, GkmexError

client = GkmexClient()
inventory = client.list_cranes(brand="Liebherr", type="mobile", limit=5)
crane = client.get_crane(inventory["data"][0]["id"])
comparison = client.compare_cranes([
    inventory["data"][0]["id"],
    inventory["data"][1]["id"],
])
```

`GkmexClient` accepts these optional constructor arguments:

- `base_url`, defaulting to `https://gkmex.com`; local tests use an HTTP loopback URL.
- `timeout`, defaulting to 20 seconds; it applies to every network request.

`list_cranes` accepts keyword-only `brand`, `type`, `limit`, `offset`, and `cursor` arguments and maps non-`None` values to `GET /api/v1/cranes`. It does not invent filters absent from the published OpenAPI contract.

`get_crane(id)` calls `GET /api/v1/cranes/{id}` after locally rejecting an empty, whitespace-padded, `.` or `..` identifier. The path segment is percent-encoded.

`compare_cranes(ids)` accepts two to five unique canonical public IDs and calls the live MCP `compare_cranes` tool at `POST /mcp`. The request sends the IDs unchanged and returns the validated `structuredContent` comparison. The SDK does not invent comparison criteria, availability, reservation, or commercial conclusions.

All successful methods return normal Python dictionaries and lists whose public Gkmex fields remain unchanged. In particular, `price_eur: null` becomes Python `None` and is never converted to zero.

## Data Flow

For REST methods, the client builds a URL relative to `base_url`, sends the request with `Accept: application/json`, validates the HTTP status and response media type, decodes JSON, and returns the public document.

For comparison, the client sends a JSON-RPC 2.0 `tools/call` request with tool name `compare_cranes` and arguments `{ "ids": [...] }`. It accepts a JSON response and the MCP server's supported Server-Sent Events form, rejects malformed or mismatched JSON-RPC envelopes, maps JSON-RPC errors to `GkmexError`, and validates that successful structured content contains a count matching its data array.

The CLI constructs the same `GkmexClient`; it has no second HTTP implementation. `GKMEX_BASE_URL` is supported only for deterministic local testing and controlled integration environments. Normal users need no environment variable, account, token, or API key.

## CLI Contract

The package installs one command:

```text
gkmex list [--brand BRAND] [--type {mobile,crawler}] [--limit 1-100] [--offset N] [--cursor TOKEN]
gkmex get PUBLIC_ID
gkmex compare PUBLIC_ID PUBLIC_ID [PUBLIC_ID ...]
gkmex --help
gkmex --version
```

Successful commands write indented JSON followed by a newline to stdout and exit `0`. API, MCP, or network failures write one concise message to stderr and exit `1`. Invalid commands, options, and arguments use `argparse` usage output and exit `2`. Ordinary failures never print a traceback.

Broken-pipe output is treated as a successful early consumer close so commands such as `gkmex list | head` do not print a traceback.

## Errors and Validation

`GkmexError` extends `Exception` and exposes stable attributes when available:

- `status` for HTTP failures;
- `code` for JSON-RPC failures;
- `details` for a safely decoded public error body.

Network failures, timeouts, malformed JSON, unsupported media types, malformed Server-Sent Events, unexpected JSON-RPC envelopes, and invalid MCP tool results become concise `GkmexError` instances. Original Python exceptions are retained through exception chaining.

Input validation is limited to invariants that prevent ambiguous or malformed requests: canonical public IDs, two-to-five unique comparison IDs, CLI integer ranges, supported crane types, and mutually exclusive pagination arguments where the public API requires them. Server-owned business validation remains on the server.

## Testing Strategy

Development follows red-green-refactor. Tests use only `unittest`, `http.server`, `subprocess`, `tempfile`, and other standard-library modules.

SDK tests verify:

- default and filtered REST URL construction;
- configured base paths and timeouts;
- percent-encoded crane IDs;
- preservation of `price_eur: null` as `None`;
- two-to-five unique comparison-ID validation before network access;
- MCP request method, tool name, arguments, JSON decoding, and SSE decoding;
- HTTP, JSON-RPC, malformed-response, and network error normalization.

CLI tests verify:

- JSON stdout and exit `0` for `list`, `get`, and `compare`;
- stderr and exit `2` for invalid usage;
- stderr and exit `1` for API or network failures;
- `--help`, `--version`, and broken-pipe behavior.

Package acceptance builds both wheel and source distribution, checks metadata, inspects their file lists, installs the wheel into a clean temporary virtual environment, imports `GkmexClient`, runs `gkmex --version`, and performs one read-only production inventory smoke request. No test writes to Gkmex or requires Gkmex credentials.

## Package Metadata and Publication

The distribution is version `1.0.0`, MIT licensed, and describes itself as the official zero-auth Python SDK and CLI for the public, read-only Gkmex used-crane inventory. Metadata includes:

- homepage and documentation: `https://gkmex.com/developers`;
- source: `https://github.com/gkmex75/gkmex-developer-resources`, package directory `packages/gkmex-python`;
- issues: the same repository's issue tracker;
- keywords for Gkmex, cranes, SDK, CLI, MCP, and inventory;
- Python classifiers from 3.10 through current supported releases.

Before upload, the release process must:

1. recheck that the PyPI JSON API still returns 404 for `gkmex`;
2. run the complete unit and package-acceptance suite;
3. build fresh wheel and source archives from a clean reviewed commit;
4. inspect archive contents and run `twine check`;
5. install and smoke-test the exact wheel in a clean virtual environment.

PyPI authentication is entered interactively at publication time. Tokens must not be written to repository files, shell history, generated configuration, logs, or documentation. If authentication is unavailable, the code may be merged but no website link or publication claim is allowed.

After upload, acceptance requires:

- `https://pypi.org/pypi/gkmex/1.0.0/json` resolves with the expected metadata;
- a clean environment can run `pip install gkmex==1.0.0`;
- `python -c 'from gkmex import GkmexClient'` succeeds;
- `gkmex --version` prints `1.0.0`;
- a read-only production list request succeeds without authentication.

## Website Discovery Follow-up

The website must not mention PyPI until the public package and clean-install checks pass. After publication, a separate `gkmex-site` pull request updates the generator and its acceptance tests so the Python SDK is linked consistently from:

- `/developers` and `/developers.md`;
- the root and sectional `llms.txt` documents;
- `agents.md`, `index.md`, and `llms-full.txt`;
- the API catalog's service-document links;
- any generated discovery files whose existing contract lists official SDK packages.

The site change is regenerated, tested, merged, and deployed from the exact merge commit. Acceptance requires the PyPI link, `pip install gkmex`, one SDK example, and one CLI example to resolve consistently on the live site. A new Ora measurement is a separate post-publication activity and is not evidence that the package itself works.

## Release Boundary

This work is complete only when:

1. the package code, tests, README, and publish artifacts pass review;
2. `gkmex==1.0.0` is publicly installable from PyPI and verified from a clean environment;
3. the post-publication site discovery pull request is merged and its exact commit is live; and
4. all public package and developer links return successful responses.

If PyPI authentication is the only blocker, the implementation remains ready but the site stays unchanged and completion is reported truthfully as blocked on registry access.
