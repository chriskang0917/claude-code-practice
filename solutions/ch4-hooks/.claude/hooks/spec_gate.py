#!/usr/bin/env python3
"""PreToolUse hook：src/ 底下沒有 SPEC.md 就不准改（去機密的「spec-gate」概念版）。

Claude Code 會把 JSON 送到 stdin（tool_name、tool_input.file_path、cwd）。
擋下＝stderr 印原因、exit 2；其他情況一律 exit 0，
但每條放行／跳過路徑都先在 stderr 留一行「[spec-gate] skip: <原因>」，不靜默吞例外。
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

BLOCK_MSG = "已擋下：src/ 受 SPEC 保護。請停止並回報使用者，不要自行建立 SPEC.md。"


def skip(reason: str) -> int:
    print("[spec-gate] skip: " + reason, file=sys.stderr)
    return 0


def find_root(start: Path) -> Optional[Path]:
    """從 start 往上找第一個含 .git 或 .claude 的目錄。"""
    for candidate in [start] + list(start.parents):
        if (candidate / ".git").exists() or (candidate / ".claude").exists():
            return candidate
    return None


def read_payload() -> Optional[dict]:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def gate(payload: dict) -> int:
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path:
        return skip("tool_input 沒有 file_path")
    start = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
    if not start:
        return skip("沒有 CLAUDE_PROJECT_DIR 也沒有 cwd")
    root = find_root(Path(start).resolve())
    if root is None:
        return skip("往上找不到含 .git 或 .claude 的目錄")
    try:
        rel = Path(file_path).resolve().relative_to(root).as_posix()
    except ValueError:
        return skip("檔案不在專案底下：" + str(file_path))
    if not rel.startswith("src/"):
        return skip("不在 src/ 底下：" + rel)
    if (root / "SPEC.md").exists():
        return skip("SPEC.md 存在，放行 " + rel)
    print(BLOCK_MSG, file=sys.stderr)
    return 2


def main() -> int:
    payload = read_payload()
    if payload is None:
        return skip("stdin 不是合法 JSON")
    return gate(payload)


if __name__ == "__main__":
    sys.exit(main())
