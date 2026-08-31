import assert from "node:assert/strict";
import test from "node:test";

import { GkmexClient, GkmexError } from "../src/index.js";
import { readJson, sendJson, withServer } from "./helpers.js";

function comparisonData(ids = ["crane-1", "crane-2"]) {
  return {
    updated_at: "2026-08-31",
    count: ids.length,
    data: ids.map((id) => ({ id, price_eur: null })),
  };
}

function mcpResult(structuredContent = comparisonData()) {
  return {
    jsonrpc: "2.0",
    id: 1,
    result: { structuredContent },
  };
}

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

test("compareCranes selects requested cranes from public MCP inventory", async () => {
  const inventory = {
    updated_at: "2026-08-31T12:00:00Z",
    count: 3,
    data: [
      {
        id: "crane-extra",
        price_eur: 99000,
        url: "https://gkmex.com/en/crane/crane-extra",
      },
      {
        id: "crane-1",
        price_eur: null,
        url: "https://gkmex.com/en/crane/crane-1",
      },
      {
        id: "crane-2",
        price_eur: 175000,
        url: "https://gkmex.com/en/crane/crane-2",
      },
    ],
  };
  const expected = {
    updated_at: inventory.updated_at,
    count: 2,
    data: [inventory.data[2], inventory.data[1]],
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
        name: "list_cranes",
        arguments: {},
      },
    });
    sendJson(response, 200, mcpResult(inventory));
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });
    const result = await client.compareCranes(["crane-2", "crane-1"]);

    assert.deepEqual(result, expected);
    assert.equal(result.data[1].price_eur, null);
    assert.equal(result.data[1].url, "https://gkmex.com/en/crane/crane-1");
  });
});

test("compareCranes preserves a configured base URL path", async () => {
  await withServer(async (request, response) => {
    assert.equal(request.url, "/proxy/v1/mcp");
    assert.deepEqual(await readJson(request), {
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: { name: "list_cranes", arguments: {} },
    });
    sendJson(
      response,
      200,
      mcpResult(comparisonData(["crane-1", "crane-2"])),
    );
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl: baseUrl + "/proxy/v1/" });
    const result = await client.compareCranes(["crane-2", "crane-1"]);

    assert.deepEqual(result, comparisonData(["crane-2", "crane-1"]));
  });
});

