---
name: gkmex-crane-comparison
description: Use when comparing two to five currently published Gkmex cranes, evaluating a shortlist against user-supplied priorities, or deciding which listing facts need commercial confirmation.
---

# Gkmex crane comparison

Compare only current Gkmex listings and keep published facts separate from commercial or engineering judgment.

## Retrieve the shortlist

Work with two to five unique public IDs. If the user has not supplied IDs, use `list_cranes` to form a relevant shortlist. For MCP, call `list_cranes` to retrieve the current inventory, select the requested IDs locally in caller order, and use `get_crane` when one listing needs its full published record.

If MCP is unavailable, use an available official Gkmex SDK or CLI, or REST: `GET https://gkmex.com/api/v1/cranes` to form a shortlist and `GET https://gkmex.com/api/v1/cranes/{id}` for one listing. These interfaces are public, zero-auth and read-only. Do not invent IDs or treat stale examples as current inventory.

## Compare published facts

Build a compact comparison table. Include the returned official `url` for every crane. Add only published fields relevant to the request: brand/model, year, crane type, capacity, `price_eur`, hours, kilometers and location.

`price_eur: null` means `POA`, never zero or the cheapest option. Mark other absent values as unknown. Do not infer missing specifications or silently convert units.

## Recommend conditionally

When the user supplies priorities, recommend conditionally using only those priorities. Explain ties and how missing data limits the result. Without priorities, present the factual comparison and do not name a winner; ask which criteria matter.

Published specifications, prices and availability are provisional. Direct quotations, inspections, transport, financing, technical-fit decisions and final availability confirmation to Gkmex. Do not claim that a crane is reserved, finally available or conclusively suitable for a lift.

## Common mistakes

- POA is unknown pricing, not a low price.
- Newer, larger or cheaper is not universally better.
- A published listing is an availability signal, not a reservation.
