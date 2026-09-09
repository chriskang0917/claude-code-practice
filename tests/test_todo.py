"""todo CLI 的 unittest：add / list / done / remove / 空清單 / 錯誤編號。"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import todo  # noqa: E402


class TodoCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        os.environ["TODO_FILE"] = str(self.tmp / "todo.json")

    def tearDown(self):
        os.environ.pop("TODO_FILE", None)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = todo.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_add_creates_item(self):
        code, out, _ = self.run_cli("add", "買牛奶")
        self.assertEqual(code, 0)
        self.assertIn("已新增 #1: 買牛奶", out)
        self.assertEqual(todo.load_items(), [{"text": "買牛奶", "done": False}])

    def test_list_shows_items_in_order(self):
        self.run_cli("add", "第一件")
        self.run_cli("add", "第二件")
        code, out, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["[ ] 1. 第一件", "[ ] 2. 第二件"])

    def test_done_marks_item(self):
        self.run_cli("add", "寫測試")
        code, out, _ = self.run_cli("done", "1")
        self.assertEqual(code, 0)
        self.assertIn("已完成 #1", out)
        self.assertTrue(todo.load_items()[0]["done"])
        _, listed, _ = self.run_cli("list")
        self.assertEqual(listed.splitlines(), ["[x] 1. 寫測試"])

    def test_list_empty(self):
        code, out, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("清單是空的", out)

    def test_done_bad_number(self):
        self.run_cli("add", "只有一件")
        for bad in ("0", "2", "abc"):
            code, _, err = self.run_cli("done", bad)
            self.assertEqual(code, 1, bad)
            self.assertIn("編號不存在", err)
        self.assertFalse(todo.load_items()[0]["done"])

    def test_remove_deletes_item_and_renumbers(self):
        self.run_cli("add", "第一件")
        self.run_cli("add", "第二件")
        self.run_cli("add", "第三件")
        code, out, _ = self.run_cli("remove", "2")
        self.assertEqual(code, 0)
        self.assertIn("已移除 #2: 第二件", out)
        self.assertEqual(
            todo.load_items(),
            [{"text": "第一件", "done": False}, {"text": "第三件", "done": False}],
        )
        _, listed, _ = self.run_cli("list")
        self.assertEqual(listed.splitlines(), ["[ ] 1. 第一件", "[ ] 2. 第三件"])

    def test_remove_bad_number(self):
        self.run_cli("add", "只有一件")
        for bad in ("0", "2", "abc"):
            code, _, err = self.run_cli("remove", bad)
            self.assertEqual(code, 1, bad)
            self.assertIn("編號不存在：{}".format(bad), err)
        self.assertEqual(todo.load_items(), [{"text": "只有一件", "done": False}])

    def test_usage_on_unknown_command(self):
        code, _, err = self.run_cli("nope")
        self.assertEqual(code, 1)
        self.assertIn("用法", err)


if __name__ == "__main__":
    unittest.main()
