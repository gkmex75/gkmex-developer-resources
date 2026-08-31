# gkmex

Zero-auth JavaScript SDK and command-line client for the public, read-only [Gkmex Cranes](https://gkmex.com) used mobile and crawler crane inventory.

## Requirements

Node.js 20 or newer.

## Install

```bash
npm install gkmex
```

## JavaScript SDK

```js
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
```

Available methods:

- `client.listCranes({ brand, type, limit, offset, cursor })`
- `client.getCrane(publicId)`
- `client.compareCranes([firstPublicId, secondPublicId])`

`compareCranes` accepts two to five unique public IDs and delegates to Gkmex's read-only MCP comparison tool.

## CLI

```bash
npx gkmex list --type mobile --limit 5
npx gkmex get crane-public-id
npx gkmex compare first-public-id second-public-id
```

Every successful command prints JSON. Invalid usage exits 2. API or network errors exit 1 and print a concise message to stderr.

## Public-data contract

The API requires no account, sign-up, token, or API key. Every operation is read-only.

A null `price_eur` means POA, never zero. Published inventory is an availability signal, not a reservation or final availability confirmation. Use each crane's public `url` and contact Gkmex to confirm specifications, price, inspection, transport, and final availability.

## Links

- Developer portal: https://gkmex.com/developers
- OpenAPI: https://gkmex.com/openapi.json
- Source: https://github.com/gkmex75/gkmex-developer-resources

## License

MIT
