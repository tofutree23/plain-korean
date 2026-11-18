#!/usr/bin/env python3
"""Advisory Korean prose checks for Claude Code, built on the writing-plain-korean linter. Never blocks.

PostToolUse (Write|Edit|MultiEdit on a .md file): lint only the text the tool wrote, so old
text by other people does not trigger it, and hand the hits back to the model as context.
Agent-internal files (the Claude config directory, any path with a .claude part) and mostly
non-Korean text are skipped.

Stop: lint the reply that just ended. Save the hits for this session and show one line to
the user. The reply is not rewritten.

UserPromptSubmit: if the previous reply had hits, hand them to the model once, then forget them.
"""
import importlib.util
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINTER = ROOT / "skills" / "writing-plain-korean" / "scripts" / "lint_korean.py"
STATE = pathlib.Path(tempfile.gettempdir()) / "plain-korean-lint"
MIN_KOREAN = 0.3  # skip text whose letters are less than this share Hangul


def load_linter():
    spec = importlib.util.spec_from_file_location("lint_korean", LINTER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def state_file(session):
    return STATE / (re.sub(r"[^\w-]", "_", session or "default") + ".json")


def lintable(lint, text):
    return bool(text.strip()) and lint.korean_share(text) >= MIN_KOREAN


def written_text(tool_input):
    if "content" in tool_input:
        return tool_input.get("content") or ""
    if "new_string" in tool_input:
        return tool_input.get("new_string") or ""
    return "\n".join(e.get("new_string", "") for e in tool_input.get("edits") or [])


def skipped_path(path, cwd):
    if not path.endswith(".md"):
        return True
    p = pathlib.Path(cwd or ".", os.path.expanduser(path))
    config = pathlib.Path(os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude"))
    for form in {p.absolute(), p.resolve()}:
        if ".claude" in form.parts or form == config or config in form.parents:
            return True
    return False


def emit(event, context):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}},
                     ensure_ascii=False))


def post_tool_use(event, lint):
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if skipped_path(path, event.get("cwd")):
        return
    text = written_text(tool_input)
    if not lintable(lint, text):
        return
    hits = lint.lint(text)
    if not hits:
        return
    emit("PostToolUse",
         f"plain-korean: {pathlib.Path(path).name}에 방금 쓴 글에서 {len(hits)}건이 걸렸다(행 번호는 새로 쓴 부분 기준).\n"
         f"{lint.summary(hits)}\n"
         "writing-plain-korean 기준으로 고칠 것만 고친다. 업무 용어(예: 품질 판정)나 인용처럼 바꾸면 뜻이 달라지는 것은 그대로 둔다.")


def stop(event, lint):
    reply = event.get("last_assistant_message") or ""
    if not lintable(lint, reply):
        return
    hits = lint.lint(reply)
    if not hits:
        return
    STATE.mkdir(parents=True, exist_ok=True)
    state_file(event.get("session_id")).write_text(json.dumps(hits, ensure_ascii=False), encoding="utf-8")
    counts = {}
    for h in hits:
        counts[h["rule"]] = counts.get(h["rule"], 0) + 1
    detail = ", ".join(f"{k} {v}" for k, v in counts.items())
    print(json.dumps({"systemMessage": f"plain-korean: 답변에서 {len(hits)}건({detail}). 다음 답변에 반영합니다."},
                     ensure_ascii=False))


def user_prompt_submit(event, lint):
    f = state_file(event.get("session_id"))
    try:
        hits = json.loads(f.read_text(encoding="utf-8"))
        f.unlink()
    except (OSError, ValueError):
        return
    if hits:
        emit("UserPromptSubmit",
             f"plain-korean: 직전 답변에서 린터가 {len(hits)}건을 찾았다. 이번 답변에서는 같은 꼴을 피한다. "
             "직전 답변을 다시 쓰거나 이 안내를 사용자에게 언급하지 않는다.\n" + lint.summary(hits, limit=8))


def main():
    try:
        event = json.load(sys.stdin)
        lint = load_linter()
        name = event.get("hook_event_name", "")
        if name == "PostToolUse":
            post_tool_use(event, lint)
        elif name == "Stop":
            stop(event, lint)
        elif name == "UserPromptSubmit":
            user_prompt_submit(event, lint)
    except Exception:  # advisory hook: a crash must never block or loop the session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
