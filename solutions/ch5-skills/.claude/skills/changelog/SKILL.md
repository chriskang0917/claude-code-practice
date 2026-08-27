---
name: changelog
description: 從 git log 產生 CHANGELOG 段落並寫進 CHANGELOG.md
argument-hint: [since-ref]
---

（changelog skill v1）從 git 歷史整理一段 Unreleased changelog，寫進 repo 根目錄的 `CHANGELOG.md`。

## 輸入

- since-ref：`$ARGUMENTS`。有給就只看 `<since-ref>..HEAD`；沒給就看全部歷史。

## 步驟

1. 取得 commit 清單：
   - 有 since-ref：`git log --oneline <since-ref>..HEAD`
   - 沒有：`git log --oneline`
2. 依 commit 訊息開頭的 type 分組（`feat:`、`fix:`、`docs:`、`refactor:`、`test:`、`chore:`；沒有 type 的歸「其他」）。
3. 用 `date +%F` 取今天日期，組成下面這段，放在 `CHANGELOG.md` 的最頂端（檔案不存在就建立；已存在就插在第一行之前，不要動舊內容）：

   ```markdown
   ## Unreleased (YYYY-MM-DD)

   ### feat
   - <subject>（<短 hash>）

   ### fix
   - ...
   ```

   只列有內容的分組。
4. 寫完後印出這段給使用者看，並提醒：這段還沒 commit。

## 限制

- 只動 `CHANGELOG.md`，不改其他檔案、不 commit、不 push。
- 不要憑空補 commit 沒寫的內容；subject 照原文。
