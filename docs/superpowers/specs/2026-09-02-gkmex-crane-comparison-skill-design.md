# Gkmex Crane Comparison Skill Design

**Date:** 2026-09-02
**Status:** Approved for implementation planning

## Outcome

Publish `gkmex-crane-comparison` as the second official Agent Skill in
`gkmex75/gkmex-developer-resources`. The skill must help an agent compare two to
five currently published Gkmex crane listings without inventing facts, treating
POA as zero, or declaring a universal winner without user-supplied priorities.

This is the first of two sequential releases intended to raise the official
skills.sh inventory from one skill to three. The third skill,
`gkmex-api-integration`, receives its own design and implementation cycle only
after this release is merged, indexed, mirrored on gkmex.com, and verified.

## Release Boundary

The release has two ordered repository phases:

1. Add and publish the portable skill from `gkmex-developer-resources`.
2. Mirror the merged, immutable skill on `gkmex-site`, add it to the first-party
   Agent Skills index, publish its direct skills.sh link, and deploy the site.

The stale local `main` checkout of `gkmex-developer-resources` is not used or
modified. Work starts in an isolated worktree based on current `origin/main`.
The dirty primary `gkmex-site` checkout is likewise left untouched; its release
uses a separate clean worktree based on the then-current `origin/main`.

## Portable Skill Structure

Create one self-contained file:

`skills/gkmex-crane-comparison/SKILL.md`

No scripts, references, assets, authentication, credentials, or write tools are
needed. The skill remains concise enough to load as one document. Its required
frontmatter is:

```yaml
---
name: gkmex-crane-comparison
description: Use when comparing two to five currently published Gkmex cranes, evaluating a shortlist against user-supplied priorities, or deciding which listing facts need commercial confirmation.
---
```

The description is a discovery trigger, not a summary of the workflow. The
directory and `name` are identical and comply with the Agent Skills naming
rules.

The existing `skills/gkmex-inventory/SKILL.md` must remain byte-for-byte
unchanged. The portable and Codex plugin manifests already discover the whole
`skills/` directory, so this release does not modify plugin runtime or MCP
configuration.

## Comparison Behavior

The skill operates only on a shortlist of two to five currently published
Gkmex listings.

### Retrieval

- When the user supplies public listing IDs, prefer the MCP `compare_cranes`
  tool.
- When the user supplies requirements but no IDs, use `list_cranes` to form a
  shortlist, then compare two to five returned IDs.
- Use `get_crane` when a comparison result needs one listing's full published
  record.
- If MCP is unavailable, use the equivalent public, zero-auth, read-only REST,
  npm, Python, or CLI surface available in the environment.
- Never invent IDs or compare stale examples as though they were current
  inventory.

### Facts and Output

Produce a compact comparison table using only published values that are useful
to the question. Candidate fields are brand/model, year, crane type, capacity,
`price_eur`, hours, kilometers, location, and public listing URL.

- Render `price_eur: null` as `POA`, never as zero or the cheapest option.
- Render absent facts as unknown; do not infer or convert missing values.
- Cite the official public listing URL for every crane.
- State which requested decision criteria cannot be evaluated because a field
  is missing.

### Recommendation Boundary

When the user supplies priorities, make a conditional recommendation using
only those priorities and show the reason. Ties and missing data remain
explicit. When the user gives no priorities, provide the factual table and ask
which criteria matter; do not label one crane as the universal best.

Published availability, specifications, and prices are provisional. The skill
must direct quotations, inspections, transport, financing, technical fit, and
final availability confirmation to Gkmex. It must not claim a crane is reserved,
finally available, or conclusively suitable for a lift.

## Developer-Resources Discovery and Tests

Update `README.md` so both portable skills are individually discoverable while
preserving the existing plugin entry points. Extend the root contract tests to
assert:

- the new directory and file exist;
- frontmatter name and description are exact;
- the existing inventory skill digest remains unchanged;
- the README names both skill paths;
- the new skill contains the public read-only interfaces and commercial
  boundaries, without credentials or write actions.

Validate the new directory with the official `skills-ref` validator or the
bundled quick validator when available. The full existing root Python, Python
SDK, and Node SDK/CLI suites remain green.

## Behavioral TDD

Skill creation follows RED, GREEN, and REFACTOR rather than prose-only review.
Use independent agents because the selected writing-skills workflow explicitly
requires behavioral pressure tests.