test("compareCranes rejects the first requested ID absent from inventory", async () => {
  await withServer(async (request, response) => {
    await readJson(request);
    sendJson(
      response,
      200,
      mcpResult(comparisonData(["crane-1", "crane-3"])),
    );
  }, async (baseUrl) => {
    const client = new GkmexClient({ baseUrl });

    await assert.rejects(
      client.compareCranes(["crane-1", "missing-first", "missing-second"]),
      (error) => {
        assert.ok(error instanceof GkmexError);
        assert.equal(error.message, "Crane not found: missing-first");
        return true;
      },
    );
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
    ["a non-string ID", ["crane-1", 2]],
    ["a blank ID", ["crane-1", "  "]],
    ["leading whitespace", ["crane-1", " crane-2"]],
    ["trailing whitespace", ["crane-1", "crane-2 "]],
    ["a dot segment", ["crane-1", "."]],
    ["a parent segment", ["crane-1", ".."]],
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
    sendJson(response, 422, {
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
        assert.equal(error.status, 422);
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

test("malformed non-2xx MCP JSON preserves status and parse cause", async () => {
  await withServer((_request, response) => {
    response.writeHead(502, { "content-type": "application/json" });
    response.end("{");
  }, async (baseUrl) => {
    await assert.rejects(
      new GkmexClient({ baseUrl }).compareCranes(["crane-1", "crane-2"]),
      (error) => {
        assert.ok(error instanceof GkmexError);
        assert.equal(error.message, "Gkmex returned invalid JSON");
        assert.equal(error.status, 502);
        assert.ok(error.cause instanceof SyntaxError);
        return true;
      },
    );
  });
});

test("getCrane rejects non-canonical IDs without fetching", async (t) => {
  let fetchCalls = 0;
  const client = new GkmexClient({
    fetch: async () => {
      fetchCalls += 1;
      throw new Error("fetch must not be called");
    },
  });

  for (const [name, id] of [
    ["non-string", 2],
    ["empty", ""],
    ["blank", "  "],
    ["leading whitespace", " crane-1"],
    ["trailing whitespace", "crane-1 "],
    ["dot segment", "."],
    ["parent segment", ".."],
  ]) {
    await t.test(name, async () => {
      await assert.rejects(client.getCrane(id), (error) => {
        assert.ok(error instanceof GkmexError);
        assert.equal(error.message, "id must be a non-empty public crane ID");
        return true;
      });
    });
  }
  assert.equal(fetchCalls, 0);
});

test("compareCranes rejects an unexpected MCP result", async () => {
  await withServer(async (request, response) => {
    await readJson(request);
    sendJson(response, 200, mcpResult(null));
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

test("JSON media-type parsing accepts suffixes and rejects lookalikes", async (t) => {
  await t.test("accepts application/*+json", async () => {
    await withServer((_request, response) => {
      response.writeHead(200, {
        "content-type": "Application/Problem+JSON ; charset=UTF-8",
      });
      response.end(JSON.stringify({ data: [] }));
    }, async (baseUrl) => {
      const result = await new GkmexClient({ baseUrl }).listCranes();
      assert.deepEqual(result, { data: [] });
    });
  });

  await t.test("rejects application/jsonp", async () => {
    await withServer((_request, response) => {
      response.writeHead(200, { "content-type": "application/jsonp" });
      response.end(JSON.stringify({ data: [] }));
    }, async (baseUrl) => {
      await assert.rejects(
        new GkmexClient({ baseUrl }).listCranes(),
        (error) => {
          assert.ok(error instanceof GkmexError);
          assert.equal(
            error.message,
            "Gkmex returned an unexpected response",
          );
          assert.equal(error.status, 200);
          return true;
        },
      );
    });
  });
});

test("REST endpoints reject event-stream responses", async () => {
  await withServer((_request, response) => {
    response.writeHead(200, { "content-type": "text/event-stream" });
    response.end("data: {}\n\n");
  }, async (baseUrl) => {
    await assert.rejects(
      new GkmexClient({ baseUrl }).listCranes(),
      (error) => {
        assert.ok(error instanceof GkmexError);
        assert.equal(error.message, "Gkmex returned an unexpected response");
        return true;
      },
    );
  });
});

test("compareCranes uses stable HTTP errors for non-RPC failures", async () => {
  await withServer((_request, response) => {
    sendJson(response, 503, { error: "MCP unavailable" });
  }, async (baseUrl) => {
    await assert.rejects(
      new GkmexClient({ baseUrl }).compareCranes(["crane-1", "crane-2"]),
      (error) => {
        assert.ok(error instanceof GkmexError);
        assert.equal(error.message, "MCP unavailable");
        assert.equal(error.status, 503);
        assert.deepEqual(error.details, { error: "MCP unavailable" });
        assert.equal("code" in error, false);
        return true;
      },
    );
  });
});

test("compareCranes validates JSON-RPC response envelopes", async (t) => {
  const validResult = { structuredContent: comparisonData() };
  const cases = [
    ["non-object", []],
    ["wrong version", { jsonrpc: "1.0", id: 1, result: validResult }],
    ["mismatched ID", { jsonrpc: "2.0", id: 2, result: validResult }],
    [
      "both result and error",
      {
        jsonrpc: "2.0",
        id: 1,
        result: validResult,
        error: { code: -32603, message: "bad" },
      },
    ],
    ["neither result nor error", { jsonrpc: "2.0", id: 1 }],
  ];

  for (const [name, payload] of cases) {
    await t.test(name, async () => {
      await withServer((_request, response) => {
        sendJson(response, 200, payload);
      }, async (baseUrl) => {
        await assert.rejects(
          new GkmexClient({ baseUrl }).compareCranes([
            "crane-1",
            "crane-2",
          ]),
          (error) => {
            assert.ok(error instanceof GkmexError);
            assert.equal(
              error.message,
              "Gkmex returned an unexpected MCP result",
            );
            return true;
          },
        );
      });
    });
  }
});

test("compareCranes turns MCP tool errors into stable errors", async (t) => {
  const cases = [
    [
      "first text content",
      [
        { type: "image", data: "ignored" },
        { type: "text", text: 123 },
        { type: "text", text: "Comparison failed" },
        { type: "text", text: "Later detail" },
      ],
      "Comparison failed",
    ],
    ["fallback", undefined, "Gkmex MCP tool returned an error"],
  ];

  for (const [name, content, expectedMessage] of cases) {
    await t.test(name, async () => {
      await withServer((_request, response) => {
        sendJson(response, 200, {
          jsonrpc: "2.0",
          id: 1,
          result: {
            isError: true,
            ...(content === undefined ? {} : { content }),
          },
        });
      }, async (baseUrl) => {
        await assert.rejects(
          new GkmexClient({ baseUrl }).compareCranes([
            "crane-1",
            "crane-2",
          ]),
          (error) => {
            assert.ok(error instanceof GkmexError);
            assert.equal(error.message, expectedMessage);
            assert.equal(error.status, 200);
            return true;
          },
        );
      });
    });
  }
});

test("compareCranes rejects non-boolean result.isError", async (t) => {
  for (const value of ["true", 1, null]) {
    await t.test(JSON.stringify(value), async () => {
      await withServer((_request, response) => {
        sendJson(response, 200, {
          jsonrpc: "2.0",
          id: 1,
          result: {
            isError: value,
            structuredContent: comparisonData(),
          },
        });
      }, async (baseUrl) => {
        await assert.rejects(
          new GkmexClient({ baseUrl }).compareCranes([
            "crane-1",
            "crane-2",
          ]),
          (error) => {
            assert.ok(error instanceof GkmexError);
            assert.equal(
              error.message,
              "Gkmex returned an unexpected MCP result",
            );
            return true;
          },
        );
      });
    });
  }
});

test("compareCranes validates structured comparison content", async (t) => {
  const cases = [
    ["missing updated_at", { count: 0, data: [] }],
    ["non-integer count", { updated_at: "now", count: 0.5, data: [] }],
    ["non-array data", { updated_at: "now", count: 0, data: {} }],
    ["inconsistent count", { updated_at: "now", count: 1, data: [] }],
  ];

  for (const [name, structuredContent] of cases) {
    await t.test(name, async () => {
      await withServer((_request, response) => {
        sendJson(response, 200, mcpResult(structuredContent));
      }, async (baseUrl) => {
        await assert.rejects(
          new GkmexClient({ baseUrl }).compareCranes([
            "crane-1",
            "crane-2",
          ]),
          (error) => {
            assert.ok(error instanceof GkmexError);
            assert.equal(
              error.message,
              "Gkmex returned an unexpected MCP result",
            );
            return true;
          },
        );
      });
    });
  }
});

test("compareCranes reads a matching JSON-RPC response from SSE", async () => {
  const expected = comparisonData(["crane-2", "crane-1"]);
  const notification = {
    jsonrpc: "2.0",
    method: "notifications/progress",
    params: { progress: 0.5 },
  };
  const serverRequest = {
    jsonrpc: "2.0",
    id: 1,
    method: "sampling/createMessage",
    params: {},
  };
  const mismatched = {
    jsonrpc: "2.0",
    id: 2,
    result: { structuredContent: comparisonData([]) },
  };
  const result = JSON.stringify({ structuredContent: expected });
  const body = [
    ": keepalive",
    "event: message",
    "data: " + JSON.stringify(notification),
    "",
    "id: server-request",
    "data: " + JSON.stringify(serverRequest),
    "",
    "retry: 1000",
    "data: " + JSON.stringify(mismatched),
    "",
    "event: message",
    'data: {"jsonrpc":"2.0",',
    'data: "id":1,"result":' + result + "}",
    "",
    "",
  ].join("\n");

  await withServer((_request, response) => {
    response.writeHead(200, {
      "content-type": "Text/Event-Stream ; charset=utf-8",
    });
    response.end(body);
  }, async (baseUrl) => {
    const actual = await new GkmexClient({ baseUrl }).compareCranes([
      "crane-2",
      "crane-1",
    ]);
    assert.deepEqual(actual, expected);
  });
});

test("compareCranes rejects malformed or unmatched SSE responses", async (t) => {
  const cases = [
    ["malformed data", "data: {\n\n"],
    [
      "no matching response",
      [
        "data: " +
          JSON.stringify({
            jsonrpc: "2.0",
            method: "notifications/progress",
          }),
        "",
        "data: " +
          JSON.stringify({
            jsonrpc: "2.0",
            id: 2,
            result: { structuredContent: comparisonData([]) },
          }),
        "",
        "",
      ].join("\n"),
    ],
  ];

  for (const [name, body] of cases) {
    await t.test(name, async () => {
      await withServer((_request, response) => {
        response.writeHead(200, { "content-type": "text/event-stream" });
        response.end(body);
      }, async (baseUrl) => {
        await assert.rejects(
          new GkmexClient({ baseUrl }).compareCranes([
            "crane-1",
            "crane-2",
          ]),
          (error) => {
            assert.ok(error instanceof GkmexError);
            assert.equal(
              error.message,
              "Gkmex returned an unexpected MCP result",
            );
            return true;
          },
        );
      });
    });
  }
});
