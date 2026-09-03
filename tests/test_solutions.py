"""各章參考解答的 unittest。

- spec_gate.py 六案例：獨立暫存目錄下跑 subprocess；env 從 os.environ 複製並移除 CLAUDE_PROJECT_DIR（除非案例指定）。
- review-flow.js：靜態結構檢查，加上用 node 以 stub 的 agent/parallel/phase/log 執行一遍（不呼叫模型；沒有 node 就跳過並說明）。
- 教材站各章貼給讀者的 heredoc 與 solutions/ 對應檔逐位元組比較（找不到 ../site 時跳過並說明）。
- 期末作業頁貼給讀者的 heredoc（只有 SPEC.md）與 solutions/capstone/ 逐位元組比較；四份工具檔刻意不貼，由 tests/test_capstone_check.py 驗證。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS = ROOT / "solutions"
SPEC_GATE = SOLUTIONS / "ch4-hooks" / ".claude" / "hooks" / "spec_gate.py"
REVIEW_FLOW = SOLUTIONS / "ch3-workflow" / ".claude" / "workflows" / "review-flow.js"
SITE_DOCS = ROOT.parent / "site" / "src" / "content" / "docs"
NODE = shutil.which("node")


def make_project() -> Path:
    tmp = Path(tempfile.mkdtemp()).resolve()
    (tmp / ".git").mkdir()
    (tmp / "src").mkdir()
    (tmp / "src" / "todo.py").write_text("# fake\n", encoding="utf-8")
    (tmp / "README.md").write_text("# fake\n", encoding="utf-8")
    return tmp


def run_gate(stdin_text, cwd, project_dir=None):
    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        [sys.executable, str(SPEC_GATE)],
        input=stdin_text, cwd=str(cwd), env=env, capture_output=True, text=True, check=False,
    )


def payload(file_path, cwd, tool="Edit"):
    return json.dumps({"tool_name": tool, "tool_input": {"file_path": str(file_path)}, "cwd": str(cwd)})


class SpecGateTest(unittest.TestCase):
    def test_1_src_without_spec_is_blocked(self):
        tmp = make_project()
        result = run_gate(payload(tmp / "src" / "todo.py", tmp), cwd=tmp)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("已擋下", result.stderr)

    def test_2_non_src_is_skipped(self):
        tmp = make_project()
        result = run_gate(payload(tmp / "README.md", tmp), cwd=tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[spec-gate] skip", result.stderr)

    def test_3_src_with_spec_is_allowed(self):
        tmp = make_project()
        (tmp / "SPEC.md").write_text("改 todo.py\n", encoding="utf-8")
        result = run_gate(payload(tmp / "src" / "todo.py", tmp), cwd=tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[spec-gate] skip", result.stderr)

    def test_4_cwd_in_subdir_walks_up_to_git(self):
        tmp = make_project()
        result = run_gate(payload(tmp / "src" / "todo.py", tmp / "src"), cwd=tmp / "src")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("已擋下", result.stderr)

    def test_5_project_dir_env_wins_over_cwd(self):
        tmp = make_project()
        result = run_gate(payload(tmp / "src" / "todo.py", "/"), cwd="/", project_dir=tmp)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("已擋下", result.stderr)

    def test_6_bad_json_is_skipped(self):
        tmp = make_project()
        result = run_gate("{not json", cwd=tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[spec-gate] skip", result.stderr)


def frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else ""


class SolutionFilesTest(unittest.TestCase):
    FILES = [
        "ch5-multisession/README.md",
        "ch3-workflow/.claude/workflows/review-flow.js",
        "ch2-subagent/.claude/agents/reviewer.md",
        "ch4-hooks/.claude/settings.json",
        "ch4-hooks/.claude/hooks/spec_gate.py",
        "ch1-skills/.claude/skills/changelog/SKILL.md",
    ]

    def test_7_solution_files_exist_and_have_required_fields(self):
        for rel in self.FILES:
            self.assertTrue((SOLUTIONS / rel).is_file(), rel)
        for rel in ("ch2-subagent/.claude/agents/reviewer.md", "ch1-skills/.claude/skills/changelog/SKILL.md"):
            fm = frontmatter(SOLUTIONS / rel)
            self.assertRegex(fm, r"(?m)^name:\s*\S", rel)
            self.assertRegex(fm, r"(?m)^description:\s*\S", rel)
        flow = REVIEW_FLOW.read_text(encoding="utf-8")
        self.assertIn("export const meta", flow)
        self.assertRegex(flow, r"name:\s*'review-flow'")
        settings = json.loads((SOLUTIONS / "ch4-hooks/.claude/settings.json").read_text(encoding="utf-8"))
        self.assertIn("PreToolUse", settings["hooks"])


# 用 node 以 stub 執行 workflow 腳本：agent/parallel/pipeline/phase/log 都是假的，不碰網路、不呼叫模型。
# 只驗證腳本的控制流（phase 順序、parallel 收到的是 thunk、schema 有給、null 會被過濾、最後有 return）。
STUB_HARNESS = r"""
const fs = require('fs');
const src = fs.readFileSync(process.env.WF_PATH, 'utf8').replace(/^export const meta = /m, 'const meta = globalThis.__wfMeta = ');
const nullFirst = process.env.WF_NULL_FIRST === '1';
const calls = [], phases = [], logs = [];
let n = 0;
const agent = async (prompt, opts = {}) => {
  const idx = n++;
  if (typeof prompt !== 'string' || !prompt.trim()) throw new Error('agent() prompt 必須是非空字串');
  calls.push({ label: opts.label, phase: opts.phase, has_schema: !!opts.schema, prompt });
  if (nullFirst && idx === 0) return null;
  return opts.schema ? { findings: [{ file: 'stub.py', line: idx + 1, note: 'stub' }] } : 'STUB_SUMMARY';
};
const parallel = async (thunks) => {
  if (!Array.isArray(thunks) || !thunks.every((t) => typeof t === 'function')) throw new Error('parallel() 需要 thunk 陣列');
  return Promise.all(thunks.map((t) => t()));
};
const pipeline = async (items, ...stages) => {
  const out = [];
  for (const item of items) { let v = item; for (const s of stages) v = await s(v, item); out.push(v); }
  return out;
};
const phase = (t) => phases.push(t);
const log = (m) => logs.push(String(m));
const run = new Function('agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'return (async () => {\n' + src + '\n})()');
run(agent, parallel, pipeline, phase, log, undefined).then((result) => {
  process.stdout.write(JSON.stringify({ meta: globalThis.__wfMeta, phases, calls, logs, result }));
}).catch((e) => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


def run_workflow_stub(path: Path, null_first: bool) -> dict:
    env = dict(os.environ, WF_PATH=str(path), WF_NULL_FIRST="1" if null_first else "0")
    result = subprocess.run([NODE, "-e", STUB_HARNESS], env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError("stub 執行失敗：\n" + result.stderr)
    return json.loads(result.stdout)


class ReviewFlowTest(unittest.TestCase):
    def test_8_review_flow_static_shape(self):
        src = REVIEW_FLOW.read_text(encoding="utf-8")
        self.assertLessEqual(len(src.rstrip("\n").split("\n")), 60, "review-flow.js 要 ≤60 行")
        self.assertRegex(src, r"(?m)^export const meta = \{")
        self.assertRegex(src, r"name:\s*'review-flow'")
        self.assertRegex(src, r"description:\s*'[^']+'")
        self.assertRegex(src, r"phases:\s*\[\s*\{\s*title:\s*'Review'\s*\},\s*\{\s*title:\s*'Synthesize'\s*\}\s*\]")
        self.assertIn("phase('Review')", src)
        self.assertIn("phase('Synthesize')", src)
        self.assertRegex(src, r"await parallel\(\[\s*\(\) => agent\(", "parallel 要收 thunk（() => agent(...)）")
        self.assertEqual(src.count("() => agent("), 2)
        self.assertEqual(src.count("schema: FINDINGS"), 2)
        self.assertIn(".filter(Boolean)", src, "agent() 可能回 null，要先過濾")
        self.assertRegex(src, r"(?m)^return summary\s*$")
        markers = ["phase('Review')", "await parallel(", ".filter(Boolean)", "phase('Synthesize')", "return summary"]
        positions = [src.index(m) for m in markers]
        self.assertEqual(positions, sorted(positions), "順序應為 Review → parallel → 過濾 null → Synthesize → return")

    @unittest.skipUnless(NODE, "找不到 node，跳過 stub 執行（test_8 的靜態檢查仍有跑）")
    def test_9_review_flow_runs_under_stub_runtime(self):
        for null_first in (False, True):
            with self.subTest(null_first=null_first):
                report = run_workflow_stub(REVIEW_FLOW, null_first)
                self.assertEqual(report["meta"]["name"], "review-flow")
                self.assertTrue(report["meta"]["description"])
                self.assertEqual([p["title"] for p in report["meta"]["phases"]], ["Review", "Synthesize"])
                self.assertEqual(report["phases"], ["Review", "Synthesize"])
                self.assertEqual([c["label"] for c in report["calls"]], ["review:todo", "review:tests", "synthesize"])
                self.assertEqual([c["phase"] for c in report["calls"]], ["Review", "Review", "Synthesize"])
                self.assertEqual([c["has_schema"] for c in report["calls"]], [True, True, False])
                self.assertIn("src/todo.py", report["calls"][0]["prompt"])
                self.assertIn("tests/test_todo.py", report["calls"][1]["prompt"])
                self.assertIn('"line"', report["calls"][2]["prompt"], "彙整 prompt 要帶 findings JSON")
                self.assertEqual(report["result"], "STUB_SUMMARY")
                expected_count = "1" if null_first else "2"
                self.assertEqual(len(report["logs"]), 1)
                self.assertIn(expected_count, report["logs"][0])


HEREDOC_OPEN = re.compile(r"^(\s*)cat > (\S+) <<'EOF'\s*$")


def site_heredocs(pattern: str = "0[1-5]-*.mdx") -> dict:
    """抓 mdx 裡 `cat > <path> <<'EOF' … EOF` 的內容（去掉 code block 的縮排）。回傳 {path: (章節檔名, 內容)}。"""
    found = {}
    for mdx in sorted(SITE_DOCS.glob(pattern)):
        lines = mdx.read_text(encoding="utf-8").split("\n")
        i = 0
        while i < len(lines):
            match = HEREDOC_OPEN.match(lines[i])
            if not match:
                i += 1
                continue
            indent, path = match.group(1), match.group(2)
            body = []
            j = i + 1
            while j < len(lines) and lines[j] != indent + "EOF":
                line = lines[j]
                if line and not line.startswith(indent):
                    raise AssertionError("{}:{} heredoc 內容縮排少於 code block".format(mdx.name, j + 1))
                body.append(line[len(indent):] if line else "")
                j += 1
            if j >= len(lines):
                raise AssertionError("{}:{} heredoc 沒有 EOF 終止行".format(mdx.name, i + 1))
            if path in found:
                raise AssertionError("{} 在多章重複貼了 {}".format(path, mdx.name))
            found[path] = (mdx.name, "\n".join(body) + "\n")
            i = j + 1
    return found


class SiteHeredocDriftTest(unittest.TestCase):
    @unittest.skipUnless(SITE_DOCS.is_dir(), "找不到 ../site/src/content/docs（單獨 clone 練習 repo 時跳過）")
    def test_10_site_heredocs_match_solutions_byte_for_byte(self):
        found = site_heredocs()
        expected = {
            str(p.relative_to(chapter)): p
            for chapter in sorted(SOLUTIONS.glob("ch[1-5]-*")) if chapter.is_dir()
            for p in chapter.rglob("*") if p.is_file() and ".claude" in p.parts
        }
        self.assertEqual(sorted(found), sorted(expected), "教材貼的檔案清單要與 solutions/ch*/.claude/** 完全一致")
        for path, (chapter, body) in found.items():
            with self.subTest(path=path, chapter=chapter):
                self.assertEqual(body.encode("utf-8"), expected[path].read_bytes(), "{} 與 solutions 的內容有漂移".format(path))

    @unittest.skipUnless(SITE_DOCS.is_dir(), "找不到 ../site/src/content/docs（單獨 clone 練習 repo 時跳過）")
    def test_11_capstone_heredocs_match_solutions_and_never_paste_the_tools(self):
        found = site_heredocs("06-capstone.mdx")
        self.assertIn("SPEC.md", found, "期末作業頁要把 SPEC.md 貼給讀者")
        for path, (page, body) in found.items():
            with self.subTest(path=path):
                self.assertFalse(path.startswith(".claude/"), "{} 不該貼在期末作業頁：四份工具檔要讀者自己寫".format(path))
                target = SOLUTIONS / "capstone" / path
                self.assertTrue(target.is_file(), "solutions/capstone/{} 不存在".format(path))
                self.assertEqual(body.encode("utf-8"), target.read_bytes(), "{} 與 solutions/capstone 的內容有漂移".format(path))


if __name__ == "__main__":
    unittest.main()
