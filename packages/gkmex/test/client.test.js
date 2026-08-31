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
