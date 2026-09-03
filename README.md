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

`tests/test_todo.py` 測 CLI 本身，`tests/test_solutions.py` 測 `solutions/` 底下各章的參考解答，`tests/test_capstone_check.py` 測期末作業的驗收腳本。
其中兩個測試會拿教材站的原始碼比對（找不到 `../site` 時顯示 `skipped=2`，單獨 clone 這個 repo 時是正常的）；
另外兩個會用 `node` 以 stub 執行 workflow 腳本，沒有 `node` 也是跳過。

## 期末作業驗收

做完教材的期末作業（交付 v1.0.0）之後，在 repo 根目錄：

```bash
make capstone        # 同 python3 capstone/check.py
```

它會逐項檢查你自己寫的 hook／skill／subagent／workflow 的形狀與行為、`remove` 指令、merge 節點、CHANGELOG 與 tag，全過印 `CAPSTONE_OK`。
沒過的項目會印原因與提示；修好再跑一次。參考解答在 `solutions/capstone/`。

## 怎麼重置

每章練習開始前把 repo 拉回乾淨的 `main`：

```bash
git merge --abort 2>/dev/null; git checkout -f main && git reset --hard origin/main && git clean -fd && git worktree prune
```

它會丟掉：未 commit 的改動、未追蹤的檔案（含你自己貼進 `.claude/` 的 agents／skills／workflows／hooks、練習產出的 `SPEC.md`、`CHANGELOG.md`）。
期末作業還會留下 tag 與兩個 worktree，重做前多清這些：`git tag -d v1.0.0; for n in feat docs; do git worktree remove --force .claude/worktrees/$n; git branch -D worktree-$n; done`（教材的步驟 0 已含這段）。

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
solutions/capstone/     期末作業的參考解答（SPEC、四份工具檔、remove.patch、提示詞）
capstone/check.py       期末作業驗收腳本（make capstone）
```
