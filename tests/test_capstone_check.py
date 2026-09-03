"""期末作業驗收腳本（capstone/check.py）的 unittest。

- 用 solutions/capstone 在暫存目錄組出一個「做完的」repo（工具鏈 commit → feat／docs 兩條分支 --no-ff merge → release commit ＋ tag）：
  整支腳本要印 CAPSTONE_OK 且 exit 0。
- 乾淨的 base repo：要印 CAPSTONE_FAIL、exit 1，且每個交付物都被點名。
- 反向：對做完的 repo 做單點破壞（hook 不擋、agent 可寫、skill 少欄位、workflow 少 filter、tag 刪掉…），對應的檢查項要變 ✗。
- remove.patch 要能乾淨套在乾淨的 src/ 與 tests/ 上（參考解答不能漂移）。

基底檔案（src/、tests/test_todo.py、README.md）優先取工作樹；學員做完 remove 之後工作樹套不上 patch，
就改取 origin/main（學員從不 push，它永遠是乾淨的 main）；兩者都不行才跳過。
維護者工作區（找得到 ../site）不退回 origin/main：工作樹套不上就直接 fail，漂移才會立刻被看到。
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPSTONE = ROOT / "solutions" / "capstone"
CHECK = ROOT / "capstone" / "check.py"
PATCH = CAPSTONE / "remove.patch"
MAINTAINER = (ROOT.parent / "site" / "src" / "content" / "docs").is_dir()
BASE_FILES = ["src/todo.py", "tests/__init__.py", "tests/test_todo.py", "README.md", ".gitignore"]

spec = importlib.util.spec_from_file_location("capstone_check", CHECK)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)  # type: ignore[union-attr]


def sh(cwd: Path, *cmd: str) -> subprocess.CompletedProcess:
    proc = subprocess.run(list(cmd), cwd=str(cwd), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError("{} 失敗：{}{}".format(" ".join(cmd), proc.stdout, proc.stderr))
    return proc


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return sh(cwd, "git", *args)


def tree_files(ref):
    """讀基底檔案：ref=None 讀工作樹，否則 git show <ref>:<path>。任一檔讀不到回 None。"""
    files = {}
    for rel in BASE_FILES:
        if ref is None:
            path = ROOT / rel
            if not path.is_file():
                return None
            files[rel] = path.read_bytes()
        else:
            proc = subprocess.run(["git", "show", "{}:{}".format(ref, rel)], cwd=str(ROOT), capture_output=True, check=False)
            if proc.returncode != 0:
                return None
            files[rel] = proc.stdout
    return files


def write_files(dst: Path, files) -> None:
    for rel, data in files.items():
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        (dst / rel).write_bytes(data)


def patch_applies(files) -> bool:
    tmp = Path(tempfile.mkdtemp(prefix="capstone-probe-"))
    try:
        write_files(tmp, files)
        return subprocess.run(["git", "apply", "--check", str(PATCH)], cwd=str(tmp), capture_output=True, check=False).returncode == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def load_base():
    """回傳 (基底檔案, 來源說明)；找不到能套 patch 的基底就回 (None, 原因)。"""
    working = tree_files(None)
    if working and patch_applies(working):
        return working, "工作樹"
    if MAINTAINER:
        return None, "維護者工作區：remove.patch 套不上工作樹的 src/、tests/（參考解答漂移了）"
    remote = tree_files("origin/main")
    if remote and patch_applies(remote):
        return remote, "origin/main"
    return None, "工作樹已不是乾淨的 main，也沒有能套 remove.patch 的 origin/main"


BASE, BASE_NOTE = load_base()


def copy_base(dst: Path) -> None:
    """只放練習 repo 的「產品」部分：src/、tests/{__init__,test_todo}.py、README.md、.gitignore。"""
    write_files(dst, BASE)


def init_repo(dst: Path) -> None:
    git(dst, "init", "-q")
    git(dst, "symbolic-ref", "HEAD", "refs/heads/main")
    git(dst, "config", "user.name", "capstone-test")
    git(dst, "config", "user.email", "capstone-test@example.invalid")
    git(dst, "config", "commit.gpgsign", "false")
    git(dst, "add", "-A")
    git(dst, "commit", "-qm", "chore: base")


def build_base_repo() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="capstone-base-")).resolve()
    copy_base(tmp)
    init_repo(tmp)
    return tmp


def build_solution_repo() -> Path:
    """照教材的流程把 solutions/capstone 組成一個做完的 repo。"""
    tmp = build_base_repo()
    shutil.copytree(CAPSTONE / ".claude", tmp / ".claude")
    shutil.copy(CAPSTONE / "SPEC.md", tmp / "SPEC.md")
    git(tmp, "add", "-A")
    git(tmp, "commit", "-qm", "chore: release 工具鏈與 remove 規格")

    git(tmp, "checkout", "-qb", "worktree-feat")
    git(tmp, "apply", str(CAPSTONE / "remove.patch"))
    git(tmp, "add", "-A")
    git(tmp, "commit", "-qm", "feat: add remove command")

    git(tmp, "checkout", "-q", "main")
    git(tmp, "checkout", "-qb", "worktree-docs")
    with (tmp / "README.md").open("a", encoding="utf-8") as fh:
        fh.write("\n## remove\n\n```bash\npython3 src/todo.py remove 1\n```\n\n移除後剩下的項目會重新從 1 編號。\n")
    git(tmp, "add", "-A")
    git(tmp, "commit", "-qm", "docs: document remove command")

    git(tmp, "checkout", "-q", "main")
    git(tmp, "merge", "-q", "--no-ff", "--no-edit", "worktree-feat")
    git(tmp, "merge", "-q", "--no-ff", "--no-edit", "worktree-docs")
    git(tmp, "branch", "-qD", "worktree-feat", "worktree-docs")

    feat_sha = git(tmp, "log", "--format=%h", "--grep=feat: add remove").stdout.split()[0]
    date = git(tmp, "log", "-1", "--format=%cs").stdout.strip()
    (tmp / "CHANGELOG.md").write_text(
        "## 1.0.0 ({})\n\n### feat\n- add remove command（{}）\n\n### docs\n- document remove command\n".format(date, feat_sha),
        encoding="utf-8",
    )
    git(tmp, "add", "-A")
    git(tmp, "commit", "-qm", "chore: release 1.0.0")
    git(tmp, "tag", "v1.0.0")
    return tmp


def clone_repo(src: Path) -> Path:
    dst = Path(tempfile.mkdtemp(prefix="capstone-mut-")).resolve()
    shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)
    return dst


def run_check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECK), "--root", str(root)], capture_output=True, text=True, check=False)


def ids(results) -> dict:
    return {r.id: r for r in results}


@unittest.skipUnless(BASE, BASE_NOTE)
class SolutionRepoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = build_solution_repo()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.repo, ignore_errors=True)

    def test_1_solution_repo_prints_capstone_ok(self):
        proc = run_check(self.repo)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("CAPSTONE_OK", proc.stdout)
        self.assertNotIn("✗", proc.stdout)
        self.assertIn("v1.0.0 →", proc.stdout)

    def test_2_every_result_ok_or_skipped(self):
        for title, results in check.run_all(self.repo):
            for r in results:
                self.assertTrue(r.ok or r.skipped, "{}：{} — {}".format(title, r.id, r.text))
                if r.id == "workflow.stub" and check.NODE:
                    self.assertTrue(r.ok, r.text)


class BaseRepoTest(unittest.TestCase):
    @unittest.skipUnless(BASE, BASE_NOTE)
    def test_3_clean_repo_fails_and_names_every_deliverable(self):
        repo = build_base_repo()
        try:
            proc = run_check(repo)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("CAPSTONE_FAIL", proc.stdout)
            failed = {r.id for _, results in check.run_all(repo) for r in results if r.failed}
            for expected in ("hook.settings", "skill.exists", "agent.exists", "workflow.exists",
                             "git.merges", "feature.remove", "feature.usage", "feature.tests_exist",
                             "docs.readme", "release.changelog", "release.tag"):
                self.assertIn(expected, failed)
            self.assertNotIn("release.clean", failed, "乾淨 repo 的工作樹本來就乾淨")
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    def test_4_not_a_practice_repo_exits_2(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            proc = run_check(tmp)
            self.assertEqual(proc.returncode, 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(BASE, BASE_NOTE)
class MutationTest(unittest.TestCase):
    """單點破壞做完的 repo，對應的檢查項必須變 ✗（其餘同組項目不受影響的就該還是 ✓）。"""

    @classmethod
    def setUpClass(cls):
        cls.solution = build_solution_repo()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.solution, ignore_errors=True)

    def mutated(self) -> Path:
        repo = clone_repo(self.solution)
        self.addCleanup(shutil.rmtree, repo, True)
        return repo

    def test_5_hook_that_never_blocks(self):
        repo = self.mutated()
        (repo / ".claude" / "hooks" / "push_gate.py").write_text("import sys\nsys.stdin.read()\nsys.exit(0)\n", encoding="utf-8")
        r = ids(check.check_hook(repo))
        self.assertTrue(r["hook.blocks_push"].failed)
        self.assertTrue(r["hook.allows_others"].ok)

    def test_6_hook_that_greps_push_anywhere(self):
        repo = self.mutated()
        (repo / ".claude" / "hooks" / "push_gate.py").write_text(
            "import sys\ntext = sys.stdin.read()\n"
            "if 'push' in text:\n    print('已擋下', file=sys.stderr)\n    sys.exit(2)\nsys.exit(0)\n",
            encoding="utf-8",
        )
        r = ids(check.check_hook(repo))
        self.assertTrue(r["hook.blocks_push"].ok)
        self.assertTrue(r["hook.allows_others"].failed, "echo push 不是 git push，不該被擋")

    def test_7_settings_matcher_not_bash(self):
        repo = self.mutated()
        path = repo / ".claude" / "settings.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"Bash"', '"Edit|Write"'), encoding="utf-8")
        r = ids(check.check_hook(repo))
        self.assertTrue(r["hook.settings_bash"].failed)
        self.assertTrue(r["hook.settings"].ok)

    def test_8_agent_with_write_tool_is_not_readonly(self):
        repo = self.mutated()
        path = repo / ".claude" / "agents" / "doc-checker.md"
        path.write_text(path.read_text(encoding="utf-8").replace("tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Write"), encoding="utf-8")
        r = ids(check.check_agent(repo))
        self.assertTrue(r["agent.readonly"].failed)
        self.assertTrue(r["agent.frontmatter"].ok)

    def test_9_skill_without_disable_model_invocation(self):
        repo = self.mutated()
        path = repo / ".claude" / "skills" / "release" / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8").replace("disable-model-invocation: true\n", ""), encoding="utf-8")
        r = ids(check.check_skill(repo))
        self.assertTrue(r["skill.frontmatter"].failed)
        self.assertIn("disable-model-invocation", r["skill.frontmatter"].text)
        self.assertTrue(r["skill.body"].ok)

    def test_10_workflow_without_filter_boolean(self):
        repo = self.mutated()
        path = repo / ".claude" / "workflows" / "ship-check.js"
        path.write_text(path.read_text(encoding="utf-8").replace(".filter(Boolean)", ""), encoding="utf-8")
        r = ids(check.check_workflow(repo))
        self.assertTrue(r["workflow.static"].failed)
        self.assertIn("filter(Boolean)", r["workflow.static"].text)

    @unittest.skipUnless(check.NODE, "找不到 node，跳過 stub 執行的反向案例")
    def test_11_workflow_parallel_without_thunks_fails_stub(self):
        repo = self.mutated()
        path = repo / ".claude" / "workflows" / "ship-check.js"
        src = path.read_text(encoding="utf-8").replace("() => agent(", "agent(")
        path.write_text(src, encoding="utf-8")
        r = ids(check.check_workflow(repo))
        self.assertTrue(r["workflow.static"].failed)
        self.assertTrue(r["workflow.stub"].failed)

    def test_12_missing_tag_and_dirty_tree(self):
        repo = self.mutated()
        git(repo, "tag", "-d", "v1.0.0")
        (repo / "README.md").write_text("changed\n", encoding="utf-8")
        r = ids(check.check_release(repo))
        self.assertTrue(r["release.tag"].failed)
        self.assertTrue(r["release.clean"].failed)
        self.assertTrue(r["release.changelog"].ok)

    def test_13_fast_forward_merge_leaves_no_merge_node(self):
        repo = self.mutated()
        # 把 main 重設到 base，再 fast-forward 一個 commit：沒有 merge 節點
        git(repo, "reset", "-q", "--hard", "HEAD~4")
        r = ids(check.check_parallel(repo))
        self.assertTrue(r["git.merges"].failed)
        self.assertTrue(r["feature.remove"].failed, "reset 回 base 之後 remove 也不在了")


class ReferencePatchTest(unittest.TestCase):
    def test_14_remove_patch_applies_cleanly_to_pristine_tree(self):
        self.assertIsNotNone(BASE, BASE_NOTE)
        if MAINTAINER:
            self.assertEqual(BASE_NOTE, "工作樹", "維護者工作區的 src/、tests/ 必須能直接套 remove.patch")
        tmp = Path(tempfile.mkdtemp(prefix="capstone-patch-")).resolve()
        try:
            copy_base(tmp)
            git(tmp, "apply", str(CAPSTONE / "remove.patch"))
            proc = subprocess.run([sys.executable, "-m", "unittest", "tests.test_todo"], cwd=str(tmp), capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("remove", (tmp / "src" / "todo.py").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
