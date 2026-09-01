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
