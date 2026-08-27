#!/usr/bin/env python3
"""極簡待辦清單 CLI：add <text> / list / done <n>。

狀態存在 .todo.json（可用環境變數 TODO_FILE 改路徑）。只用標準函式庫，Python 3.9 以上可跑。
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

USAGE = "用法：todo.py add <text> | list | done <n>"


def todo_path() -> Path:
    return Path(os.environ.get("TODO_FILE", ".todo.json"))


def load_items() -> List[Dict]:
    path = todo_path()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_items(items: List[Dict]) -> None:
    with todo_path().open("w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def cmd_add(text: str) -> int:
    if not text.strip():
        print("錯誤：內容不可為空", file=sys.stderr)
        return 1
    items = load_items()
    items.append({"text": text.strip(), "done": False})
    save_items(items)
    print("已新增 #{}: {}".format(len(items), text.strip()))
    return 0


def cmd_list() -> int:
    items = load_items()
    if not items:
        print("（清單是空的）")
        return 0
    for index, item in enumerate(items, start=1):
        mark = "x" if item["done"] else " "
        print("[{}] {}. {}".format(mark, index, item["text"]))
    return 0


def cmd_done(raw_number: str) -> int:
    items = load_items()
    number = parse_number(raw_number, len(items))
    if number is None:
        print("錯誤：編號不存在：{}".format(raw_number), file=sys.stderr)
        return 1
    items[number - 1]["done"] = True
    save_items(items)
    print("已完成 #{}: {}".format(number, items[number - 1]["text"]))
    return 0


def parse_number(raw: str, count: int) -> Optional[int]:
    try:
        number = int(raw)
    except ValueError:
        return None
    if number < 1 or number > count:
        return None
    return number


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(USAGE, file=sys.stderr)
        return 1
    command, rest = args[0], args[1:]
    if command == "add" and rest:
        return cmd_add(" ".join(rest))
    if command == "list" and not rest:
        return cmd_list()
    if command == "done" and len(rest) == 1:
        return cmd_done(rest[0])
    print(USAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
