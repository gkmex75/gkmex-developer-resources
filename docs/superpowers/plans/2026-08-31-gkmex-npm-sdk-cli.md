# Gkmex npm SDK and CLI Implementation Plan

> **Registry-name correction — 2026-08-31:** npm rejected unscoped `gkmex` with E403 because it was too similar to `knex`; the owner selected the available authenticated scope name `@gstcranes/gkmex`. All earlier plan snippets using unscoped `gkmex` as the package identity, install/import target, availability query, tarball name, publish result, or registry URL are superseded by `@gstcranes/gkmex`. The package directory and CLI binary remain `packages/gkmex` and `gkmex`.

> **Production-contract correction — 2026-08-31:** Local and production MCP discovery proved that the public tools are `list_cranes` and `get_crane`; no `compare_cranes` tool exists. A read-only production `tools/call` to `list_cranes` with `{}` returned HTTP 200 and all 29 published records, including sampled public IDs and URLs. All `compare_cranes` references in the historical task transcript below are superseded and are not the supported contract. The implemented `compareCranes` calls `list_cranes` with empty arguments, validates its structured inventory, and locally selects only the requested cranes in caller order.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a zero-dependency Node.js SDK and CLI named gkmex for the public, zero-auth, read-only Gkmex crane inventory.

**Architecture:** The package lives under packages/gkmex in the existing public developer-resources repository. One GkmexClient owns every REST and MCP request; the CLI is a thin JSON-output adapter over that client, so transport and error behavior have a single implementation.

**Tech Stack:** Node.js 20 ESM, built-in fetch, node:test, node:http, npm package tooling, Git.

---

## Scope and File Map

This plan changes only the gkmex-developer-resources repository. It does not modify gkmex-site, deploy Cloudflare Pages, add a website link, or call Ora.ai. Those actions remain blocked until the npm registry publicly resolves gkmex.

Files created:

- packages/gkmex/package.json — npm identity, exports, binary, engine, scripts, and publish allowlist.
- packages/gkmex/src/client.js — REST/MCP transport, validation, and GkmexError.
- packages/gkmex/src/index.js — stable public exports.
- packages/gkmex/src/index.d.ts — TypeScript declarations for the JavaScript package.
- packages/gkmex/bin/gkmex.js — argument parsing, SDK delegation, JSON output, and exit codes.
- packages/gkmex/test/helpers.js — real local HTTP server helper.
- packages/gkmex/test/client.test.js — SDK contract and error tests.
- packages/gkmex/test/cli.test.js — spawned CLI acceptance tests.
- packages/gkmex/test/package.test.js — metadata and tarball allowlist tests.
- packages/gkmex/README.md — package installation and usage guide.
- packages/gkmex/LICENSE — package-local MIT license.

## Task 1: Package Harness and Successful REST Operations

**Files:**

- Create: packages/gkmex/package.json
- Create: packages/gkmex/test/helpers.js
- Create: packages/gkmex/test/client.test.js
- Create: packages/gkmex/src/client.js
- Create: packages/gkmex/src/index.js

- [ ] **Step 1: Add the minimal test-harness manifest**

Create packages/gkmex/package.json as non-runtime test scaffolding:

~~~json
{
  "name": "gkmex",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "test": "node --test"
  }
}
~~~

Run:

~~~bash
cd packages/gkmex
npm test
~~~

Expected: PASS with zero tests. This manifest only enables ESM test execution; the publish metadata remains intentionally incomplete until Task 4 tests drive it.

- [ ] **Step 2: Add the real local HTTP test helper**

Create packages/gkmex/test/helpers.js:

~~~js
import { createServer } from "node:http";
import { once } from "node:events";

export function sendJson(response, status, value) {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(value));
}

export async function readJson(request) {
  let body = "";
  request.setEncoding("utf8");
  for await (const chunk of request) {
    body += chunk;
  }
  return JSON.parse(body);
}

export async function withServer(handler, run) {
  const server = createServer(handler);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  const baseUrl = "http://127.0.0.1:" + address.port;

  try {
    return await run(baseUrl);
  } finally {
    await new Promise((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  }
}
~~~

- [ ] **Step 3: Write failing REST success tests**

Create packages/gkmex/test/client.test.js:

~~~js
import assert from "node:assert/strict";
import test from "node:test";

import { GkmexClient } from "../src/index.js";
import { sendJson, withServer } from "./helpers.js";

test("listCranes maps supported filters to the public REST collection", async () => {
  await withServer((request, response) => {
    assert.equal(request.method, "GET");
    assert.equal(
      request.url,
      "/api/v1/cranes?limit=2&offset=1&brand=Liebherr&type=mobile",
    );
    assert.equal(request.headers.accept, "application/json");
    sendJson(response, 200, {
      updated_at: "2026-08-31",
      count: 1,
      total: 1,
      limit: 2,
      offset: 1,
      next_cursor: null,
      data: [{ id: "crane-1", brand: "Liebherr", price_eur: 120000 }],
    });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });
    const result = await client.listCranes({
      limit: 2,
      offset: 1,
      brand: "Liebherr",
      type: "mobile",
    });

    assert.equal(result.data[0].id, "crane-1");
    assert.equal(result.total, 1);
  });
});

