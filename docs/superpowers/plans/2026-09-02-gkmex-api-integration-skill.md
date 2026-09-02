# Gkmex API Integration Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish and verify the third portable Gkmex skill for truthful API/SDK consumers without changing runtime behavior.

**Architecture:** Add one self-contained skill and README discovery entries. Extend root contracts and add a Node test that runs the actual fenced example using the real SDK with the HTTP boundary controlled. Keep all package, manifest and old skill bytes unchanged.

**Tech Stack:** Markdown/YAML, Python unittest, Node built-in test runner, official skills-ref, Git/GitHub, skills.sh read-only discovery.

---

## Context and file map

Worktree `/Users/gokmentanacar/.config/superpowers/worktrees/gkmex-developer-resources/gkmex-api-integration-skill`, branch `feat/gkmex-api-integration-skill`, base `534cbdaa937adad1d6cea678ea2f9ebc155ffc36`.

Approved design: `docs/superpowers/specs/2026-09-02-gkmex-api-integration-skill-design.md`.

- Create `skills/gkmex-api-integration/SKILL.md`.
- Modify `README.md` in the Portable Agent Plugin and Agent integration files lists only.
- Modify `tests/test_agent_plugin.py`: third name, third README list entry, exact new frontmatter and both old digests.
- Create `tests/test_api_integration_example.mjs`: executable-example contract.
- The design and this plan are separate allowed documentation files.
- No other files change. In particular, leave package code/metadata, plugin/MCP manifests, two existing skills, CI, and openapi.yaml untouched.

## Task 1: Implement and verify the portable skill

- [x] **1. Observe baseline behavior before creating the skill.** See the design's Behavioral evidence section. A and C meet core requirements; B hides503 and changes unknown price to0. No skill file existed during these runs. Record GREEN against the same tasks later.

- [ ] **2. Add failing repository contracts.** In `tests/test_agent_plugin.py`, add:

```python
API_SKILL = ROOT / "skills" / "gkmex-api-integration" / "SKILL.md"
API_DESCRIPTION = (
    "Use when building or troubleshooting an application that consumes Gkmex's "
    "public crane inventory through REST, the official JavaScript SDK, or the Python SDK."
)
COMPARISON_SHA256 = "8ca224019c41b17ffcbc083eab9caf8562681ac2b60016327771b1c5169b9870"
```

Add this method to `AgentPluginContractTests`:

```python
    def test_api_integration_skill_is_portable_and_discoverable(self):
        self.assertTrue(API_SKILL.is_file(), API_SKILL)
        text = API_SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(
            "---\nname: gkmex-api-integration\ndescription: "
            + API_DESCRIPTION + "\n---\n\n# Gkmex API integration\n"
        ))
        self.assertEqual(hashlib.sha256(SKILL.read_bytes()).hexdigest(), SKILL_SHA256)
        self.assertEqual(hashlib.sha256(COMPARISON_SKILL.read_bytes()).hexdigest(), COMPARISON_SHA256)
        for title in ("## Portable Agent Plugin", "## Agent integration files"):
            section = README.read_text(encoding="utf-8").split(title, 1)[1].split("\n## ", 1)[0]
            self.assertEqual(section.count("skills/gkmex-api-integration/SKILL.md"), 1)
```

Change the existing sorted skill-name expectation to:

```python
["gkmex-api-integration", "gkmex-crane-comparison", "gkmex-inventory"]
```

In the existing expected `portable_block`, immediately after the comparison line insert:

```markdown
- `skills/gkmex-api-integration/SKILL.md` — API and SDK integration skill
```

Create `tests/test_api_integration_example.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import test from "node:test";
import { GkmexClient, GkmexError } from "../packages/gkmex/src/client.js";

const skillPath = new URL("../skills/gkmex-api-integration/SKILL.md", import.meta.url);
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

function example() {
  assert.ok(existsSync(skillPath), "integration skill must exist");
  const text = readFileSync(skillPath, "utf8");
  const blocks = [...text.matchAll(/```js\n([\s\S]*?)\n```/g)];
  assert.equal(blocks.length, 1, "one runnable JavaScript example");
  const source = blocks[0][1];
  const importLine = 'import { GkmexClient } from "@gstcranes/gkmex";';
  assert.ok(source.startsWith(importLine));
  return new AsyncFunction("GkmexClient", "console", source.slice(importLine.length));
}

async function runExample(responses) {
  const requests = [];
  const lines = [];
  class FixtureClient extends GkmexClient {
    constructor() {
      super({ fetch: async (url, init) => {
        const position = requests.length;
        requests.push({ url: new URL(url), init });
        assert.ok(position < responses.length, "unexpected additional request");
        const { status = 200, body } = responses[position];
        return new Response(JSON.stringify(body), {
          status, headers: { "content-type": "application/json" },
        });
      } });
    }
  }
  await example()(FixtureClient, { log: value => lines.push(value) });
  return { requests, lines };
}

const crane = id => ({ id, brand: "Example", model: "Fixture", price_eur: null, url: `https://gkmex.com/en/crane/${id}` });
const page = (data, next_cursor, offset = 0) => ({ updated_at: "2026-09-02", count: data.length, total: 3, limit: 100, offset, next_cursor, data });

