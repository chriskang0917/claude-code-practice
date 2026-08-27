# 練習 repo 常用指令。在 practice/ 執行 `make <target>`。
.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help test test-all reset

help:  ## 列出所有 target
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

test:  ## python3 -m unittest -v
	python3 -m unittest -v

test-all:  ## 兩個直譯器都跑一次（python3 與 /usr/bin/python3）
	python3 --version && python3 -m unittest -v
	/usr/bin/python3 --version && /usr/bin/python3 -m unittest -v

reset:  ## 重置回乾淨的 main（同教材步驟 0；還沒有 origin 時退回本地 main）。會丟掉未 commit 的改動與未追蹤檔
	git merge --abort 2>/dev/null; git checkout -f main && (git reset --hard origin/main 2>/dev/null || git reset --hard main) && git clean -fd && git worktree prune