### RED Baselines

Before creating the skill, give agents the raw Gkmex interface facts and stable
fixture records but not the proposed skill. Record their actual outputs for:

1. A time-pressured request to choose the “best” of three cranes without any
   decision criteria.
2. A criteria-driven request where one crane is POA and another lacks a field
   required by the user's priority.
3. A comparison request where MCP is unavailable but REST data is supplied.

A useful RED failure is observable: selecting a universal winner, treating POA
as zero, hiding missing data, omitting official URLs, inventing a value, or
failing to use an available read-only fallback.

### GREEN and REFACTOR

Run the same scenarios with the new skill explicitly supplied. Passing output
must respect the two-to-five boundary, facts, POA handling, URLs, conditional
recommendation rule, fallback, and commercial caveat. Revise only instructions
needed to close failures observed in RED/GREEN; do not accumulate hypothetical
rules. Re-run until all three scenarios comply.

## skills.sh Publication

After the developer-resources PR is reviewed and merged:

- verify the raw merged `SKILL.md` content and digest;
- verify skills.sh repository/search discovery reports two skills and exposes a
  canonical page for `gkmex-crane-comparison`;
- verify the page renders the intended skill body;
- do not create duplicate issues or synthetic/repeated installs.

Read-only discovery is preferred. If skills.sh indexing demonstrably requires a
CLI discovery/install action, perform one clean installation in a temporary
directory as the release's functional install test and do not repeat it.

## First-Party gkmex.com Identity

The site phase starts only after the developer-resources merge SHA and skill
bytes are fixed. Copy the exact skill into the `gkmex-site` canonical `skills/`
tree and pin its byte length, SHA-256 digest, and immutable GitHub source URL.

Generalize the site's single-skill generator input into a small declarative
collection immediately used by both `gkmex-inventory` and
`gkmex-crane-comparison`. The generator must:

- validate each canonical skill's length and SHA-256;
- copy each exact byte stream to
  `/.well-known/agent-skills/<name>/SKILL.md`;
- emit one discovery 0.2.0 index record per skill with its description, URL,
  and digest;
- publish the exact comparison skill skills.sh URL in `index.md`, `llms.txt`,
  `/.well-known/llms.txt`, `llms-full.txt`, `agents.md`, and `developers.md`;
- preserve the existing inventory skill bytes, record, link, MCP behavior, and
  all unrelated generated outputs.

Site tests build in a temporary output tree and assert both exact copies,
digests, index records, direct skills.sh links, and the absence of unexpected
scope. Production acceptance verifies the two live skill files, index, agent
Markdown documents, and MCP `tools/list` before release completion.

## Measurement and Stop Conditions

This release aims to move the official skills.sh count from one to two. It does
not call Ora because Ora's published quality threshold is three or more skills;
a two-skill scan would spend the one targeted measurement without a plausible
score change.

Stop and diagnose before continuing when:

- a behavioral test fails after the skill is loaded;
- existing skill bytes or plugin/MCP contracts change unexpectedly;
- skills.sh does not expose the merged comparison skill;
- the gkmex.com skill copy or digest differs from the merged source;
- a production Agent Skills or MCP regression appears.

Do not retry installs or external measurements to mask a failed release. Once
the comparison release passes every gate, begin a separate design cycle for
`gkmex-api-integration`. Only after the third official skill is live will one
targeted `skills-sh-quality` Ora measurement be permitted.

## Explicit Non-Goals

- No crane suitability calculator or lift engineering advice.
- No new API, MCP tool, SDK method, CLI command, authentication, or write path.
- No edits to the existing inventory skill.
- No plugin manifest redesign or unrelated package release.
- No Ora scan during the two-skill intermediate state.

## Acceptance Criteria

The release is complete when all of the following are true:

- behavioral RED failures were observed and the same scenarios pass with the
  skill;
- the new skill validates against the Agent Skills format;
- all developer-resources test suites pass and the change is merged;
- skills.sh exposes exactly the intended comparison skill and reports two skills
  for the official repository/owner;
- gkmex.com serves the exact merged skill bytes and a correct digest/index
  record;
- canonical Gkmex agent documents link directly to the comparison skill page;
- live MCP read-only behavior remains intact;
- no Ora request was sent.
