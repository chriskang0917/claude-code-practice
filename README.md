# claude-code-practice

Claude Code 進階功能練習用的迷你 repo：一個純 stdlib 的 Python 待辦清單 CLI，加上測試。
它只是練習場，程式本身刻意簡單，重點是讓你在上面練 worktree、workflow、subagent、hooks、skills。

## 需求

- Python 3.9 以上（只用標準函式庫，不用裝任何套件）
- git

## 怎麼跑

```bash
python3 src/todo.py add "買牛奶"
python3 src/todo.py list
python3 src/todo.py done 1
```

狀態存在目前目錄的 `.todo.json`（已列在 `.gitignore`）；想換位置設環境變數 `TODO_FILE=/path/to/file.json`。

## 怎麼測

```bash
python3 -m unittest -v
```

`tests/test_todo.py` 測 CLI 本身，`tests/test_solutions.py` 測 `solutions/` 底下各章的參考解答。

## 怎麼重置

每章練習開始前把 repo 拉回乾淨的 `main`：

```bash
git merge --abort 2>/dev/null; git checkout -f main && git reset --hard origin/main && git clean -fd && git worktree prune
```

這會丟掉你未 commit 的改動與未追蹤檔案（含你自己貼進 `.claude/` 的檔案），這正是重置的目的。

## 目錄

```
src/todo.py             CLI 本體
tests/                  unittest
.claude/                練習時你會在這裡放 agents / skills / workflows / hooks（目前只有佔位檔）
solutions/chN-*/        各章參考解答，練習卡住時對照用
```