test("getCrane percent-encodes the public ID and preserves POA", async () => {
  await withServer((request, response) => {
    assert.equal(request.method, "GET");
    assert.equal(request.url, "/api/v1/cranes/id%2Fwith%20space");
    sendJson(response, 200, {
      id: "id/with space",
      brand: "Demag",
      model: "CC 2800",
      price_eur: null,
      url: "https://gkmex.com/en/crane/id%2Fwith%20space",
    });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });
    const result = await client.getCrane("id/with space");

    assert.equal(result.price_eur, null);
    assert.equal(result.id, "id/with space");
  });
});
~~~

- [ ] **Step 4: Run the REST tests and verify RED**

Run:

~~~bash
cd packages/gkmex
node --test test/client.test.js
~~~

Expected: FAIL with ERR_MODULE_NOT_FOUND for src/index.js. The failure proves the tests require the missing SDK surface.

- [ ] **Step 5: Implement the smallest successful REST client**

Create packages/gkmex/src/client.js:

~~~js
const DEFAULT_BASE_URL = "https://gkmex.com";

function normalizedBaseUrl(value) {
  const url = new URL(value ?? DEFAULT_BASE_URL);
  if (!url.pathname.endsWith("/")) {
    url.pathname += "/";
  }
  return url;
}

export class GkmexClient {
  constructor(options = {}) {
    this.baseUrl = normalizedBaseUrl(options.baseUrl);
    this.fetch = options.fetch ?? globalThis.fetch;
  }

  async listCranes(options = {}) {
    const url = new URL("/api/v1/cranes", this.baseUrl);
    for (const key of ["limit", "offset", "cursor", "brand", "type"]) {
      if (options[key] !== undefined) {
        url.searchParams.set(key, String(options[key]));
      }
    }
    const response = await this.fetch(url, {
      headers: { accept: "application/json" },
    });
    return response.json();
  }

  async getCrane(id) {
    const url = new URL(
      "/api/v1/cranes/" + encodeURIComponent(String(id)),
      this.baseUrl,
    );
    const response = await this.fetch(url, {
      headers: { accept: "application/json" },
    });
    return response.json();
  }
}
~~~

Create packages/gkmex/src/index.js:

~~~js
export { GkmexClient } from "./client.js";
~~~

- [ ] **Step 6: Run the REST tests and verify GREEN**

Run:

~~~bash
cd packages/gkmex
node --test test/client.test.js
~~~

Expected: 2 tests pass, 0 fail.

- [ ] **Step 7: Commit the REST client**

~~~bash
git add packages/gkmex/package.json packages/gkmex/test/helpers.js packages/gkmex/test/client.test.js packages/gkmex/src/client.js packages/gkmex/src/index.js
git commit -m "feat: add Gkmex JavaScript client"
~~~

## Task 2: MCP Comparison and Stable Errors

**Files:**

- Modify: packages/gkmex/test/client.test.js
- Modify: packages/gkmex/src/client.js
- Modify: packages/gkmex/src/index.js

- [ ] **Step 1: Extend the import and add failing comparison/error tests**

Replace the SDK import in packages/gkmex/test/client.test.js with:

~~~js
import { GkmexClient, GkmexError } from "../src/index.js";
~~~

Append:

~~~js
test("compareCranes delegates to the authoritative MCP tool", async () => {
  await withServer(async (request, response) => {
    assert.equal(request.method, "POST");
    assert.equal(request.url, "/mcp");
    assert.equal(request.headers["content-type"], "application/json");
    assert.equal(request.headers.accept, "application/json, text/event-stream");
    assert.deepEqual(await readJson(request), {
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "compare_cranes",
        arguments: { ids: ["crane-1", "crane-2"] },
      },
    });
    sendJson(response, 200, {
      jsonrpc: "2.0",
      id: 1,
      result: {
        content: [{ type: "text", text: "{}" }],
        structuredContent: {
          updated_at: "2026-08-31",
          count: 2,
          data: [{ id: "crane-1" }, { id: "crane-2" }],
        },
        isError: false,
      },
    });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });
    const result = await client.compareCranes(["crane-1", "crane-2"]);
    assert.deepEqual(result.data.map((crane) => crane.id), ["crane-1", "crane-2"]);
  });
});

