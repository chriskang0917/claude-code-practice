"""各章參考解答的 unittest。

spec_gate.py 的六個案例都在獨立暫存目錄下跑 subprocess；env 從 os.environ 複製並移除
CLAUDE_PROJECT_DIR（除非案例指定），避免受外層 Claude Code session 影響。
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS = ROOT / "solutions"
SPEC_GATE = SOLUTIONS / "ch4-hooks" / ".claude" / "hooks" / "spec_gate.py"


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
        "ch1-multisession/README.md",
        "ch2-workflow/.claude/workflows/review-flow.js",
        "ch3-subagent/.claude/agents/reviewer.md",
        "ch4-hooks/.claude/settings.json",
        "ch4-hooks/.claude/hooks/spec_gate.py",
        "ch5-skills/.claude/skills/changelog/SKILL.md",
    ]

    def test_7_solution_files_exist_and_have_required_fields(self):
        for rel in self.FILES:
            self.assertTrue((SOLUTIONS / rel).is_file(), rel)
        for rel in ("ch3-subagent/.claude/agents/reviewer.md", "ch5-skills/.claude/skills/changelog/SKILL.md"):
            fm = frontmatter(SOLUTIONS / rel)
            self.assertRegex(fm, r"(?m)^name:\s*\S", rel)
            self.assertRegex(fm, r"(?m)^description:\s*\S", rel)
        flow = (SOLUTIONS / "ch2-workflow/.claude/workflows/review-flow.js").read_text(encoding="utf-8")
        self.assertIn("export const meta", flow)
        self.assertRegex(flow, r"name:\s*'review-flow'")
        settings = json.loads((SOLUTIONS / "ch4-hooks/.claude/settings.json").read_text(encoding="utf-8"))
        self.assertIn("PreToolUse", settings["hooks"])


if __name__ == "__main__":
    unittest.main()
