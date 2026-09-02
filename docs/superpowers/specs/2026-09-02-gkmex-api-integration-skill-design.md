# Gkmex API Integration Skill Design

Date: 2026-09-02. Status: scope approved by the user's `onay` after the explicit integration-skill, publication, site-mirror and single-measurement proposal.

## Outcome and boundaries

Publish `gkmex-api-integration` as the third useful official skill. It helps developers implement consumers of the existing public inventory, distinct from inventory search and crane-shortlist comparison. The user approved one compact guide covering connection, pagination and errors, followed by publication and one Ora quality measurement after all three skills are verified.

Use one self-contained `skills/gkmex-api-integration/SKILL.md`. No scripts, assets, UI metadata, SDK releases, new endpoints, MCP changes, credentials, WAF changes, dependency additions or modifications to existing skill bytes. The already-approved portable and Codex manifests discover `skills/`; leave them untouched.

Alternatives considered: expanding SDK behavior would unnecessarily alter runtime scope; only adding another README page would not supply discoverable task-specific skill guidance. The chosen portable reference/technique skill uses the existing interfaces and publishing pipeline.

## Verified integration contract

- Developer-resources base `534cbdaa937adad1d6cea678ea2f9ebc155ffc36`; stale primary main is not used.
- JavaScript: `@gstcranes/gkmex`, Node20+, `GkmexClient().listCranes` / `getCrane`.
- Python: `gkmex`, Python3.10+, `GkmexClient().list_cranes` / `get_crane`.
- Both SDK list, second-page and detail calls passed live smoke checks using source identical to origin/main.
- REST public GET routes: `/api/health`, `/api/v1/cranes`, `/api/v1/cranes/{id}`. Zero-auth and read-only.
- Collection keys: `brand`, `type` (`mobile`/`crawler`), `limit`1..100, `offset`>=0 or opaque `cursor`. Cursor and offset together return400; live check reproduced it.
- `count` is current-page length; `total` is matching total. Continue using `next_cursor` while preserving filters. No-match200 contains empty `data`.
- Details use a returned public ID. Preserve `url`, `price_eur` and nullable fields; null price is POA, not zero.
- Python SDK sets its own truthful user-agent. Direct stdlib `Python-urllib` can be rejected by Cloudflare1010; a truthful app identifier works. Do not modify site protection or invent authentication to solve this.
- Existing MCP actually has three tools and two resources. Do not propagate the earlier stale two-tool assertion or change runtime behavior.

## Guide design

The name is `gkmex-api-integration`; the description triggers on application integration/troubleshooting through REST or official SDKs, not general crane buying.

The body has a compact interface table, one complete runnable JavaScript cursor example, documented REST fallback, and a short data/error contract. It distinguishes empty200, unknown price, malformed/non-JSON responses, and failed HTTP/network calls. Transient retries must be bounded if added; there is no fixed retry framework. Verification covers pagination, empty data, POA and failure before claiming a consumer works.

## Behavioral evidence and tests

Before writing SKILL.md, independent agents ran three offline application scenarios:

1. JavaScript exporter resuming at offset4 then using cursors: PASS. It used offset only on page1 and opaque cursor subsequently.
2. Python preview under a request to use numeric placeholders and suppress errors: RED. Actual baseline used `except GkmexError: return empty_preview()` and `"price_eur": price if isinstance(price, int) and not isinstance(price, bool) else 0`. It described failures as the same empty shape and unknown price as0. This hides API outages and changes public price meaning.
3. Python3.9 fallback without compatible SDK: primary requirements PASS. It selected stdlib REST with a truthful user-agent, timeout and no unbounded retries. Its exception formatting has a separate generic `.reason`/TimeoutError weakness; do not turn that into a universal API-specific rule.

Repeat the same scenarios with the final skill. Require compatible interfaces, opaque pagination, truthful data and distinct failure state. Record actual outputs, not only a grader opinion.

Repository tests preserve both existing skill SHA256 pins, ensure third-skill discovery/frontmatter and README coverage, and execute the actual fenced JavaScript example through the real SDK with controlled HTTP responses. Example tests cover multiple pages (including count/total differences), empty200 and HTTP400 propagation. No production test-only methods or package changes.

Baseline suites: root11, Python SDK35, Node130. Validate the skill with bundled quick_validate and pinned official skills-ref. Independently review specification compliance, then code quality before merging.

## Ordered release

1. Developer-resources implementation, behavioral verification, review and PR merge.
2. Verify immutable raw source bytes/digest and skills.sh exact search, full detail body and badge3. Prefer read-only discovery; at most one temporary functional install if indexing requires it, never repeated/synthetic installs or duplicate issues.
3. Only after immutable source and discovery are verified, write a separate site-phase plan with the actual merge SHA, length and digest. Add one entry to the existing canonical collection, exact skill copy/index/provenance and direct link in the same six Markdown documents. Preserve two old skills/records/links and all other outputs. New clean site feature and merged release worktrees; primary dirty checkout remains untouched.
4. Deploy from the clean merged site tree and verify all three skills, index/catalog, six documents, unchanged inventory and MCP runtime.
5. Run exactly one targeted Ora `skills-sh-quality` measurement and report actual score/status and `storedScanUpdated`. Do not claim the stored site score changed when the response says it did not.

## Completion and stop conditions

Complete after third skill is merged, indexed, mirrored, live-verified and the one permitted measurement is reported. Stop and diagnose substantive test, source-integrity or live regression failures. An external index delay is not permission to repeat installs or spend the measurement prematurely. No other site/domain changes and no general memory/config edits.

Self-review: scope is one skill with two ordered release phases; canonical site source pin is intentionally resolved only after the first merge. All three existing runtime tools are preserved. No unverified package/API method is introduced. The design reflects the user's approved scope; it does not request another scope expansion.
