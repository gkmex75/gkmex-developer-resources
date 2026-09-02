# Gkmex developer resources

Official public integration resources for the [Gkmex Cranes](https://gkmex.com) used mobile and crawler crane inventory.

The REST API, NLWeb endpoint and MCP tools are free, zero-auth, require no sign-up and are read-only. Published inventory is an availability signal, not a reservation; confirm specifications, price and final availability with Gkmex.

## Quick start

```bash
curl https://gkmex.com/api/v1/cranes
curl 'https://gkmex.com/api/v1/cranes?type=mobile&limit=5'
```

The collection supports `brand`, `type`, `limit`, `cursor` and `offset`. Use a returned public `id` with `GET /api/v1/cranes/{id}`.

## Public interfaces

- [Developer portal](https://gkmex.com/developers)
- [OpenAPI 3.1](https://gkmex.com/openapi.json)
- [REST inventory](https://gkmex.com/api/v1/cranes)
- [MCP server](https://gkmex.com/mcp) — `list_cranes`, `get_crane`
- [MCP server card](https://gkmex.com/.well-known/mcp/server-card.json)
- [NLWeb 0.55 endpoint](https://gkmex.com/ask)
- [Agent Skills index](https://gkmex.com/.well-known/agent-skills/index.json)
- [llms.txt](https://gkmex.com/llms.txt)
- [Deprecation policy](https://gkmex.com/developers/deprecation-policy)

## Portable Agent Plugin

This repository root conforms to Agent Plugins 1.0.0 and packages the existing public Gkmex integration surfaces without credentials or write access.

- `plugin.json` — portable plugin identity and metadata
- `skills/gkmex-inventory/SKILL.md` — inventory search and inspection skill
- `skills/gkmex-crane-comparison/SKILL.md` — shortlist comparison skill
- `skills/gkmex-api-integration/SKILL.md` — API and SDK integration skill
- `mcp.json` — portable Streamable HTTP configuration for `https://gkmex.com/mcp`

The `.codex-plugin/plugin.json` and `.mcp.json` files remain available for Codex-compatible clients; they do not replace the portable root files.

## MCP configuration

This repository includes `.mcp.json` for clients that accept a remote Streamable HTTP server configuration. Connect to `https://gkmex.com/mcp`; no API key or OAuth flow is required.

## Agent integration files

- `plugin.json` — portable Agent Plugins 1.0.0 manifest
- `mcp.json` — portable Streamable HTTP MCP configuration
- `skills/gkmex-inventory/SKILL.md` — portable inventory skill
- `skills/gkmex-crane-comparison/SKILL.md` — portable comparison skill
- `skills/gkmex-api-integration/SKILL.md` — API and SDK integration skill
- `.claude/CLAUDE.md` — Claude integration guidance
- `.cursor/rules/gkmex.mdc` — Cursor rule
- `.windsurf/rules/gkmex.md` — Windsurf rule
- `.codex-plugin/plugin.json` — Codex plugin manifest
- `openapi.yaml` — compact copy of the public REST contract

## Safety and commercial boundaries

All interfaces are read-only. Do not claim that a listing is reserved or finally available. A null `price_eur` means POA, not zero. Link users to the public listing or [contact Gkmex](https://gkmex.com/contact) for quotations, inspections, transport, financing and final confirmation.
