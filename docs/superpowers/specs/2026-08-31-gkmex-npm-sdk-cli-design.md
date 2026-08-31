# Gkmex npm SDK and CLI Design

## Goal

Publish a real, useful `gkmex` npm package that gives developers and command-line users zero-auth, read-only access to the public Gkmex crane inventory. The package must reflect live Gkmex behavior rather than introduce score-only claims or duplicate server-owned comparison logic.

## Context

Gkmex already publishes a public REST API, an MCP server, OpenAPI documentation, and developer integration resources. The remaining truthful Ora.ai opportunity is a package-registry SDK and CLI. The npm names `gkmex` and `@gkmex/cranes` were unused when checked on 2026-08-31. The owner selected the unscoped `gkmex` package so publication does not depend on creating an npm organization.

This design covers the package implementation and npm publication only. Linking the package from `gkmex.com/developers`, regenerating the site, deploying the site, and running a targeted Ora.ai measurement form a separate follow-up phase. The website must not link to npm until the published package resolves publicly.

## Chosen Approach

Add a zero-runtime-dependency ECMAScript module package under `packages/gkmex` in the existing public `gkmex-developer-resources` repository. It uses Node.js 20's built-in `fetch`, ships JavaScript directly without a build step, and includes TypeScript declaration files for editor and TypeScript consumers.

Alternatives rejected:

- A TypeScript compiler and bundler add build dependencies without improving this three-operation client materially.
- A separate `gkmex-js` repository fragments the already public developer resource surface and adds another release lifecycle.
- Adding the package to `gkmex-site` couples npm releases to a generated Cloudflare Pages repository whose inventory output changes nightly.

## Package Layout

The package lives entirely under `packages/gkmex`:

- `package.json` defines package metadata, ESM exports, the `gkmex` binary, Node `>=20`, test scripts, and the publish allowlist.
- `src/client.js` owns URL construction, REST requests, MCP calls, response validation, and `GkmexError`.
- `src/index.js` is the public SDK export surface.
- `src/index.d.ts` defines the public options, crane, inventory, comparison, error, and client types.
- `bin/gkmex.js` parses CLI arguments, calls the public client API, writes JSON results to stdout, and writes errors to stderr.
- `test/client.test.js` verifies SDK behavior against a local HTTP server.
- `test/cli.test.js` spawns the packaged CLI against a local HTTP server and verifies output and exit codes.
- `README.md` documents installation, SDK examples, CLI examples, the zero-auth/read-only contract, POA behavior, and commercial-confirmation limits.
- `LICENSE` carries the repository's MIT license inside the independently published package.

No runtime dependency is permitted. Development also relies only on Node's built-in test runner and standard library.

## Public SDK Contract

Consumers import the client and error type from the package root:

```js
import { GkmexClient, GkmexError } from "gkmex";

const client = new GkmexClient();
const inventory = await client.listCranes({
  brand: "Liebherr",
  type: "mobile",
  limit: 20,
});
const crane = await client.getCrane("public-crane-id");
const comparison = await client.compareCranes([
  "first-public-id",
  "second-public-id",
]);
```

`new GkmexClient(options)` accepts:

- `baseUrl`, defaulting to `https://gkmex.com`; tests use it to target a local server.
- `fetch`, defaulting to `globalThis.fetch`; tests may inject a compatible implementation without adding a mocking library.

`listCranes(options)` maps the supported `limit`, `offset`, `cursor`, `brand`, and `type` fields to `GET /api/v1/cranes`. It does not invent filters absent from the published OpenAPI contract.

`getCrane(id)` calls `GET /api/v1/cranes/{id}` after rejecting an empty ID locally.

`compareCranes(ids)` accepts two to five unique, non-empty public IDs and calls the live MCP `compare_cranes` tool at `POST /mcp`. The package returns the structured comparison content produced by Gkmex. It does not reimplement comparison rules or infer availability.

Every crane record is returned unchanged. In particular, `price_eur: null` remains POA and is never converted to zero. The package does not add reservation, checkout, authentication, availability, or write operations.

## Data Flow

For REST methods, the client builds a URL relative to `baseUrl`, sends a GET request with `accept: application/json`, checks the status and content type, and returns the decoded JSON document.

