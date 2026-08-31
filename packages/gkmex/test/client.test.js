import assert from "node:assert/strict";
import test from "node:test";

import { GkmexClient } from "../src/index.js";
import { sendJson, withServer } from "./helpers.js";

test("withServer surfaces handler errors and closes connections", async (t) => {
  const cases = [
    ["synchronous", (error) => () => {
      throw error;
    }],
    ["asynchronous", (error) => async (_request, response) => {
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
