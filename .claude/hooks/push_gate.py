#!/usr/bin/env python3
"""PreToolUse hook：不准從 Claude session 執行 git push。"""
import json
import sys


BLOCK_MSG = (
    "已擋下：這個 repo 的 push 一律由人在自己的終端機執行，不從 Claude session 發出。"
    "請停下來把情況回報給使用者，不要改寫指令再試一次。"
)


def skip(reason):
    print("[push-gate] skip: " + reason, file=sys.stderr)
    return 0


def main():
    try:
        payload = json.load(sys.stdin)   # Claude Code 從 stdin 餵進來的 JSON
    except (ValueError, OSError):
        return skip("stdin 不是合法 JSON")
    command = (payload.get("tool_input") or {}).get("command") if isinstance(payload, dict) else None
    if not command:
        return skip("tool_input 沒有 command")
    if "git" in command and "push" in command:
        print(BLOCK_MSG, file=sys.stderr)
        return 2
    return skip("不是 git push")


if __name__ == "__main__":
    sys.exit(main())
