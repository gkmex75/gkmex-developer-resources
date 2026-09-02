import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin.json"
MCP = ROOT / "mcp.json"
SKILL = ROOT / "skills" / "gkmex-inventory" / "SKILL.md"
COMPARISON_SKILL = (
    ROOT / "skills" / "gkmex-crane-comparison" / "SKILL.md"
)
API_SKILL = ROOT / "skills" / "gkmex-api-integration" / "SKILL.md"
COMPARISON_DESCRIPTION = (
    "Use when comparing two to five currently published Gkmex cranes, "
    "evaluating a shortlist against user-supplied priorities, or deciding "
    "which listing facts need commercial confirmation."
)
API_DESCRIPTION = (
    "Use when building or troubleshooting an application that consumes Gkmex's "
    "public crane inventory through REST, the official JavaScript SDK, or the "
    "Python SDK."
)
README = ROOT / "README.md"

CODEX_PLUGIN_SHA256 = "9a925b9c22b5786e5077adb5f0de4751d054ee87e5685abb1d7ff1e2da71e104"
CODEX_MCP_SHA256 = "52ae85607a63fda2a58416e246277a4b7258dc4f0dd61ee6badff6ac86aa4e89"
SKILL_SHA256 = "a299d9a47f9bb2bd29352f626e8d9a98db39ccaf1f1885c372666ec93e6192d2"
COMPARISON_SHA256 = "8ca224019c41b17ffcbc083eab9caf8562681ac2b60016327771b1c5169b9870"


class AgentPluginContractTests(unittest.TestCase):
    def test_portable_manifest_is_the_exact_agent_plugins_v1_identity(self):
        self.assertTrue(PLUGIN.is_file(), PLUGIN)
        self.assertEqual(
            json.loads(PLUGIN.read_text(encoding="utf-8")),
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                "name": "gkmex-developer-resources",
                "version": "0.1.0",
                "description": "Portable public, zero-auth, read-only access to Gkmex used-crane inventory through an Agent Skill and MCP server.",
                "author": {"name": "Gkmex Cranes", "url": "https://gkmex.com"},
                "homepage": "https://gkmex.com/developers",
                "repository": "https://github.com/gkmex75/gkmex-developer-resources",
                "license": "MIT",
                "keywords": ["gkmex", "cranes", "inventory", "mcp", "agent-skills", "npm", "pypi"],
            },
        )

    def test_portable_mcp_config_is_one_public_streamable_http_server(self):
        self.assertTrue(MCP.is_file(), MCP)
        self.assertEqual(
            json.loads(MCP.read_text(encoding="utf-8")),
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
                "mcpServers": {
                    "gkmex-inventory": {
                        "type": "streamable-http",
                        "url": "https://gkmex.com/mcp",
                    }
                },
            },
        )
        self.assertNotRegex(
            MCP.read_text(encoding="utf-8"),
            re.compile(r'"(?:headers|env|token|password|secret|authorization|oauth)"', re.I),
        )

    def test_existing_skill_and_codex_contracts_remain_present(self):
        self.assertTrue(SKILL.is_file(), SKILL)
        skill_bytes = SKILL.read_bytes()
        self.assertEqual(hashlib.sha256(skill_bytes).hexdigest(), SKILL_SHA256)
        skill = SKILL.read_text(encoding="utf-8")
        self.assertRegex(
            skill,
            r"\A---\n"
            r"name: gkmex-inventory\n"
            r"description: Find and inspect currently published Gkmex used mobile and crawler cranes through the official public read-only API or MCP server\.\n"
            r"---\n\n"
            r"# Gkmex inventory\n",
        )
        codex_plugin = ROOT / ".codex-plugin" / "plugin.json"
        self.assertTrue(codex_plugin.is_file(), codex_plugin)
        self.assertEqual(hashlib.sha256(codex_plugin.read_bytes()).hexdigest(), CODEX_PLUGIN_SHA256)
        codex_manifest = json.loads(codex_plugin.read_text(encoding="utf-8"))
        self.assertEqual(codex_manifest["skills"], "./skills/")
        self.assertEqual(codex_manifest["mcpServers"], "./.mcp.json")
        self.assertEqual(
            set(codex_manifest),
            {"name", "version", "description", "author", "skills", "mcpServers", "interface"},
        )
        codex_mcp = ROOT / ".mcp.json"
        self.assertTrue(codex_mcp.is_file(), codex_mcp)
        self.assertEqual(hashlib.sha256(codex_mcp.read_bytes()).hexdigest(), CODEX_MCP_SHA256)
        self.assertEqual(
            json.loads(codex_mcp.read_text(encoding="utf-8"))["mcpServers"]["gkmex-inventory"],
            {"type": "http", "url": "https://gkmex.com/mcp"},
        )

    def test_crane_comparison_skill_is_portable_and_discoverable(self):
        self.assertEqual(
            sorted(
                path.parent.name
                for path in (ROOT / "skills").glob("*/SKILL.md")
            ),
            ["gkmex-api-integration", "gkmex-crane-comparison", "gkmex-inventory"],
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

    def test_api_integration_skill_is_portable_and_discoverable(self):
        self.assertTrue(API_SKILL.is_file(), API_SKILL)
        skill = API_SKILL.read_text(encoding="utf-8")
        self.assertTrue(
            skill.startswith(
                "---\n"
                "name: gkmex-api-integration\n"
                "description: "
                + API_DESCRIPTION
                + "\n---\n\n# Gkmex API integration\n"
            )
        )
        self.assertEqual(
            hashlib.sha256(SKILL.read_bytes()).hexdigest(), SKILL_SHA256
        )
        self.assertEqual(
            hashlib.sha256(COMPARISON_SKILL.read_bytes()).hexdigest(),
            COMPARISON_SHA256,
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
            "Build a compact comparison table.",
            "Include the returned official `url` for every crane.",
            "Mark other absent values as unknown.",
            "recommend conditionally using only those priorities",
            "Explain ties",
            "do not name a winner",
            "`price_eur: null` means `POA`",
            "final availability",
        ):
            self.assertIn(required, skill, required)
        self.assertNotIn("`compare_cranes`", skill)
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
        api_path = "skills/gkmex-api-integration/SKILL.md"
        self.assertEqual(portable_section.count(comparison_path), 1)
        self.assertEqual(integration_section.count(comparison_path), 1)
        self.assertEqual(portable_section.count(api_path), 1)
        self.assertEqual(integration_section.count(api_path), 1)

    def test_readme_distinguishes_portable_and_codex_entry_points(self):
        readme = README.read_text(encoding="utf-8")
        portable_block = """## Portable Agent Plugin

This repository root conforms to Agent Plugins 1.0.0 and packages the existing public Gkmex integration surfaces without credentials or write access.

- `plugin.json` — portable plugin identity and metadata
- `skills/gkmex-inventory/SKILL.md` — inventory search and inspection skill
- `skills/gkmex-crane-comparison/SKILL.md` — shortlist comparison skill
- `skills/gkmex-api-integration/SKILL.md` — API and SDK integration skill
- `mcp.json` — portable Streamable HTTP configuration for `https://gkmex.com/mcp`

The `.codex-plugin/plugin.json` and `.mcp.json` files remain available for Codex-compatible clients; they do not replace the portable root files.
"""
        self.assertIn(portable_block, readme)


if __name__ == "__main__":
    unittest.main()
