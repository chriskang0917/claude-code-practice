#!/usr/bin/env python3
"""PreToolUse hook：不准從 Claude session 執行 git push（「push-gate」）。

Claude Code 會把 JSON 送到 stdin（tool_name、tool_input.command）。
擋下＝stderr 印原因、exit 2；其他情況一律 exit 0，
但每條放行／跳過路徑都先在 stderr 留一行「[push-gate] skip: <原因>」，不靜默吞例外。
"""
import json
import re
import sys

BLOCK_MSG = "已擋下：這個 repo 不從 Claude session push。請停下來回報使用者，不要換別的指令再試。"
# 同一段管線裡同時出現 git 與 push 就擋（含 git push --tags、cd x && git push）；寧可誤擋，不要漏擋。
PUSH = re.compile(r"\bgit\b[^|;&]*\bpush\b")


def skip(reason: str) -> int:
    print("[push-gate] skip: " + reason, file=sys.stderr)
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return skip("stdin 不是合法 JSON")
    if not isinstance(payload, dict):
        return skip("payload 不是物件")
    command = (payload.get("tool_input") or {}).get("command")
    if not command:
        return skip("tool_input 沒有 command")
    if not PUSH.search(command):
        return skip("不是 git push：" + command.splitlines()[0][:60])
    print(BLOCK_MSG, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
