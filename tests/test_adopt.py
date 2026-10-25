"""``wb adopt``: install into a repository that has content, changing no file that is there."""

import io
import json
import os
import unittest
import unittest.mock

from tests.test_adopt_preview import OWN_AGENTS, SEED, AdoptPreviewBase, sha
from tests.test_install import Typist, correct
from tests.test_recover import run_recover, shape
from workbench import approve, cli, install, manifest, projectfs, sources

MARKER = os.path.join(".workbench", "local", "incomplete")
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_TRUNC | os.O_APPEND


class AdoptBase(AdoptPreviewBase):
    def run_adopt(self, place, path, reply=correct, select=("h", "notes"), seed=SEED):
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(path, None)], list(select))
        code = install.run(self.guarded, command, Typist(out, reply), out, err, seed=seed,
                           adopt=True)
        return code, out.getvalue(), err.getvalue()

    def hashes(self, place, rels):
        found = {}
        for rel in rels:
            with open(os.path.join(place, *rel.split("/")), "rb") as handle:
                found[rel] = sha(handle.read())
        return found

    def store_text(self, *parts):
        with open(os.path.join(self.store_root, *parts), "rb") as handle:
            return handle.read()


class AdoptWriteTest(AdoptBase):
    def test_adopt_creates_what_is_missing_and_changes_no_file_that_exists(self):
        path = self.good_set()
        place = self.repo(files={"README.md": b"hello\n", "AGENTS.md": OWN_AGENTS,
                                 "src/app.py": b"print(1)\n"})
        before = self.hashes(place, ["README.md", "AGENTS.md", "src/app.py", ".git/index"])
        code, out, err = self.run_adopt(place, path)
        self.assertEqual(0, code, (out, err))
        self.assertEqual(before, self.hashes(place, list(before)))
        for rel in ("docs/README.md", "docs/notes.md", ".workbench/manifest.json",
                    ".workbench/.gitignore"):
            self.assertTrue(os.path.isfile(os.path.join(place, rel)), rel)
        self.assertFalse(os.path.exists(os.path.join(place, MARKER)))
        self.assertIn("nothing was committed", out)

    def test_adopt_attaches_nothing_and_says_so(self):
        path = self.good_set()
        place = self.repo()
        code, out, err = self.run_adopt(place, path)
        self.assertEqual(0, code, (out, err))
        self.assertIn("wb attach", out)
        self.assertNotIn("attached p/h", out)
        self.assertFalse(os.path.exists(os.path.join(place, ".workbench", "local", "harness.json")))
        self.assertEqual([".git", ".workbench", "AGENTS.md", "README.md", "docs"],
                         sorted(os.listdir(place)))

    def test_adopt_counts_what_it_created_kept_and_did_not_fill(self):
        path = self.good_set(with_policy=True)
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        code, out, err = self.run_adopt(place, path, select=("h", "notes", "policy"))
        self.assertEqual(0, code, (out, err))
        self.assertIn("kept 1 existing file", out)
        self.assertIn("1 block not filled", out)
        self.assertIn("wb upgrade", out)

    def test_the_manifest_records_a_kept_file_at_its_own_hash_and_no_block_for_it(self):
        path = self.good_set(with_policy=True)
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        self.assertEqual(0, self.run_adopt(place, path, select=("h", "notes", "policy"))[0])
        with open(os.path.join(place, ".workbench", "manifest.json"), "rb") as handle:
            document = json.loads(handle.read())
        entries = {(e["path"], e.get("block")): e for e in document["files"]}
        self.assertEqual({"class": "seeded", "hash": sha(OWN_AGENTS), "path": "AGENTS.md"},
                         entries[("AGENTS.md", None)])
        self.assertEqual([], [e for e in document["files"] if "block" in e])

    def test_the_store_holds_the_project_with_the_kept_hash_in_its_baselines(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        self.assertEqual(0, self.run_adopt(place, path)[0])
        project = manifest.project_id(SEED)
        baselines = json.loads(self.store_text("projects", project, "baselines"))["baselines"]
        self.assertEqual(sha(OWN_AGENTS), baselines["AGENTS.md"])
        self.assertEqual(sha(b"# Notes\n"), baselines["docs/notes.md"])
        seen = json.loads(self.store_text("projects", project, "seen"))
        self.assertEqual({"format": 1, "kind": "path", "value": place}, seen)

    def test_no_existing_file_is_ever_opened_for_writing(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS, "CONTRIBUTING.md": b"hello\n"})
        opened = []
        real = os.open

        def watching(name, flags, *args, **kwargs):
            if flags & (WRITE_FLAGS | os.O_CREAT) and "dir_fd" in kwargs:
                opened.append(name)
            return real(name, flags, *args, **kwargs)

        os.supports_dir_fd.add(watching)
        self.addCleanup(os.supports_dir_fd.discard, watching)
        with unittest.mock.patch.object(os, "open", watching):
            code, out, err = self.run_adopt(place, path)
        self.assertEqual(0, code, (out, err))
        self.assertEqual([], [name for name in opened if name in ("AGENTS.md", "CONTRIBUTING.md", "index")])
        self.assertIn("manifest.json", opened)      # the watch does see the files adopt creates

    def test_a_wrong_digest_cancels_and_writes_nothing(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        before = shape(place)
        code, out, err = self.run_adopt(place, path, reply=lambda text: "0" * 12)
        self.assertEqual(1, code)
        self.assertIn("cancelled: nothing was written", out)
        self.assertEqual(before, shape(place))

    def test_a_kept_file_changed_after_the_preview_refuses_and_writes_nothing(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})

        def edit_then_confirm(text):
            with open(os.path.join(place, "AGENTS.md"), "ab") as handle:
                handle.write(b"edited after the preview\n")
            return correct(text)

        code, out, err = self.run_adopt(place, path, reply=edit_then_confirm)
        self.assertEqual(1, code, (out, err))
        self.assertIn("changed", err)
        self.assertFalse(os.path.exists(os.path.join(place, ".workbench")))
        self.assertFalse(os.path.exists(os.path.join(place, "docs")))

    def test_a_missing_path_that_appears_after_the_preview_refuses_and_writes_nothing(self):
        path = self.good_set()
        place = self.repo()

        def appear_then_confirm(text):
            os.makedirs(os.path.join(place, "docs"))
            with open(os.path.join(place, "docs", "notes.md"), "wb") as handle:
                handle.write(b"mine\n")
            return correct(text)

        code, out, err = self.run_adopt(place, path, reply=appear_then_confirm)
        self.assertEqual(1, code, (out, err))
        self.assertFalse(os.path.exists(os.path.join(place, ".workbench")))
        with open(os.path.join(place, "docs", "notes.md"), "rb") as handle:
            self.assertEqual(b"mine\n", handle.read())

    def test_a_conflict_refuses_before_anything_is_asked_or_written(self):
        path = self.good_set()
        place = self.repo(files={"docs": b"a file where a directory is planned\n"})
        before = shape(place)
        code, out, err = self.run_adopt(place, path)
        self.assertEqual(1, code)
        self.assertIn("docs", err)
        self.assertNotIn("digest:", out)
        self.assertEqual(before, shape(place))

    def test_adopt_refuses_a_new_project_and_an_existing_one_with_nothing_written(self):
        path = self.good_set()
        empty = self.place("empty", "empty")
        code, out, err = self.run_adopt(empty, path)
        self.assertEqual(1, code)
        self.assertIn("wb install", err)
        self.assertEqual([], os.listdir(empty))
        done = self.place("done", "missing")
        self.assertEqual(0, self.run_install(done, path)[0])
        before = shape(done)
        code, out, err = self.run_adopt(done, path)
        self.assertEqual(1, code)
        self.assertIn("wb upgrade", err)
        self.assertEqual(before, shape(done))

    def test_adopt_is_refused_without_terminals_before_anything_is_read(self):
        path = self.good_set()
        place = self.repo()
        before = shape(place)
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False):
            code, out, err = self.run_adopt(place, path)
        self.assertEqual(1, code)
        self.assertIn("owner-run", err)
        self.assertIn("preview adopt", err)
        self.assertEqual(before, shape(place))

    def test_the_cli_refuses_adopt_without_terminals(self):
        path = self.good_set()
        place = self.repo()
        before = shape(place)
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False):
            code = cli.main(["adopt", place, "--package", path, "--select", "h", "notes"], out, err,
                            store_root=self.store_root, stdin=io.StringIO(""))
        self.assertEqual(1, code)
        self.assertIn("owner-run", err.getvalue())
        self.assertEqual(before, shape(place))

    def test_the_cli_runs_adopt_for_the_owner(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["adopt", place, "--package", path, "--select", "h", "notes"], out, err,
                        store_root=self.store_root, stdin=Typist(out, correct))
        self.assertEqual(0, code, (out.getvalue(), err.getvalue()))
        self.assertTrue(os.path.isfile(os.path.join(place, ".workbench", "manifest.json")))


