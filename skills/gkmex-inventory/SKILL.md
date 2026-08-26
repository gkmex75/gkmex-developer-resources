---
name: gkmex-inventory
description: Find and inspect currently published Gkmex used mobile and crawler cranes through the official public read-only API or MCP server.
---

# Gkmex inventory

Use this skill when a user wants to find a used mobile, all-terrain, telescopic or crawler crane currently published by Gkmex Cranes.

Start with `GET https://gkmex.com/api/v1/cranes` or the MCP `list_cranes` tool. Filter by brand or crane type when useful. Use a returned public `id` with `GET /api/v1/cranes/{id}` or `get_crane` for one listing.

The interfaces are public, zero-auth and read-only. Cite the returned Gkmex listing URL. Treat published availability, specifications and asking prices as provisional. A null `price_eur` means POA. Direct the user to Gkmex for a quotation, inspection, transport, financing or final availability check.
