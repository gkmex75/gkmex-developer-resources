# Gkmex PyPI Trusted Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure tokenless, approval-gated PyPI publishing for future `gkmex` Python releases from the exact GitHub Release event ref/SHA without republishing `1.0.0`.

**Architecture:** Add one top-level GitHub Actions workflow with an unprivileged build job and a separate OIDC-enabled publish job. Protect the publish job with a GitHub `pypi` environment requiring `gkmex75` approval, then register that exact workflow/environment identity as a Trusted Publisher on the existing PyPI project.

**Tech Stack:** GitHub Actions, Python 3.12, `unittest`, PEP 517 `build`, Twine, GitHub environments, PyPI Trusted Publishing/OIDC, `actionlint`, GitHub CLI, browser control for authenticated PyPI settings.

---

## Scope and Safety Gates

Repository work is confined to:

- Create: `.github/workflows/publish-python.yml`
- Create: `tests/__init__.py`
- Create: `tests/test_publish_workflow.py`
- Existing design: `docs/superpowers/specs/2026-09-01-gkmex-pypi-trusted-publishing-design.md`
- This plan: `docs/superpowers/plans/2026-09-01-gkmex-pypi-trusted-publishing.md`

External state changes are confined to:

- GitHub environment `pypi` in `gkmex75/gkmex-developer-resources`
- One GitHub Actions Trusted Publisher entry in PyPI project `gkmex`

Hard stops:

- Do not create, publish, edit, or delete a GitHub Release.
- Do not create or push a version tag.
- Do not upload another PyPI file or version.
- Do not add a PyPI/Twine token to GitHub, a file, an environment variable, a
  command, or chat.
- Do not enable `workflow_dispatch`, `skip-existing`, password fallback, or a
  reusable publish workflow.
- If the PyPI publisher card already exists, verify it instead of creating a
  duplicate.

## Fixed Versions and Identities

Use these exact values:

```text
GitHub owner:        gkmex75
GitHub repository:   gkmex-developer-resources
Default branch:      main
Workflow filename:   publish-python.yml
Workflow trigger:    release.published
GitHub environment:  pypi
Required reviewer:   gkmex75 (user ID 266572182)
PyPI project:        gkmex
Release tag prefix:  gkmex-python-v
Python:              3.12
build:               1.6.0
twine:               7.0.0
actionlint:           1.7.12
```

Pin the actions to these resolved commits:

```text
actions/checkout v7.0.1:
  3d3c42e5aac5ba805825da76410c181273ba90b1
actions/setup-python v7.0.0:
  5fda3b95a4ea91299a34e894583c3862153e4b97
actions/upload-artifact v7.0.1:
  043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
actions/download-artifact v8.0.1:
  3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c
pypa/gh-action-pypi-publish v1.14.2 commit:
  dc37677b2e1c63e2034f94d8a5b11f265b73ba33
```

### Task 1: Establish the Trusted Publishing Baseline

**Files:** None

- [ ] **Step 1: Confirm the feature worktree and ancestry**

Run:

```bash
cd /Users/gokmentanacar/.config/superpowers/worktrees/gkmex-developer-resources/pypi-trusted-publishing
git status --short
git rev-parse HEAD
git merge-base --is-ancestor origin/main HEAD
```

Expected: empty status; `HEAD` contains the approved design commits and remains
based on `origin/main`.

- [ ] **Step 2: Reconfirm that no release automation or PyPI secret exists**

Run:

```bash
test ! -d .github/workflows
gh secret list --repo gkmex75/gkmex-developer-resources
gh api repos/gkmex75/gkmex-developer-resources/environments --jq '.environments[]?.name'
gh release list --repo gkmex75/gkmex-developer-resources --limit 20
curl -fsSL 'https://pypi.org/pypi/gkmex/json?trusted-publishing-baseline=1' \
  | jq -e '.info.version == "1.0.0" and (.releases | keys == ["1.0.0"])'
```

Expected: no workflow directory, no GitHub secret names, no `pypi`
environment, no release created by this task, and PyPI contains only `1.0.0`.

- [ ] **Step 3: Run the existing package baselines**

Run:

```bash
cd packages/gkmex-python
PYTHONPATH=src /Users/gokmentanacar/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -W error::ResourceWarning -m unittest discover -s tests
cd ../gkmex
npm test
cd ../..
```

