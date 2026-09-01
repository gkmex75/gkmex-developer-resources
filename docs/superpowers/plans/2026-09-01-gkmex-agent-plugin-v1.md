# Gkmex Portable Agent Plugin v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the existing Gkmex inventory skill and public remote MCP server as a conformant Agent Plugins v1 package, make it explicit on gkmex.com discovery surfaces, and measure Ora.ai once through a quota-safe gate.

**Architecture:** Treat `gkmex75/gkmex-developer-resources` itself as the portable plugin root: root `plugin.json`, root `mcp.json`, and the existing `skills/gkmex-inventory/SKILL.md`. Release that repository first, then update the `gkmex-site` generator so the already-public repository is named and linked as the Gkmex portable Agent Plugin. Keep the existing `.codex-plugin/plugin.json` and `.mcp.json` unchanged because they are client-specific contracts.

**Tech Stack:** Agent Plugins 1.0.0 JSON Schemas, JSON, Python 3 `unittest`, Python `jsonschema[format-nongpl]==4.25.1`, generated static HTML/Markdown/JSON, Node.js test runner, Git/GitHub CLI, Cloudflare Pages/Wrangler, MCP Inspector, Ora.ai REST API.

---

## File Map

### `gkmex-developer-resources`

- Create `plugin.json`: closed portable Agent Plugins identity document.
- Create `mcp.json`: portable Streamable HTTP MCP configuration.
- Create `tests/test_agent_plugin.py`: exact offline package and zero-credential contract.
- Modify `README.md`: distinguish portable and Codex-specific plugin entry points.
- Preserve `.codex-plugin/plugin.json`, `.mcp.json`, and `skills/gkmex-inventory/SKILL.md` byte-for-byte.

### `gkmex-site`

- Modify `build_site.py`: generate explicit Agent Plugin discovery copy and one API catalog documentation entry.
- Modify `tests/test_build_site.py`: generated-output contract for the exact links, labels, ordering, and scope.
- Regenerate exactly:
  - `site/.well-known/api-catalog`
  - `site/.well-known/llms.txt`
  - `site/agents.md`
  - `site/developers.md`
  - `site/developers/index.html`
  - `site/developers/llms.txt`
  - `site/index.md`
  - `site/llms-full.txt`
  - `site/llms.txt`

---

### Task 1: Define the Portable Plugin Contract in RED

**Files:**
- Create: `tests/test_agent_plugin.py`

- [ ] **Step 1: Add the exact failing package contract**

Create `tests/test_agent_plugin.py`:

```python
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin.json"
MCP = ROOT / "mcp.json"
SKILL = ROOT / "skills" / "gkmex-inventory" / "SKILL.md"
README = ROOT / "README.md"


class AgentPluginTests(unittest.TestCase):
    def test_portable_manifest_is_the_exact_agent_plugins_v1_identity(self):
        self.assertTrue(PLUGIN.is_file(), f"missing portable manifest: {PLUGIN}")
        manifest = json.loads(PLUGIN.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest,
            {
                "$schema": (
                    "https://agent-plugins.org/schemas/1.0.0/"
                    "plugin.schema.json"
                ),
                "name": "gkmex-developer-resources",
                "version": "0.1.0",
                "description": (
                    "Portable public, zero-auth, read-only access to Gkmex "
                    "used-crane inventory through an Agent Skill and MCP server."
                ),
                "author": {
                    "name": "Gkmex Cranes",
                    "url": "https://gkmex.com",
                },
                "homepage": "https://gkmex.com/developers",
                "repository": (
                    "https://github.com/gkmex75/gkmex-developer-resources"
                ),
                "license": "MIT",
                "keywords": [
                    "gkmex",
                    "cranes",
                    "inventory",
                    "mcp",
                    "agent-skills",
                    "npm",
                    "pypi",
                ],
            },
        )

    def test_portable_mcp_config_is_one_public_streamable_http_server(self):
        self.assertTrue(MCP.is_file(), f"missing portable MCP config: {MCP}")
        config = json.loads(MCP.read_text(encoding="utf-8"))
        self.assertEqual(
            config,
            {
                "$schema": (
                    "https://agent-plugins.org/schemas/1.0.0/"
                    "mcp.schema.json"
                ),
                "mcpServers": {
                    "gkmex-inventory": {
                        "type": "streamable-http",
                        "url": "https://gkmex.com/mcp",
                    }
                },
            },
        )
        raw = MCP.read_text(encoding="utf-8")
        self.assertNotRegex(
            raw,
            re.compile(
                r'"(?:headers|env|token|password|secret|authorization|oauth)"',
                re.IGNORECASE,
            ),
        )

    def test_existing_skill_and_codex_contracts_remain_present(self):
        skill = SKILL.read_text(encoding="utf-8")
        self.assertRegex(
            skill,
            re.compile(
                r"\A---\n"
                r"name: gkmex-inventory\n"
                r"description: .+\n"
                r"---\n\n# Gkmex inventory\n",
            ),
        )
        codex = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        legacy_mcp = json.loads(
            (ROOT / ".mcp.json").read_text(encoding="utf-8")
        )
        self.assertEqual(codex["skills"], "./skills/")
        self.assertEqual(codex["mcpServers"], "./.mcp.json")
        self.assertEqual(
            legacy_mcp["mcpServers"]["gkmex-inventory"],
            {"type": "http", "url": "https://gkmex.com/mcp"},
        )

    def test_readme_distinguishes_portable_and_codex_entry_points(self):
        readme = README.read_text(encoding="utf-8")
        for fragment in (
            "## Portable Agent Plugin",
            "`plugin.json`",
            "`mcp.json`",
            "`skills/gkmex-inventory/SKILL.md`",
            "`.codex-plugin/plugin.json`",
            "`.mcp.json`",
            "Agent Plugins 1.0.0",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, readme)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest tests.test_agent_plugin -v
```

