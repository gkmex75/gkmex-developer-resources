import tomllib
import unittest
from pathlib import Path

import gkmex
from gkmex import GkmexClient, GkmexError, __version__


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


class PackageTests(unittest.TestCase):
    def test_metadata_is_the_exact_public_package_contract(self):
        metadata = tomllib.loads(
            (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        project = metadata["project"]

        self.assertEqual(project["name"], "gkmex")
        self.assertEqual(project["version"], "1.0.0")
        self.assertEqual(project["requires-python"], ">=3.10")
        self.assertEqual(project["license"], "MIT")
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(project["scripts"], {"gkmex": "gkmex.cli:main"})
        self.assertEqual(
            metadata["tool"]["setuptools"],
            {"package-dir": {"": "src"}, "packages": {"find": {"where": ["src"]}}},
        )
        self.assertEqual(
            project["urls"]["Source"],
            "https://github.com/gkmex75/gkmex-developer-resources/tree/main/packages/gkmex-python",
        )
        self.assertEqual(
            project["urls"]["Documentation"],
            "https://gkmex.com/developers",
        )

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
