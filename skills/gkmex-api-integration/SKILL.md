---
name: gkmex-api-integration
description: Use when building or troubleshooting an application that consumes Gkmex's public crane inventory through REST, the official JavaScript SDK, or the Python SDK.
---

# Gkmex API integration

Build consumers of the published inventory; use the inventory and comparison workflows for buying questions. Check the [developer guide](https://gkmex.com/developers) and [OpenAPI contract](https://gkmex.com/openapi.json) before adding integration behavior.

## Choose the existing interface

| Runtime | Official package | List / detail methods |
| --- | --- | --- |
| Node.js 20+ | `npm install @gstcranes/gkmex` | `listCranes` / `getCrane` |
| Python 3.10+ | `pip install gkmex` | `list_cranes` / `get_crane` |

Both export `GkmexClient` and `GkmexError`. Respect the application's chosen stack. If its runtime cannot use an SDK, call public REST instead: `GET https://gkmex.com/api/health`, `GET https://gkmex.com/api/v1/cranes`, and `GET https://gkmex.com/api/v1/cranes/{id}`. Use a returned public ID for details; never guess one.

All interfaces are public, zero-auth and read-only. Do not request an API key or invent OAuth. For direct HTTP clients, send `Accept: application/json`, a truthful application User-Agent and a finite timeout. A non-JSON403 can come from edge protection, not missing API credentials; inspect it without changing server protection.

## Read pages correctly

Collection filters are `brand`, `type` (`mobile` or `crawler`), `limit` (1–100), and either `offset` or `cursor`. Never send cursor and offset together. Keep filters stable across pages. Treat `next_cursor` as opaque: send it unchanged through normal query encoding, then stop when absent or null. `count` is this page's length, not the matching `total`.

```js
import { GkmexClient } from "@gstcranes/gkmex";

const client = new GkmexClient();
let cursor;
do {
  const page = await client.listCranes({
    type: "mobile",
    limit: 100,
    ...(cursor ? { cursor } : {}),
  });
  for (const crane of page.data) console.log(crane.url);
  cursor = page.next_cursor;
} while (cursor);
```

## Preserve data and failures

An empty `data` array with HTTP200 is a valid no-match result; guard before accessing its first record. A timeout, HTTP error or malformed response is not empty inventory. Expose failure or incomplete-result state; do not silently return an empty success. Inspect SDK `GkmexError.status` and public error details. Correct400 parameters or a404 ID before retrying; bound any transient retries and respect Retry-After when supplied.

Keep published field names, URLs and nullable values unchanged. `price_eur: null` means POA, never zero; separate any UI placeholder from the stored price. Published availability, prices and specifications remain provisional. Direct final commercial confirmation to Gkmex.

## Verify the consumer

Check a bounded live read and returned-ID lookup, then exercise multiple pages, empty data, POA and an HTTP failure. Report what actually passed; do not label partial or cached data as a fresh complete inventory.