Expected: the portable manifest and MCP tests fail because root `plugin.json` and `mcp.json` do not exist; the README test also fails because the portable section does not exist. Failures must be caused by the missing feature, not syntax or import errors.

- [ ] **Step 3: Commit the RED contract**

```bash
git add tests/test_agent_plugin.py
git diff --cached --check
git commit -m "test: define portable Agent Plugin contract"
```

---

### Task 2: Implement the Portable Package in GREEN

**Files:**
- Create: `plugin.json`
- Create: `mcp.json`
- Modify: `README.md`
- Test: `tests/test_agent_plugin.py`

- [ ] **Step 1: Create the portable root manifest**

Create `plugin.json` exactly:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "gkmex-developer-resources",
  "version": "0.1.0",
  "description": "Portable public, zero-auth, read-only access to Gkmex used-crane inventory through an Agent Skill and MCP server.",
  "author": {
    "name": "Gkmex Cranes",
    "url": "https://gkmex.com"
  },
  "homepage": "https://gkmex.com/developers",
  "repository": "https://github.com/gkmex75/gkmex-developer-resources",
  "license": "MIT",
  "keywords": [
    "gkmex",
    "cranes",
    "inventory",
    "mcp",
    "agent-skills",
    "npm",
    "pypi"
  ]
}
```

- [ ] **Step 2: Create the portable MCP configuration**

Create `mcp.json` exactly:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "gkmex-inventory": {
      "type": "streamable-http",
      "url": "https://gkmex.com/mcp"
    }
  }
}
```

- [ ] **Step 3: Document the portable package without changing client-specific files**

Insert this section in `README.md` immediately before `## MCP configuration`:

```markdown
## Portable Agent Plugin

This repository root conforms to Agent Plugins 1.0.0 and packages the existing public Gkmex integration surfaces without credentials or write access.

- `plugin.json` — portable plugin identity and metadata
- `skills/gkmex-inventory/SKILL.md` — inventory search and inspection skill
- `mcp.json` — portable Streamable HTTP configuration for `https://gkmex.com/mcp`

The `.codex-plugin/plugin.json` and `.mcp.json` files remain available for Codex-compatible clients; they do not replace the portable root files.
```

Add these two entries before the existing skill entry under `## Agent integration files`:

```markdown
- `plugin.json` — portable Agent Plugins 1.0.0 manifest
- `mcp.json` — portable Streamable HTTP MCP configuration
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_agent_plugin -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Validate against the immutable official schemas**

Run:

```bash
agent_plugin_schema_dir="$(mktemp -d)"
curl -fsSL \
  https://agent-plugins.org/schemas/1.0.0/plugin.schema.json \
  -o "$agent_plugin_schema_dir/plugin.schema.json"
curl -fsSL \
  https://agent-plugins.org/schemas/1.0.0/mcp.schema.json \
  -o "$agent_plugin_schema_dir/mcp.schema.json"