class AdoptFailureTest(AdoptBase):
    def fail_at(self, place, path, call):
        original = projectfs.Writer.create_file
        calls = [0]

        def failing(writer, rel, data, executable=False):
            calls[0] += 1
            if calls[0] == call:
                raise OSError("disk full")
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", failing):
            return self.run_adopt(place, path)

    def test_a_failure_part_way_exits_3_names_adopt_and_keeps_the_marker(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        code, out, err = self.fail_at(place, path, 4)
        self.assertEqual(3, code)
        self.assertIn("failed: disk full", err)
        self.assertIn("the adopt is unfinished", err)
        self.assertTrue(os.path.isfile(os.path.join(place, MARKER)))
        with open(os.path.join(place, "AGENTS.md"), "rb") as handle:
            self.assertEqual(OWN_AGENTS, handle.read())
        self.assertNotIn("AGENTS.md", err.split("not written:")[-1])

    def test_recover_clears_a_marker_when_nothing_else_was_written_and_keeps_every_file(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS, "README.md": b"hello\n"})
        before = self.hashes(place, ["AGENTS.md", "README.md", ".git/index"])
        code, out, err = self.fail_at(place, path, 2)
        self.assertEqual(3, code, err)
        code, out, err = run_recover(self, place)
        self.assertEqual(0, code, (out, err))
        self.assertIn("cleared the marker", out)
        self.assertFalse(os.path.exists(os.path.join(place, ".workbench")))
        self.assertEqual(before, self.hashes(place, list(before)))
        self.assertEqual([".git", "AGENTS.md", "README.md"], sorted(os.listdir(place)))

    def test_recover_after_a_part_way_failure_deletes_nothing_and_changes_no_kept_file(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS, "README.md": b"hello\n"})
        code, out, err = self.fail_at(place, path, 5)
        self.assertEqual(3, code, err)
        before = shape(place)
        code, out, err = run_recover(self, place)
        self.assertEqual(1, code, (out, err))
        self.assertIn("refused:", err)
        self.assertEqual(before, shape(place))

    def test_recover_refuses_when_a_kept_file_was_changed_since(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        code, out, err = self.fail_at(place, path, 2)
        self.assertEqual(3, code, err)
        with open(os.path.join(place, "AGENTS.md"), "ab") as handle:
            handle.write(b"changed\n")
        before = shape(place)
        code, out, err = run_recover(self, place)
        self.assertEqual(1, code, (out, err))
        self.assertIn("AGENTS.md", err)
        self.assertEqual(before, shape(place))

    def test_recover_clears_the_marker_of_an_adoption_that_was_carried_out(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        original = projectfs.Writer.remove_marker

        def never(writer):
            raise OSError("cannot remove the marker")

        with unittest.mock.patch.object(projectfs.Writer, "remove_marker", never):
            code, out, err = self.run_adopt(place, path)
        self.assertEqual(3, code, err)
        self.assertTrue(os.path.isfile(os.path.join(place, MARKER)))
        code, out, err = run_recover(self, place)
        self.assertEqual(0, code, (out, err))
        self.assertFalse(os.path.exists(os.path.join(place, MARKER)))
        with open(os.path.join(place, "AGENTS.md"), "rb") as handle:
            self.assertEqual(OWN_AGENTS, handle.read())
        self.assertTrue(os.path.isfile(os.path.join(place, ".workbench", "manifest.json")))


if __name__ == "__main__":
    unittest.main()
