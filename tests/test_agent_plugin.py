import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin.json"
MCP = ROOT / "mcp.json"
SKILL = ROOT / "skills" / "gkmex-inventory" / "SKILL.md"
README = ROOT / "README.md"


class AgentPluginContractTests(unittest.TestCase):
    def test_portable_manifest_is_the_exact_agent_plugins_v1_identity(self):
        self.assertTrue(PLUGIN.exists())
        self.assertEqual(
            json.loads(PLUGIN.read_text()),
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
        self.assertTrue(MCP.exists())
        self.assertEqual(
            json.loads(MCP.read_text()),
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
            MCP.read_text(),
            re.compile(r'"(?:headers|env|token|password|secret|authorization|oauth)"', re.I),
        )

    def test_existing_skill_and_codex_contracts_remain_present(self):
        skill = SKILL.read_text()
        self.assertRegex(skill, r"\A---\s*\nname:\s*gkmex-inventory\s*\n")
        self.assertRegex(skill, r"description:\s*.+\n---\s*\n#\s+.+")
        self.assertTrue((ROOT / ".codex-plugin" / "plugin.json").exists())
        self.assertTrue((ROOT / ".mcp.json").exists())
        self.assertEqual(
            json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["gkmex-inventory"],
            {"type": "http", "url": "https://gkmex.com/mcp"},
        )

    def test_readme_distinguishes_portable_and_codex_entry_points(self):
        readme = README.read_text()
        for entry in (
            "## Portable Agent Plugin",
            "`plugin.json`",
            "`mcp.json`",
            "`skills/gkmex-inventory/SKILL.md`",
            "`.codex-plugin/plugin.json`",
            "`.mcp.json`",
            "Agent Plugins 1.0.0",
        ):
            self.assertIn(entry, readme)


if __name__ == "__main__":
    unittest.main()