printf '%s  %s\n' \
  '0a4aad95ce337878ad38802ebf0daa3fde76abe3f65400c86bcbb1ec0b3ab883' \
  "$agent_plugin_schema_dir/plugin.schema.json" \
  | shasum -a 256 -c -
printf '%s  %s\n' \
  '6539175bfcdf43085855183e86da40ea94b166547a72b47ae9a0a390516d3acb' \
  "$agent_plugin_schema_dir/mcp.schema.json" \
  | shasum -a 256 -c -
python3 -m venv "$agent_plugin_schema_dir/venv"
"$agent_plugin_schema_dir/venv/bin/python" -m pip install \
  --disable-pip-version-check 'jsonschema[format-nongpl]==4.25.1'
"$agent_plugin_schema_dir/venv/bin/python" - \
  "$agent_plugin_schema_dir" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

schema_dir = Path(sys.argv[1])
root = Path.cwd()
for document_name, schema_name in (
    ("plugin.json", "plugin.schema.json"),
    ("mcp.json", "mcp.schema.json"),
):
    document = json.loads((root / document_name).read_text(encoding="utf-8"))
    schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(document)
    print(f"SCHEMA_PASS {document_name}")
PY
```

Expected: both checksum lines print `OK`, followed by `SCHEMA_PASS plugin.json` and `SCHEMA_PASS mcp.json`.

- [ ] **Step 6: Run every developer-repository gate**

Run in the repository root:

```bash
python3 -m unittest discover -s tests -v
(cd packages/gkmex-python && \
  PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v)
(cd packages/gkmex && npm test)
python3 -m json.tool plugin.json >/dev/null
python3 -m json.tool mcp.json >/dev/null
git diff --check
git status --short --branch
```

Expected: root 8/8, Python 35/35, npm 130/130, both JSON documents parse, and only the three intended implementation files are uncommitted.

- [ ] **Step 7: Commit the portable implementation**

```bash
git add plugin.json mcp.json README.md
git diff --cached --check
git commit -m "feat: publish portable Agent Plugin v1"
```

---

### Task 3: Review, Merge, and Verify the Public Plugin Root

**Files:**
- No additional repository files.

- [ ] **Step 1: Review the complete branch and rerun the fresh gates**

Run:

```bash
python3 -m unittest discover -s tests -v
(cd packages/gkmex-python && \
  PYTHONPATH=src python3 -W error::ResourceWarning -m unittest discover -s tests -v)
(cd packages/gkmex && npm test)
python3 -m json.tool plugin.json >/dev/null
python3 -m json.tool mcp.json >/dev/null
git diff --check
git status --short --branch
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

Expected: root 8/8, Python 35/35, npm 130/130, valid JSON, a clean
feature worktree, and only the design, plan, RED contract, portable package,
and README changes in the branch diff. Perform an independent code review
focused on schema conformance, credential absence, package boundaries, and
README truthfulness. Fix any Critical or Important finding through a new
RED-GREEN cycle before proceeding.

- [ ] **Step 2: Push and create the developer-repository PR**

```bash
git push -u origin feat/agent-plugin-v1
gh pr create \
  --repo gkmex75/gkmex-developer-resources \
  --base main \
  --head feat/agent-plugin-v1 \
  --title "Publish Gkmex portable Agent Plugin v1" \
  --body-file - <<'EOF'
## Summary
- add the portable Agent Plugins 1.0.0 root manifest
- expose the existing public Gkmex MCP server through portable `mcp.json`
- document portable and Codex-specific entry points without adding credentials or write access

## Verification
- root Python contract tests
- Python SDK tests
- npm SDK tests
- official Agent Plugins schema checksums and validation
EOF
```

Expected: one PR URL for the exact two-commit branch.

- [ ] **Step 3: Merge only after the PR tree matches the reviewed tree**

Record the branch SHA and tree, confirm the PR head matches them, then merge through GitHub without force-pushing:

```bash
git rev-parse HEAD
git show -s --format=%T HEAD
gh pr view --repo gkmex75/gkmex-developer-resources --json headRefOid,mergeable,state,url
gh pr merge --repo gkmex75/gkmex-developer-resources --merge
```

Expected: merged PR and a new `main` merge SHA. Keep the branch and worktree for
the finishing-development-branch decision; do not attempt local cleanup here.

- [ ] **Step 4: Verify the public GitHub package bytes and schemas**

Create a clean detached worktree at the merge SHA:

```bash
developer_pr_number="$(gh pr view feat/agent-plugin-v1 \
  --repo gkmex75/gkmex-developer-resources \
  --json number --jq .number)"
developer_merge_sha="$(gh pr view "$developer_pr_number" \
  --repo gkmex75/gkmex-developer-resources \
  --json mergeCommit --jq .mergeCommit.oid)"
git fetch origin main
git worktree add \
  /Users/gokmentanacar/.config/superpowers/worktrees/gkmex-developer-resources/agent-plugin-v1-release \
  --detach "$developer_merge_sha"
git -C /Users/gokmentanacar/.config/superpowers/worktrees/gkmex-developer-resources/agent-plugin-v1-release \
  status --short
```

Expected: clean detached worktree at the recorded merge SHA.

Compare these three public URLs with the merged files:

```text
https://raw.githubusercontent.com/gkmex75/gkmex-developer-resources/main/plugin.json
https://raw.githubusercontent.com/gkmex75/gkmex-developer-resources/main/mcp.json
https://raw.githubusercontent.com/gkmex75/gkmex-developer-resources/main/skills/gkmex-inventory/SKILL.md
```

Run from the detached release worktree:

```bash
python3 - <<'PY'
from pathlib import Path
from urllib.request import Request, urlopen

root = Path.cwd()
base = (
    "https://raw.githubusercontent.com/gkmex75/"
    "gkmex-developer-resources/main/"
)
for relative in (
    "plugin.json",
    "mcp.json",
    "skills/gkmex-inventory/SKILL.md",
):
    request = Request(
        base + relative,
        headers={"User-Agent": "gkmex-agent-plugin-live/1.0"},
    )
    with urlopen(request, timeout=20) as response:
        assert response.status == 200, (relative, response.status)
        public = response.read()
    local = (root / relative).read_bytes()
    assert public == local, relative
    print(f"PUBLIC_BYTE_PASS {relative}")
PY

agent_plugin_release_schema_dir="$(mktemp -d)"
curl -fsSL \
  https://agent-plugins.org/schemas/1.0.0/plugin.schema.json \
  -o "$agent_plugin_release_schema_dir/plugin.schema.json"
curl -fsSL \
  https://agent-plugins.org/schemas/1.0.0/mcp.schema.json \
  -o "$agent_plugin_release_schema_dir/mcp.schema.json"
printf '%s  %s\n' \
  '0a4aad95ce337878ad38802ebf0daa3fde76abe3f65400c86bcbb1ec0b3ab883' \
  "$agent_plugin_release_schema_dir/plugin.schema.json" \
  | shasum -a 256 -c -
printf '%s  %s\n' \
  '6539175bfcdf43085855183e86da40ea94b166547a72b47ae9a0a390516d3acb' \
  "$agent_plugin_release_schema_dir/mcp.schema.json" \
  | shasum -a 256 -c -
python3 -m venv "$agent_plugin_release_schema_dir/venv"
"$agent_plugin_release_schema_dir/venv/bin/python" -m pip install \
  --disable-pip-version-check 'jsonschema[format-nongpl]==4.25.1'
"$agent_plugin_release_schema_dir/venv/bin/python" - \
  "$agent_plugin_release_schema_dir" <<'PY'
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

schema_dir = Path(sys.argv[1])
root = Path.cwd()
for document_name, schema_name in (
    ("plugin.json", "plugin.schema.json"),
    ("mcp.json", "mcp.schema.json"),
):
    document = json.loads((root / document_name).read_text(encoding="utf-8"))
    schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(document)
    print(f"SCHEMA_PASS {document_name}")
PY

npx -y @modelcontextprotocol/inspector \
  --cli https://gkmex.com/mcp \
  --transport http \
  --method tools/list \
  --format json
```

Expected: public bytes match the merge tree; schemas pass; tools are exactly `list_cranes`, `get_crane`, and `compare_cranes`.

---

### Task 4: Create an Isolated Site Worktree and Define Discovery in RED

**Files:**
- Modify: `tests/test_build_site.py`

- [ ] **Step 1: Preserve and fingerprint the dirty primary site checkout**

Run without modifying the primary checkout:

```bash
git -C /Users/gokmentanacar/projects/gkmex-site \
  status --porcelain=v1 -uall \
  | shasum -a 256
git -C /Users/gokmentanacar/projects/gkmex-site status --short --branch
```

