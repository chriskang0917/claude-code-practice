# ch5 多 session 多工：參考解答

ch5 沒有要貼的檔案，這裡是兩條 worktree 的提示詞全文、第三個終端機的收斂指令，和收尾步驟。

## 終端機 A

```bash
claude --worktree a
```

提示詞（整段貼）：

```text
只改 src/todo.py 與 tests/test_todo.py：list 加 --json 輸出（印出 JSON 陣列，每筆含 text 與 done）並補測試，不要動 README，做完只 commit 不要 push
```

## 終端機 B

```bash
claude --worktree b
```

提示詞（整段貼）：

```text
只改 README.md 加三個使用範例，不要動 src/ 與 tests/，做完只 commit 不要 push
```

## 終端機 C（主 checkout，收斂）

等 A、B 都回報「已 commit」再做：

```bash
git merge --no-ff worktree-a && git merge --no-ff worktree-b && python3 -m unittest -v
```

預期：`git log --oneline --graph` 看到兩個 merge 節點；測試 `OK`。

## 收尾

1. 回終端機 A、B 各打 `/exit`，提示 keep／remove 時選 **remove**（已 merge 進 main，刪掉安全）。
2. 主 checkout：

```bash
git worktree prune && git branch -d worktree-a worktree-b
```

## 故障排除

- merge 衝突：`git merge --abort`，回該 session 要求「只改指定檔案」重做一次。
- remove 顯示 locked：`git worktree unlock .claude/worktrees/<name>` 再 remove。