Expected: Python `35/35` and npm `130/130` pass.

### Task 2: Add a Failing Workflow Security Contract

**Files:**

- Create: `tests/__init__.py`
- Create: `tests/test_publish_workflow.py`
- Target: `.github/workflows/publish-python.yml`

- [ ] **Step 1: Create the empty root test package marker**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 2: Write the workflow contract test**

Create `tests/test_publish_workflow.py` with:

```python
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-python.yml"


class PublishWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(WORKFLOW.is_file(), f"missing workflow: {WORKFLOW}")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def job(self, name):
        match = re.search(
            rf"(?ms)^  {re.escape(name)}:\n"
            rf"(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
            self.workflow,
        )
        self.assertIsNotNone(match, f"missing job: {name}")
        return match.group("body")

    def test_only_published_python_releases_enter_the_build(self):
        triggers = re.findall(
            r"(?ms)^on:\n"
            r"(?P<body>.*?)(?=^[A-Za-z0-9_-]+:(?:[^\n]*\n|\Z)|\Z)",
            self.workflow,
        )
        self.assertEqual(
            triggers,
            ["  release:\n    types: [published]\n\n"],
        )
        for forbidden in (
            "workflow_dispatch:",
            "pull_request:",
            "pull_request_target:",
            "workflow_call:",
            "\n  push:",
        ):
            self.assertNotIn(forbidden, self.workflow)
        self.assertNotIn("continue-on-error:", self.workflow)

        build = self.job("build")
        self.assertIn(
            "if: startsWith(github.event.release.tag_name, "
            "'gkmex-python-v')",
            build,
        )
        self.assertNotRegex(build, r"(?m)^\s+ref:")
        self.assertIn("persist-credentials: false", build)
        self.assertIn(
            "RELEASE_TAG: ${{ github.event.release.tag_name }}",
            build,
        )
        self.assertIn(
            'pathlib.Path("packages/gkmex-python/pyproject.toml").read_text(',
            build,
        )
        self.assertIn('version = metadata["project"]["version"]', build)
        self.assertIn(
            'expected = f"gkmex-python-v{version}"',
            build,
        )
        self.assertRegex(
            build,
            r'actual = os\.environ\["RELEASE_TAG"\]\s+'
            r"if actual != expected:\s+"
            r"raise SystemExit\(\s+"
            r'f"release tag \{actual!r\} must equal \{expected!r\}"\s+'
            r"\)",
        )

    def test_oidc_is_confined_to_the_approved_publish_job(self):
        jobs = re.search(
            r"(?ms)^jobs:\n(?P<body>.*)\Z",
            self.workflow,
        )
        self.assertIsNotNone(jobs, "missing top-level jobs block")
        job_names = re.findall(
            r"(?m)^  ([A-Za-z0-9_-]+):\n",
            jobs.group("body"),
        )
        self.assertEqual(job_names, ["build", "publish"])

        build = self.job("build")
        publish = self.job("publish")

        self.assertEqual(
            re.findall(r"(?m)^permissions:.*$", self.workflow),
            ["permissions: {}"],
        )
        self.assertIn("permissions: {}\n\njobs:\n", self.workflow)
        self.assertEqual(
            re.findall(r"(?m)^    permissions:.*$", build),
            ["    permissions:"],
        )
        self.assertIn(
            "    permissions:\n      contents: read\n    steps:\n",
            build,
        )
        self.assertNotIn("id-token:", build)
        self.assertEqual(self.workflow.count("id-token: write"), 1)
        self.assertIn("needs: build", publish)
        self.assertIn(
            "environment:\n      name: pypi\n"
            "      url: https://pypi.org/p/gkmex",
            publish,
        )
        self.assertEqual(
            re.findall(r"(?m)^    permissions:.*$", publish),
            ["    permissions:"],
        )
        self.assertIn(
            "    permissions:\n      id-token: write\n    steps:\n",
            publish,
        )
        self.assertNotRegex(publish, r"(?m)^\s+run:")
        for forbidden in (
            "actions/checkout",
            "secrets.",
            "password:",
            "user:",
            "skip-existing",
            "TWINE_",
        ):
            self.assertNotIn(forbidden, publish)

    def test_every_action_is_pinned_to_the_approved_commit(self):
        expected = [
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
            "pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33",
        ]
        actual = re.findall(
            r"(?m)^\s+uses:\s+([^\s#]+)",
            self.workflow,
        )
        self.assertEqual(actual, expected)
        for action in actual:
            self.assertRegex(action, r"@[0-9a-f]{40}$")
        for version in (
            "# v7.0.1",
            "# v7.0.0",
            "# v8.0.1",
            "# v1.14.2",
        ):
            self.assertIn(version, self.workflow)

    def test_verified_distributions_are_the_only_publish_input(self):
        build = self.job("build")
        publish = self.job("publish")

        run_headers = re.findall(r"(?m)^        run:[ \t]*(.*)$", build)
        self.assertEqual(
            run_headers,
            [
                "python -m pip install --disable-pip-version-check "
                "build==1.6.0 twine==7.0.0",
                "|",
                "python -m unittest discover -s tests",
                "PYTHONPATH=packages/gkmex-python/src python "
                "-W error::ResourceWarning -m unittest discover "
                "-s packages/gkmex-python/tests",
                "python -m build --outdir dist packages/gkmex-python",
                "|",
                "python -m twine check dist/*",
            ],
        )
        heredocs = re.findall(
            r"(?m)^[ \t]+(python - <<'PY'.*)$",
            build,
        )
        self.assertEqual(heredocs, ["python - <<'PY'", "python - <<'PY'"])

        self.assertIn("build==1.6.0 twine==7.0.0", build)
        self.assertIn(
            "PYTHONPATH=packages/gkmex-python/src python "
            "-W error::ResourceWarning -m unittest discover "
            "-s packages/gkmex-python/tests",
            build,
        )
        self.assertIn("python -m unittest discover -s tests", build)
        self.assertIn(
            "python -m build --outdir dist packages/gkmex-python",
            build,
        )
        self.assertRegex(
            build,
            r"expected = \{\s+"
            r'f"gkmex-\{version\}-py3-none-any\.whl",\s+'
            r'f"gkmex-\{version\}\.tar\.gz",\s+'
            r"\}\s+"
            r'actual = \{path\.name for path in pathlib\.Path\("dist"\)'
            r"\.iterdir\(\)\}\s+"
            r"if actual != expected:\s+raise SystemExit\(\s+"
            r'f"unexpected distributions: \{sorted\(actual\)!r\}; "\s+'
            r'f"expected \{sorted\(expected\)!r\}"\s+\)',
        )
        self.assertIn("python -m twine check dist/*", build)
        self.assertIn("name: gkmex-python-distributions", build)
        self.assertIn("path: dist/", build)
        self.assertIn("if-no-files-found: error", build)
        self.assertIn("retention-days: 1", build)
        self.assertIn("name: gkmex-python-distributions", publish)
        self.assertIn("path: dist/", publish)
        self.assertIn("packages-dir: dist/", publish)
        self.assertIn("print-hash: true", publish)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
/Users/gokmentanacar/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -m unittest tests.test_publish_workflow -v
```

