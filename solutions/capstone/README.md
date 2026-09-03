# 期末作業：交付 todo CLI v1.0.0——參考解答

教材的期末作業**不給檔案貼**，只給規格；這裡是四份工具檔的參考寫法、兩個 worktree 的提示詞全文、`remove` 指令的參考實作，卡住時對照用。
驗收腳本（`python3 capstone/check.py`／`make capstone`）檢查的是形狀與行為，不是逐位元組比對——你的版本跟這裡長得不一樣沒關係，過驗收就是過。

## 檔案

| 檔案 | 對應章節 | 驗收看什麼 |
| --- | --- | --- |
| `SPEC.md` | — | 教材貼給你的規格原文（feat／docs 兩個 session 都照它做） |
| `.claude/settings.json` ＋ `.claude/hooks/push_gate.py` | 第 4 章 | matcher 是 `Bash`（settings.json 另有 `worktree.baseRef: head`，讓 `--worktree` 從本機 HEAD 長）；`git push`（含 `--tags`、`cd x && git push`）→ exit 2 且 stderr 含「已擋下」；`git status`、`echo push`、壞 JSON → exit 0 |
| `.claude/skills/release/SKILL.md` | 第 1 章 | `name: release`、`argument-hint`、`disable-model-invocation: true`；正文有 `$ARGUMENTS`、先跑 unittest、寫 `CHANGELOG.md`、`git tag`、不 push |
| `.claude/agents/doc-checker.md` | 第 2 章 | `name: doc-checker`、`tools` 只有 Read／Grep／Glob；正文對照 `src/todo.py` 與 `README.md`、回報附行號 |
| `.claude/workflows/ship-check.js` | 第 3 章 | `meta.name` 是 `ship-check`、≥2 站、`parallel` 收 thunk、≥2 個 schema、`.filter(Boolean)`、`log`、`return`；node stub 跑得完 |
| `remove.patch` | 第 5 章（feat worktree） | `remove <n>` 與兩個測試的參考實作：`git apply solutions/capstone/remove.patch` |

## 流程（與教材相同）

1. 重置到乾淨的 `main`，貼 `SPEC.md`，寫四份工具檔，**先 commit**（worktree 從 main 長出來，沒 commit 的檔案帶不過去）：

   ```bash
   git add -A && git commit -m "chore: release 工具鏈與 remove 規格"
   ```

2. `claude --worktree` 預設從 `origin/main` 長，本機沒 push 的工具鏈不會在裡面；`settings.json` 的 `worktree.baseRef: head` 讓它改從本機 HEAD 長（沒設的備案：先 `git worktree add .claude/worktrees/feat -b worktree-feat main`，同名 `--worktree` 會直接進既有的）。終端機 A：`claude --worktree feat`，開好先 `!ls SPEC.md .claude/hooks/` 確認，再整段貼：

   ```text
   讀 SPEC.md，只改 src/todo.py 與 tests/test_todo.py，完成「新指令 remove」與「測試」兩節，不要動 README；python3 -m unittest tests.test_todo -v 全過之後，用訊息「feat: add remove command」commit，不要 push
   ```

3. 終端機 B：`claude --worktree docs`，整段貼：

   ```text
   讀 SPEC.md，只改 README.md 完成「文件」那一節，不要動 src/ 與 tests/；用訊息「docs: document remove command」commit，不要 push
   ```

4. 主 checkout 收斂：

   ```bash
   git merge --no-ff --no-edit worktree-feat && git merge --no-ff --no-edit worktree-docs && python3 -m unittest tests.test_todo -v
   ```

   A、B 各 `/exit` 選 **remove**，然後 `git worktree prune`。

5. 主 checkout 開 `claude`，依序：`@agent-doc-checker 對照 src/todo.py 與 README.md，找出 remove 相關的不一致`（有就修、commit；它順手列的其他 README 缺漏可不理）→ `/ship-check`（要 go）→ `/release 1.0.0` → `把 main 和 tag 推到 origin`（看 hook 擋下）→ `/exit`。

6. `make capstone`，看到 `CAPSTONE_OK`。

## 故障排除

- **worktree 裡沒有 `.claude/` 或 `SPEC.md`**：步驟 1 沒 commit，或 `settings.json` 少了 `worktree.baseRef: head`（`--worktree` 就照預設從 `origin/main` 長）。回主 checkout 確認 commit 了、settings 修好，再到 worktree 裡 `git merge main`。
- **`/ship-check` 給 no-go**：看 reasons 列的 檔名:行號，回主 checkout 修、commit，再跑一次。
- **`/release` 說工作樹不乾淨**：`git status` 看是什麼；doc-checker 之後改的檔要先 commit。
- **merge 時畫面變成一堆 `#`**：git 開了 vim 要你確認合併訊息（少了 `--no-edit`），打 `:wq` 再 Enter。
- **驗收說 merge 節點不夠**：收斂用了 fast-forward。`git log --oneline` 找到「chore: release 工具鏈…」的 hash → `git tag -d v1.0.0` → `git reset --hard <hash>` → 重做 merge（`--no-ff --no-edit`）→ 重跑 `/release 1.0.0`。
- **驗收說還有 worktree、或 remove 說 locked**：先 `git worktree unlock .claude/worktrees/<name>`，再 `git worktree remove` 那個路徑、`git branch -d` 它的分支、`git worktree prune`。
