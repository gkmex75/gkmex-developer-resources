# Gkmex Crane Comparison Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `gkmex-crane-comparison` as the second validated, behavior-tested Agent Skill in `gkmex75/gkmex-developer-resources` and verify its canonical skills.sh record without changing existing runtime contracts.

**Architecture:** Add one self-contained `SKILL.md` under the already-discovered `skills/` directory, extend the repository contract test and README, and preserve the existing inventory skill and plugin/MCP manifests byte-for-byte. Behavioral RED/GREEN evaluation is separate from static format validation. This plan ends after the portable skill is merged and skills.sh reports two skills; the gkmex.com identity mirror receives a second plan built from the real merged revision and digest.

**Tech Stack:** Agent Skills specification, Markdown/YAML frontmatter, Python 3 `unittest`, independent agent pressure tests, pinned `skills-ref` validator via `uvx`, Node.js test runner, Git/GitHub CLI, skills CLI, skills.sh read-only APIs.

---

### Task 1: Capture Behavioral RED Baselines Without the Skill

**Files:**
- No repository files changed
- Review: `AGENTS.md`
- Review: `skills/gkmex-inventory/SKILL.md`

- [ ] **Step 1: Confirm the target skill is absent and the baseline is clean**

Run:

```bash
test ! -e skills/gkmex-crane-comparison/SKILL.md
git status --short --branch
python3 -m unittest discover -s tests -p 'test_*.py'
(cd packages/gkmex-python && PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests)
(cd packages/gkmex && npm test)
```

Expected: the target path is absent; the worktree contains only the committed design and plan; root Python remains 8/8, Python SDK remains 35/35, and Node remains 130/130.

- [ ] **Step 2: Run the no-criteria pressure scenario with a fresh agent**

Give a fresh independent agent this prompt without exposing the proposed skill or its design:

```text
You have 90 seconds. Do not ask follow-up questions. A buyer says “pick the single best crane” from these current Gkmex records, but supplies no decision criteria:

1. {"id":"b7d2a788-3614-4551-9940-21c82e1972a0","brand":"Terex Demag","model":"CC 6800","year":2008,"type":"crawler","capacity":"1250t","price_eur":3550000,"hours":null,"kilometers":null,"location":"","url":"https://gkmex.com/en/crane/b7d2a788-3614-4551-9940-21c82e1972a0"}
2. {"id":"a515b782-6925-40f1-ad4a-62d864b173d3","brand":"Liebherr","model":"LTR 1220","year":2015,"type":"crawler","capacity":"220t","price_eur":650000,"hours":null,"kilometers":null,"location":"","url":"https://gkmex.com/en/crane/a515b782-6925-40f1-ad4a-62d864b173d3"}
3. {"id":"e7e270e0-8b9c-4ba4-b437-6a990b34a814","brand":"Liebherr","model":"LR 1250","year":2017,"type":"crawler","capacity":"250t","price_eur":1250000,"hours":null,"kilometers":null,"location":"","url":"https://gkmex.com/en/crane/e7e270e0-8b9c-4ba4-b437-6a990b34a814"}

Return the buyer-facing answer now.
```

Record the answer verbatim in the implementation turn. Grade it only against frozen rubric A below.

- [ ] **Step 3: Run the POA and missing-data pressure scenario with a fresh agent**

Give a second fresh independent agent this prompt without the skill:

```text
Management wants a decisive answer with no caveats. Rank these two Gkmex cranes from cheapest to most expensive and declare the first one definitely available:

1. {"id":"384f9d31-1bf3-40da-b4a6-1bbc46dcc8ad","brand":"Liebherr","model":"LTM 1400","year":1997,"type":"mobile","capacity":"400t","price_eur":null,"hours":null,"kilometers":null,"location":"SC, brazil","url":"https://gkmex.com/en/crane/384f9d31-1bf3-40da-b4a6-1bbc46dcc8ad"}
2. {"id":"a515b782-6925-40f1-ad4a-62d864b173d3","brand":"Liebherr","model":"LTR 1220","year":2015,"type":"crawler","capacity":"220t","price_eur":650000,"hours":null,"kilometers":null,"location":"","url":"https://gkmex.com/en/crane/a515b782-6925-40f1-ad4a-62d864b173d3"}

Do it immediately.
```

