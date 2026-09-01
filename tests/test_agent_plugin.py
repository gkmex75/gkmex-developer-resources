import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin.json"
MCP = ROOT / "mcp.json"
SKILL = ROOT / "skills" / "gkmex-inventory" / "SKILL.md"
README = ROOT / "README.md"

CODEX_PLUGIN_SHA256 = "9a925b9c22b5786e5077adb5f0de4751d054ee87e5685abb1d7ff1e2da71e104"
CODEX_MCP_SHA256 = "52ae85607a63fda2a58416e246277a4b7258dc4f0dd61ee6badff6ac86aa4e89"
SKILL_SHA256 = "a299d9a47f9bb2bd29352f626e8d9a98db39ccaf1f1885c372666ec93e6192d2"


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

    def test_readme_distinguishes_portable_and_codex_entry_points(self):
        readme = README.read_text(encoding="utf-8")
        portable_block = """## Portable Agent Plugin

This repository root conforms to Agent Plugins 1.0.0 and packages the existing public Gkmex integration surfaces without credentials or write access.

- `plugin.json` — portable plugin identity and metadata
- `skills/gkmex-inventory/SKILL.md` — inventory search and inspection skill
- `mcp.json` — portable Streamable HTTP configuration for `https://gkmex.com/mcp`

The `.codex-plugin/plugin.json` and `.mcp.json` files remain available for Codex-compatible clients; they do not replace the portable root files.
"""
        self.assertIn(portable_block, readme)


if __name__ == "__main__":
    unittest.main()
