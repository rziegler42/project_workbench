"""The `code-work` helper's `shared` subcommand: the shared branches a project declares.

Plan `2026-10-23-push-checkpoint`, increment B. The file is `.workbench/shared-branches.json`,
`{"format": 1, "shared": ["name", ...]}`. It is read without following a link and is bounded; anything that is
not exactly that is refused, because the answer is read as the list of branches a push stops for. The helper
runs no program and holds no git code, which the source tests of the helper already assert for the whole file."""

import json
import os
import unittest

from test_codework_helper import Project

FILE = ".workbench/shared-branches.json"
MAX_FILE = 8192


def declared(*names, **more):
    document = {"format": 1, "shared": list(names)}
    document.update(more)
    return json.dumps(document)


class Shared(Project):
    def shared(self, cwd=None):
        return self.check("shared", cwd=cwd)

    def listed(self):
        code, out, err = self.shared()
        self.assertEqual((0, ""), (code, err), out)
        self.assertTrue(out.endswith("\n") and out.count("\n") == 1, out)
        report = json.loads(out)
        self.assertEqual(["format", "shared"], sorted(report))
        self.assertEqual(1, report["format"])
        self.assertTrue(out.isascii())
        return report["shared"]

    def refused(self, contains=""):
        code, out, err = self.shared()
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertTrue(err.isascii(), err)
        return err


class Reading(Shared):
    def test_no_file_lists_none(self):
        self.assertEqual([], self.listed())

    def test_the_declared_names_are_listed_in_file_order(self):
        self.write(FILE, declared("release", "dev/next", "v1.x", "a_b-c.d"))
        self.assertEqual(["release", "dev/next", "v1.x", "a_b-c.d"], self.listed())

    def test_an_empty_list_is_a_list(self):
        self.write(FILE, declared())
        self.assertEqual([], self.listed())

    def test_it_runs_from_a_directory_below_the_root(self):
        self.write(FILE, declared("release"))
        self.assertEqual((0, ""), self.shared(cwd=os.path.join(self.place, "docs"))[::2])

    def test_it_changes_nothing(self):
        self.write(FILE, declared("release"))
        before = self.snapshot()
        self.assertEqual(0, self.shared()[0])
        self.assertEqual(before, self.snapshot())

    def test_it_takes_no_argument(self):
        for argv in (["shared", "x"], ["shared", "--all"], ["shared", FILE]):
            with self.subTest(argv):
                code, out, err = self.check(*argv)
                self.assertEqual((1, ""), (code, out))
                self.assertTrue(err.startswith("refused: usage"), err)

    def test_it_is_listed_in_the_usage(self):
        code, out, err = self.check("nothing")
        self.assertEqual(1, code)
        self.assertIn("shared", err)


class Refusing(Shared):
    def test_a_name_that_is_not_a_branch_name_is_refused(self):
        for name in ("", "-x", "a b", "a..b", "a//b", "a/", "a.", "/a", ".hidden", "a/.b", "a.lock", "a/b.lock",
                     "a@{1}", "a\nb", "a\x00b", "café", "a*", "a?", "a~1", "a^", "a:b", "a\\b", "x" * 201,
                     "refs/heads/a b"):
            with self.subTest(name=name):
                self.write(FILE, json.dumps({"format": 1, "shared": [name]}))
                self.refused("shared-branches.json")

    def test_a_name_that_is_not_text_is_refused(self):
        for value in (1, None, True, ["a"], {"a": 1}, 1.5):
            with self.subTest(value=value):
                self.write(FILE, json.dumps({"format": 1, "shared": [value]}))
                self.refused()

    def test_a_repeated_name_is_refused(self):
        self.write(FILE, declared("a", "b", "a"))
        self.refused("more than once")

    def test_more_than_64_names_are_refused_and_64_are_read(self):
        self.write(FILE, declared(*["b%d" % n for n in range(64)]))
        self.assertEqual(64, len(self.listed()))
        self.write(FILE, declared(*["b%d" % n for n in range(65)]))
        self.refused("64")

    def test_a_name_of_200_bytes_is_read_and_one_of_201_is_not(self):
        self.write(FILE, declared("x" * 200))
        self.assertEqual(["x" * 200], self.listed())

    def test_the_wrong_shape_is_refused(self):
        for text in ('{"format": 1}', '{"shared": []}', '{"format": 2, "shared": []}', '{"format": "1", "shared": []}',
                     '{"format": true, "shared": []}', '{"format": 1.0, "shared": []}',
                     '{"format": 1, "shared": "main"}', '{"format": 1, "shared": null}',
                     '{"format": 1, "shared": {}}', '{"format": 1, "shared": [], "extra": 1}',
                     '[]', '"x"', 'null', '1', '', '   ', '{', '{"format": 1, "shared": [],}', 'NaN',
                     '{"format": 1, "shared": [] } trailing', '{"format": 1, "shared": ["a"]}\x00'):
            with self.subTest(text=text):
                self.write(FILE, text)
                self.refused("shared-branches.json")

    def test_a_repeated_key_is_refused(self):
        self.write(FILE, '{"format": 1, "shared": ["a"], "shared": []}')
        self.refused("more than once")
        self.write(FILE, '{"format": 1, "format": 1, "shared": []}')
        self.refused("more than once")

    def test_text_that_is_not_utf8_is_refused(self):
        self.write(FILE, b'{"format": 1, "shared": ["\xff"]}')
        self.refused("shared-branches.json")

    def test_a_file_over_the_bound_is_refused_and_one_at_the_bound_is_read(self):
        text = declared("a")
        self.write(FILE, text + " " * (MAX_FILE - len(text)))
        self.assertEqual(["a"], self.listed())
        self.write(FILE, text + " " * (MAX_FILE - len(text) + 1))
        self.refused("larger than")

    def test_a_link_is_not_followed(self):
        self.write("elsewhere.json", declared("release"))
        os.symlink(os.path.join(self.place, "elsewhere.json"), os.path.join(self.place, *FILE.split("/")))
        self.refused("shared-branches.json")

    def test_a_dangling_link_is_refused_and_not_taken_for_a_missing_file(self):
        os.symlink(os.path.join(self.place, "nowhere.json"), os.path.join(self.place, *FILE.split("/")))
        self.refused("shared-branches.json")

    def test_a_directory_or_a_pipe_in_its_place_is_refused(self):
        os.mkdir(os.path.join(self.place, *FILE.split("/")))
        self.refused("shared-branches.json")
        os.rmdir(os.path.join(self.place, *FILE.split("/")))
        os.mkfifo(os.path.join(self.place, *FILE.split("/")))
        self.refused("shared-branches.json")

    def test_nothing_in_a_name_reaches_the_message_except_as_escapes(self):
        self.write(FILE, json.dumps({"format": 1, "shared": ["a\x1b[31m‮\ud83d"]}, ensure_ascii=False)
                   .encode("utf-8", "surrogatepass"))
        err = self.refused()
        self.assertNotIn("\x1b", err)


if __name__ == "__main__":
    unittest.main()