test("compareCranes rejects invalid ID sets before making a request", async () => {
  let calls = 0;
  const client = new GkmexClient({
    fetch: async () => {
      calls += 1;
      throw new Error("must not run");
    },
  });

  for (const ids of [
    ["one"],
    ["one", "one"],
    ["one", "two", "three", "four", "five", "six"],
    ["one", ""],
  ]) {
    await assert.rejects(
      client.compareCranes(ids),
      (error) =>
        error instanceof GkmexError &&
        error.message === "ids must contain two to five unique public crane IDs",
    );
  }
  assert.equal(calls, 0);
});

test("HTTP and JSON-RPC failures become GkmexError", async () => {
  await withServer(async (request, response) => {
    if (request.url.startsWith("/api/v1/cranes/")) {
      sendJson(response, 404, { error: "Crane not found" });
      return;
    }
    await readJson(request);
    sendJson(response, 200, {
      jsonrpc: "2.0",
      id: 1,
      error: { code: -32602, message: "Crane not found" },
    });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });

    await assert.rejects(
      client.getCrane("missing"),
      (error) =>
        error instanceof GkmexError &&
        error.status === 404 &&
        error.message === "Crane not found",
    );
    await assert.rejects(
      client.compareCranes(["missing", "crane-2"]),
      (error) =>
        error instanceof GkmexError &&
        error.code === -32602 &&
        error.message === "Crane not found",
    );
  });
});

test("empty IDs, malformed responses, and network failures are normalized", async () => {
  const noNetwork = new GkmexClient({
    fetch: async () => {
      throw new Error("socket closed");
    },
  });
  await assert.rejects(
    noNetwork.getCrane("crane-1"),
    (error) =>
      error instanceof GkmexError &&
      error.message === "Unable to reach Gkmex" &&
      error.cause?.message === "socket closed",
  );

  const malformed = new GkmexClient({
    fetch: async () =>
      new Response("not json", {
        status: 200,
        headers: { "content-type": "text/plain" },
      }),
  });
  await assert.rejects(
    malformed.listCranes(),
    (error) =>
      error instanceof GkmexError &&
      error.message === "Gkmex returned an unexpected response",
  );

  const invalidJson = new GkmexClient({
    fetch: async () =>
      new Response("{", {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
  });
  await assert.rejects(
    invalidJson.listCranes(),
    (error) =>
      error instanceof GkmexError &&
      error.message === "Gkmex returned invalid JSON",
  );

  const client = new GkmexClient();
  await assert.rejects(
    client.getCrane(""),
    (error) =>
      error instanceof GkmexError &&
      error.message === "id must be a non-empty public crane ID",
  );
});
~~~

Also add readJson to the helper import:

~~~js
import { readJson, sendJson, withServer } from "./helpers.js";
~~~

- [ ] **Step 2: Run the client tests and verify RED**

Run:

~~~bash
cd packages/gkmex
node --test test/client.test.js
~~~

Expected: FAIL because GkmexError and compareCranes are not exported or implemented, and successful HTTP status is not checked.

- [ ] **Step 3: Replace the client with the validated REST/MCP implementation**

Replace packages/gkmex/src/client.js with:

~~~js
const DEFAULT_BASE_URL = "https://gkmex.com";

function normalizedBaseUrl(value) {
  const url = new URL(value ?? DEFAULT_BASE_URL);
  if (!url.pathname.endsWith("/")) {
    url.pathname += "/";
  }
  return url;
}

export class GkmexError extends Error {
  constructor(message, options = {}) {
    super(
      message,
      options.cause === undefined ? undefined : { cause: options.cause },
    );
    this.name = "GkmexError";
    if (options.status !== undefined) this.status = options.status;
    if (options.code !== undefined) this.code = options.code;
    if (options.details !== undefined) this.details = options.details;
  }
}

export class GkmexClient {
  constructor(options = {}) {
    this.baseUrl = normalizedBaseUrl(options.baseUrl);
    this.fetch = options.fetch ?? globalThis.fetch;
  }

  async #requestJson(path, init = {}) {
    const url = new URL(path, this.baseUrl);
    let response;
    try {
      response = await this.fetch(url, init);
    } catch (cause) {
      throw new GkmexError("Unable to reach Gkmex", { cause });
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.toLowerCase().includes("application/json")) {
      throw new GkmexError("Gkmex returned an unexpected response", {
        status: response.status,
      });
    }

    let payload;
    try {
      payload = await response.json();
    } catch (cause) {
      throw new GkmexError("Gkmex returned invalid JSON", {
        status: response.status,
        cause,
      });
    }

    if (!response.ok) {
      throw new GkmexError(
        typeof payload?.error === "string"
          ? payload.error
          : "Gkmex request failed with HTTP " + response.status,
        { status: response.status, details: payload },
      );
    }
    return payload;
  }

  async listCranes(options = {}) {
    const url = new URL("/api/v1/cranes", this.baseUrl);
    for (const key of ["limit", "offset", "cursor", "brand", "type"]) {
      if (options[key] !== undefined) {
        url.searchParams.set(key, String(options[key]));
      }
    }
    return this.#requestJson(url.pathname + url.search, {
      headers: { accept: "application/json" },
    });
  }

  async getCrane(id) {
    if (typeof id !== "string" || id.trim().length === 0) {
      throw new GkmexError("id must be a non-empty public crane ID");
    }
    return this.#requestJson(
      "/api/v1/cranes/" + encodeURIComponent(id),
      { headers: { accept: "application/json" } },
    );
  }

  async compareCranes(ids) {
    if (
      !Array.isArray(ids) ||
      ids.length < 2 ||
      ids.length > 5 ||
      ids.some((id) => typeof id !== "string" || id.length === 0) ||
      new Set(ids).size !== ids.length
    ) {
      throw new GkmexError(
        "ids must contain two to five unique public crane IDs",
      );
    }

    const payload = await this.#requestJson("/mcp", {
      method: "POST",
      headers: {
        accept: "application/json, text/event-stream",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "compare_cranes",
          arguments: { ids },
        },
      }),
    });

    if (payload?.error) {
      throw new GkmexError(
        payload.error.message ?? "Gkmex MCP request failed",
        { code: payload.error.code, details: payload.error.data },
      );
    }
    const comparison = payload?.result?.structuredContent;
    if (!comparison || typeof comparison !== "object") {
      throw new GkmexError("Gkmex returned an unexpected MCP result");
    }
    return comparison;
  }
}
~~~

