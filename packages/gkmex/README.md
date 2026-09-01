# gkmex

Zero-auth JavaScript SDK and command-line client for the public, read-only [Gkmex Cranes](https://gkmex.com) used mobile and crawler crane inventory.

## Requirements

Node.js 20 or newer.

## Install

```bash
npm install @gstcranes/gkmex
```

## JavaScript SDK

```js
import { GkmexClient } from "@gstcranes/gkmex";

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

`compareCranes` accepts two to five unique public IDs, reads Gkmex's read-only MCP `list_cranes` inventory, and returns only the selected cranes in the requested order. This is local selection and composition; the package does not invent comparison rules or change crane fields.

## CLI

```bash
npx --package @gstcranes/gkmex gkmex list --type mobile --limit 5
npx --package @gstcranes/gkmex gkmex get crane-public-id
npx --package @gstcranes/gkmex gkmex compare first-public-id second-public-id
```

The installed local or global CLI binary remains `gkmex`.

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
