"""Checks that every plugin and marketplace manifest agrees. Run: python3 -m unittest discover -s tests"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS = ROOT / "plugins"

AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
AGENT_PLUGINS_MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
AGENT_PLUGINS_KEYS = {
    "$schema", "name", "version", "description", "author", "homepage", "repository", "license", "keywords", "extensions",
}
NAME = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?$")

# Manifest path within a plugin -> harnesses that read it.
PLUGIN_MANIFESTS = {
    "plugin.json": "Agent Plugins (Copilot, Cursor, Codex)",
    ".claude-plugin/plugin.json": "Claude Code",
    ".codex-plugin/plugin.json": "Codex",
    ".cursor-plugin/plugin.json": "Cursor",
    "gemini-extension.json": "Gemini CLI",
}
MARKETPLACES = {
    "claude": ".claude-plugin/marketplace.json",
    "copilot": ".github/plugin/marketplace.json",
    "cursor": ".cursor-plugin/marketplace.json",
    "codex": ".agents/plugins/marketplace.json",
}


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def plugin_dirs() -> list[Path]:
    if not PLUGINS.is_dir():
        return []
    return sorted(p for p in PLUGINS.iterdir() if p.is_dir())


def frontmatter_name(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None
    name = re.search(r"^name:\s*(\S+)\s*$", match.group(1), re.MULTILINE)
    return name.group(1) if name else None


def resolve_source(harness: str, marketplace: dict, entry: dict) -> Path:
    """Resolve a marketplace entry's source to a directory, using each harness's own rules."""
    source = entry["source"]
    if harness == "codex":
        assert isinstance(source, dict) and source.get("source") == "local", f"codex source must be local: {source!r}"
        source = source["path"]
    if isinstance(source, dict):
        source = source["path"]
    if harness == "claude":
        assert source.startswith("./"), f"Claude Code requires a ./ prefix: {source!r}"
    if harness == "cursor" and "/" not in source:
        source = f"{marketplace.get('metadata', {}).get('pluginRoot', '.')}/{source}"
    assert ".." not in Path(source).parts, f"source escapes the marketplace root: {source!r}"
    return (ROOT / source).resolve()


class PluginManifestTests(unittest.TestCase):
    def test_plugins_exist(self):
        if not plugin_dirs():
            self.skipTest("no plugins under plugins/ yet")

    def test_every_manifest_is_present_and_agrees(self):
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                manifests = {}
                for rel, harness in PLUGIN_MANIFESTS.items():
                    path = plugin / rel
                    self.assertTrue(path.is_file(), f"{plugin.name}: missing {rel} for {harness}")
                    manifests[rel] = load(path)
                for field in ("name", "version", "description"):
                    values = {rel: m.get(field) for rel, m in manifests.items()}
                    self.assertEqual(len(set(values.values())), 1, f"{plugin.name}: {field} differs: {values}")
                self.assertEqual(manifests["plugin.json"]["name"], plugin.name, "plugin name must match its directory")
                self.assertRegex(plugin.name, NAME)

    def test_agent_plugins_manifest_is_metadata_only(self):
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                manifest = load(plugin / "plugin.json")
                self.assertEqual(manifest.get("$schema"), AGENT_PLUGINS_SCHEMA)
                self.assertLessEqual(set(manifest), AGENT_PLUGINS_KEYS, "Agent Plugins 1.0 rejects component path fields")
                self.assertLessEqual(set(manifest.get("author", {})), {"name", "email", "url"})

    def test_every_plugin_ships_skills_named_after_their_folders(self):
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                skills = sorted((plugin / "skills").glob("*/SKILL.md"))
                if not skills:
                    self.skipTest(f"{plugin.name}: no skills/*/SKILL.md yet")
                for skill in skills:
                    self.assertEqual(frontmatter_name(skill), skill.parent.name, f"{skill}: frontmatter name mismatch")

    def test_standalone_skills_are_named_after_their_folders_and_unique(self):
        # Root skills/ holds skills installed one by one with the skills CLI, which installs them unnamespaced next to plugin skills.
        plugin_skills = {s.parent.name for p in plugin_dirs() for s in (p / "skills").glob("*/SKILL.md")}
        for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
            with self.subTest(skill=skill.parent.name):
                self.assertEqual(frontmatter_name(skill), skill.parent.name, f"{skill}: frontmatter name mismatch")
                self.assertNotIn(skill.parent.name, plugin_skills, "a plugin already ships a skill with this name")

    def test_skill_names_do_not_repeat_the_plugin_name(self):
        # Harnesses namespace plugin skills by plugin, so git/skills/branch is already seen as git:branch.
        for plugin in plugin_dirs():
            for skill in (plugin / "skills").glob("*/SKILL.md"):
                with self.subTest(skill=f"{plugin.name}:{skill.parent.name}"):
                    self.assertFalse(skill.parent.name.startswith(f"{plugin.name}-"), "drop the plugin-name prefix")

    def test_mcp_servers_agree_across_harness_files(self):
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                portable, claude = plugin / "mcp.json", plugin / ".mcp.json"
                gemini = load(plugin / "gemini-extension.json").get("mcpServers", {})
                if not (portable.exists() or claude.exists() or gemini):
                    continue
                self.assertTrue(portable.is_file() and claude.is_file(), f"{plugin.name}: need both mcp.json and .mcp.json")
                self.assertEqual(load(portable).get("$schema"), AGENT_PLUGINS_MCP_SCHEMA)
                names = {
                    "mcp.json": set(load(portable)["mcpServers"]),
                    ".mcp.json": set(load(claude)["mcpServers"]),
                    "gemini-extension.json": set(gemini),
                }
                self.assertEqual(len({frozenset(n) for n in names.values()}), 1, f"{plugin.name}: {names}")

    def test_lsp_servers_agree_across_harness_files(self):
        # Claude Code reads .lsp.json (extensionToLanguage); Copilot CLI reads com.github.copilot/lsp.json (fileExtensions).
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                claude, copilot = plugin / ".lsp.json", plugin / "com.github.copilot" / "lsp.json"
                if not (claude.exists() or copilot.exists()):
                    continue
                self.assertTrue(claude.is_file() and copilot.is_file(),
                                f"{plugin.name}: need both .lsp.json and com.github.copilot/lsp.json")
                # A server may be a plain command, or a launcher script: `sh -c SCRIPT` for Claude Code, which has no
                # shell option, and the same SCRIPT in Copilot's `bash` field (its `powershell` field covers Windows).
                def claude_launch(s):
                    args = s.get("args", [])
                    return ("script", args[1]) if s["command"] == "sh" and args[:1] == ["-c"] else (s["command"], args)

                def copilot_launch(s):
                    if "bash" in s:
                        self.assertIn("powershell", s, f"{plugin.name}: a bash launcher needs a powershell twin for Windows")
                        return ("script", s["bash"])
                    return (s["command"], s.get("args", []))

                claude_servers = {name: (claude_launch(s), s["extensionToLanguage"]) for name, s in load(claude).items()}
                copilot_servers = {
                    name: (copilot_launch(s), s["fileExtensions"]) for name, s in load(copilot)["lspServers"].items()
                }
                self.assertEqual(claude_servers, copilot_servers)

    def test_no_shared_hooks_file(self):
        # Claude Code, Codex, Cursor, and Gemini CLI all read hooks/hooks.json with different event names.
        for plugin in plugin_dirs():
            with self.subTest(plugin=plugin.name):
                self.assertFalse((plugin / "hooks" / "hooks.json").exists(), "use a per-harness hooks file instead")


class MarketplaceTests(unittest.TestCase):
    def test_every_marketplace_lists_every_plugin(self):
        expected = {p.name: p.resolve() for p in plugin_dirs()}
        names = set()
        for harness, rel in MARKETPLACES.items():
            with self.subTest(marketplace=rel):
                path = ROOT / rel
                self.assertTrue(path.is_file(), f"missing {rel}")
                marketplace = load(path)
                names.add(marketplace["name"])
                entries = {e["name"]: resolve_source(harness, marketplace, e) for e in marketplace["plugins"]}
                self.assertEqual(entries, expected)
        self.assertEqual(len(names), 1, f"marketplace names differ: {names}")

    def test_marketplace_entries_match_plugin_descriptions(self):
        for harness, rel in MARKETPLACES.items():
            for entry in load(ROOT / rel)["plugins"]:
                with self.subTest(marketplace=rel, plugin=entry["name"]):
                    manifest = load(PLUGINS / entry["name"] / "plugin.json")
                    if "description" in entry:
                        self.assertEqual(entry["description"], manifest["description"])
                    if "version" in entry:
                        self.assertNotEqual(harness, "claude", "Claude Code warns when an entry repeats plugin.json version")
                        self.assertEqual(entry["version"], manifest["version"])

    def test_owner_is_set(self):
        for rel in ("claude", "copilot", "cursor"):
            with self.subTest(marketplace=MARKETPLACES[rel]):
                self.assertTrue(load(ROOT / MARKETPLACES[rel])["owner"]["name"])

    def test_codex_entries_have_policy_and_category(self):
        for entry in load(ROOT / MARKETPLACES["codex"])["plugins"]:
            with self.subTest(plugin=entry["name"]):
                self.assertIn(entry["policy"]["installation"], {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"})
                self.assertTrue(entry["category"])


if __name__ == "__main__":
    unittest.main()