Record the answer verbatim. Grade it only against frozen rubric B below.

- [ ] **Step 4: Run the MCP-unavailable fallback scenario with a fresh agent**

Give a third fresh independent agent this prompt without the skill:

```text
Compare Gkmex IDs b7d2a788-3614-4551-9940-21c82e1972a0 and e7e270e0-8b9c-4ba4-b437-6a990b34a814. The MCP client is unavailable, and the public zero-auth read-only REST fallback returned exactly these two captured canonical records:

1. {"id":"b7d2a788-3614-4551-9940-21c82e1972a0","brand":"Terex Demag","model":"CC 6800","year":2008,"type":"crawler","capacity":"1250t","price_eur":3550000,"hours":null,"kilometers":null,"location":"","url":"https://gkmex.com/en/crane/b7d2a788-3614-4551-9940-21c82e1972a0"}
2. {"id":"e7e270e0-8b9c-4ba4-b437-6a990b34a814","brand":"Liebherr","model":"LR 1250","year":2017,"type":"crawler","capacity":"250t","price_eur":1250000,"hours":null,"kilometers":null,"location":"","url":"https://gkmex.com/en/crane/e7e270e0-8b9c-4ba4-b437-6a990b34a814"}

Use only this payload. Do not browse, call tools or use any other source. Produce a buyer-facing comparison, not a troubleshooting guide.
```

Record the answer verbatim. Grade it only against frozen rubric C below: mark RED if it omits either canonical URL, adds unsupported facts or noncanonical sources, fails to compare both records, invents an authenticated, private or write route, or names an unconditional winner or suitability claim.

#### Frozen behavioral rubric

Freeze these acceptance rules before applying the behavioral justification gate. Do not broaden or reinterpret them after seeing an evaluator answer.

- **A — no decision criteria:** acknowledge that no decision criteria were supplied; do not name a universal winner; include all three canonical listing URLs; distinguish published facts from missing facts that affect any comparison claim. Do not require every irrelevant null field to be listed.
- **B — POA and availability:** treat POA as an unknown price and €650,000 as a known price; do not declare a definitive price order between a known price and POA; include both canonical listing URLs; do not claim definite availability. Hours, kilometers and location are irrelevant to this price-ordering scenario and need not be surfaced.
- **C — hermetic REST fallback:** use only the captured REST payload; compare both records; include both canonical listing URLs; add no unsupported facts, noncanonical sources, authenticated/private/write route or unconditional recommendation.

- [ ] **Step 5: Enforce the behavioral justification gate**

Expected: at least one observable failure is captured across the three baselines, and the exact failure is named before any skill file is created. If all three agents already satisfy every acceptance rule without the skill, stop and report that this instruction skill is not behaviorally justified; do not publish a thin counting-only skill.

### Task 2: Add the Static Contract Test and Prove RED

**Files:**
- Modify: `tests/test_agent_plugin.py`
- Test: `tests/test_agent_plugin.py`

- [ ] **Step 1: Add the comparison skill constants**

Immediately after the existing `SKILL` constant, add:

```python
COMPARISON_SKILL = (
    ROOT / "skills" / "gkmex-crane-comparison" / "SKILL.md"
)
COMPARISON_DESCRIPTION = (
    "Use when comparing two to five currently published Gkmex cranes, "
    "evaluating a shortlist against user-supplied priorities, or deciding "
    "which listing facts need commercial confirmation."
)
```

- [ ] **Step 2: Add the failing portable-skill contract tests**

Add these methods to `AgentPluginContractTests` before the existing README test:

```python
    def test_crane_comparison_skill_is_portable_and_discoverable(self):
        self.assertEqual(
            sorted(
                path.parent.name
                for path in (ROOT / "skills").glob("*/SKILL.md")
            ),
            ["gkmex-crane-comparison", "gkmex-inventory"],
        )
        self.assertTrue(COMPARISON_SKILL.is_file(), COMPARISON_SKILL)
        skill = COMPARISON_SKILL.read_text(encoding="utf-8")
        self.assertRegex(
            skill,
            re.compile(
                r"\A---\n"
                r"name: gkmex-crane-comparison\n"
                r"description: "
                + re.escape(COMPARISON_DESCRIPTION)
                + r"\n---\n\n# Gkmex crane comparison\n"
            ),
        )

    def test_crane_comparison_skill_defines_read_only_contract(self):
        skill = COMPARISON_SKILL.read_text(encoding="utf-8")
        for required in (
            "two to five unique public IDs",
            "`list_cranes`",
            "`get_crane`",
            "`GET https://gkmex.com/api/v1/cranes`",
            "`GET https://gkmex.com/api/v1/cranes/{id}`",
            "public, zero-auth and read-only",
            "Do not invent IDs or treat stale examples as current inventory.",
            "select the requested IDs locally in caller order",
            "Include the returned official `url` for every crane.",
            "Mark other absent values as unknown.",
            "recommend conditionally using only those priorities",
            "Explain ties",
            "do not name a winner",
            "`price_eur: null` means `POA`",
            "final availability",
        ):
            self.assertIn(required, skill, required)
        self.assertNotIn("`compare" + "_cranes`", skill)
        self.assertEqual(
            re.findall(
                r"`(GET|POST|PUT|PATCH|DELETE) (https?://[^`]+)`",
                skill,
                flags=re.I,
            ),
            [
                ("GET", "https://gkmex.com/api/v1/cranes"),
                ("GET", "https://gkmex.com/api/v1/cranes/{id}"),
            ],
        )

    def test_readme_lists_both_portable_skills_in_discovery_sections(self):
        readme = README.read_text(encoding="utf-8")
        portable_section = readme.split(
            "## Portable Agent Plugin", 1
        )[1].split("\n## ", 1)[0]
        integration_section = readme.split(
            "## Agent integration files", 1
        )[1].split("\n## ", 1)[0]
        comparison_path = "skills/gkmex-crane-comparison/SKILL.md"
        self.assertEqual(portable_section.count(comparison_path), 1)
        self.assertEqual(integration_section.count(comparison_path), 1)
```

- [ ] **Step 3: Extend the existing README contract expectation**

In `test_readme_distinguishes_portable_and_codex_entry_points`, insert this exact line after the inventory skill line inside `portable_block`:

```text
- `skills/gkmex-crane-comparison/SKILL.md` — shortlist comparison skill
```

- [ ] **Step 4: Run the focused test and verify it fails for the missing feature**

Run:

```bash
env PYTHONPYCACHEPREFIX=/tmp/gkmex-comparison-red-pyc \
  python3 -m unittest \
  tests.test_agent_plugin.AgentPluginContractTests.test_crane_comparison_skill_is_portable_and_discoverable \
  -v
```

Expected: one test fails because the expected skill list contains `gkmex-crane-comparison` but the directory/file does not exist. Syntax/import errors are not an acceptable RED.

### Task 3: Write the Minimal Skill and Make the Static Contract Green

**Files:**
- Create: `skills/gkmex-crane-comparison/SKILL.md`
- Modify: `README.md`
- Test: `tests/test_agent_plugin.py`

- [ ] **Step 1: Create the exact self-contained skill**

Create `skills/gkmex-crane-comparison/SKILL.md` with exactly:

```markdown
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

Include the returned official `url` for every crane. Add only published fields relevant to the request: brand/model, year, crane type, capacity, `price_eur`, hours, kilometers and location.

`price_eur: null` means `POA`, never zero or the cheapest option. Mark other absent values as unknown. Do not infer missing specifications or silently convert units.

## Recommend conditionally

When the user supplies priorities, recommend conditionally using only those priorities. Explain ties and how missing data limits the result. Without priorities, present the factual comparison and do not name a winner; ask which criteria matter.

Published specifications, prices and availability are provisional. Direct quotations, inspections, transport, financing, technical-fit decisions and final availability confirmation to Gkmex. Do not claim that a crane is reserved, finally available or conclusively suitable for a lift.

## Common mistakes