Expected: four failures containing `missing workflow:` because
`.github/workflows/publish-python.yml` does not exist.

### Task 3: Implement the Two-Job Trusted Publishing Workflow

**Files:**

- Create: `.github/workflows/publish-python.yml`
- Test: `tests/test_publish_workflow.py`

- [ ] **Step 1: Create the exact release workflow**

Create `.github/workflows/publish-python.yml` with:

```yaml
name: Publish Gkmex Python package

on:
  release:
    types: [published]

permissions: {}

jobs:
  build:
    name: Build and verify distributions
    if: startsWith(github.event.release.tag_name, 'gkmex-python-v')
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Check out the release tag
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 1
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: "3.12"

      - name: Install pinned release tooling
        run: python -m pip install --disable-pip-version-check build==1.6.0 twine==7.0.0

      - name: Validate the release tag against package metadata
        env:
          RELEASE_TAG: ${{ github.event.release.tag_name }}
        run: |
          python - <<'PY'
          import os
          import pathlib
          import tomllib

          metadata = tomllib.loads(
              pathlib.Path("packages/gkmex-python/pyproject.toml").read_text(
                  encoding="utf-8"
              )
          )
          version = metadata["project"]["version"]
          expected = f"gkmex-python-v{version}"
          actual = os.environ["RELEASE_TAG"]
          if actual != expected:
              raise SystemExit(
                  f"release tag {actual!r} must equal {expected!r}"
              )
          print(f"validated Python release {version}")
          PY

      - name: Run release contract tests
        run: python -m unittest discover -s tests

      - name: Run Python package tests
        run: PYTHONPATH=packages/gkmex-python/src python -W error::ResourceWarning -m unittest discover -s packages/gkmex-python/tests

      - name: Build wheel and source distribution
        run: python -m build --outdir dist packages/gkmex-python

      - name: Verify distribution filenames
        run: |
          python - <<'PY'
          import pathlib
          import tomllib

          metadata = tomllib.loads(
              pathlib.Path("packages/gkmex-python/pyproject.toml").read_text(
                  encoding="utf-8"
              )
          )
          version = metadata["project"]["version"]
          expected = {
              f"gkmex-{version}-py3-none-any.whl",
              f"gkmex-{version}.tar.gz",
          }
          actual = {path.name for path in pathlib.Path("dist").iterdir()}
          if actual != expected:
              raise SystemExit(
                  f"unexpected distributions: {sorted(actual)!r}; "
                  f"expected {sorted(expected)!r}"
              )
          print("distribution allowlist verified")
          PY

      - name: Check distribution metadata
        run: python -m twine check dist/*

      - name: Store verified distributions
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: gkmex-python-distributions
          path: dist/
          if-no-files-found: error
          retention-days: 1

  publish:
    name: Publish distributions to PyPI
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/gkmex
    permissions:
      id-token: write
    steps:
      - name: Download verified distributions
        uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
        with:
          name: gkmex-python-distributions
          path: dist/

      - name: Publish distributions
        uses: pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33 # v1.14.2
        with:
          packages-dir: dist/
          print-hash: true
```