Replace packages/gkmex/src/index.js with:

~~~js
export { GkmexClient, GkmexError } from "./client.js";
~~~

- [ ] **Step 4: Run the client tests and verify GREEN**

Run:

~~~bash
cd packages/gkmex
node --test test/client.test.js
~~~

Expected: 6 tests pass, 0 fail.

- [ ] **Step 5: Commit comparison and errors**

~~~bash
git add packages/gkmex/test/client.test.js packages/gkmex/src/client.js packages/gkmex/src/index.js
git commit -m "feat: add Gkmex comparison and stable errors"
~~~

## Task 3: Deterministic JSON CLI

**Files:**

- Create: packages/gkmex/test/cli.test.js
- Create: packages/gkmex/bin/gkmex.js

- [ ] **Step 1: Write the failing CLI tests**

Create packages/gkmex/test/cli.test.js:

~~~js
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { readJson, sendJson, withServer } from "./helpers.js";

const CLI = fileURLToPath(new URL("../bin/gkmex.js", import.meta.url));

function runCli(args, options = {}) {
  const env = { ...process.env };
  if (options.baseUrl) {
    env.GKMEX_BASE_URL = options.baseUrl;
  } else {
    delete env.GKMEX_BASE_URL;
  }

  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [CLI, ...args], { env });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", reject);
    child.on("close", (code) => resolve({ code, stdout, stderr }));
  });
}

test("list prints JSON and forwards validated filters", async () => {
  await withServer((request, response) => {
    assert.equal(request.url, "/api/v1/cranes?limit=1&type=crawler");
    sendJson(response, 200, {
      updated_at: "2026-08-31",
      count: 1,
      data: [{ id: "crawler-1", price_eur: null }],
    });
  }, async (baseUrl) => {
    const result = await runCli(
      ["list", "--limit", "1", "--type", "crawler"],
      { baseUrl },
    );
    assert.equal(result.code, 0);
    assert.equal(result.stderr, "");
    assert.equal(JSON.parse(result.stdout).data[0].price_eur, null);
  });
});

test("get prints one crane as JSON", async () => {
  await withServer((request, response) => {
    assert.equal(request.url, "/api/v1/cranes/crane-1");
    sendJson(response, 200, { id: "crane-1", brand: "Liebherr" });
  }, async (baseUrl) => {
    const result = await runCli(["get", "crane-1"], { baseUrl });
    assert.equal(result.code, 0);
    assert.equal(JSON.parse(result.stdout).id, "crane-1");
  });
});

test("compare calls MCP and prints the structured comparison", async () => {
  await withServer(async (request, response) => {
    assert.equal(request.url, "/mcp");
    const body = await readJson(request);
    assert.deepEqual(body.params.arguments.ids, ["crane-1", "crane-2"]);
    sendJson(response, 200, {
      jsonrpc: "2.0",
      id: 1,
      result: {
        structuredContent: {
          updated_at: "2026-08-31",
          count: 2,
          data: [{ id: "crane-1" }, { id: "crane-2" }],
        },
      },
    });
  }, async (baseUrl) => {
    const result = await runCli(
      ["compare", "crane-1", "crane-2"],
      { baseUrl },
    );
    assert.equal(result.code, 0);
    assert.equal(JSON.parse(result.stdout).count, 2);
  });
});

