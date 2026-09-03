#!/usr/bin/env python3
"""期末作業驗收：在練習 repo 根目錄執行 `python3 capstone/check.py`（或 `make capstone`）。

六組檢查，對應教材五章加出版：
  [1] push-gate hook（第 4 章）  [2] release skill（第 1 章）  [3] doc-checker subagent（第 2 章）
  [4] ship-check workflow（第 3 章）  [5] 平行開發與收斂（第 5 章）  [6] 出版（CHANGELOG、tag、工作樹乾淨）
每項印 ✓／✗ 與原因；全過印 CAPSTONE_OK 並 exit 0，否則 CAPSTONE_FAIL 並 exit 1。
只用標準函式庫。workflow 的 stub 執行需要 node，沒有就標示跳過（不算失敗）。
檢查的是「形狀與行為」，不是逐位元組比對——四份工具檔是你自己寫的，跟 solutions/ 長得不一樣沒關係。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

NODE = shutil.which("node")
READONLY_TOOLS = {"Read", "Grep", "Glob"}


class Result:
    def __init__(self, id: str, ok: bool, text: str, hint: str = "", skipped: bool = False):
        self.id, self.ok, self.text, self.hint, self.skipped = id, ok, text, hint, skipped

    @property
    def failed(self) -> bool:
        return not self.ok and not self.skipped


def ok(id: str, text: str) -> Result:
    return Result(id, True, text)


def fail(id: str, text: str, hint: str = "") -> Result:
    return Result(id, False, text, hint)


def skipped(id: str, text: str, hint: str = "") -> Result:
    return Result(id, False, text, hint, skipped=True)


# ───────────── 共用小工具 ─────────────


def run(cmd: List[str], cwd: Path, stdin: Optional[str] = None, env: Optional[dict] = None, timeout: int = 60):
    return subprocess.run(
        cmd, cwd=str(cwd), input=stdin, env=env, capture_output=True, text=True, check=False, timeout=timeout,
    )


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return run(["git", *args], cwd=root)


def frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """回傳 (frontmatter dict, 正文)。沒有 frontmatter 就是 ({}, 全文)。"""
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not match:
        return {}, text
    fields: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip("'\"")
    return fields, match.group(2)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ───────────── [1] push-gate hook（第 4 章）─────────────


def matcher_hits_bash(matcher: str) -> bool:
    if "Bash" in [m.strip() for m in matcher.split("|")]:
        return True
    try:
        return re.fullmatch(matcher, "Bash") is not None
    except re.error:
        return False


def check_hook(root: Path) -> List[Result]:
    results: List[Result] = []
    settings_path = root / ".claude" / "settings.json"
    script = root / ".claude" / "hooks" / "push_gate.py"

    if not settings_path.is_file():
        results.append(fail("hook.settings", ".claude/settings.json 不存在", "第 4 章的三層設定表：專案層是 .claude/settings.json"))
    else:
        try:
            settings = json.loads(read_text(settings_path))
        except ValueError as exc:
            settings = None
            results.append(fail("hook.settings", ".claude/settings.json 不是合法 JSON：{}".format(exc)))
        if settings is not None:
            results.append(ok("hook.settings", ".claude/settings.json 是合法 JSON"))
            entries = ((settings.get("hooks") or {}).get("PreToolUse")) or []
            wired = any(
                isinstance(entry, dict)
                and matcher_hits_bash(str(entry.get("matcher", "")))
                and any("push_gate.py" in str(h.get("command", "")) for h in entry.get("hooks", []) if isinstance(h, dict))
                for entry in entries
            )
            if wired:
                results.append(ok("hook.settings_bash", "PreToolUse 有 matcher 含 Bash、command 指到 push_gate.py"))
            else:
                results.append(fail("hook.settings_bash", "PreToolUse 裡找不到「matcher 含 Bash 且 command 含 push_gate.py」的項目",
                                    "push 是 Bash 工具跑的，所以 matcher 要是 Bash，不是 Edit|Write"))

    if not script.is_file():
        results.append(fail("hook.script", ".claude/hooks/push_gate.py 不存在"))
        return results
    results.append(ok("hook.script", ".claude/hooks/push_gate.py 存在"))

    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))

    def gate(stdin_text: str) -> subprocess.CompletedProcess:
        return run([sys.executable, str(script)], cwd=root, stdin=stdin_text, env=env, timeout=20)

    def payload(tool: str, **tool_input) -> str:
        return json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": str(root)})

    try:
        blocked, leaks = [], []
        for command in ("git push origin main", "git push --tags", "cd /tmp && git push"):
            proc = gate(payload("Bash", command=command))
            if proc.returncode == 2 and "已擋下" in proc.stderr:
                blocked.append(command)
            else:
                leaks.append("{!r} → exit {}，stderr={!r}".format(command, proc.returncode, proc.stderr.strip()[:80]))
        if leaks:
            results.append(fail("hook.blocks_push", "沒擋下 git push：" + "；".join(leaks),
                                "擋下＝stderr 印含「已擋下」的理由並 exit 2（exit 1 只是非阻斷錯誤）"))
        else:
            results.append(ok("hook.blocks_push", "git push／git push --tags／cd … && git push 都被擋（exit 2，stderr 含「已擋下」）"))

        passed, wrongly = [], []
        benign = [payload("Bash", command="git status"), payload("Bash", command="git log --oneline"),
                  payload("Bash", command="echo push"), payload("Edit", file_path=str(root / "README.md"))]
        for text in benign:
            proc = gate(text)
            label = json.loads(text)["tool_input"]
            if proc.returncode == 0:
                passed.append(label)
            else:
                wrongly.append("{} → exit {}".format(label, proc.returncode))
        if wrongly:
            results.append(fail("hook.allows_others", "誤擋了不是 push 的指令：" + "；".join(wrongly),
                                "只擋「git … push」；echo push、沒有 command 的 Edit payload 都要放行（exit 0）"))
        else:
            results.append(ok("hook.allows_others", "git status／git log／echo push／Edit payload 都放行（exit 0）"))

        proc = gate("{not json")
        if proc.returncode == 0:
            results.append(ok("hook.bad_json", "stdin 不是 JSON 時放行（exit 0），不會讓閘門自己炸掉"))
        else:
            results.append(fail("hook.bad_json", "stdin 不是 JSON 時 exit {}".format(proc.returncode),
                                "read 不到 payload 要 skip（exit 0）並在 stderr 留一行原因"))
    except subprocess.TimeoutExpired:
        results.append(fail("hook.blocks_push", "push_gate.py 超過 20 秒沒結束", "hook 要讀 stdin 一次就結束，不要等輸入"))
    return results


# ───────────── [2] release skill（第 1 章）─────────────


def check_skill(root: Path) -> List[Result]:
    path = root / ".claude" / "skills" / "release" / "SKILL.md"
    if not path.is_file():
        return [fail("skill.exists", ".claude/skills/release/SKILL.md 不存在", "skill 是資料夾：.claude/skills/<name>/SKILL.md")]
    results = [ok("skill.exists", ".claude/skills/release/SKILL.md 存在")]
    fields, body = frontmatter(read_text(path))
    missing = []
    if fields.get("name") != "release":
        missing.append("name 要是 release")
    if not fields.get("description"):
        missing.append("description 不能空")
    if not fields.get("argument-hint"):
        missing.append("argument-hint 要寫（例如 <version>）")
    if fields.get("disable-model-invocation", "").lower() != "true":
        missing.append("disable-model-invocation: true（會 commit、打 tag 的步驟不該讓 Claude 自己決定要不要跑）")
    if missing:
        results.append(fail("skill.frontmatter", "frontmatter 缺：" + "；".join(missing)))
    else:
        results.append(ok("skill.frontmatter", "frontmatter：name=release、description、argument-hint、disable-model-invocation: true"))
    need = {"$ARGUMENTS": "$ARGUMENTS" in body, "CHANGELOG.md": "CHANGELOG.md" in body,
            "git tag": "git tag" in body, "unittest": "unittest" in body, "push": re.search(r"push", body, re.I) is not None}
    lacking = [k for k, v in need.items() if not v]
    if lacking:
        results.append(fail("skill.body", "正文缺：" + "、".join(lacking),
                            "步驟要用 $ARGUMENTS 收版本號、先跑 unittest、寫 CHANGELOG.md、git tag，並寫明不 push"))
    else:
        results.append(ok("skill.body", "正文有 $ARGUMENTS、先跑 unittest、寫 CHANGELOG.md、git tag、不 push"))
    return results


# ───────────── [3] doc-checker subagent（第 2 章）─────────────


def check_agent(root: Path) -> List[Result]:
    path = root / ".claude" / "agents" / "doc-checker.md"
    if not path.is_file():
        return [fail("agent.exists", ".claude/agents/doc-checker.md 不存在")]
    results = [ok("agent.exists", ".claude/agents/doc-checker.md 存在")]
    fields, body = frontmatter(read_text(path))
    missing = []
    if fields.get("name") != "doc-checker":
        missing.append("name 要是 doc-checker")
    if not fields.get("description"):
        missing.append("description 不能空（寫觸發時機，Claude 才會自動派）")
    if missing:
        results.append(fail("agent.frontmatter", "frontmatter 缺：" + "；".join(missing)))
    else:
        results.append(ok("agent.frontmatter", "frontmatter：name=doc-checker、description"))
    tools_raw = fields.get("tools", "")
    tools = {t.strip() for t in tools_raw.split(",") if t.strip()}
    if not tools:
        results.append(fail("agent.readonly", "frontmatter 沒有 tools（不寫＝繼承全部工具，它就改得了檔）",
                            "對照員只給 Read, Grep, Glob"))
    elif not tools <= READONLY_TOOLS:
        results.append(fail("agent.readonly", "tools 含可寫或可執行的工具：" + ", ".join(sorted(tools - READONLY_TOOLS)),
                            "唯讀＝只有 Read／Grep／Glob；「請不要改檔」的提示詞不算"))
    else:
        results.append(ok("agent.readonly", "tools 只有 " + ", ".join(sorted(tools)) + "（唯讀）"))
    need = {"README.md": "README.md" in body, "src/todo.py": "src/todo.py" in body, "行號": "行號" in body}
    lacking = [k for k, v in need.items() if not v]
    if lacking:
        results.append(fail("agent.body", "正文缺：" + "、".join(lacking), "要寫清楚對照哪兩個檔、回報附行號"))
    else:
        results.append(ok("agent.body", "正文寫明對照 src/todo.py 與 README.md，回報附行號"))
    return results


# ───────────── [4] ship-check workflow（第 3 章）─────────────

# 用 node 以 stub 執行 workflow 腳本：agent/parallel/pipeline/phase/log 都是假的，不碰網路、不呼叫模型。
STUB_HARNESS = r"""
const fs = require('fs');
const src = fs.readFileSync(process.env.WF_PATH, 'utf8').replace(/^export const meta = /m, 'const meta = globalThis.__wfMeta = ');
const nullFirst = process.env.WF_NULL_FIRST === '1';
const calls = [], phases = [], logs = [];
let n = 0;
const agent = async (prompt, opts = {}) => {
  const idx = n++;
  if (typeof prompt !== 'string' || !prompt.trim()) throw new Error('agent() prompt 必須是非空字串');
  calls.push({ label: opts.label, phase: opts.phase, has_schema: !!opts.schema });
  if (nullFirst && idx === 0) return null;
  if (!opts.schema) return 'STUB_TEXT';
  const props = (opts.schema && opts.schema.properties) || {};
  if (props.verdict) return { verdict: 'go', reasons: [] };
  return { findings: [{ file: 'stub.py', line: idx + 1, note: 'stub' }] };
};
const parallel = async (thunks) => {
  if (!Array.isArray(thunks) || !thunks.every((t) => typeof t === 'function')) throw new Error('parallel() 需要 thunk 陣列（() => agent(...)）');
  return Promise.all(thunks.map((t) => t()));
};
const pipeline = async (items, ...stages) => {
  const out = [];
  for (const item of items) { let v = item; for (const s of stages) v = await s(v, item); out.push(v); }
  return out;
};
const phase = (t) => phases.push(t);
const log = (m) => logs.push(String(m));
const runner = new Function('agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'return (async () => {\n' + src + '\n})()');
runner(agent, parallel, pipeline, phase, log, undefined).then((result) => {
  process.stdout.write(JSON.stringify({ meta: globalThis.__wfMeta, phases, calls, logs, result }));
}).catch((e) => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


def run_workflow_stub(path: Path, null_first: bool) -> dict:
    env = dict(os.environ, WF_PATH=str(path), WF_NULL_FIRST="1" if null_first else "0")
    proc = run([NODE or "node", "-e", STUB_HARNESS], cwd=path.parent, env=env, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip().splitlines()[0] if proc.stderr.strip() else "node 執行失敗")
    return json.loads(proc.stdout)


def check_workflow(root: Path) -> List[Result]:
    path = root / ".claude" / "workflows" / "ship-check.js"
    if not path.is_file():
        return [fail("workflow.exists", ".claude/workflows/ship-check.js 不存在")]
    results = [ok("workflow.exists", ".claude/workflows/ship-check.js 存在")]
    src = read_text(path)
    rules = [
        (re.search(r"(?m)^\s*export const meta\s*=\s*\{", src) is not None, "頂層 export const meta = { … }"),
        (re.search(r"name:\s*['\"]ship-check['\"]", src) is not None, "meta.name 是 'ship-check'"),
        (re.search(r"description:\s*['\"][^'\"]+['\"]", src) is not None, "meta.description 非空"),
        (re.search(r"phases:\s*\[", src) is not None and len(re.findall(r"title:", src)) >= 2, "meta.phases 至少兩站"),
        (len(re.findall(r"\bphase\(", src)) >= 2, "至少兩次 phase(...) 呼叫"),
        ("parallel(" in src and len(re.findall(r"\(\)\s*=>\s*agent\(", src)) >= 2, "parallel([...]) 收至少兩個 thunk（() => agent(...)）"),
        (src.count("schema:") >= 2, "至少兩個 agent 給 schema"),
        (".filter(Boolean)" in src, "有 .filter(Boolean) 濾掉回 null 的 agent"),
        ("log(" in src, "至少一個 log(...)"),
        (re.search(r"(?m)^\s*return\b", src) is not None, "頂層 return"),
    ]
    broken = [text for passed, text in rules if not passed]
    if broken:
        results.append(fail("workflow.static", "腳本缺：" + "；".join(broken), "上面列的就是缺哪一項；寫法對照第 3 章「腳本長什麼樣」與期末「規格 4」"))
    else:
        results.append(ok("workflow.static", "meta／phases／parallel 收 thunk／schema／filter(Boolean)／log／return 都在"))
    if not NODE:
        results.append(skipped("workflow.stub", "找不到 node，跳過 stub 執行（靜態檢查有跑）"))
        return results
    try:
        problems = []
        for null_first in (False, True):
            report = run_workflow_stub(path, null_first)
            tag = "（第一個 agent 回 null）" if null_first else ""
            if (report.get("meta") or {}).get("name") != "ship-check":
                problems.append("meta.name 不是 ship-check" + tag)
            if len(report["phases"]) < 2:
                problems.append("phase() 少於兩次" + tag)
            if len(report["calls"]) < 3:
                problems.append("agent() 少於三次（兩個平行檢查＋一個裁決）" + tag)
            if sum(1 for c in report["calls"] if c["has_schema"]) < 2:
                problems.append("給 schema 的 agent 少於兩個" + tag)
            if not null_first and report["result"] is None:
                problems.append("全部成功時 return 了 null")
        if problems:
            results.append(fail("workflow.stub", "stub 執行：" + "；".join(problems)))
        else:
            results.append(ok("workflow.stub", "stub 執行：≥2 站、≥3 個 agent、≥2 個 schema；第一個 agent 回 null 也跑得完"))
    except (RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        results.append(fail("workflow.stub", "stub 執行失敗：{}".format(exc),
                            "常見原因：parallel 收到的不是 thunk、頂層語法錯誤、return 之前就 throw"))
    return results


# ───────────── [5] 平行開發與收斂（第 5 章）─────────────


def check_parallel(root: Path) -> List[Result]:
    results: List[Result] = []
    head = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if head == "main":
        results.append(ok("git.on_main", "目前在 main"))
    else:
        results.append(fail("git.on_main", "目前在 {!r}，驗收要在主 checkout 的 main 上跑".format(head)))
    merges = git(root, "rev-list", "--merges", "--count", "HEAD").stdout.strip()
    if merges.isdigit() and int(merges) >= 2:
        results.append(ok("git.merges", "main 的歷史有 {} 個 merge 節點".format(merges)))
    else:
        results.append(fail("git.merges", "main 只有 {} 個 merge 節點（需要 ≥2：feat 與 docs 各一）".format(merges or 0),
                            "收斂要用 git merge --no-ff，fast-forward 不會留下 merge 節點"))
    worktrees = [l for l in git(root, "worktree", "list", "--porcelain").stdout.splitlines() if l.startswith("worktree ")]
    if len(worktrees) == 1:
        results.append(ok("git.worktrees", "git worktree list 只剩主 checkout"))
    else:
        results.append(fail("git.worktrees", "還有 {} 個 worktree 沒收".format(len(worktrees) - 1),
                            "CLI：/exit 選 remove；Orca：側欄刪除；再 git worktree prune"))

    cli = root / "src" / "todo.py"
    tmpdir = Path(tempfile.mkdtemp())
    env = dict(os.environ, TODO_FILE=str(tmpdir / "todo.json"))

    def todo(*args: str) -> subprocess.CompletedProcess:
        return run([sys.executable, str(cli), *args], cwd=root, env=env, timeout=20)

    try:
        todo("add", "A")
        todo("add", "B")
        removed = todo("remove", "1")
        listed = todo("list")
        if removed.returncode == 0 and "已移除 #1: A" in removed.stdout and listed.stdout.splitlines() == ["[ ] 1. B"]:
            results.append(ok("feature.remove", "remove 1 印「已移除 #1: A」，list 剩「[ ] 1. B」（編號重排）"))
        else:
            results.append(fail("feature.remove", "remove 行為不符 SPEC：exit {}，stdout={!r}，之後 list={!r}".format(
                removed.returncode, removed.stdout.strip(), listed.stdout.strip()),
                "SPEC.md「新指令 remove」：成功印 已移除 #<n>: <text>，剩下的編號往前補"))
        bad = [todo("remove", raw) for raw in ("0", "5", "abc")]
        after = todo("list")
        if all(p.returncode == 1 and "編號不存在" in p.stderr for p in bad) and after.stdout.splitlines() == ["[ ] 1. B"]:
            results.append(ok("feature.remove_bad", "remove 0／5／abc 都 exit 1、stderr 含「編號不存在」，清單不變"))
        else:
            results.append(fail("feature.remove_bad", "錯誤編號的處理不符 SPEC：" + "；".join(
                "remove {} → exit {}".format(raw, p.returncode) for raw, p in zip(("0", "5", "abc"), bad)),
                "跟 done 一樣：stderr 印 錯誤：編號不存在：<原輸入>，exit 1，清單不動"))
        usage = todo()
        if "remove" in usage.stderr:
            results.append(ok("feature.usage", "沒帶參數時 USAGE 列出 remove"))
        else:
            results.append(fail("feature.usage", "USAGE 沒有 remove", "SPEC.md：USAGE 改成 add <text> | list | done <n> | remove <n>"))
    except subprocess.TimeoutExpired:
        results.append(fail("feature.remove", "src/todo.py 超過 20 秒沒結束"))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    test_file = root / "tests" / "test_todo.py"
    if test_file.is_file() and re.search(r"def test_\w*remove", read_text(test_file)):
        results.append(ok("feature.tests_exist", "tests/test_todo.py 有 remove 的測試"))
    else:
        results.append(fail("feature.tests_exist", "tests/test_todo.py 沒有名字含 remove 的測試", "SPEC.md「測試」：至少兩個"))
    try:
        tests = run([sys.executable, "-m", "unittest", "tests.test_todo"], cwd=root, timeout=120)
        if tests.returncode == 0:
            summary = [l for l in tests.stderr.splitlines() if l.startswith("Ran ")]
            results.append(ok("feature.tests_pass", "python3 -m unittest tests.test_todo → OK" + ("（{}）".format(summary[0]) if summary else "")))
        else:
            tail = tests.stderr.strip().splitlines()[-1] if tests.stderr.strip() else ""
            results.append(fail("feature.tests_pass", "python3 -m unittest tests.test_todo 失敗：" + tail))
    except subprocess.TimeoutExpired:
        results.append(fail("feature.tests_pass", "unittest 超過 120 秒"))

    readme = root / "README.md"
    if readme.is_file() and re.search(r"todo\.py remove\b", read_text(readme)):
        results.append(ok("docs.readme", "README.md 有 todo.py remove 的用法範例"))
    else:
        results.append(fail("docs.readme", "README.md 沒有 todo.py remove 的用法範例", "docs worktree 的產出；merge 進來了嗎？"))
    return results


# ───────────── [6] 出版 ─────────────


def check_release(root: Path) -> List[Result]:
    results: List[Result] = []
    changelog = root / "CHANGELOG.md"
    if not changelog.is_file():
        results.append(fail("release.changelog", "CHANGELOG.md 不存在", "/release 1.0.0 應該建立它"))
    else:
        text = read_text(changelog)
        headings = [l for l in text.splitlines() if l.startswith("## ")]
        first = headings[0] if headings else ""
        bullets = [l for l in text.splitlines() if l.lstrip().startswith("- ")]
        if re.match(r"^## v?1\.0\.0 \(\d{4}-\d{2}-\d{2}\)\s*$", first) and bullets:
            results.append(ok("release.changelog", "CHANGELOG.md 第一段是「{}」，有 {} 條".format(first, len(bullets))))
        else:
            results.append(fail("release.changelog", "CHANGELOG.md 第一個標題是 {!r}（要是 ## 1.0.0 (YYYY-MM-DD)），條目 {} 條".format(first, len(bullets))))
        if "remove" in text:
            results.append(ok("release.changelog_remove", "CHANGELOG.md 列到了 remove 的 commit"))
        else:
            results.append(fail("release.changelog_remove", "CHANGELOG.md 沒有 remove", "feat commit 的訊息要含 remove，release 才會把它列進來"))
    tag = git(root, "tag", "--list", "v1.0.0").stdout.strip()
    if not tag:
        results.append(fail("release.tag", "沒有 tag v1.0.0", "/release 1.0.0 的最後一步是 git tag v1.0.0"))
    elif git(root, "merge-base", "--is-ancestor", "v1.0.0", "HEAD").returncode == 0:
        results.append(ok("release.tag", "tag v1.0.0 存在且在 main 的歷史上"))
    else:
        results.append(fail("release.tag", "tag v1.0.0 存在但不在目前 HEAD 的歷史上"))
    dirty = git(root, "status", "--porcelain").stdout.strip()
    if not dirty:
        results.append(ok("release.clean", "工作樹乾淨，全部都 commit 了"))
    else:
        results.append(fail("release.clean", "工作樹不乾淨：" + dirty.splitlines()[0] + ("…" if "\n" in dirty else ""),
                            "交付＝全部進 git；/release 也要求乾淨的工作樹"))
    return results


# ───────────── 總覽 ─────────────

SECTIONS = [
    ("push-gate hook（第 4 章）", check_hook),
    ("release skill（第 1 章）", check_skill),
    ("doc-checker subagent（第 2 章）", check_agent),
    ("ship-check workflow（第 3 章）", check_workflow),
    ("平行開發與收斂（第 5 章）", check_parallel),
    ("出版", check_release),
]


def run_all(root: Path) -> List[Tuple[str, List[Result]]]:
    return [(title, fn(root)) for title, fn in SECTIONS]


def banner(root: Path, passed: int, total: int, failed: int) -> str:
    line = "═" * 44
    if failed:
        return "\n".join([line, " CAPSTONE_FAIL  {}/{} 項通過".format(passed, total), " 先修上面 ✗ 的項目，再跑一次 make capstone", line])
    sha = git(root, "rev-parse", "--short", "v1.0.0^{commit}").stdout.strip()
    date = git(root, "log", "-1", "--format=%cs", "v1.0.0").stdout.strip()
    return "\n".join([
        line,
        " CAPSTONE_OK  todo CLI v1.0.0 已交付",
        " 五章的工具都是你自己寫的，也都跑過了：",
        "   第 1 章 skill      /release",
        "   第 2 章 subagent   doc-checker",
        "   第 3 章 workflow   /ship-check",
        "   第 4 章 hook       push-gate",
        "   第 5 章 worktree   feat ＋ docs 兩個 merge 節點",
        " v1.0.0 → {}（{}）".format(sha, date),
        line,
    ])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="期末作業驗收")
    parser.add_argument("--root", default=".", help="練習 repo 根目錄（預設：目前目錄）")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not (root / "src" / "todo.py").is_file() or git(root, "rev-parse", "--git-dir").returncode != 0:
        print("找不到練習 repo（要在 claude-code-practice 根目錄執行，或用 --root 指定）", file=sys.stderr)
        return 2

    sections = run_all(root)
    passed = total = failed = 0
    for index, (title, results) in enumerate(sections, start=1):
        print("[{}/{}] {}".format(index, len(sections), title))
        for r in results:
            mark = "·" if r.skipped else ("✓" if r.ok else "✗")
            print("  {} {}".format(mark, r.text))
            if r.failed and r.hint:
                print("      → {}".format(r.hint))
            total += 0 if r.skipped else 1
            passed += 1 if r.ok else 0
            failed += 1 if r.failed else 0
        print()
    print(banner(root, passed, total, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
