import json
import unittest

from workbench import installplan, unfinished

H1, H2, H3 = "1" * 64, "2" * 64, "3" * 64
PROJECT = "a" * 64


def good(**changes):
    values = dict(command="install", project=PROJECT, version="0.1.0",
                  files=[("AGENTS.md", "create", None, H1), ("docs/a.md", "replace", H2, H3)],
                  dirs=[".workbench", "docs"], git=installplan.GIT_SKELETON,
                  store=[("projects/%s/baselines" % PROJECT, None, H1)])
    values.update(changes)
    return unfinished.build(**values)


def edited(**changes):
    """The record of `good()` with some top-level keys replaced, in the writer's own layout."""
    document = json.loads(good())
    document.update(changes)
    return (json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n").encode("ascii")


class Build(unittest.TestCase):
    def test_a_record_reads_back_as_it_was_built(self):
        record = unfinished.parse(good())
        self.assertEqual(("install", PROJECT, "0.1.0"), record[:3])
        self.assertEqual((".workbench", "docs"), record.dirs)
        self.assertEqual(
            [unfinished.FileWrite("AGENTS.md", "create", None, H1),
             unfinished.FileWrite("docs/a.md", "replace", H2, H3)], list(record.files))
        self.assertEqual(unfinished.StoreWrite("projects/%s/baselines" % PROJECT, None, H1),
                         record.store[0])

    def test_the_git_skeleton_is_recorded_with_a_hash_for_each_file_and_none_for_a_directory(self):
        record = unfinished.parse(good())
        by_path = {g.path: g.hash for g in record.git}
        self.assertEqual(len(installplan.GIT_SKELETON), len(record.git))
        self.assertIsNone(by_path["objects"])
        self.assertEqual(unfinished.sha(b"ref: refs/heads/main\n"), by_path["HEAD"])

    def test_the_same_plan_always_gives_the_same_bytes(self):
        self.assertEqual(good(), good())

    def test_an_unknown_project_is_allowed_and_a_plan_may_record_nothing_else(self):
        record = unfinished.parse(good(project=None, dirs=[], git=[], store=[], files=[]))
        self.assertEqual((None, (), (), (), ()), (record.project, record.dirs, record.files,
                                                  record.git, record.store))

    def test_a_plan_that_cannot_be_read_back_is_refused_when_it_is_built(self):
        for changes in (
                {"command": "recover"}, {"files": [("../x", "create", None, H1)]},
                {"files": [(".workbench/local/incomplete", "create", None, H1)]},
                {"files": [("AGENTS.md", "create", None, H1)] * 2},
                {"files": [("a", "create", None, "nothex")]},
                {"files": [("a", "replace", None, H1)]},
                {"files": [("a", "create", H1, H1)]},
                {"dirs": [".workbench/local"]}, {"dirs": ["a", "a"]},
                {"dirs": ["docs"], "files": [("docs", "create", None, H1)]},
                {"store": [("../x", None, H1)]}, {"git": [("../x", None)]},
                {"version": "bad version"}, {"project": "short"}):
            with self.subTest(changes), self.assertRaises(unfinished.UnfinishedError):
                good(**changes)

    def test_a_record_over_the_size_bound_is_refused_when_it_is_built(self):
        files = [("dir/file-%06d.md" % n, "create", None, H1) for n in range(12000)]
        with self.assertRaises(unfinished.UnfinishedError):
            good(files=files)


class Bounds(unittest.TestCase):
    def test_a_record_with_too_many_entries_is_refused(self):
        count = unfinished.MAX_ENTRIES + 1
        with self.assertRaises(unfinished.UnfinishedError):
            good(dirs=["d%d" % n for n in range(count)], git=[], store=[], files=[])
        with self.assertRaises(unfinished.UnfinishedError):
            good(dirs=["d%d" % n for n in range(count // 2 + 1)], git=[], store=[],
                 files=[("f%d" % n, "create", None, H1) for n in range(count // 2 + 1)])

    def test_the_most_entries_allowed_read_back(self):
        record = unfinished.parse(good(dirs=["d%d" % n for n in range(unfinished.MAX_ENTRIES - 3)],
                                       git=[], store=[], files=[("f", "create", None, H1)]))
        self.assertEqual(unfinished.MAX_ENTRIES - 3, len(record.dirs))


class Parse(unittest.TestCase):
    def refused(self, data):
        with self.assertRaises(unfinished.UnfinishedError):
            unfinished.parse(data)

    def test_an_empty_marker_is_no_record(self):
        with self.assertRaises(unfinished.UnfinishedError) as caught:
            unfinished.parse(b"")
        self.assertIn("no record", str(caught.exception))

    def test_a_marker_that_is_not_json_is_refused(self):
        for data in (b"not json", b"{", b"[]", b"null", b'{"a":1}\n\xff', b"\xff\xfe",
                     good()[:-5], good()[:40], good() + b"x"):
            with self.subTest(data[:20]):
                self.refused(data)

    def test_text_that_is_not_bytes_is_refused(self):
        self.refused(good().decode())
        self.refused(None)

    def test_an_oversized_marker_is_refused(self):
        self.refused(good() + b" " * (2 * 1024 * 1024))

    def test_a_deeply_nested_marker_is_refused(self):
        self.refused(b"[" * 100000)
        self.refused(b'{"a":' * 100 + b"1" + b"}" * 100)

    def test_unknown_missing_or_duplicate_keys_are_refused(self):
        document = json.loads(good())
        self.refused(json.dumps(dict(document, extra=1)).encode())
        del document["store"]
        self.refused(json.dumps(document).encode())
        text = good().decode().replace('"format":1', '"format":1,"format":1')
        self.refused(text.encode())

    def test_other_types_and_formats_are_refused(self):
        for changes in ({"format": 2}, {"format": True}, {"format": "1"}, {"command": "x"},
                        {"command": ["install"]}, {"project": 5}, {"workbench": ""},
                        {"workbench": 3}, {"files": {}}, {"dirs": "x"}, {"git": None},
                        {"store": 1}):
            with self.subTest(changes):
                self.refused(edited(**changes))

    def test_bad_file_entries_are_refused(self):
        def entry(**changes):
            base = {"after": H1, "before": None, "op": "create", "path": "a"}
            base.update(changes)
            return [base]

        for files in (
                entry(path="/etc/passwd"), entry(path="../a"), entry(path="a/../b"),
                entry(path=""), entry(path=5), entry(path="a\\b"), entry(path=".git/config"),
                entry(path=".workbench/local/incomplete"), entry(path=".workbench/local/x"),
                entry(path=".workbench/local"), entry(after="ABC"), entry(after=None),
                entry(before="x"), entry(op="delete"), entry(op="replace"),
                entry() + entry(), [{"after": H1, "before": None, "op": "create"}],
                [{"after": H1, "before": None, "op": "create", "path": "a", "x": 1}],
                ["a"], [[]]):
            with self.subTest(files):
                self.refused(edited(files=files))

    def test_bad_directory_git_and_store_entries_are_refused(self):
        for changes in (
                {"dirs": ["/x"]}, {"dirs": ["a", "a"]}, {"dirs": [".workbench/local"]},
                {"dirs": [".git"]}, {"dirs": [5]}, {"dirs": [None]},
                {"git": [{"path": "../x", "hash": None}]},
                {"git": [{"path": "objects", "hash": "bad"}]},
                {"git": [{"path": "objects", "hash": None}] * 2},
                {"git": [{"path": "objects"}]}, {"git": ["objects"]},
                {"store": [{"path": "../x", "before": None, "after": H1}]},
                {"store": [{"path": "/x", "before": None, "after": H1}]},
                {"store": [{"path": "a", "before": None, "after": "bad"}]},
                {"store": [{"path": "a", "before": "bad", "after": H1}]},
                {"store": [{"path": "a", "before": None, "after": H1}] * 2}, {"store": [{"path": "a", "after": H1}]}):
            with self.subTest(changes):
                self.refused(edited(**changes))

    def test_a_record_not_in_the_writers_layout_is_refused(self):
        document = json.loads(good())
        for data in (json.dumps(document, indent=2).encode(),
                     json.dumps(document, sort_keys=True).encode(),
                     good().rstrip(b"\n"), good().replace(b",", b", ", 1)):
            with self.subTest(data[:30]):
                self.refused(data)

    def test_a_path_may_not_be_both_a_file_and_a_directory(self):
        self.refused(edited(dirs=["AGENTS.md"]))

    def test_a_lone_surrogate_is_refused(self):
        data = edited(workbench="v1").replace(b'"v1"', b'"\\ud800"')
        self.assertIn(b"\\ud800", data)
        with self.assertRaises(unfinished.UnfinishedError):
            unfinished.parse(data)

    def test_the_local_directory_is_refused_however_its_name_is_spelled(self):
        for path in (".workbench/LOCAL/x", ".Workbench/Local/incomplete", ".workbench/local /x",
                     ".workbench/local./x", ".WORKBENCH/LOCAL", ".workbench/Local"):
            with self.subTest(path):
                self.refused(edited(files=[{"after": H1, "before": None, "op": "create",
                                            "path": path}]))
                self.refused(edited(dirs=[path]))
        self.assertTrue(unfinished.parse(edited(dirs=[".workbench/localx", ".workbench"])))

    def test_paths_that_collide_on_a_case_insensitive_filesystem_are_refused(self):
        def entry(path):
            return {"after": H1, "before": None, "op": "create", "path": path}

        for files in ([entry("A"), entry("a")], [entry("\u00e9"), entry("e\u0301")],
                      [entry("a"), entry("a/b")], [entry("a "), entry("a")]):
            with self.subTest(files):
                self.refused(edited(files=files, dirs=[]))
        for dirs in (["a", "A"], ["docs", "Docs "]):
            with self.subTest(dirs):
                self.refused(edited(dirs=dirs, files=[]))
        self.refused(edited(dirs=["DOCS"], files=[entry("docs")]))
        self.refused(edited(dirs=["a/b"], files=[entry("A")]))
        self.refused(edited(git=[{"path": "HEAD", "hash": None},
                                 {"path": "head", "hash": None}]))
        self.refused(edited(store=[{"path": "a/B", "before": None, "after": H1},
                                 {"path": "A/b", "before": None, "after": H1}]))
        self.assertTrue(unfinished.parse(edited(dirs=["docs/sub"], files=[entry("docs/a.md")])))


if __name__ == "__main__":
    unittest.main()
