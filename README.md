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
其中一個測試會拿教材站的原始碼比對（找不到 `../site` 時顯示 `skipped=1`，單獨 clone 這個 repo 時是正常的）；
另一個會用 `node` 以 stub 執行 workflow 腳本，沒有 `node` 也是跳過。

## 怎麼重置

每章練習開始前把 repo 拉回乾淨的 `main`：

```bash
git merge --abort 2>/dev/null; git checkout -f main && git reset --hard origin/main && git clean -fd && git worktree prune
```

它會丟掉：未 commit 的改動、未追蹤的檔案（含你自己貼進 `.claude/` 的 agents／skills／workflows／hooks、練習產出的 `SPEC.md`、`CHANGELOG.md`）。

它**不會**動被 `.gitignore` 忽略的檔案（`git clean -fd` 沒有 `-x`），所以這些會留著：

| 留下的檔案 | 影響 | 想清掉 |
| --- | --- | --- |
| `.todo.json` | `python3 src/todo.py list` 會顯示上次的待辦 | `rm -f .todo.json` |
| `.claude/settings.local.json` | 你核准過的權限規則；留著沒壞處 | 通常不用 |
| `.claude/worktrees/` | 第 5 章選 keep 留下的 worktree；`git worktree prune` 只清已刪目錄的紀錄 | `git worktree remove .claude/worktrees/<name>` |
| `__pycache__/` | 無 | 不用 |

`make reset` 是同一行；`make clean-state` 只精確刪 `.todo.json` 與 `__pycache__/`，不碰其他 worktree。

## 目錄

```
src/todo.py             CLI 本體
tests/                  unittest
.claude/                練習時你會在這裡放 agents / skills / workflows / hooks（目前只有佔位檔）
solutions/chN-*/        各章參考解答，練習卡住時對照用
```