test("help and version are available without a network request", async () => {
  const help = await runCli(["--help"]);
  assert.equal(help.code, 0);
  assert.match(help.stdout, /gkmex list/);
  assert.equal(help.stderr, "");

  const version = await runCli(["--version"]);
  assert.equal(version.code, 0);
  assert.equal(version.stdout, "1.0.0\n");
  assert.equal(version.stderr, "");
});

test("invalid usage exits 2 and prints usage to stderr", async () => {
  for (const args of [
    [],
    ["unknown"],
    ["get"],
    ["compare", "one"],
    ["list", "--limit", "0"],
    ["list", "--type", "tower"],
  ]) {
    const result = await runCli(args);
    assert.equal(result.code, 2, args.join(" "));
    assert.equal(result.stdout, "");
    assert.match(result.stderr, /Usage:/);
  }
});

test("API failures exit 1 without a stack trace", async () => {
  await withServer((request, response) => {
    sendJson(response, 404, { error: "Crane not found" });
  }, async (baseUrl) => {
    const result = await runCli(["get", "missing"], { baseUrl });
    assert.equal(result.code, 1);
    assert.equal(result.stdout, "");
    assert.equal(result.stderr, "Crane not found\n");
    assert.doesNotMatch(result.stderr, /\n\s+at /);
  });
});
~~~

- [ ] **Step 2: Run the CLI tests and verify RED**

Run:

~~~bash
cd packages/gkmex
node --test test/cli.test.js
~~~

Expected: all tests FAIL because bin/gkmex.js does not exist.

- [ ] **Step 3: Implement the CLI as a thin SDK adapter**

Create packages/gkmex/bin/gkmex.js:

~~~js
#!/usr/bin/env node

import { readFileSync } from "node:fs";

import { GkmexClient, GkmexError } from "../src/index.js";

const packageJson = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf8"),
);

const USAGE = [
  "Usage:",
  "  gkmex list [--brand <brand>] [--type <mobile|crawler>] [--limit <1-100>] [--offset <n>] [--cursor <token>]",
  "  gkmex get <public-id>",
  "  gkmex compare <public-id> <public-id> [public-id ...]",
  "  gkmex --help",
  "  gkmex --version",
].join("\n");

class UsageError extends Error {}

function valueAfter(args, index, flag) {
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new UsageError(flag + " requires a value");
  }
  return value;
}

function parseInteger(value, flag, minimum, maximum) {
  if (!/^\d+$/.test(value)) {
    throw new UsageError(flag + " must be an integer");
  }
  const parsed = Number(value);
  if (parsed < minimum || (maximum !== undefined && parsed > maximum)) {
    const range = maximum === undefined
      ? "at least " + minimum
      : "between " + minimum + " and " + maximum;
    throw new UsageError(flag + " must be " + range);
  }
  return parsed;
}

function parseList(args) {
  const options = {};
  for (let index = 0; index < args.length; index += 2) {
    const flag = args[index];
    const value = valueAfter(args, index, flag);
    if (flag === "--limit") {
      options.limit = parseInteger(value, flag, 1, 100);
    } else if (flag === "--offset") {
      options.offset = parseInteger(value, flag, 0);
    } else if (flag === "--type") {
      if (!["mobile", "crawler"].includes(value)) {
        throw new UsageError("--type must be mobile or crawler");
      }
      options.type = value;
    } else if (flag === "--brand") {
      if (value.trim().length === 0) {
        throw new UsageError("--brand must not be empty");
      }
      options.brand = value;
    } else if (flag === "--cursor") {
      if (value.length === 0) {
        throw new UsageError("--cursor must not be empty");
      }
      options.cursor = value;
    } else {
      throw new UsageError("Unknown option: " + flag);
    }
  }
  return options;
}

function parseGet(args) {
  if (args.length !== 1 || args[0].trim().length === 0) {
    throw new UsageError("get requires one public crane ID");
  }
  return args[0];
}

function parseCompare(args) {
  if (
    args.length < 2 ||
    args.length > 5 ||
    args.some((id) => id.length === 0) ||
    new Set(args).size !== args.length
  ) {
    throw new UsageError(
      "compare requires two to five unique public crane IDs",
    );
  }
  return args;
}

async function main(args) {
  if (args.length === 1 && args[0] === "--help") {
    process.stdout.write(USAGE + "\n");
    return;
  }
  if (args.length === 1 && args[0] === "--version") {
    process.stdout.write(packageJson.version + "\n");
    return;
  }
  if (args.length === 0) {
    throw new UsageError("A command is required");
  }

  const client = new GkmexClient({
    baseUrl: process.env.GKMEX_BASE_URL,
  });
  const [command, ...rest] = args;
  let result;
  if (command === "list") {
    result = await client.listCranes(parseList(rest));
  } else if (command === "get") {
    result = await client.getCrane(parseGet(rest));
  } else if (command === "compare") {
    result = await client.compareCranes(parseCompare(rest));
  } else {
    throw new UsageError("Unknown command: " + command);
  }
  process.stdout.write(JSON.stringify(result, null, 2) + "\n");
}