Record the SHA-256 and full status output. Never pull, switch, reset, build, test, stage, or deploy from this dirty checkout.

- [ ] **Step 2: Create the isolated site feature worktree**

Run:

```bash
git -C /Users/gokmentanacar/projects/gkmex-site fetch origin main
git -C /Users/gokmentanacar/projects/gkmex-site check-ignore -q .worktrees
git -C /Users/gokmentanacar/projects/gkmex-site worktree add \
  /Users/gokmentanacar/projects/gkmex-site/.worktrees/agent-plugin-discovery \
  -b feat/agent-plugin-discovery origin/main
```

Expected: the worktree starts at the current remote `main`; `.worktrees` is ignored.

- [ ] **Step 3: Verify the clean site baseline**

Run in the new worktree:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_worker.mjs
git status --short --branch
```

Expected baseline: Python 46/46, Worker 21/21, clean worktree.

- [ ] **Step 4: Add the exact failing generated-output contract**

Add this method to `SeoAcceptanceTests` in `tests/test_build_site.py`:

```python
    def test_portable_agent_plugin_is_explicitly_discoverable(self):
        plugin_root = (
            "https://github.com/gkmex75/gkmex-developer-resources"
        )
        plugin_manifest = plugin_root + "/blob/main/plugin.json"
        label = "Gkmex portable Agent Plugin"

        markdown_link = f"[{label}]({plugin_root})"
        for relative in (
            "llms.txt",
            ".well-known/llms.txt",
            "llms-full.txt",
            "index.md",
            "agents.md",
            "developers/llms.txt",
        ):
            body = (SITE / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                self.assertEqual(body.count(markdown_link), 1)

        developers_html = (SITE / "developers/index.html").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            developers_html.count(
                f'href="{plugin_root}">{label}</a>'
            ),
            1,
        )
        self.assertEqual(
            developers_html.count(
                f'href="{plugin_manifest}">Agent Plugins v1 manifest</a>'
            ),
            1,
        )

        developers_markdown = (SITE / "developers.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(developers_markdown.count(markdown_link), 1)
        self.assertEqual(
            developers_markdown.count(
                f"[Agent Plugins v1 manifest]({plugin_manifest})"
            ),
            1,
        )

        api_catalog = json.loads(
            (SITE / ".well-known/api-catalog").read_text(encoding="utf-8")
        )
        self.assertEqual(
            api_catalog["linkset"][0]["service-doc"],
            [
                {
                    "href": "https://gkmex.com/developers",
                    "type": "text/html",
                    "title": "Gkmex developer documentation",
                },
                {
                    "href": plugin_root,
                    "type": "text/html",
                    "title": label,
                },
                {
                    "href": "https://www.npmjs.com/package/@gstcranes/gkmex",
                    "type": "text/html",
                    "title": "Gkmex Node.js SDK and CLI",
                },
                {
                    "href": "https://pypi.org/project/gkmex/",
                    "type": "text/html",
                    "title": "Gkmex Python SDK and CLI",
                },
            ],
        )

        for relative in ("api/llms.txt", "inventory/llms.txt"):
            body = (SITE / relative).read_text(encoding="utf-8")
            with self.subTest(unrelated=relative):
                self.assertNotIn(label, body)
```

- [ ] **Step 5: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest -v \
  tests.test_build_site.SeoAcceptanceTests.test_portable_agent_plugin_is_explicitly_discoverable
```

Expected: FAIL because the current generated discovery files use `Public developer repository` and the API catalog has no plugin entry.

- [ ] **Step 6: Commit the RED site contract**

```bash
git add tests/test_build_site.py
git diff --cached --check
git commit -m "test: define portable Agent Plugin discovery"
```

---

### Task 5: Generate the Minimal Site Discovery Change in GREEN

**Files:**
- Modify: `build_site.py`
- Modify: the nine generated files listed in the File Map
- Test: `tests/test_build_site.py`

- [ ] **Step 1: Add the two plugin discovery constants**

Immediately after `DEVELOPER_REPOSITORY` in `build_site.py`, add:

```python
AGENT_PLUGIN_URL = DEVELOPER_REPOSITORY
AGENT_PLUGIN_MANIFEST_URL = (
    DEVELOPER_REPOSITORY + "/blob/main/plugin.json"
)
```

- [ ] **Step 2: Add one ordered API catalog documentation entry**

In `_write_agent_files()`, insert this object immediately after the existing Gkmex developer documentation object and before the npm object:

```python
                    {
                        "href": AGENT_PLUGIN_URL,
                        "type": "text/html",
                        "title": "Gkmex portable Agent Plugin",
                    },
```

In the existing `expected_service_docs` list in
`test_official_sdks_and_clis_are_consistently_discoverable`, insert this same
expected entry immediately after the developer documentation object:

```python
            {
                "href": (
                    "https://github.com/gkmex75/"
                    "gkmex-developer-resources"
                ),
                "type": "text/html",
                "title": "Gkmex portable Agent Plugin",
            },
```

- [ ] **Step 3: Replace the shared repository route with the explicit plugin link**

Replace the shared `Public developer repository` bullet in `llms` with:

```python
- [Gkmex portable Agent Plugin]({AGENT_PLUGIN_URL}): root `plugin.json`, portable MCP configuration, inventory skill and integration resources
```

Because `llms` is the source for `llms.txt`, `/.well-known/llms.txt`,
`llms-full.txt`, `index.md`, and `agents.md`, do not hand-edit separate generator
strings for those outputs.

- [ ] **Step 4: Update the developer HTML and Markdown source strings**

In the developer HTML machine-readable resources list, replace the public
repository list item with these two adjacent items:

```python
<li><a href="{AGENT_PLUGIN_URL}">Gkmex portable Agent Plugin</a></li><li><a href="{AGENT_PLUGIN_MANIFEST_URL}">Agent Plugins v1 manifest</a></li>
```

In the developer Markdown machine-readable resources list, replace the public
repository bullet with:

```python
- [Gkmex portable Agent Plugin]({AGENT_PLUGIN_URL})
- [Agent Plugins v1 manifest]({AGENT_PLUGIN_MANIFEST_URL})
```

- [ ] **Step 5: Update only the developer section guide**

Replace the portable-files sentence in `developers/llms.txt`'s generator string
with this exact Markdown link and truthful description:

```python
The [Gkmex portable Agent Plugin]({AGENT_PLUGIN_URL}) packages the root Agent Plugins v1 manifest, the public Streamable HTTP MCP configuration, the inventory skill, OpenAPI and client-specific integration files. Commercial enquiries remain on the Gkmex contact page.
```

Do not add the label to `api/llms.txt` or `inventory/llms.txt`.

- [ ] **Step 6: Regenerate from the checked-in normalized fixture**

Run:

```bash
python3 build_site.py \
  --from-json data/inventory-sync.json \
  --skip-image-download
git status --short
```

Expected: only `build_site.py` and the nine approved generated files change;
the committed inventory, listing pages, media, sitemap, Worker, and data files
remain byte-identical.

- [ ] **Step 7: Run the focused test and verify GREEN**

Run:

```bash
python3 -m unittest -v \
  tests.test_build_site.SeoAcceptanceTests.test_portable_agent_plugin_is_explicitly_discoverable
```

Expected: PASS.

- [ ] **Step 8: Run every site gate**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_worker.mjs
python3 -m json.tool site/.well-known/api-catalog >/dev/null
node --check worker.mjs
node --check site/_worker.js
cmp -s worker.mjs site/_worker.js
git diff --check
git status --short --branch
```

Expected: Python 47/47, Worker 21/21, JSON/syntax/parity/diff checks pass, and only the approved source, test, and nine generated files differ from `origin/main`.

- [ ] **Step 9: Commit the site implementation**

```bash
git add \
  build_site.py \
  site/.well-known/api-catalog \
  site/.well-known/llms.txt \
  site/agents.md \
  site/developers.md \
  site/developers/index.html \
  site/developers/llms.txt \
  site/index.md \
  site/llms-full.txt \
  site/llms.txt
git diff --cached --check
git commit -m "feat: publish Agent Plugin discovery"
```

---

### Task 6: Review, Merge, Deploy, and Verify the Site

**Files:**
- No additional source files.

- [ ] **Step 1: Review the complete site branch**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_worker.mjs
python3 -m json.tool site/.well-known/api-catalog >/dev/null
node --check worker.mjs
node --check site/_worker.js
cmp -s worker.mjs site/_worker.js
git diff --check
git status --short --branch
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

Expected: Python 47/47, Worker 21/21, JSON/syntax/parity/diff checks pass, and
the branch contains only the plan-approved source, test, and nine generated
files. Perform an independent review for exact generated-file scope,
external-link truthfulness, catalog ordering, and primary-checkout preservation.
Fix any Critical or Important finding through RED-GREEN before proceeding.

- [ ] **Step 2: Push and create the site PR**

```bash
git push -u origin feat/agent-plugin-discovery
gh pr create \
  --repo gkmex75/gkmex-site \
  --base main \
  --head feat/agent-plugin-discovery \
  --title "Publish Gkmex Agent Plugin discovery" \
  --body-file - <<'EOF'
## Summary
- name the existing public developer repository as the Gkmex portable Agent Plugin
- link the root Agent Plugins v1 manifest from developer documentation
- add one exact plugin entry to the API catalog

## Verification
- 47 Python acceptance tests
- 21 Worker tests
- generated JSON, Worker syntax/parity, and diff checks
EOF
```

- [ ] **Step 3: Merge only the reviewed tree**

Record branch SHA/tree, verify the PR head, and merge through GitHub:

```bash
git rev-parse HEAD
git show -s --format=%T HEAD
gh pr view --repo gkmex75/gkmex-site --json headRefOid,mergeable,state,url
gh pr merge --repo gkmex75/gkmex-site --merge
```

Expected: merged PR and a new `main` merge SHA. Keep the branch and worktree for
the final cleanup decision.

- [ ] **Step 4: Create a clean detached release worktree**

Run:

```bash
site_pr_number="$(gh pr view feat/agent-plugin-discovery \
  --repo gkmex75/gkmex-site \
  --json number --jq .number)"
site_merge_sha="$(gh pr view "$site_pr_number" \
  --repo gkmex75/gkmex-site \
  --json mergeCommit --jq .mergeCommit.oid)"
git fetch origin main
git show -s --format='%H %T' "$site_merge_sha"
git worktree add \
  /Users/gokmentanacar/projects/gkmex-site/.worktrees/agent-plugin-discovery-release \
  --detach "$site_merge_sha"
cd /Users/gokmentanacar/projects/gkmex-site/.worktrees/agent-plugin-discovery-release
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_worker.mjs
python3 -m json.tool site/.well-known/api-catalog >/dev/null
node --check worker.mjs
node --check site/_worker.js
cmp -s worker.mjs site/_worker.js
git diff --check
git status --short
```

Expected: recorded merge SHA/tree, Python 47/47, Worker 21/21, every auxiliary
gate passes, and the detached release worktree is clean.

- [ ] **Step 5: Deploy the exact merged tree to Cloudflare Pages**

Run only from the clean detached release worktree:

```bash
env \
  -u CLOUDFLARE_API_TOKEN \
  -u CLOUDFLARE_WORKERS_TOKEN \
  -u CLOUDFLARE_ACCOUNT_ID \
  /Users/gokmentanacar/projects/crane-rental-directory/node_modules/.bin/wrangler \
  pages deploy site \
  --project-name gkmex-site \
  --branch main
```

Expected: one successful Production deployment URL. Record the deployment ID,
URL, merge SHA, and merge tree.

- [ ] **Step 6: Verify all live artifacts and protocols**

Run from the detached release worktree:

```bash
python3 - <<'PY'
from pathlib import Path
from urllib.request import Request, urlopen

root = Path.cwd() / "site"
checks = {
    "https://gkmex.com/.well-known/api-catalog": root / ".well-known/api-catalog",
    "https://gkmex.com/.well-known/llms.txt": root / ".well-known/llms.txt",
    "https://gkmex.com/agents.md": root / "agents.md",
    "https://gkmex.com/developers.md": root / "developers.md",
    "https://gkmex.com/developers": root / "developers/index.html",
    "https://gkmex.com/developers/llms.txt": root / "developers/llms.txt",
    "https://gkmex.com/index.md": root / "index.md",
    "https://gkmex.com/llms-full.txt": root / "llms-full.txt",
    "https://gkmex.com/llms.txt": root / "llms.txt",
}
for url, path in checks.items():
    request = Request(
        url,
        headers={"User-Agent": "gkmex-agent-plugin-live/1.0"},
    )
    with urlopen(request, timeout=20) as response:
        assert response.status == 200, (url, response.status)
        live = response.read()
    expected = path.read_bytes()
    assert live == expected, url
    print(f"LIVE_BYTE_PASS {url}")
PY

npx -y @modelcontextprotocol/inspector \
  --cli https://gkmex.com/mcp \
  --transport http \
  --method tools/list \
  --format json
```

Expected: byte parity for all nine artifacts and exactly the existing three MCP
tools. If any byte or protocol check fails, do not call Ora.ai; restore the last
known-good site deployment through the rollback procedure in the design.

- [ ] **Step 7: Prove the primary checkout was preserved**

Run:

```bash
git -C /Users/gokmentanacar/projects/gkmex-site \
  status --porcelain=v1 -uall \
  | shasum -a 256
git -C /Users/gokmentanacar/projects/gkmex-site status --short --branch
```

Compare the output and SHA-256 with the pre-worktree baseline. Expected: exact
match.

---

### Task 7: Run One Quota-Safe Ora.ai Measurement

**Files:**
- No repository files.

- [ ] **Step 1: Read the persisted baseline without scanning**

Run:

```bash
curl -fsSL \
  -A 'gkmex-agent-plugin-release/1.0' \
  'https://ora.ai/api/score/gkmex.com?format=audit' \
  | jq '{score,grade,scannedAt,check:(.layers[].checks[]|select(.id=="agent-plugins-repo")|{id,status,score,maxScore,details})}'
```

Expected: record the current persisted score and `agent-plugins-repo` result
without changing Ora state.

- [ ] **Step 2: Send exactly one targeted Agent Plugin check**

Run once:

```bash
curl -fsSL -X POST \
  -A 'gkmex-agent-plugin-release/1.0' \
  'https://ora.ai/api/scan/checks' \
  -H 'Content-Type: application/json' \
  --data '{"url":"gkmex.com","checkIds":["agent-plugins-repo"]}' \
  | jq '{contractVersion,urlKind,storedScanUpdated,results:[.results[]|{id,status,score,maxScore,details}]}'
```

Expected: exactly one `agent-plugins-repo` result. Do not retry on timeout,
scanner variance, cache delay, or an unchanged result.

- [ ] **Step 3: Gate at most one non-forced full scan**

If and only if the targeted result has a score above zero or a status beginning
with `pass`, send one request:

```bash
curl -fsSL -X POST \
  -A 'gkmex-agent-plugin-release/1.0' \
  'https://ora.ai/api/scan?format=audit' \
  -H 'Content-Type: application/json' \
  --data '{"url":"gkmex.com","maxAgeSeconds":3600}' \
  | jq '{score,grade,scannedAt,analysisStatus,layers:[.layers[]|{id,name,score,maxScore}],check:(.layers[].checks[]|select(.id=="agent-plugins-repo")|{id,status,score,maxScore,details})}'
```

Never send `force: true`. Full-scan count must be zero or one.

- [ ] **Step 4: Read the persisted post-state separately**

Run:

```bash
curl -fsSL \
  -A 'gkmex-agent-plugin-release/1.0' \
  'https://ora.ai/api/score/gkmex.com?format=audit' \
  | jq '{score,grade,scannedAt,check:(.layers[].checks[]|select(.id=="agent-plugins-repo")|{id,status,score,maxScore,details})}'
```

Report the targeted result, optional synchronous full result, and persisted GET
separately. Claim a score increase only when the persisted GET proves it; an
unchanged external result is not a rollback trigger when live acceptance
passed.

---

### Task 8: Final Verification and Handoff

**Files:**
- No additional source files.

- [ ] **Step 1: Run a final independent implementation review**

Review both merged trees against the design and this plan. Confirm exact file
scope, schema digests, tests, public GitHub bytes, deployed site bytes, MCP tool
list, Ora call counts, and primary checkout preservation. Resolve every Critical
or Important finding before completion.

- [ ] **Step 2: Record the truthful release evidence**

Report:

- both PR URLs, merge SHAs, and merge trees;
- developer tests 8/8, Python SDK 35/35, npm 130/130;
- site tests 47/47 and Worker 21/21;
- both official schema checksum and validation results;
- Cloudflare deployment ID/URL/source;
- live nine-file parity and MCP three-tool result;
- targeted/full/forced Ora call counts and synchronous versus persisted scores;
- the unchanged primary-checkout fingerprint;
- any scanner or indexing limitation without claiming unsupported score credit.

- [ ] **Step 3: Invoke the finishing-development-branch workflow**

Both PRs are already merged at this point. Use the skill to decide safe local
branch/worktree cleanup. Never remove the dirty primary site checkout or delete
an unmerged branch. Preserve worktrees unless the selected completion option
explicitly permits cleanup.
