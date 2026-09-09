---
name: release
description: 把目前的 main 出成一個版本：測試全過後產生 CHANGELOG.md 條目、commit、打 tag。只在使用者明確說要出版本／release 時用
argument-hint: <version>
disable-model-invocation: true
---

把目前的 `main` 出成一個版本。版本號從 `$ARGUMENTS` 讀（例如 `1.0.0`）。

## 步驟

1. 讀版本號：`$ARGUMENTS` 是空的就停下來問使用者，不要自己猜一個。版本號不含開頭的 `v`。
2. 確認在 `main`（`git rev-parse --abbrev-ref HEAD`），而且 `git status --porcelain` 沒有輸出。任一項不符就停下來回報，不要自己先 commit。
3. 跑 `python3 -m unittest -v`。最後一行不是 `OK` 就停下來回報失敗的測試，不要繼續出版。
4. 找上一個 tag：`git describe --tags --abbrev=0`。找得到就只取 `<上一個 tag>..HEAD` 的 `git log --oneline`；找不到就取全部。
5. 把這些 commit 依訊息開頭的 type 分組（`feat:`、`fix:`、`docs:`、`refactor:`、`test:`、`chore:`；沒有 type 的歸「其他」），空的分組不要列。
6. 用 `date +%F` 取今天日期，把下面這段插到 `CHANGELOG.md` 最前面（檔案不存在就新建；已存在就插在第一行之前，舊內容一個字都不動）：

   ```markdown
   ## <版本號> (YYYY-MM-DD)

   ### feat
   - <commit 標題>（<短 hash>）
   ```

7. `git add CHANGELOG.md && git commit -m "chore: release <版本號>"`。
8. `git tag v<版本號>`。
9. 把剛寫進去的那段 changelog 與 tag 名印給使用者看，並講明：**沒有 push**，要推到 remote 請使用者自己在終端機做。

## 限制

- 只動 `CHANGELOG.md`，其他檔案一律不改。
- 絕不執行 push；這個 repo 的 push-gate hook 也會擋下來。
- 版本號沒給、工作樹不乾淨、測試沒過——任何一項都停下來回報，不要繞過去硬做。
