#!/usr/bin/env python3
"""Run the hooks the way Claude Code and Codex run them: JSON on stdin, a fresh process."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINT_HOOK = ROOT / "hooks" / "lint_hook.py"
SESSION_START = ROOT / "hooks" / "session_start.py"
LINTER = ROOT / "skills" / "writing-plain-korean" / "scripts" / "lint_korean.py"
BAD = "판정은 인증 서버가 하고, 화면이 아니라 role을 넘깁니다. 실제로 반영되었습니다."
GOOD = "테스트가 모두 통과했습니다. 다음 단계로 넘어갑니다."


def run(script, event, env=None):
    proc = subprocess.run([sys.executable, "-I", str(script)], input=json.dumps(event, ensure_ascii=False),
                          capture_output=True, text=True, env=env, timeout=20)
    return proc.returncode, proc.stdout


class LintHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ, TMPDIR=self.tmp.name, CLAUDE_CONFIG_DIR=str(pathlib.Path(self.tmp.name) / "config"))
        self.session = "test-" + pathlib.Path(self.tmp.name).name

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, path, text):
        return run(LINT_HOOK, {"hook_event_name": "PostToolUse", "cwd": self.tmp.name, "tool_name": "Edit",
                               "tool_input": {"file_path": path, "old_string": "x", "new_string": text}}, self.env)

    def test_markdown_edit_with_hits_returns_context(self):
        code, out = self.edit("docs/guide.md", BAD)
        self.assertEqual(code, 0)
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        for rule in ("concept_word", "contrast", "filler"):
            self.assertIn(rule, context)

    def test_clean_text_and_other_files_are_quiet(self):
        self.assertEqual(self.edit("docs/guide.md", GOOD), (0, ""))
        self.assertEqual(self.edit("src/app.ts", BAD), (0, ""))
        self.assertEqual(self.edit("docs/english.md", "The build passed and every test is green now."), (0, ""))

    def test_agent_internal_paths_are_skipped(self):
        self.assertEqual(self.edit("project/.claude/skills/x/SKILL.md", BAD), (0, ""))
        self.assertEqual(self.edit(self.env["CLAUDE_CONFIG_DIR"] + "/memory/note.md", BAD), (0, ""))

    def test_stop_saves_hits_and_next_prompt_gets_them_once(self):
        code, out = run(LINT_HOOK, {"hook_event_name": "Stop", "session_id": self.session,
                                    "last_assistant_message": BAD}, self.env)
        self.assertEqual(code, 0)
        self.assertIn("plain-korean", json.loads(out)["systemMessage"])
        prompt = {"hook_event_name": "UserPromptSubmit", "session_id": self.session, "prompt": "다음"}
        _, first = run(LINT_HOOK, prompt, self.env)
        self.assertIn("contrast", json.loads(first)["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(run(LINT_HOOK, prompt, self.env), (0, ""))

    def test_clean_reply_saves_nothing(self):
        self.assertEqual(run(LINT_HOOK, {"hook_event_name": "Stop", "session_id": self.session,
                                         "last_assistant_message": GOOD}, self.env), (0, ""))

    def test_bad_input_never_fails(self):
        proc = subprocess.run([sys.executable, "-I", str(LINT_HOOK)], input="not json",
                              capture_output=True, text=True, env=self.env, timeout=20)
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))


class SessionStartTest(unittest.TestCase):
    def test_prints_rule_block_only(self):
        proc = subprocess.run([sys.executable, "-I", str(SESSION_START)], capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("A가 아니라 B", proc.stdout)
        self.assertNotIn("rules:start", proc.stdout)
        self.assertNotIn("붙여 넣는다", proc.stdout)


class VersionTest(unittest.TestCase):
    def test_every_manifest_names_the_same_version(self):
        versions = {
            "claude plugin": json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"],
            "claude marketplace": json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())["plugins"][0]["version"],
            "codex plugin": json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())["version"],
        }
        skill = (ROOT / "skills" / "writing-plain-korean" / "SKILL.md").read_text(encoding="utf-8")
        import re
        versions["skill"] = re.search(r'version: "([^"]+)"', skill).group(1)
        self.assertEqual(len(set(versions.values())), 1, versions)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## {versions['skill']}", changelog)


class LinterSelfTest(unittest.TestCase):
    def test_self_test_passes(self):
        proc = subprocess.run([sys.executable, "-I", str(LINTER), "--self-test"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_repository_prose_passes_its_own_linter(self):
        files = [ROOT / "README.md", ROOT / "prompts" / "rules.md",
                 ROOT / "skills" / "writing-plain-korean" / "SKILL.md"]
        proc = subprocess.run([sys.executable, "-I", str(LINTER), *map(str, files)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    unittest.main()
