import assert from "node:assert/strict";
import test from "node:test";

import { GkmexClient, GkmexError } from "../src/index.js";
import { readJson, sendJson, withServer } from "./helpers.js";

test("withServer surfaces handler errors and closes connections", async (t) => {
  const cases = [
    ["synchronous", (error) => () => {
      throw error;
    }],
    ["immediate asynchronous", (error) => async () => {
      throw error;
    }],
    ["delayed asynchronous", (error) => async (_request, response) => {
      sendJson(response, 200, {});
      await new Promise((resolve) => setTimeout(resolve, 20));
      throw error;
    }],
  ];

  for (const [name, createHandler] of cases) {
    await t.test(name, async () => {
      const expected = new Error(name + " handler failed");

      await assert.rejects(
        withServer(createHandler(expected), async (baseUrl) => {
          await fetch(baseUrl);
        }),
        (error) => error === expected,
      );
    });
  }
});

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

test("listCranes preserves a configured base URL path", async () => {
  await withServer((request, response) => {
    assert.equal(request.url, "/proxy/v1/api/v1/cranes");
    sendJson(response, 200, { data: [] });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl: baseUrl + "/proxy/v1/" });
    const result = await client.listCranes();

    assert.deepEqual(result.data, []);
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

test("compareCranes delegates to MCP and preserves the input order", async () => {
  const expected = {
    cranes: [
      { id: "crane-1", price_eur: null },
      { id: "crane-2", price_eur: 120000 },
    ],
  };

  await withServer(async (request, response) => {
    assert.equal(request.method, "POST");
    assert.equal(request.url, "/mcp");
    assert.equal(request.headers["content-type"], "application/json");
    assert.equal(
      request.headers.accept,
      "application/json, text/event-stream",
    );
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
      result: { structuredContent: expected },
    });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });
    const result = await client.compareCranes(["crane-1", "crane-2"]);

    assert.deepEqual(result, expected);
    assert.equal(result.cranes[0].price_eur, null);
  });
});

test("compareCranes preserves a configured base URL path", async () => {
  await withServer(async (request, response) => {
    assert.equal(request.url, "/proxy/v1/mcp");
    assert.deepEqual((await readJson(request)).params.arguments.ids, [
      "crane-2",
      "crane-1",
    ]);
    sendJson(response, 200, {
      result: { structuredContent: { cranes: [] } },
    });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl: baseUrl + "/proxy/v1/" });
    const result = await client.compareCranes(["crane-2", "crane-1"]);

    assert.deepEqual(result, { cranes: [] });
  });
});

test("compareCranes rejects invalid IDs without fetching", async (t) => {
  const cases = [
    ["fewer than two", ["crane-1"]],
    ["duplicates", ["crane-1", "crane-1"]],
    [
      "more than five",
      ["crane-1", "crane-2", "crane-3", "crane-4", "crane-5", "crane-6"],
    ],
    ["an empty ID", ["crane-1", ""]],
  ];

  for (const [name, ids] of cases) {
    await t.test(name, async () => {
      let fetchCalls = 0;
      const client = new GkmexClient({
        fetch: async () => {
          fetchCalls += 1;
          throw new Error("fetch must not be called");
        },
      });

      await assert.rejects(client.compareCranes(ids), (error) => {
        assert.ok(error instanceof GkmexError);
        assert.equal(
          error.message,
          "ids must contain two to five unique public crane IDs",
        );
        return true;
      });
      assert.equal(fetchCalls, 0);
    });
  }
});

test("getCrane maps public REST errors to GkmexError", async () => {
  await withServer((request, response) => {
    assert.equal(request.url, "/api/v1/cranes/missing");
    sendJson(response, 404, { error: "Crane not found" });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });

    await assert.rejects(client.getCrane("missing"), (error) => {
      assert.ok(error instanceof GkmexError);
      assert.equal(error.message, "Crane not found");
      assert.equal(error.status, 404);
      assert.deepEqual(error.details, { error: "Crane not found" });
      assert.equal("code" in error, false);
      return true;
    });
  });
});

test("compareCranes maps JSON-RPC errors to GkmexError", async () => {
  await withServer(async (request, response) => {
    await readJson(request);
    sendJson(response, 200, {
      jsonrpc: "2.0",
      id: 1,
      error: {
        code: -32602,
        message: "Crane not found",
        data: { id: "missing" },
      },
    });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });

    await assert.rejects(
      client.compareCranes(["missing", "crane-2"]),
      (error) => {
        assert.ok(error instanceof GkmexError);
        assert.equal(error.message, "Crane not found");
        assert.equal(error.code, -32602);
        assert.deepEqual(error.details, { id: "missing" });
        assert.equal("status" in error, false);
        return true;
      },
    );
  });
});

test("network failures become GkmexError with the original cause", async () => {
  const cause = new Error("connection refused");
  const client = new GkmexClient({
    fetch: async () => {
      throw cause;
    },
  });

  await assert.rejects(client.getCrane("crane-1"), (error) => {
    assert.ok(error instanceof GkmexError);
    assert.equal(error.message, "Unable to reach Gkmex");
    assert.equal(error.cause, cause);
    assert.equal("status" in error, false);
    assert.equal("code" in error, false);
    assert.equal("details" in error, false);
    return true;
  });
});

test("non-JSON responses become stable GkmexError instances", async () => {
  await withServer((_request, response) => {
    response.writeHead(200, { "content-type": "text/plain" });
    response.end("not JSON");
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });

    await assert.rejects(client.getCrane("crane-1"), (error) => {
      assert.ok(error instanceof GkmexError);
      assert.equal(error.message, "Gkmex returned an unexpected response");
      assert.equal(error.status, 200);
      return true;
    });
  });
});

test("invalid JSON responses become stable GkmexError instances", async () => {
  await withServer((_request, response) => {
    response.writeHead(200, { "content-type": "application/json" });
    response.end("{");
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });

    await assert.rejects(client.getCrane("crane-1"), (error) => {
      assert.ok(error instanceof GkmexError);
      assert.equal(error.message, "Gkmex returned invalid JSON");
      assert.equal(error.status, 200);
      assert.ok(error.cause instanceof SyntaxError);
      return true;
    });
  });
});

test("getCrane rejects an empty ID without fetching", async () => {
  let fetchCalls = 0;
  const client = new GkmexClient({
    fetch: async () => {
      fetchCalls += 1;
      throw new Error("fetch must not be called");
    },
  });

  await assert.rejects(client.getCrane("  "), (error) => {
    assert.ok(error instanceof GkmexError);
    assert.equal(error.message, "id must be a non-empty public crane ID");
    return true;
  });
  assert.equal(fetchCalls, 0);
});

test("compareCranes rejects an unexpected MCP result", async () => {
  await withServer(async (request, response) => {
    await readJson(request);
    sendJson(response, 200, { result: { structuredContent: null } });
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });

    await assert.rejects(
      client.compareCranes(["crane-1", "crane-2"]),
      (error) => {
        assert.ok(error instanceof GkmexError);
        assert.equal(error.message, "Gkmex returned an unexpected MCP result");
        return true;
      },
    );
  });
});
