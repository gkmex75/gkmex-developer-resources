import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

import { GkmexClient, GkmexError } from "../packages/gkmex/src/client.js";

const skillPath = new URL(
  "../skills/gkmex-api-integration/SKILL.md",
  import.meta.url,
);
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

function example() {
  assert.ok(existsSync(skillPath));
  const matches = [...readFileSync(skillPath, "utf8").matchAll(/```js\n([\s\S]*?)\n```/g)];
  assert.equal(matches.length, 1);
  const source = matches[0][1];
  assert.ok(source.startsWith('import { GkmexClient } from "@gstcranes/gkmex";'));
  const remaining = source.replace(
    'import { GkmexClient } from "@gstcranes/gkmex";\n',
    "",
  );
  return new AsyncFunction("GkmexClient", "console", remaining);
}

async function runExample(responses) {
  const requests = [];
  const lines = [];
  class FixtureClient extends GkmexClient {
    constructor() {
      super({
        fetch: async (url, init) => {
          const position = requests.length;
          requests.push({ url: new URL(url), init });
          assert.ok(position < responses.length, "unexpected additional request");
          const response = responses[position];
          const { status = 200, body = response } = response;
          return new Response(JSON.stringify(body), {
            status,
            headers: { "content-type": "application/json" },
          });
        },
      });
    }
  }
  await example()(FixtureClient, { log: (value) => lines.push(value) });
  return { requests, lines };
}

function crane(id) {
  return {
    id,
    brand: "Example",
    model: "Fixture",
    price_eur: null,
    url: `https://gkmex.com/en/crane/${id}`,
  };
}

function page(data, next_cursor, offset = 0) {
  return {
    updated_at: "2026-09-02",
    count: data.length,
    total: 3,
    limit: 100,
    offset,
    next_cursor,
    data,
  };
}

test("example follows opaque cursors with stable filters and no offset", async () => {
  const { requests, lines } = await runExample([
    page([crane("a"), crane("b")], "opaque token+/="),
    page([crane("c")], null, 2),
  ]);

  assert.deepEqual(lines, [
    "https://gkmex.com/en/crane/a",
    "https://gkmex.com/en/crane/b",
    "https://gkmex.com/en/crane/c",
  ]);
  assert.equal(requests.length, 2);
  for (const { url, init } of requests) {
    assert.equal(url.origin, "https://gkmex.com");
    assert.equal(url.pathname, "/api/v1/cranes");
    assert.equal(url.searchParams.get("type"), "mobile");
    assert.equal(url.searchParams.get("limit"), "100");
    assert.equal(url.searchParams.has("offset"), false);
    assert.equal(new Headers(init.headers).has("authorization"), false);
  }
  assert.equal(requests[0].url.searchParams.has("cursor"), false);
  assert.equal(requests[1].url.searchParams.get("cursor"), "opaque token+/=");
});

test("example accepts empty200 without inventing records", async () => {
  const { requests, lines } = await runExample([page([], null)]);
  assert.equal(requests.length, 1);
  assert.deepEqual(lines, []);
});

test("example propagates an HTTP failure instead of reporting empty success", async () => {
  await assert.rejects(
    runExample([{ status: 400, body: { error: "invalid filter" } }]),
    (error) => error instanceof GkmexError && error.status === 400,
  );
});
