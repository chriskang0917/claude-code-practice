# SPEC：todo CLI v1.0.0

## 新指令 remove

- `python3 src/todo.py remove <n>`：移除第 n 筆（編號與 `list` 顯示的相同，從 1 起算）。
- 成功：印 `已移除 #<n>: <text>`，exit 0；剩下的項目編號往前補（`list` 重新從 1 排）。
- 編號不存在（0、超出範圍、不是整數）：stderr 印 `錯誤：編號不存在：<原輸入>`，exit 1，清單不變。
- `USAGE` 改成 `用法：todo.py add <text> | list | done <n> | remove <n>`。

## 測試

- `tests/test_todo.py` 至少加兩個測試（測試函式名稱要含 `remove`）：移除成功（清單少一筆、編號重排）、錯誤編號（exit 1、清單不變）。

## 文件

- `README.md` 的「怎麼跑」加上 `remove` 的範例，並用一句話說明移除後編號會重排。

## 出版

- `CHANGELOG.md` 最上面一段是 `## 1.0.0 (YYYY-MM-DD)`，條目從 git log 產生。
- 打 tag `v1.0.0`。不 push。
