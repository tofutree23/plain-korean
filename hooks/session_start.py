#!/usr/bin/env python3
"""SessionStart hook for Codex: print the short rule block from prompts/rules.md.

Codex runs only this hook, so the rules reach the model at the start of every session.
Claude Code does not use it: there the skill loads by its description and lint_hook.py
feeds back what it finds.
"""
import pathlib
import re
import sys

RULES = pathlib.Path(__file__).resolve().parent.parent / "prompts" / "rules.md"
FALLBACK = (
    "사람이 읽는 한국어는 회의에서 동료에게 말하듯 쓴다. 번역투 개념어는 풀어 쓰고, "
    "'A가 아니라 B' 꼴은 B만 쓰고, 사실을 더하지 않는 꾸미는 말은 지운다. em-dash와 가운뎃점은 쓰지 않는다."
)


def rule_block(text):
    m = re.search(r"<!-- rules:start -->\n(.*?)\n<!-- rules:end -->", text, flags=re.S)
    return m.group(1).strip() if m else ""


def main():
    try:
        block = rule_block(RULES.read_text(encoding="utf-8"))
    except OSError:
        block = ""
    sys.stdout.write("PLAIN KOREAN RULES\n\n" + (block or FALLBACK) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