test("example follows opaque cursors with stable filters and no offset", async () => {
  const { requests, lines } = await runExample([
    { body: page([crane("a"), crane("b")], "opaque token+/=") },
    { body: page([crane("c")], null, 2) },
  ]);
  assert.deepEqual(lines, ["a", "b", "c"].map(id => crane(id).url));
  assert.equal(requests.length, 2);
  for (const { url, init } of requests) {
    assert.equal(url.origin, "https://gkmex.com");
    assert.equal(url.pathname, "/api/v1/cranes");
    assert.equal(url.searchParams.get("type"), "mobile");
    assert.equal(url.searchParams.get("limit"), "100");
    assert.equal(url.searchParams.has("offset"), false);
    assert.equal(new Headers(init.headers).has("authorization"), false);
  }
  assert.equal(requests[0].url.searchParams.has("cursor"), false);
  assert.equal(requests[1].url.searchParams.get("cursor"), "opaque token+/=");
});

test("example accepts empty200 without inventing records", async () => {
  const { requests, lines } = await runExample([{ body: { ...page([], null), total: 0 } }]);
  assert.equal(requests.length, 1);
  assert.deepEqual(lines, []);
});

test("example propagates an HTTP failure instead of reporting empty success", async () => {
  await assert.rejects(runExample([{ status: 400, body: { error: "invalid filter" } }]),
    error => error instanceof GkmexError && error.status === 400);
});
```

Run `python3 -m unittest tests.test_agent_plugin -v` and `node --test tests/test_api_integration_example.mjs`. Expected RED: missing skill, third discovery and README entry; Node assertions say integration skill must exist. Do not accept syntax/setup errors as RED.

- [ ] **3. Write the minimal skill using the observed failures.** Create exactly this text (outer fence here is documentation, not part of the skill):

````markdown
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
````

- [ ] **4. Add README discovery only.** Immediately after comparison in both discovery lists add `- \`skills/gkmex-api-integration/SKILL.md\` — API and SDK integration skill`. Do not edit unrelated MCP/SDK prose in this release.

- [ ] **5. GREEN and validation.** Run focused root and example tests, then full suites:

```bash
python3 -m unittest discover -s tests -v
node --test tests/test_api_integration_example.mjs
```

From `packages/gkmex-python`: `env PYTHONPATH=src /opt/homebrew/bin/python3.12 -m unittest discover -s tests -v`.
From `packages/gkmex`: `npm test`.

Expected root12, example3, Python SDK35, Node130. Run:

```bash
python3 /Users/gokmentanacar/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/gkmex-api-integration
uvx --from 'git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref' skills-ref validate skills/gkmex-api-integration
git diff --check
wc -w skills/gkmex-api-integration/SKILL.md
shasum -a 256 skills/gkmex-inventory/SKILL.md skills/gkmex-crane-comparison/SKILL.md skills/gkmex-api-integration/SKILL.md
```

The two old pins must remain exact. Keep the guide below500 words; do not pad for scoring. Run the fenced example once against live inventory with the official source import locally substituted; it must return the same mobile URL set as a separate read-only REST request.

- [ ] **6. Commit and report.** Stage only the four implementation files and commit `feat: add Gkmex API integration skill`. Controller owns design/plan/evidence commits. Report actual RED/GREEN, counts, canonical bytes/hash and self-review concerns. No push, package publication or site changes by implementer.

## Task 2: Behavioral GREEN, independent review and discovery (controller)

- [ ] Repeat the three baseline application tasks in fresh agents with the exact skill supplied. Pagination must preserve filters and not combine cursor+offset; preview must distinguish HTTP failure from empty200 and preserve null/POA; Python3.9 fallback must use compatible REST with finite timeout and truthful User-Agent. Inspect actual code/results. Fix only demonstrated gaps and repeat affected tests.
- [ ] Run spec review, then quality review of the entire base-to-HEAD diff. Resolve substantive findings with the implementer and re-review. Preserve exactly four implementation paths plus approved design/plan.
- [ ] Push `feat/gkmex-api-integration-skill`, create PR with real test counts, inspect checks/state/head SHA, merge reviewed head only. Fetch main and verify merge/source bytes. Do not switch the primary checkout.
- [ ] Read skills.sh search `https://skills.sh/api/search?q=gkmex-api-integration`, detail `https://www.skills.sh/gkmex75/gkmex-developer-resources/gkmex-api-integration`, badge `https://skills.sh/b/gkmex75/gkmex-developer-resources`. Match exact search ID (search count is fuzzy), full rendered body including Show more and badge3. If required, perform at most one temp functional installation with `npx -y skills@1.5.23 add gkmex75/gkmex-developer-resources --skill gkmex-api-integration --agent codex --copy -y`; never a global/project install or repeated telemetry action. Verify installed bytes against merged source.
- [ ] Once indexing is verified, create the separate site plan using actual immutable merge SHA and digest. The approved site/measurement design is already fixed; no scope expansion. No Ora request before the site phase passes.

## Self-review

The plan matches the approved design: one guide, real decision-changing error rules, no runtime changes, real example execution plus independent behavioral tests, exact preservation of two older skills and staged source/discovery/site/measurement gates. No future source SHA is fabricated. Node test controls only HTTP while exercising existing SDK and actual fenced code. BaselineB is the observed defect; A/C are regression controls rather than claimed failures.