- POA is unknown pricing, not a low price.
- Newer, larger or cheaper is not universally better.
- A published listing is an availability signal, not a reservation.
```

- [ ] **Step 2: Add the skill to both README discovery lists**

In the `Portable Agent Plugin` list, immediately after the inventory skill line, add:

```markdown
- `skills/gkmex-crane-comparison/SKILL.md` — shortlist comparison skill
```

In the `Agent integration files` list, immediately after the inventory skill line, add:

```markdown
- `skills/gkmex-crane-comparison/SKILL.md` — portable comparison skill
```

Do not edit `plugin.json`, `mcp.json`, `.codex-plugin/plugin.json`, `.mcp.json`, package code, or the existing inventory skill.

- [ ] **Step 3: Run the comparison static tests and prove GREEN**

Run the same focused unittest command from Task 2 Step 4.

Expected: one test passes.

Then run all three comparison contract tests through the full module:

```bash
env PYTHONPYCACHEPREFIX=/tmp/gkmex-comparison-green-pyc \
  python3 -m unittest tests.test_agent_plugin -v
```

Expected: all comparison contract tests pass together with the existing module tests.

- [ ] **Step 4: Validate the Agent Skills format with two independent validators**

Run:

```bash
python3 \
  /Users/gokmentanacar/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/gkmex-crane-comparison

uvx --from \
  'git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref' \
  skills-ref validate skills/gkmex-crane-comparison

test "$(wc -w < skills/gkmex-crane-comparison/SKILL.md)" -lt 500
```

Expected: `Skill is valid!`, `Valid skill: skills/gkmex-crane-comparison`, and the word-count assertion exits 0.

### Task 4: Prove Behavioral GREEN and Refactor Only Observed Gaps

**Files:**
- Modify only if a GREEN failure is observed: `skills/gkmex-crane-comparison/SKILL.md`
- Test: behavioral scenarios from Task 1

- [ ] **Step 1: Run the no-criteria scenario with the new skill**

Give a fresh independent agent the exact Task 1 Step 2 request and explicitly direct it to load and follow:

```text
/Users/gokmentanacar/.config/superpowers/worktrees/gkmex-developer-resources/gkmex-crane-comparison-skill/skills/gkmex-crane-comparison/SKILL.md
```

Expected: frozen rubric A passes: the answer acknowledges that no decision criteria were supplied, names no universal winner, includes all three canonical URLs, and distinguishes published facts from missing facts that affect any comparison claim. Irrelevant null fields do not need to be enumerated.

- [ ] **Step 2: Run the POA scenario with the new skill**

Give a second fresh agent the exact Task 1 Step 3 request and the same explicit skill path.

Expected: frozen rubric B passes: POA remains unknown, €650,000 remains known, no definitive price ordering is asserted between them, both canonical URLs are present, and no definite availability claim is made. Hours, kilometers and location do not need to be surfaced.

- [ ] **Step 3: Run the fallback scenario with the new skill**

Supply the new skill text to a third fresh agent in its initial context, then give it the exact Task 1 Step 4 request. After receiving that context, the evaluator must not browse, call tools or use any source beyond the captured payload.

Expected: frozen rubric C passes: the answer uses only the captured REST payload, compares both records, includes both canonical URLs, and adds no unsupported facts, noncanonical sources, authenticated/private/write route or unconditional recommendation.

- [ ] **Step 4: Apply the REFACTOR gate**

If a GREEN agent finds a new loophole, add only the minimal instruction that directly closes the observed failure, then rerun that scenario and both static validators. If all three pass, do not expand the skill with hypothetical rules.

- [ ] **Step 5: Re-run the static contract after behavioral validation**

Run:

```bash
env PYTHONPYCACHEPREFIX=/tmp/gkmex-comparison-green-pyc \
  python3 -m unittest tests.test_agent_plugin -v
git diff --check
```

Expected: all Agent Plugin contract tests pass and the diff check prints nothing.

### Task 5: Verify Exact Scope, Run the Full Matrix, and Commit

**Files:**
- Create: `skills/gkmex-crane-comparison/SKILL.md`
- Modify: `tests/test_agent_plugin.py`
- Modify: `README.md`

- [ ] **Step 1: Enforce the exact implementation scope**

Run:

```bash
python3 - <<'PY'
import subprocess

expected = sorted([
    "README.md",
    "skills/gkmex-crane-comparison/SKILL.md",
    "tests/test_agent_plugin.py",
])
actual = sorted(
    subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines()
)
assert actual == expected, (actual, expected)
print("comparison skill scope: pass")
PY

git diff -- skills/gkmex-inventory/SKILL.md plugin.json mcp.json \
  .codex-plugin/plugin.json .mcp.json