- [ ] **Step 2: Run the focused contract and verify GREEN**

Run:

```bash
/Users/gokmentanacar/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -m unittest tests.test_publish_workflow -v
```

Expected: four tests pass.

- [ ] **Step 3: Run `actionlint` from a verified release archive**

Run:

```bash
actionlint_dir=$(mktemp -d /tmp/actionlint-1.7.12.XXXXXX)
gh release download v1.7.12 \
  --repo rhysd/actionlint \
  --pattern actionlint_1.7.12_checksums.txt \
  --pattern actionlint_1.7.12_darwin_arm64.tar.gz \
  --dir "$actionlint_dir"
(
  cd "$actionlint_dir"
  rg ' actionlint_1.7.12_darwin_arm64.tar.gz$' \
    actionlint_1.7.12_checksums.txt | shasum -a 256 -c -
)
tar -xzf "$actionlint_dir/actionlint_1.7.12_darwin_arm64.tar.gz" \
  -C "$actionlint_dir"
"$actionlint_dir/actionlint" .github/workflows/publish-python.yml
```

Expected: archive checksum `OK`; `actionlint` produces no output and exits `0`.

- [ ] **Step 4: Run all local regression gates**

Run:

```bash
/Users/gokmentanacar/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -m unittest discover -s tests -v
cd packages/gkmex-python
PYTHONPATH=src /Users/gokmentanacar/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -W error::ResourceWarning -m unittest discover -s tests
cd ../gkmex
npm test
cd ../..
git diff --check
```

Expected: root `4/4`, Python package `35/35`, npm `130/130`, and clean diff check.

- [ ] **Step 5: Scan the exact scope for credentials and unpinned actions**

Run:

```bash
if rg -l --hidden \
  'pypi-[A-Za-z0-9_-]{85,}|npm_[A-Za-z0-9]{20,}' \
  .github tests docs/superpowers/specs/2026-09-01-gkmex-pypi-trusted-publishing-design.md \
  docs/superpowers/plans/2026-09-01-gkmex-pypi-trusted-publishing.md; then
  exit 1
fi
if rg -n 'TWINE_|PYPI_API_TOKEN|secrets\.|password:|user:' \
  .github/workflows/publish-python.yml; then
  exit 1
fi
python3 - <<'PY'
import pathlib
import re

workflow = pathlib.Path(
    ".github/workflows/publish-python.yml"
).read_text(encoding="utf-8")
refs = re.findall(r"(?m)^\s+uses:\s+([^\s#]+)", workflow)
if not refs or any(not re.search(r"@[0-9a-f]{40}$", ref) for ref in refs):
    raise SystemExit(f"unpinned action refs: {refs!r}")
print(f"verified {len(refs)} pinned action refs")
PY
```

