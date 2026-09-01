# Gkmex Python SDK and CLI

`gkmex` is the official zero-auth Python SDK and command-line client for the public Gkmex used-crane inventory. It requires no account, token, or API key. Every operation is read-only.

## Install

```bash
pip install gkmex
```

Python 3.10 or newer is required. The installed package has no runtime dependencies.

## Python SDK

```python
from gkmex import GkmexClient

client = GkmexClient()
inventory = client.list_cranes(brand="Liebherr", limit=5)
crane = client.get_crane(inventory["data"][0]["id"])
comparison = client.compare_cranes([
    inventory["data"][0]["id"],
    inventory["data"][1]["id"],
])

print(crane["url"])
print(comparison)
```

`list_cranes` supports the published `brand`, `type`, `limit`, `offset`, and `cursor` filters. `get_crane` reads one public record. `compare_cranes` asks the public Gkmex MCP tool to compare two to five unique crane IDs.

Methods return ordinary Python dictionaries and lists with the published field names unchanged. A JSON `price_eur` value of `null` becomes Python `None`; it means POA (price on application), not zero.

## CLI

Every successful command writes indented JSON to stdout:

```bash
gkmex list --brand Liebherr --limit 5
gkmex get PUBLIC_ID
gkmex compare PUBLIC_ID PUBLIC_ID
```

Use `gkmex --help` for the complete option list and `gkmex --version` for the installed version. Invalid usage exits with status 2. API, MCP, or network failures print a concise message to stderr and exit with status 1.

## Commercial boundary

A published crane listing is an inventory signal, not a reservation. Follow the public record's `url` field and contact Gkmex to confirm final specifications and availability, condition information, transport, financing, and commercial terms before a purchase decision.

## Public resources

- Developer documentation: https://gkmex.com/developers
- Source and issues: https://github.com/gkmex75/gkmex-developer-resources
- Public inventory: https://gkmex.com/api/v1/cranes