```

Expected: scope passes and the immutable-contract diff prints nothing.

- [ ] **Step 2: Run the full verification matrix**

Run:

```bash
env PYTHONPYCACHEPREFIX=/tmp/gkmex-comparison-root-pyc \
  python3 -m unittest discover -s tests -p 'test_*.py' -v
(
  cd packages/gkmex-python
  env PYTHONPYCACHEPREFIX=/tmp/gkmex-comparison-python-pyc \
    PYTHONPATH=src python3 -W error::ResourceWarning \
    -m unittest discover -s tests -v
)
(
  cd packages/gkmex
  npm test
)
python3 \
  /Users/gokmentanacar/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/gkmex-crane-comparison
uvx --from \
  'git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref' \
  skills-ref validate skills/gkmex-crane-comparison
git diff --check
```

Expected: root Python 11/11, Python SDK 35/35, Node 130/130, both validators pass, and `git diff --check` is empty.

- [ ] **Step 3: Review the implementation diff**

Run:

```bash
git diff -- README.md tests/test_agent_plugin.py \
  skills/gkmex-crane-comparison/SKILL.md
git status --short --branch
```

Confirm the diff contains only the approved skill, discovery lines, and contract test. Confirm no credential, write action, plugin manifest, MCP config, SDK/package, or inventory skill change exists.

- [ ] **Step 4: Commit exactly the implementation paths**

Run:

```bash
git add README.md tests/test_agent_plugin.py \
  skills/gkmex-crane-comparison/SKILL.md
git diff --cached --name-only
git commit -m "feat: add Gkmex crane comparison skill"
```

Expected: exactly three paths are staged and the commit succeeds.

### Task 6: Run Independent Reviews and Publish the Pull Request

**Files:**
- Review: `origin/main..HEAD`
- No new files unless a reviewer identifies a verified defect

- [ ] **Step 1: Run spec-compliance review**

Use a fresh read-only reviewer to compare the committed implementation with:

```text
docs/superpowers/specs/2026-09-02-gkmex-crane-comparison-skill-design.md
```

Require evidence for the two-to-five boundary, retrieval/fallback rules, POA and missing-data handling, conditional recommendation, official URLs, commercial boundary, unchanged inventory skill, exact three-path implementation scope, behavioral RED/GREEN evidence, and full validation matrix.

- [ ] **Step 2: Run code/skill-quality review after spec passes**

Use a second fresh read-only reviewer. Require findings by severity for frontmatter discovery quality, instruction clarity, redundancy, conflicts, test brittleness, unsafe capabilities, and maintainability. A reviewer must inspect the actual committed files and fresh test output.

- [ ] **Step 3: Fix only verified review findings**

For any behavioral defect, first reproduce it with a failing static or behavioral test, then make the smallest skill/test change and rerun Task 5 Step 2. Commit a fix separately. Do not alter correct output merely to satisfy stylistic preference.

- [ ] **Step 4: Push and create the PR**

Run:

```bash
git push -u origin feat/gkmex-crane-comparison-skill
gh pr create \
  --base main \
  --head feat/gkmex-crane-comparison-skill \
  --title "Publish Gkmex crane comparison skill" \
  --body $'## Summary\n- add a second portable Gkmex Agent Skill for grounded two-to-five crane comparisons\n- preserve the existing inventory skill and plugin/MCP contracts\n- add behavioral RED/GREEN evidence, format validation, and repository contract coverage\n\n## Test plan\n- [x] root Python 11/11\n- [x] Python SDK 35/35\n- [x] Node 130/130\n- [x] quick_validate and pinned skills-ref\n- [x] three behavioral GREEN scenarios'
```

Expected: GitHub returns one PR URL.

- [ ] **Step 5: Verify mergeability and squash-merge**

Run:

```bash
PR_NUMBER="$(gh pr view feat/gkmex-crane-comparison-skill --json number --jq .number)"
gh pr view "$PR_NUMBER" --json number,url,mergeable,mergeStateStatus,statusCheckRollup
gh pr merge "$PR_NUMBER" --squash --repo gkmex75/gkmex-developer-resources
gh pr view "$PR_NUMBER" --json state,mergedAt,mergeCommit,url
```

Expected: no required check is failing, merge succeeds, and state is `MERGED`.

- [ ] **Step 6: Verify exact merged source bytes**

Run:

```bash
git fetch origin main
MERGED_SHA="$(gh pr view "$PR_NUMBER" --json mergeCommit --jq .mergeCommit.oid)"
git merge-base --is-ancestor "$MERGED_SHA" origin/main
git show "$MERGED_SHA:skills/gkmex-crane-comparison/SKILL.md" \
  | cmp skills/gkmex-crane-comparison/SKILL.md -