try {
  await main(process.argv.slice(2));
} catch (error) {
  if (error instanceof UsageError) {
    process.stderr.write(error.message + "\n\n" + USAGE + "\n");
    process.exitCode = 2;
  } else {
    const message = error instanceof GkmexError
      ? error.message
      : "Unexpected Gkmex CLI failure";
    process.stderr.write(message + "\n");
    process.exitCode = 1;
  }
}
~~~

- [ ] **Step 4: Run the CLI tests and verify GREEN**

Run:

~~~bash
cd packages/gkmex
node --test test/cli.test.js
~~~

Expected: 6 tests pass, 0 fail.

- [ ] **Step 5: Run the complete current suite**

Run:

~~~bash
cd packages/gkmex
npm test
~~~

Expected: 12 tests pass, 0 fail.

- [ ] **Step 6: Commit the CLI**

~~~bash
git add packages/gkmex/bin/gkmex.js packages/gkmex/test/cli.test.js
git commit -m "feat: add Gkmex JSON CLI"
~~~

## Task 4: Types, Package Documentation, and Publish Artifact

**Files:**

- Create: packages/gkmex/test/package.test.js
- Modify: packages/gkmex/package.json
- Create: packages/gkmex/src/index.d.ts
- Create: packages/gkmex/README.md
- Create: packages/gkmex/LICENSE
- Modify mode: packages/gkmex/bin/gkmex.js

- [ ] **Step 1: Write failing package contract tests**

Create packages/gkmex/test/package.test.js:

~~~js
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { readFile, stat } from "node:fs/promises";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import test from "node:test";

const execFileAsync = promisify(execFile);
const ROOT = fileURLToPath(new URL("..", import.meta.url));

test("package metadata exposes the SDK and CLI without dependencies", async () => {
  const metadata = JSON.parse(
    await readFile(new URL("../package.json", import.meta.url), "utf8"),
  );
  assert.equal(metadata.name, "gkmex");
  assert.equal(metadata.version, "1.0.0");
  assert.equal(metadata.private, undefined);
  assert.equal(metadata.type, "module");
  assert.equal(metadata.engines.node, ">=20");
  assert.equal(metadata.bin.gkmex, "./bin/gkmex.js");
  assert.equal(metadata.exports["."].import, "./src/index.js");
  assert.equal(metadata.exports["."].types, "./src/index.d.ts");
  assert.deepEqual(metadata.files, ["bin", "src", "README.md", "LICENSE"]);
  assert.equal(metadata.dependencies, undefined);
  assert.equal(metadata.devDependencies, undefined);
});

test("types, documentation, license, and executable are publishable", async () => {
  const declarations = await readFile(
    new URL("../src/index.d.ts", import.meta.url),
    "utf8",
  );
  assert.match(declarations, /class GkmexClient/);
  assert.match(declarations, /compareCranes/);
  assert.match(declarations, /price_eur: number \| null/);

  const readme = await readFile(new URL("../README.md", import.meta.url), "utf8");
  assert.match(readme, /npm install gkmex/);
  assert.match(readme, /gkmex compare/);
  assert.match(readme, /POA/);
  assert.match(readme, /final availability/);

  const license = await readFile(new URL("../LICENSE", import.meta.url), "utf8");
  assert.match(license, /^MIT License/);

  const executable = await stat(new URL("../bin/gkmex.js", import.meta.url));
  assert.notEqual(executable.mode & 0o111, 0);

  const { stdout } = await execFileAsync(
    "npm",
    ["pack", "--dry-run", "--json"],
    { cwd: ROOT },
  );
  const [packed] = JSON.parse(stdout);
  const paths = packed.files.map((file) => file.path).sort();
  assert.deepEqual(paths, [
    "LICENSE",
    "README.md",
    "bin/gkmex.js",
    "package.json",
    "src/client.js",
    "src/index.d.ts",
    "src/index.js",
  ]);
});
~~~

- [ ] **Step 2: Run the package tests and verify RED**

Run:

~~~bash
cd packages/gkmex
node --test test/package.test.js
~~~

Expected: FAIL because the manifest is private and missing exports/bin/files metadata, while declarations, README, and package-local LICENSE do not exist.

- [ ] **Step 3: Replace the manifest with final public metadata**

Replace packages/gkmex/package.json with:

~~~json
{
  "name": "gkmex",
  "version": "1.0.0",
  "description": "Zero-auth JavaScript SDK and CLI for the public Gkmex used-crane inventory.",
  "type": "module",
  "main": "./src/index.js",
  "types": "./src/index.d.ts",
  "exports": {
    ".": {
      "types": "./src/index.d.ts",
      "import": "./src/index.js"
    }
  },
  "bin": {
    "gkmex": "./bin/gkmex.js"
  },
  "files": [
    "bin",
    "src",
    "README.md",
    "LICENSE"
  ],
  "scripts": {
    "test": "node --test"
  },
  "engines": {
    "node": ">=20"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/gkmex75/gkmex-developer-resources.git",
    "directory": "packages/gkmex"
  },
  "homepage": "https://gkmex.com/developers",
  "bugs": {
    "url": "https://github.com/gkmex75/gkmex-developer-resources/issues"
  },
  "keywords": [
    "gkmex",
    "cranes",
    "sdk",
    "cli",
    "mcp",
    "inventory"
  ],
  "license": "MIT",
  "publishConfig": {
    "access": "public"
  }
}
~~~

- [ ] **Step 4: Add the complete TypeScript declarations**

Create packages/gkmex/src/index.d.ts:

~~~ts
export type CraneType = "mobile" | "crawler";

export interface Crane {
  id: string;
  brand: string;
  model: string;
  year?: number | null;
  capacity?: string;
  type?: CraneType;
  location?: string;
  price_eur: number | null;
  image?: string;
  url: string;
  [key: string]: unknown;
}

export interface InventoryResponse {
  updated_at: string;
  count: number;
  total?: number;
  limit?: number;
  offset?: number;
  next_cursor?: string | null;
  data: Crane[];
}

export interface ComparisonResponse {
  updated_at: string;
  count: number;
  data: Crane[];
}

export interface ListCranesOptions {
  limit?: number;
  offset?: number;
  cursor?: string;
  brand?: string;
  type?: CraneType;
}

export interface GkmexClientOptions {
  baseUrl?: string;
  fetch?: typeof globalThis.fetch;
}

export interface GkmexErrorOptions {
  status?: number;
  code?: number;
  details?: unknown;
  cause?: unknown;
}

export class GkmexError extends Error {
  status?: number;
  code?: number;
  details?: unknown;
  constructor(message: string, options?: GkmexErrorOptions);
}

export class GkmexClient {
  constructor(options?: GkmexClientOptions);
  listCranes(options?: ListCranesOptions): Promise<InventoryResponse>;
  getCrane(id: string): Promise<Crane>;
  compareCranes(ids: string[]): Promise<ComparisonResponse>;
}
~~~

- [ ] **Step 5: Add the package README**

Create packages/gkmex/README.md:

~~~~markdown
# gkmex

