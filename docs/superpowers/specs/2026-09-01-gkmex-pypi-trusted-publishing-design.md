# Gkmex PyPI Trusted Publishing Design

**Date:** 2026-09-01
**Status:** Approved
**Repository:** `gkmex75/gkmex-developer-resources`
**PyPI project:** `gkmex`

## Goal

Replace long-lived PyPI credentials in the release path with GitHub Actions
Trusted Publishing. Future Python releases must be built from the exact GitHub
Release event ref/SHA, pass the package gates, require an explicit `gkmex75`
environment approval, and reach PyPI through a short-lived OIDC credential.

This change must not republish or modify `gkmex==1.0.0`.

## Current State

- `gkmex==1.0.0` is public on PyPI.
- The repository has no GitHub Actions workflows.
- `main` is the default branch.
- The repository is public and `gkmex75` is its only collaborator and admin.
- The first release used an interactive API token. That token is outside the
  automated design and will not be stored in GitHub.

## Decisions

### Release trigger

The workflow is invoked only for GitHub's `release.published` event. Its build
job proceeds only when the release tag begins with `gkmex-python-v`, so npm or
other future package releases in the same repository remain unaffected. It has
no `workflow_dispatch`, `push`, pull-request, or reusable-workflow trigger.

Python release tags use this contract:

```text
gkmex-python-v<project version>
```

For example, a package declaring `version = "1.1.0"` must be released with the
tag `gkmex-python-v1.1.0`. The build fails before artifact upload when the tag
suffix and `pyproject.toml` version differ.

### Workflow and environment identity

PyPI will trust exactly these GitHub OIDC claims:

```text
Owner:       gkmex75
Repository:  gkmex-developer-resources
Workflow:    publish-python.yml
Environment: pypi
```

The GitHub `pypi` environment requires approval from `gkmex75`. Self-review
must remain allowed because `gkmex75` is the repository's only collaborator;
preventing self-review would deadlock every release.

### Job separation

The top-level, non-reusable workflow has two jobs.

1. `build` checks out the release event's fully qualified ref and event SHA,
   validates the tag/version contract, runs all Python package tests, builds
   wheel and sdist, runs Twine metadata checks, and uploads the two files as a
   short-lived GitHub Actions artifact. It has no OIDC permission.
2. `publish` depends on `build`, enters the protected `pypi` environment,
   downloads only the built distributions, and invokes the official PyPA
   publishing action. Only this job receives `id-token: write`.

The publish job contains no checkout, build, test, shell, username, password,
API token, or repository secret step. Its only operational steps are artifact
download and PyPI publish.

### Dependency and action integrity

- Every third-party GitHub Action is pinned to a full commit SHA with its
  release tag recorded in a comment.
- Python release tooling is installed at explicit versions in the unprivileged
  build job, and the isolated PEP 517 backend is pinned exactly to
  `setuptools==84.0.0` in package metadata.
- `skip-existing` is not enabled. Duplicate or conflicting releases must fail
  visibly.
- PyPI attestations remain enabled through the official publish action's
  Trusted Publishing default.

## Workflow Data Flow

```text
GitHub Release published with a gkmex-python-v tag
  -> checkout the release event's fully qualified ref + event SHA
  -> validate tag suffix == pyproject version
  -> run Python tests
  -> build wheel + sdist
  -> Twine check
  -> upload GitHub artifact
  -> wait for gkmex75 approval on environment pypi
  -> mint short-lived PyPI credential through OIDC
  -> publish the exact artifact to project gkmex
```

The GitHub release target, package version, artifact contents, OIDC identity,
and PyPI project therefore remain bound to one release event.

## Failure Handling

- Non-Python release tag: skip both jobs; other package releases remain
  unaffected.
- Python tag/version mismatch: fail in `build`; no artifact and no OIDC
  credential.
- Python test, build, or Twine failure: fail in `build`; `publish` never starts.
- Missing environment approval: deployment remains waiting and nothing reaches
  PyPI.
- PyPI publisher-claim mismatch: short-lived token minting fails; no API-token
  fallback exists.
- Duplicate PyPI version: publish fails; immutable files are not skipped or
  replaced.

## Verification Strategy

Repository acceptance coverage will assert the workflow's security contract,
including its sole trigger, release-event ref/SHA checkout, version gate,
separated jobs, Python-tag job filter, artifact handoff, protected environment,
job-scoped OIDC permission, pinned actions, and absence of secrets or password
inputs.
The existing 35 Python tests and package artifact checks remain release gates.

Before merging:

- run the new workflow contract test red then green;
- run all Python package tests and npm regression tests;
- validate the workflow with `actionlint`;
- inspect the exact diff and credential scan.

After merging, without publishing a package:

- confirm GitHub recognizes and enables `publish-python.yml` on `main`;
- confirm the `pypi` environment requires `gkmex75` approval;
- add and visually verify the exact publisher identity on PyPI;
- confirm no PyPI credential exists in repository or environment secrets;
- do not create a test release or republish `1.0.0`.

Trusted Publishing cannot be exercised end to end without publishing a new
immutable version. The first live OIDC proof therefore belongs to the next
real Python release.

## Rollback

If configuration is wrong before the next release, remove the trusted
publisher from the PyPI `gkmex` Publishing settings and disable the GitHub
workflow. The already-published `1.0.0` files and the live SDK remain
unchanged. The project-scoped emergency token may be retained outside GitHub
for manual recovery, but it is never added to this workflow.

## References

- PyPI: adding a publisher to an existing project:
  <https://docs.pypi.org/trusted-publishers/adding-a-publisher/>
- PyPI Trusted Publishing security model:
  <https://docs.pypi.org/trusted-publishers/security-model/>
- PyPA publish action:
  <https://github.com/pypa/gh-action-pypi-publish>