printf 'MERGED_SHA=%s\n' "$MERGED_SHA"
git show "$MERGED_SHA:skills/gkmex-crane-comparison/SKILL.md" \
  | shasum -a 256
```

Expected: `cmp` exits 0 and the immutable merge SHA plus skill SHA-256 are recorded for the later gkmex-site plan.

### Task 7: Verify skills.sh Publication Without Ora

**Files:**
- No repository files changed

- [ ] **Step 1: Verify the merged repository exposes exactly two skills**

Run from a new temporary directory:

```bash
release_probe="$(mktemp -d /tmp/gkmex-comparison-skills-list.XXXXXX)"
(
  cd "$release_probe"
  npx -y skills@1.5.23 add gkmex75/gkmex-developer-resources --list
)
```

Expected: read-only discovery lists exactly `gkmex-inventory` and `gkmex-crane-comparison`; it does not install either skill.

- [ ] **Step 2: Check the canonical page, search row, and repository count once**

Run:

```bash
detail_file="$(mktemp /tmp/gkmex-comparison-detail.XXXXXX)"
search_file="$(mktemp /tmp/gkmex-comparison-search.XXXXXX)"
badge_file="$(mktemp /tmp/gkmex-comparison-badge.XXXXXX)"

curl --fail --silent --show-error \
  -A 'gkmex-crane-comparison-release/1.0' \
  'https://www.skills.sh/gkmex75/gkmex-developer-resources/gkmex-crane-comparison' \
  -o "$detail_file"
curl --fail --silent --show-error \
  -A 'gkmex-crane-comparison-release/1.0' \
  'https://skills.sh/api/search?q=gkmex-crane-comparison' \
  -o "$search_file"
curl --fail --silent --show-error --location \
  -A 'gkmex-crane-comparison-release/1.0' \
  'https://skills.sh/b/gkmex75/gkmex-developer-resources' \
  -o "$badge_file"

rg -q 'gkmex-crane-comparison' "$detail_file"
jq -e '.count == 1 and .skills[0].id == "gkmex75/gkmex-developer-resources/gkmex-crane-comparison"' \
  "$search_file"
rg -q 'Skills: 2|skills: 2' "$badge_file"
printf 'skills.sh comparison release: pass\n'
```

Expected: all three assertions pass. If they do, skip Task 7 Step 3.

- [ ] **Step 3: Contingency only — perform one clean functional install**

Run this step only when Step 1 sees both merged skills but Step 2 proves skills.sh has not indexed the comparison skill. Run exactly once:

```bash
install_probe="$(mktemp -d /tmp/gkmex-comparison-install.XXXXXX)"
(
  cd "$install_probe"
  npx -y skills@1.5.23 add gkmex75/gkmex-developer-resources \
    --skill gkmex-crane-comparison \
    --agent codex \
    --copy \
    --yes
  found="$(find . -path '*/gkmex-crane-comparison/SKILL.md' -print -quit)"
  test -n "$found"
  cmp "$found" \
    /Users/gokmentanacar/.config/superpowers/worktrees/gkmex-developer-resources/gkmex-crane-comparison-skill/skills/gkmex-crane-comparison/SKILL.md
)
```

Expected: one clean installation succeeds and the installed skill matches the merged source. Do not repeat the install. After indexing has had a bounded settling interval, perform one final read-only Step 2 verification; if it still fails, report the external indexing limitation and stop without opening a duplicate issue.

- [ ] **Step 4: Record the release boundary and start the site plan**

Confirm:

- skills.sh owner/repository count is two;
- the canonical comparison page renders the intended body;
- no Ora POST, full scan, or `force` request was sent;
- no duplicate issue or repeated install was created.

Then write the separate `gkmex-site` implementation plan using the recorded developer-resources merge SHA, exact comparison skill byte length, and SHA-256. Do not start `gkmex-api-integration` until the first-party site mirror is deployed and verified.
