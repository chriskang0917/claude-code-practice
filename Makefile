# 練習 repo 常用指令。在 practice/ 執行 `make <target>`。
.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help test test-all reset clean-state

help:  ## 列出所有 target
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

test:  ## python3 -m unittest -v
	python3 -m unittest -v

test-all:  ## 兩個直譯器都跑一次（python3 與 /usr/bin/python3）
	python3 --version && python3 -m unittest -v
	/usr/bin/python3 --version && /usr/bin/python3 -m unittest -v

reset:  ## 重置回乾淨的 main（同教材步驟 0；還沒有 origin 時退回本地 main）。丟掉未 commit 改動與未追蹤檔；不動 gitignore 的 .todo.json、.claude/settings.local.json
	git merge --abort 2>/dev/null; git checkout -f main && (git reset --hard origin/main 2>/dev/null || git reset --hard main) && git clean -fd && git worktree prune

clean-state:  ## 只精確刪練習狀態：.todo.json 與 __pycache__/（不碰 settings.local.json、不碰其他 worktree）
	rm -f .todo.json
	rm -rf __pycache__ src/__pycache__ tests/__pycache__
