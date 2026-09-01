# Gkmex Portable Agent Plugin v1 Design

## Goal

Publish the existing public Gkmex inventory skill and remote MCP server as one
truthful, portable Agent Plugins v1 package, then make that package explicit on
the existing gkmex.com developer-discovery surfaces. The intended Ora.ai outcome
is to move `agent-plugins-repo` from fail to pass without inventing capabilities,
authentication, write operations, or a second MCP service.

## Current State

The public `gkmex75/gkmex-developer-resources` repository is already discovered
by Ora.ai and already contains:

- `skills/gkmex-inventory/SKILL.md`;
- `.mcp.json` for clients using the existing Codex-style configuration;
- `.codex-plugin/plugin.json` for Codex-specific presentation metadata;
- the public REST, MCP, NLWeb, OpenAPI, npm SDK, and PyPI SDK resources.

The missing portable contract is the Agent Plugins v1 root layout. The standard
requires `plugin.json` at the plugin root, discovers skills from `skills/`, and
discovers MCP servers from root `mcp.json`. The portable manifest is a closed
schema and therefore must not copy Codex-only fields such as `skills`,
`mcpServers`, or `interface` into root `plugin.json`.

The live Gkmex site already links the public developer repository from its
developer portal and machine-readable guides. This release will make the link's
Agent Plugin purpose explicit and add the repository to the API catalog's
documentation links.

## Scope

### Developer resources repository

Create root `plugin.json` with this exact portable identity:

- schema: `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`;
- name: `gkmex-developer-resources`;
- version: `0.1.0`, matching the existing Codex plugin version;
- description limited to the existing public, zero-auth, read-only inventory;
- author: Gkmex Cranes at `https://gkmex.com`;
- homepage: `https://gkmex.com/developers`;
- repository: `https://github.com/gkmex75/gkmex-developer-resources`;
- license: `MIT`;
- keywords for Gkmex, cranes, inventory, MCP, Agent Skills, npm, and PyPI.

Create root `mcp.json` with the Agent Plugins v1 MCP schema and exactly one
server:

- name: `gkmex-inventory`;
- type: `streamable-http`;
- URL: `https://gkmex.com/mcp`.

The configuration must contain no headers, variables, credentials, OAuth
claims, fallback transports, or alternative endpoints. The existing
`.codex-plugin/plugin.json` and `.mcp.json` remain intact because they serve a
different client contract.

Update the repository README to distinguish the portable Agent Plugins files
from the Codex-specific files and document that `skills/gkmex-inventory` is
discovered at its fixed standard location.

### Gkmex site repository

Keep `build_site.py` as the only source of generated site artifacts. Add
constants for the public plugin root and root manifest, then describe the
existing repository link as the `Gkmex portable Agent Plugin` on:

- `/developers` and `/developers.md`;
- `/llms.txt` and `/.well-known/llms.txt`;
- `/llms-full.txt`, `/index.md`, and `/agents.md`;
- `/developers/llms.txt`.

Add one exact API catalog `service-doc` entry whose URL is the public repository
root and whose title is `Gkmex portable Agent Plugin`. The human developer page
also links directly to the root `plugin.json` source on GitHub. Do not add the
GitHub URL to the sitemap because it is external.

## Architecture and Release Order

The GitHub repository itself is the plugin package root. This avoids a nested
directory that Ora.ai or other clients would have to guess and reuses the
existing standard `skills/` directory without copying the skill.

Release is deliberately ordered across two repositories:

1. Merge the portable package into `gkmex-developer-resources`.
2. Verify the public GitHub `plugin.json`, `mcp.json`, and skill paths.
3. Merge the generated discovery-copy change into `gkmex-site`.
4. Deploy the exact merged Gkmex site tree and verify live link parity.
5. Run one targeted Ora.ai `agent-plugins-repo` check. Only if it improves may
   one non-forced full scan run. Never use `force: true` for this release.

The site never proxies or executes the plugin files. It only points agents to
the public package root; clients load the package from GitHub and connect to the
existing public Streamable HTTP MCP endpoint.

## Validation and Tests

### Developer resources repository

Add a root unittest contract that fails before implementation and then enforces:

- exact portable `plugin.json` content and allowed top-level fields;
- exact portable `mcp.json` content;
- matching Agent Plugins schema versions;
- exact `streamable-http` endpoint;
- absence of headers, credentials, tokens, environment variables, and auth
  configuration;
- presence and valid frontmatter of `skills/gkmex-inventory/SKILL.md`;
- preservation of the existing Codex-specific manifest and MCP configuration;
- README coverage for both portable and Codex-specific entry points.

Validate both new JSON documents against the canonical Agent Plugins v1 schemas
as a separate release gate. The gate must download only the versioned canonical
schema URLs and reject unexpected bytes before validation. The approved SHA-256
digests are `0a4aad95ce337878ad38802ebf0daa3fde76abe3f65400c86bcbb1ec0b3ab883`
for `plugin.schema.json` and
`6539175bfcdf43085855183e86da40ea94b166547a72b47ae9a0a390516d3acb`
for `mcp.schema.json`. Run the existing root workflow tests, Python package
tests, and npm tests unchanged.

### Gkmex site repository

Extend the generated-site acceptance test before implementation so it requires:

- the exact plugin repository and manifest URLs;
- the exact `Gkmex portable Agent Plugin` label on every approved discovery
  surface;
- exactly one ordered API catalog entry;
- no portable-plugin claim on unrelated inventory pages;
- regenerated artifacts that match `build_site.py` byte-for-byte.

Run the complete Python and Worker suites, JSON validation, syntax/parity checks,
and `git diff --check` before release.

### Live acceptance

After both merges, verify:

- the GitHub package files return the merged bytes;
- both documents pass the canonical Agent Plugins v1 schemas;
- the MCP Inspector can initialize `https://gkmex.com/mcp` and list the existing
  three read-only tools;
- every changed gkmex.com artifact matches the deployed merge tree;
- no tag, package release, API write, or additional MCP surface was created.

## Failure Handling and Rollback

A schema-validation, repository-path, MCP-handshake, generated-artifact, or live
byte-parity failure blocks the Ora measurement. Fix the source and re-run local
and live acceptance before measuring.

If the developer repository is correct but the site deployment regresses,
revert only the site discovery-copy commit and redeploy the last known-good site
tree. The portable plugin can remain published because it does not change the
live API. If the portable package itself is invalid after merge, revert its
single implementation commit before publishing site discovery links.

An unchanged Ora result is not a rollback condition when the official schemas,
public GitHub files, site links, and live MCP behavior all pass. Do not create a
fake second MCP server, write action, credential flow, or client extension to
chase the score.

## Acceptance Criteria

- The public developer repository is a conformant Agent Plugins v1 package.
- It exposes exactly the existing inventory skill and existing public remote MCP
  server through standard fixed locations.
- No credential or write capability is introduced.
- Gkmex developer-discovery surfaces name and link the portable plugin.
- Existing tests remain green and the new contracts pass from both merged trees.
- Live GitHub, gkmex.com, and MCP evidence match the merged source.
- Ora.ai is measured once through the quota-safe targeted gate and is reported
  without overstating cache or scanner results.
