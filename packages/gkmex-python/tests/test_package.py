import unittest
from pathlib import Path

import gkmex
from gkmex import GkmexClient, GkmexError, __version__


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


def toml_section(document, name):
    marker = f"[{name}]\n"
    start = document.index(marker) + len(marker)
    remainder = document[start:]
    end = remainder.find("\n[")
    return remainder if end == -1 else remainder[:end]


class PackageTests(unittest.TestCase):
    def test_metadata_is_the_exact_public_package_contract(self):
        document = (PACKAGE_ROOT / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        project = toml_section(document, "project")
        build_system = toml_section(document, "build-system")
        scripts = toml_section(document, "project.scripts")
        urls = toml_section(document, "project.urls")
        setuptools = toml_section(document, "tool.setuptools")
        packages = toml_section(document, "tool.setuptools.packages.find")

        for field in (
            'name = "gkmex"',
            'version = "1.0.0"',
            'requires-python = ">=3.10"',
            'license = "MIT"',
            "dependencies = []",
        ):
            self.assertIn(field, project)
        self.assertNotIn('"License ::', project)
        self.assertEqual(
            build_system.strip(),
            'requires = ["setuptools==84.0.0"]\n'
            'build-backend = "setuptools.build_meta"',
        )
        self.assertEqual(scripts.strip(), 'gkmex = "gkmex.cli:main"')
        self.assertIn(
            'Source = "https://github.com/gkmex75/gkmex-developer-resources/tree/main/packages/gkmex-python"',
            urls,
        )
        self.assertIn(
            'Documentation = "https://gkmex.com/developers"',
            urls,
        )
        self.assertEqual(setuptools.strip(), 'package-dir = { "" = "src" }')
        self.assertEqual(packages.strip(), 'where = ["src"]')

    def test_public_import_surface_and_version_are_stable(self):
        self.assertEqual(__version__, "1.0.0")
        self.assertIs(gkmex.GkmexClient, GkmexClient)
        self.assertIs(gkmex.GkmexError, GkmexError)
        self.assertEqual(
            gkmex.__all__,
            ["GkmexClient", "GkmexError", "__version__"],
        )

    def test_package_license_matches_the_repository_license(self):
        self.assertEqual(
            (PACKAGE_ROOT / "LICENSE").read_bytes(),
            (REPOSITORY_ROOT / "LICENSE").read_bytes(),
        )

    def test_source_distribution_manifest_includes_complete_tests(self):
        manifest = (PACKAGE_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertIn("recursive-include tests *.py", manifest.splitlines())

    def test_readme_documents_sdk_cli_and_public_data_boundaries(self):
        readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
        required = (
            "pip install gkmex",
            "from gkmex import GkmexClient",
            "client.list_cranes",
            "client.get_crane",
            "client.compare_cranes",
            "gkmex list --brand Liebherr --limit 5",
            "gkmex get PUBLIC_ID",
            "gkmex compare PUBLIC_ID PUBLIC_ID",
            "zero-auth",
            "read-only",
            "price_eur",
            "None",
            "POA",
            "not a reservation",
            "final specifications and availability",
            'crane["url"]',
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, readme)

        forbidden = (
            "guaranteed availability",
            "reserves the crane",
            "write API",
            "GKMEX_BASE_URL",
        )
        for fragment in forbidden:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, readme)


if __name__ == "__main__":
    unittest.main()