For comparison, the client sends one JSON-RPC 2.0 `tools/call` request with tool name `compare_cranes` and the supplied IDs. It accepts the JSON response, rejects a JSON-RPC error, and decodes the tool's structured JSON result. The request is stateless and requires no MCP session or authentication.

The CLI creates the same `GkmexClient` and delegates every operation to it. There is no second HTTP implementation in the CLI.

## CLI Contract

The npm package installs one binary named `gkmex`:

```text
gkmex list [--brand <brand>] [--type <mobile|crawler>] [--limit <1-100>] [--offset <n>] [--cursor <token>]
gkmex get <public-id>
gkmex compare <public-id> <public-id> [public-id ...]
gkmex --help
gkmex --version
```

Successful commands write pretty-printed JSON followed by a newline to stdout and exit `0`. API or network failures write one concise message to stderr and exit `1`. Invalid commands, missing values, unsupported options, and locally invalid arguments write the error plus usage guidance to stderr and exit `2`.

The CLI supports `GKMEX_BASE_URL` for deterministic local tests and controlled integration environments. Normal users require no environment variables, account, or API key.

## Errors

`GkmexError` extends `Error` and exposes stable fields where available:

- `status` for HTTP failures;
- `code` for JSON-RPC failures;
- `details` for a safely decoded public error body.

Malformed JSON, unexpected media types, and network failures become `GkmexError` instances with concise messages. Error handling must not print stack traces during ordinary CLI failures. The SDK preserves the original error as `cause` when Node provides one.

## Package Metadata and Publication

The first release is version `1.0.0`, licensed under MIT like the repository. Metadata includes:

- homepage `https://gkmex.com/developers`;
- repository `https://github.com/gkmex75/gkmex-developer-resources` with package directory `packages/gkmex`;
- bugs URL for the same GitHub repository;
- keywords covering Gkmex, cranes, SDK, CLI, MCP, and inventory;
- a `files` allowlist that publishes only the executable, source, declarations, README, and license.

Before publication, `npm pack --dry-run` and inspection of the tarball file list must prove that repository-only files are excluded. Publishing requires an authenticated npm identity with rights to the unused `gkmex` name. This repository currently has no npm authentication; implementation may merge without claiming publication. Immediately before publishing, the release process rechecks that `gkmex` is still available and stops rather than silently changing names if another owner has claimed it. Actual publication occurs only after `npm whoami` succeeds, followed by `npm publish --access public` from `packages/gkmex`.

After publication, acceptance requires:

- `npm view gkmex@1.0.0` resolves with the expected metadata;
- a clean temporary directory can run `npx --yes gkmex@1.0.0 --version`;
- a clean temporary Node project can install `gkmex@1.0.0` and import `GkmexClient`;
- a production smoke request through the installed SDK can read public inventory without authentication.

## Testing Strategy

Development follows red-green-refactor. Each public behavior receives a failing test before implementation.

SDK tests use a real local Node HTTP server and verify:

- default and filtered list URL construction;
- percent-encoded crane IDs;
- two-to-five unique ID validation;
- MCP request method, tool name, arguments, and structured result decoding;
- HTTP, JSON-RPC, malformed-response, and network error normalization;
- preservation of `price_eur: null`.

CLI tests spawn `node bin/gkmex.js` with `GKMEX_BASE_URL` pointing to the local server and verify:

- JSON stdout and exit `0` for `list`, `get`, and `compare`;
- stderr and exit `2` for invalid usage;
- stderr and exit `1` for server failures;
- help and version output.

Package acceptance verifies `npm pack --dry-run`, the exact publish file allowlist, executable permissions, and importability from the produced tarball. No automated test writes to Gkmex, requires credentials, or changes inventory.

## Release Boundaries

This phase ends when the package code, tests, documentation, and publish artifact are reviewed and merged, and either:

1. npm authentication is available and version `1.0.0` is published and verified; or
2. publication is explicitly reported as blocked by missing npm authentication, without adding a dead website link or claiming an Ora.ai score improvement.

The subsequent site phase may begin only after the npm registry returns the published package. That phase updates the generated developer page and discovery documents, deploys the exact reviewed commit, and uses the separately governed Ora.ai targeted-check budget.