Expected: credential scan has no output; five pinned action refs verified.

- [ ] **Step 6: Commit the tested workflow**

Run:

```bash
git add .github/workflows/publish-python.yml tests/__init__.py tests/test_publish_workflow.py
git commit -m "ci: add trusted PyPI publishing"
```

Expected: one commit containing only the workflow and its root tests.

### Task 4: Review, Merge, and Record the Exact Repository State

**Files:** No new files unless a verified review finding requires a test-first fix.

- [ ] **Step 1: Request independent code review**

Use the `requesting-code-review` skill. Review the exact range
`origin/main..HEAD` for:

- release event and Python tag isolation;
- release-event ref/SHA checkout and tag/version binding;
- build/publish job separation;
- OIDC permission scope;
- action SHA pins and release-tool pins;
- artifact allowlist and one-day retention;
- absence of tokens, secrets, password fallback, `skip-existing`, and manual
  triggers;
- no path that can republish `1.0.0` during setup.

Fix valid findings test-first, rerun Task 3 gates, and obtain a clean final
review.

- [ ] **Step 2: Push and open one PR**

Run:

```bash
git status --short
git push -u origin feat/pypi-trusted-publishing
gh pr create \
  --base main \
  --head feat/pypi-trusted-publishing \
  --title "Add trusted PyPI publishing" \
  --body '## Summary

- add release-only, tokenless PyPI publishing for the Gkmex Python package
- separate unprivileged build verification from the approval-gated OIDC publish job
- pin every action and verify the workflow security contract

## Verification

- root workflow contract: 4/4
- Python package: 35/35
- npm regression: 130/130
- actionlint: clean
- independent review: no release blockers
- no release, tag, PyPI upload, or credential created by this PR'
```

Expected: one PR against `main`.

- [ ] **Step 3: Inspect GitHub's PR state and merge**

Run:

```bash
gh pr view --json number,state,mergeable,statusCheckRollup,url
gh pr checks
gh pr merge --merge
git fetch origin --prune
git rev-parse origin/main
```

Expected: mergeable PR; if no CI checks are configured, report that truthfully
and rely on the recorded local gates. Record the exact merge SHA.

- [ ] **Step 4: Verify the merged workflow bytes**

Run from the feature worktree after fetching `origin/main`:

```bash
git show origin/main:.github/workflows/publish-python.yml \
  | cmp .github/workflows/publish-python.yml -
git show origin/main:tests/test_publish_workflow.py \
  | cmp tests/test_publish_workflow.py -
```

Expected: both comparisons exit `0` with no output.

### Task 5: Create the Approval-Gated GitHub Environment

**External state:** GitHub repository environment only

- [ ] **Step 1: Create `pypi` with the exact reviewer policy**

Run:

```bash
gh api --method PUT \
  repos/gkmex75/gkmex-developer-resources/environments/pypi \
  --input - <<'JSON'
{
  "wait_timer": 0,
  "prevent_self_review": false,
  "reviewers": [
    {
      "type": "User",
      "id": 266572182
    }
  ],
  "deployment_branch_policy": null,
  "can_admins_bypass": false
}
JSON
```

Expected: environment response names `pypi` and includes a required reviewer
for `gkmex75`.

- [ ] **Step 2: Verify approval, bypass, and secret state**

Run:

```bash
gh api repos/gkmex75/gkmex-developer-resources/environments/pypi \
  | jq -e '
      .name == "pypi"
      and .can_admins_bypass == false
      and any(
        .protection_rules[];
        .type == "required_reviewers"
        and any(
          .reviewers[];
          .reviewer.login == "gkmex75"
          and .reviewer.id == 266572182
        )
      )
    '
if gh api repos/gkmex75/gkmex-developer-resources/environments/pypi/secrets \
  --jq '.secrets[].name' | rg -i 'PYPI|TWINE'; then
  exit 1
fi
if gh secret list --repo gkmex75/gkmex-developer-resources \
  | rg -i 'PYPI|TWINE'; then
  exit 1
fi
```

Expected: policy assertion succeeds; neither environment nor repository has a
PyPI/Twine secret name.

### Task 6: Register the Existing PyPI Project's Trusted Publisher

**External state:** PyPI project `gkmex` Publishing settings only

- [ ] **Step 1: Open the authenticated PyPI publishing settings**

Use the browser-control skill and navigate the existing signed-in browser to:

```text
https://pypi.org/manage/project/gkmex/settings/publishing/
```

If authentication is required, ask the user to sign in in that selected
browser and resume only after they confirm.

- [ ] **Step 2: Resolve duplicate state before writing**

Inspect the current publisher cards. If a card already exactly matches all
four values below, do not create another card; continue to verification. If a
partially matching or contradictory card exists, stop and report it instead of
deleting or replacing it.

```text
Owner:       gkmex75
Repository:  gkmex-developer-resources
Workflow:    publish-python.yml
Environment: pypi
```

- [ ] **Step 3: Add the exact GitHub Actions publisher**

In the GitHub Actions publisher form, enter the four exact values above and
select **Add** once. Do not enter any token, password, project name, branch,
tag, or workflow path; PyPI expects the workflow filename only.

- [ ] **Step 4: Verify the resulting card visually**

Read the resulting publisher card and confirm it shows:

```text
gkmex75/gkmex-developer-resources
publish-python.yml
pypi
```

Take no action on project owners, maintainers, existing releases, API tokens,
or any other settings.

### Task 7: Verify the Ready-but-Untriggered Release Path

**Files:** None

- [ ] **Step 1: Confirm GitHub recognizes the workflow on `main`**

Run:

```bash
gh api repos/gkmex75/gkmex-developer-resources/actions/workflows/publish-python.yml \
  | jq -e '
      .state == "active"
      and .path == ".github/workflows/publish-python.yml"
    '
gh workflow view publish-python.yml \
  --repo gkmex75/gkmex-developer-resources --yaml
```

Expected: workflow is active and GitHub renders the merged YAML.

- [ ] **Step 2: Confirm setup did not trigger or publish anything**

Run:

```bash
gh run list \
  --repo gkmex75/gkmex-developer-resources \
  --workflow publish-python.yml \
  --limit 20 \
  --json databaseId,event,status,conclusion,url
curl -fsSL 'https://pypi.org/pypi/gkmex/json?trusted-publishing-final=1' \
  | jq -e '
      .info.version == "1.0.0"
      and (.releases | keys == ["1.0.0"])
      and ([.urls[].filename] | sort == [
        "gkmex-1.0.0-py3-none-any.whl",
        "gkmex-1.0.0.tar.gz"
      ])
    '
```

Expected: no runs for this new workflow and PyPI still has exactly the two
`1.0.0` artifacts.

- [ ] **Step 3: Run the final local workflow and package gates from the exact merge tree**

Create a clean detached worktree at the recorded merge SHA, run the gates, and
remove that verification worktree through Git:

```bash
merge_sha=$(git rev-parse origin/main)
verify_worktree=$(mktemp -d /tmp/gkmex-pypi-merge-verify.XXXXXX)
git worktree add --detach "$verify_worktree" "$merge_sha"
cd "$verify_worktree"
/Users/gokmentanacar/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -m unittest discover -s tests -v
cd packages/gkmex-python
PYTHONPATH=src /Users/gokmentanacar/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  -W error::ResourceWarning -m unittest discover -s tests
cd ../gkmex
npm test
cd /Users/gokmentanacar/.config/superpowers/worktrees/gkmex-developer-resources/pypi-trusted-publishing
git worktree remove "$verify_worktree"
```

Expected: the detached worktree reports the recorded `origin/main` SHA; root
`4/4`, Python `35/35`, and npm `130/130` pass from that exact tree; `git
worktree remove` exits `0`.

- [ ] **Step 4: Record the handoff contract for the next real release**

Report:

- repository merge SHA and PR URL;
- active workflow path;
- GitHub environment reviewer/bypass state;
- exact PyPI publisher identity;
- local test counts and `actionlint` result;
- unchanged PyPI `1.0.0` release/files;
- explicit statement that no release/tag/upload was created;
- next release operator steps:
  1. update the version in `packages/gkmex-python/pyproject.toml` and
     `packages/gkmex-python/src/gkmex/client.py`, plus the matching assertions
     in `packages/gkmex-python/tests/test_package.py`, to the same new version;
  2. merge and verify the package;
  3. create `gkmex-python-v<version>`;
  4. publish the GitHub Release;
  5. approve the waiting `pypi` environment deployment;
  6. verify PyPI hashes and attestations.

Do not claim that OIDC upload has been live-tested until that next real
release succeeds.
