---
name: release
description: 出一個版本：測試全過後更新 CHANGELOG.md、commit、打 tag。只在使用者說要 release／出版本時用
argument-hint: <version>
disable-model-invocation: true
---

（release skill v1）把目前的 `main` 出成一個版本。版本號：`$ARGUMENTS`（例如 `1.0.0`）；沒給就停下來問使用者，不要自己猜。

## 步驟

1. 確認在 `main` 且工作樹乾淨（`git status --porcelain` 沒有輸出）；不是就停下來回報。
2. 跑 `python3 -m unittest -v`，最後不是 `OK` 就停下來回報，不要出版。
3. 找上一個 tag：`git describe --tags --abbrev=0`。有就只看 `<tag>..HEAD` 的 `git log --oneline`；沒有就看全部。
4. 依 commit 訊息開頭的 type 分組（`feat:`、`fix:`、`docs:`、`refactor:`、`test:`、`chore:`；沒有 type 的歸「其他」），只列有內容的分組。
5. 用 `date +%F` 取今天日期，把下面這段放在 `CHANGELOG.md` 最頂端（檔案不存在就建立；已存在就插在第一行之前，不動舊內容）：

   ```markdown
   ## <version> (YYYY-MM-DD)

   ### feat
   - <subject>（<短 hash>）
   ```

6. `git add CHANGELOG.md && git commit -m "chore: release <version>"`。
7. `git tag v<version>`。
8. 把那段 changelog 與 tag 名印給使用者看，並提醒：**沒有 push**，要推的話由使用者自己在終端機做。

## 限制

- 只動 `CHANGELOG.md`，不改其他檔案。
- 絕不 push（repo 的 push-gate hook 也會擋）。
- 測試沒過、工作樹不乾淨、版本號沒給：一律停下來回報，不要硬做。