Zero-auth JavaScript SDK and command-line client for the public, read-only [Gkmex Cranes](https://gkmex.com) used mobile and crawler crane inventory.

## Requirements

Node.js 20 or newer.

## Install

~~~bash
npm install gkmex
~~~

## JavaScript SDK

~~~js
import { GkmexClient } from "gkmex";

const client = new GkmexClient();

const inventory = await client.listCranes({
  brand: "Liebherr",
  type: "mobile",
  limit: 5,
});

const crane = await client.getCrane(inventory.data[0].id);
const comparison = await client.compareCranes([
  inventory.data[0].id,
  inventory.data[1].id,
]);

console.log(crane.url);
console.log(comparison.data);
~~~

Available methods:

- client.listCranes({ brand, type, limit, offset, cursor })
- client.getCrane(publicId)
- client.compareCranes([firstPublicId, secondPublicId])

compareCranes accepts two to five unique public IDs and delegates to Gkmex's read-only MCP comparison tool.

## CLI

~~~bash
npx gkmex list --type mobile --limit 5
npx gkmex get crane-public-id
npx gkmex compare first-public-id second-public-id
~~~

Every successful command prints JSON. Invalid usage exits 2. API or network errors exit 1 and print a concise message to stderr.

## Public-data contract

The API requires no account, sign-up, token, or API key. Every operation is read-only.

A null price_eur means POA, never zero. Published inventory is an availability signal, not a reservation or final availability confirmation. Use each crane's public url and contact Gkmex to confirm specifications, price, inspection, transport, and final availability.

## Links

- Developer portal: https://gkmex.com/developers
- OpenAPI: https://gkmex.com/openapi.json
- Source: https://github.com/gkmex75/gkmex-developer-resources

## License

MIT
~~~~

- [ ] **Step 6: Add the package-local MIT license and executable mode**

Create packages/gkmex/LICENSE with the exact repository license:

~~~text
MIT License

Copyright (c) 2026 Gkmex Cranes

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
~~~

Set only the CLI executable bit:

~~~bash
chmod +x packages/gkmex/bin/gkmex.js
~~~

- [ ] **Step 7: Run the package test and verify GREEN**

Run:

~~~bash
cd packages/gkmex
node --test test/package.test.js
~~~

Expected: 2 tests pass, 0 fail; npm pack dry-run contains exactly the seven allowlisted files.

- [ ] **Step 8: Run the full package suite**

Run:

~~~bash
cd packages/gkmex
npm test
~~~

Expected: 14 tests pass, 0 fail.

- [ ] **Step 9: Commit the publishable artifact**

~~~bash
git add packages/gkmex/package.json packages/gkmex/src/index.d.ts packages/gkmex/README.md packages/gkmex/LICENSE packages/gkmex/bin/gkmex.js packages/gkmex/test/package.test.js
git commit -m "docs: prepare Gkmex npm package"
~~~

## Task 5: Release Verification and npm Publication Gate

**Files:**

- Verify only; no source file changes expected.

- [ ] **Step 1: Run fresh complete verification**

Run:

~~~bash
cd packages/gkmex
npm test
npm pack --dry-run --json
~~~

Expected: 14 tests pass; dry-run reports gkmex@1.0.0 and exactly LICENSE, README.md, bin/gkmex.js, package.json, src/client.js, src/index.d.ts, and src/index.js.

- [ ] **Step 2: Verify installation from the real tarball in a clean temporary project**

Run from packages/gkmex:

~~~bash
release_tmp=$(mktemp -d)
trap 'rm -rf "$release_tmp"' EXIT
npm pack --pack-destination "$release_tmp"
mkdir "$release_tmp/app"
cd "$release_tmp/app"
npm init -y
npm install "$release_tmp/gkmex-1.0.0.tgz"
node --input-type=module -e 'import { GkmexClient, GkmexError } from "gkmex"; if (typeof GkmexClient !== "function" || typeof GkmexError !== "function") process.exit(1)'
./node_modules/.bin/gkmex --version
~~~

Expected: clean install succeeds, the import command exits 0, and the CLI prints 1.0.0.

- [ ] **Step 3: Run one read-only production smoke request from the reviewed CLI**

Run from packages/gkmex so this step does not depend on shell state from Step 2:

~~~bash
node bin/gkmex.js list --limit 1
~~~

Expected: exit 0 and JSON with count, data, and no authentication prompt. Confirm that any null price_eur remains null.

- [ ] **Step 4: Verify repository cleanliness**

Return to the worktree root and run:

~~~bash
cd "$(git rev-parse --show-toplevel)"
git diff --check
git status --short
git log --oneline --decorate -5
~~~

Expected: no uncommitted files, no whitespace errors, and the design plus implementation commits visible on feat/npm-sdk-cli.

- [ ] **Step 5: Check the publication identity without exposing credentials**

Run from packages/gkmex:

~~~bash
npm whoami
~~~

Expected when authenticated: one npm username and exit 0.

If it returns E401, stop the publication substep, report exactly that npm authentication is missing, and do not add a website link or claim npm/Ora completion. The reviewed branch may still proceed through its normal PR/merge workflow.

- [ ] **Step 6: Recheck package-name availability immediately before publication**

Run:

~~~bash
availability_log=$(mktemp)
trap 'rm -f "$availability_log"' EXIT
if npm view gkmex name >"$availability_log" 2>&1; then
  printf 'STOP: npm package gkmex is now owned; do not publish or rename silently.\n'
  sed -n '1,20p' "$availability_log"
  exit 1
fi
if ! rg -q 'E404|Not Found' "$availability_log"; then
  printf 'STOP: npm availability check failed for a reason other than an unused name.\n'
  sed -n '1,20p' "$availability_log"
  exit 1
fi
~~~

Expected: the registry returns E404/Not Found, proving the selected name is still unused. Any other result stops publication.

- [ ] **Step 7: Publish the reviewed public package**

This external write is already within the owner-approved npm publication scope. Run only after Steps 1–6 pass:

~~~bash
npm publish --access public
~~~

Expected: npm reports + gkmex@1.0.0. Do not retry blindly if the registry returns an ambiguous failure; first run npm view gkmex@1.0.0 to determine whether the release landed.

- [ ] **Step 8: Verify the public registry and clean-environment CLI**

Run:

~~~bash
npm view gkmex@1.0.0 name version description homepage repository bin engines --json
public_tmp=$(mktemp -d)
trap 'rm -rf "$public_tmp"' EXIT
cd "$public_tmp"
npx --yes gkmex@1.0.0 --version
npx --yes gkmex@1.0.0 list --limit 1
~~~

Expected: metadata matches the reviewed package, version prints 1.0.0, and the list command returns public inventory JSON without authentication.

- [ ] **Step 9: Record the boundary for the follow-up site phase**

Report the exact npm version and public package URL https://www.npmjs.com/package/gkmex. Do not modify gkmex-site or call Ora.ai in this plan. The next approved design/plan must add the now-live npm link to generated developer resources, deploy the exact reviewed site commit, and then use the separately governed targeted Ora.ai check budget.
