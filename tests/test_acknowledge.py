import io
import os
import sys
import unittest
import unittest.mock

from tests import support
from tests import test_upgrade_preview as base_tests
from workbench import acknowledge, acknowledgement, approve, cli, confirm, manifest, store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = base_tests.SCRIPT
POLICY = ".workbench/p/a/policy.md"
MANIFEST = ".workbench/manifest.json"


class Typed(io.StringIO):
    """Standard input that answers when asked and may do something first."""

    def __init__(self, text, before=None):
        io.StringIO.__init__(self, text)
        self.before = before

    def readline(self, *args):
        if self.before:
            self.before()
        return io.StringIO.readline(self, *args)


class Acknowledge(base_tests.UpgradePreview):
    def setUp(self):
        base_tests.UpgradePreview.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)

    def baselines(self):
        return acknowledgement.read_baselines(self.guarded, self.project_id)

    def run_it(self, answer=None, *args, stdin=None, place=None):
        out, err = io.StringIO(), io.StringIO()
        shown = {}

        def reply():
            return shown["digest"][:12] if answer is None else answer

        class Ask(Typed):
            def readline(this, *a):
                shown["digest"] = [line for line in out.getvalue().splitlines()
                                   if line.startswith("digest: ")][-1][len("digest: "):]
                return reply() + "\n"

        code = cli.main(["acknowledge", place or self.place] + list(args), out, err,
                        store_root=self.store_root, stdin=stdin or Ask(""))
        return code, out.getvalue(), err.getvalue()

    def installed_project(self):
        self.package_path = self.version()
        self.install(self.package_path)

    def snapshot(self):
        return self.tree(self.place), self.tree(self.store_root)


class Accepting(Acknowledge):
    def test_a_clean_project_has_nothing_to_acknowledge(self):
        self.installed_project()
        before = self.snapshot()
        code, out, err = self.run_it()
        self.assertEqual((0, "nothing to acknowledge\n", ""), (code, out, err))
        self.assertEqual(before, self.snapshot())

    def test_an_edited_file_is_listed_and_acknowledged(self):
        self.installed_project()
        was = self.baselines()
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        project = self.tree(self.place)
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("changed %s\n" % SCRIPT, out)
        self.assertIn("baseline %s" % was[SCRIPT], out)
        self.assertIn("acknowledged 1 paths; the project was not touched", out)
        now = self.baselines()
        self.assertNotEqual(was[SCRIPT], now[SCRIPT])
        self.assertEqual({k: v for k, v in was.items() if k != SCRIPT},
                         {k: v for k, v in now.items() if k != SCRIPT})
        self.assertEqual(project, self.tree(self.place))
        code, _, err = self.preview("--package", self.package_path)
        self.assertEqual((0, ""), (code, err))

    def test_only_the_listed_paths_change_and_the_rest_is_kept(self):
        self.installed_project()
        was = self.baselines()
        self.edit(SCRIPT, lambda data: data + b"# one\n")
        self.edit(POLICY, lambda data: data + b"# two\n")
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        now = self.baselines()
        self.assertEqual({SCRIPT, POLICY}, {k for k in now if now[k] != was.get(k)})
        self.assertEqual(was.keys(), now.keys())

    def test_an_edited_manifest_is_listed_with_its_summary(self):
        self.installed_project()
        self.edit(MANIFEST, lambda data: data.replace(b'"workbench": "0.1.0"',
                                                      b'"workbench": "0.0.9"'))
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("changed %s\n" % MANIFEST, out)
        self.assertIn("packages:\n  p from local:p", out)
        self.assertIn("recorded by workbench 0.0.9", out)
        self.assertEqual(manifest.parse(self.read(MANIFEST))["workbench"], "0.0.9")

    def test_a_file_added_under_the_workbench_directory_is_acknowledged(self):
        self.installed_project()
        with open(os.path.join(self.place, ".workbench", "extra.txt"), "wb") as handle:
            handle.write(b"x")
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("added .workbench/extra.txt\n", out)
        self.assertIn(".workbench/extra.txt", self.baselines())

    def test_a_file_removed_is_acknowledged_by_dropping_its_baseline(self):
        self.installed_project()
        os.unlink(os.path.join(self.place, *SCRIPT.split("/")))
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("removed %s\n" % SCRIPT, out)
        self.assertNotIn(SCRIPT, self.baselines())

    def test_the_local_directory_is_not_part_of_the_list(self):
        self.installed_project()
        os.makedirs(os.path.join(self.place, ".workbench", "local"), exist_ok=True)
        with open(os.path.join(self.place, ".workbench", "local", "notes"), "wb") as handle:
            handle.write(b"mine")
        self.assertEqual((0, "nothing to acknowledge\n", ""), self.run_it())

    def test_the_project_is_never_written(self):
        self.installed_project()
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        before = self.tree(self.place)
        self.run_it()
        self.assertEqual(before, self.tree(self.place))


class Scope(Acknowledge):
    def test_an_edited_seeded_file_blocks_the_upgrade_until_it_is_acknowledged(self):
        path = self.version()
        self.install(path)
        self.edit("AGENTS.md", lambda data: data + b"\nMy own rule.\n")
        newer = self.version(a=base_tests.FILL(b"Rule B\n"))
        self.approve(newer)
        self.warm(newer)
        self.refused("--package", newer, contains="AGENTS.md")
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("changed AGENTS.md\n", out)
        code, out, err = self.preview("--package", newer)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("replace AGENTS.md block p/a slot:policy", out)

    def test_a_manifest_seed_of_another_known_project_is_refused(self):
        self.installed_project()
        other = self.project_id
        document = manifest.parse(self.read(MANIFEST))
        document["seed"] = "seed-2"
        self.edit(MANIFEST, lambda data: manifest.serialize(document))
        before = self.snapshot()
        code, out, err = self.run_it()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("treated as new here", err)
        self.assertNotEqual(other, manifest.project_id("seed-2"))
        self.assertEqual(before, self.snapshot())

    def test_a_linked_directory_under_the_workbench_directory_is_not_followed(self):
        self.installed_project()
        outside = os.path.join(self.root, "outside")
        os.makedirs(outside)
        with open(os.path.join(outside, "x"), "wb") as handle:
            handle.write(b"x")
        link = os.path.join(self.place, ".workbench", "p", "a")
        os.rename(link, link + ".moved")
        os.symlink(outside, link)
        before = self.snapshot()
        code, out, err = self.run_it()
        self.assertEqual(1, code, out)
        self.assertEqual(before[1], self.tree(self.store_root))
        self.assertNotIn(outside, out)


class Binding(Acknowledge):
    def test_a_manifest_that_differs_between_two_reads_is_refused(self):
        self.installed_project()
        good = self.read(MANIFEST)
        document = manifest.parse(good)
        document["files"][0]["hash"] = "0" * 64
        evil = manifest.serialize(document)
        reads = []
        real = acknowledge.projectfs.Writer.read_file

        def flip(writer, rel):
            state = real(writer, rel)
            if rel == MANIFEST:
                reads.append(1)
                if len(reads) % 2 == 0:
                    state = state._replace(data=evil, hash=acknowledge._sha(evil))
            return state

        before = self.snapshot()
        with unittest.mock.patch.object(acknowledge.projectfs.Writer, "read_file", flip):
            code, out, err = self.run_it()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("the manifest changed while it was read", err)
        self.assertEqual(before[1], self.tree(self.store_root))

    def test_every_file_entry_of_the_manifest_is_shown(self):
        self.installed_project()
        self.edit(MANIFEST, lambda data: data.replace(b'"workbench": "0.1.0"', b'"workbench": "0.0.9"'))
        code, out, err = self.run_it()
        for item in manifest.parse(self.read(MANIFEST))["files"]:
            self.assertIn("  %s %s" % (item["path"], item["class"]), out)
            self.assertIn(item["hash"], out)

    def test_a_long_path_is_shown_in_full(self):
        self.installed_project()
        name = "d" * 150 + "/" + "e" * 150 + "/" + "f" * 100
        full = os.path.join(self.place, ".workbench", *name.split("/"))
        os.makedirs(os.path.dirname(full))
        with open(full, "wb") as handle:
            handle.write(b"x")
        code, out, err = self.run_it()
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("added .workbench/" + name + "\n", out)

    def test_the_store_is_untouched_without_terminals(self):
        before = self.tree(self.store_root)
        import shutil
        shutil.rmtree(self.store_root)
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False):
            code = cli.main(["acknowledge", self.place], io.StringIO(), io.StringIO(),
                            store_root=self.store_root, stdin=io.StringIO(""))
        self.assertEqual(1, code)
        self.assertFalse(os.path.exists(self.store_root))
        self.assertTrue(before is not None)


class Declining(Acknowledge):
    def test_a_wrong_answer_writes_nothing(self):
        self.installed_project()
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        before = self.snapshot()
        code, out, err = self.run_it("no")
        self.assertEqual((1, ""), (code, err))
        self.assertIn("cancelled: nothing was written", out)
        self.assertEqual(before, self.snapshot())

    def test_a_short_prefix_of_the_digest_is_not_enough(self):
        self.installed_project()
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        before = self.snapshot()
        out = io.StringIO()

        class Short(io.StringIO):
            def readline(this, *a):
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:11] + "\n"

        code = cli.main(["acknowledge", self.place], out, io.StringIO(),
                        store_root=self.store_root, stdin=Short(""))
        self.assertEqual(1, code)
        self.assertEqual(before, self.snapshot())

    def test_typed_ahead_input_is_discarded_before_the_answer_is_read(self):
        self.installed_project()
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        order = []
        out = io.StringIO()

        class Ask(io.StringIO):
            def readline(this, limit=-1):
                order.append(("read", limit))
                return "x\n"

        with unittest.mock.patch.object(confirm, "discard_typed_ahead",
                                        lambda stream: order.append("flush")):
            code = cli.main(["acknowledge", self.place], out, io.StringIO(),
                            store_root=self.store_root, stdin=Ask(""))
        self.assertEqual(1, code)
        self.assertEqual(["flush", ("read", confirm.MAX_ANSWER)], order)

    def test_an_oversized_answer_is_bounded_and_refused(self):
        self.installed_project()
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        before = self.snapshot()
        code, out, err = self.run_it("a" * 5000)
        self.assertEqual(1, code)
        self.assertEqual(before, self.snapshot())

    def test_the_project_changing_after_the_list_is_refused(self):
        self.installed_project()
        self.edit(SCRIPT, lambda data: data + b"# one\n")
        before = self.snapshot()
        edited = []

        def change():
            if not edited:
                edited.append(1)
                self.edit(POLICY, lambda data: data + b"# sneaked in\n")

        out, err = io.StringIO(), io.StringIO()

        class Ask(Typed):
            def readline(this, *a):
                change()
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:12] + "\n"

        code = cli.main(["acknowledge", self.place], out, err, store_root=self.store_root,
                        stdin=Ask(""))
        self.assertEqual(1, code)
        self.assertIn("the project changed while the list was shown", err.getvalue())
        self.assertEqual(before[1], self.tree(self.store_root))

    def test_a_link_where_a_file_is_expected_cannot_be_acknowledged(self):
        self.installed_project()
        full = os.path.join(self.place, *SCRIPT.split("/"))
        os.unlink(full)
        os.symlink("/etc/passwd", full)
        before = self.snapshot()
        code, out, err = self.run_it()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("cannot be acknowledged", err)
        self.assertEqual(before, self.snapshot())

    def test_a_project_unknown_here_is_refused(self):
        self.install(self.version(), store_writes=False)
        code, out, err = self.run_it()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("refused: ", err)
        self.assertIn("treated as new here", err)

    def test_a_project_first_seen_elsewhere_is_refused(self):
        self.installed_project()
        self.guarded.write("projects/%s/seen" % self.project_id, acknowledgement._canonical(
            {"format": 1, "kind": "path", "value": "/somewhere/else"}))
        code, out, err = self.run_it()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("first seen at /somewhere/else", err)

    def test_a_manifest_that_cannot_be_read_is_refused(self):
        self.installed_project()
        self.edit(MANIFEST, lambda data: data + b"x")
        before = self.snapshot()
        code, out, err = self.run_it()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("the manifest is not valid", err)
        self.assertEqual(before, self.snapshot())

    def test_a_target_that_is_not_a_project_is_refused(self):
        os.makedirs(os.path.join(self.root, "empty"))
        code, out, err = self.run_it(place=os.path.join(self.root, "empty"))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("refused: ", err)

    def test_too_many_differences_are_refused_not_truncated(self):
        self.installed_project()
        with unittest.mock.patch.object(acknowledge, "MAX_LISTED", 1):
            self.edit(SCRIPT, lambda data: data + b"#\n")
            self.edit(POLICY, lambda data: data + b"#\n")
            before = self.snapshot()
            code, out, err = self.run_it()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("more than the 1 that can be reviewed", err)
        self.assertEqual(before, self.snapshot())

    def test_a_failing_store_write_exits_3_and_says_the_baselines_are_unchanged(self):
        self.installed_project()
        self.edit(SCRIPT, lambda data: data + b"#\n")
        was = self.baselines()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("disk full")):
            code, out, err = self.run_it()
        self.assertEqual(3, code)
        self.assertIn("failed: disk full", err)
        self.assertIn("the baselines were not changed", err)
        self.assertEqual(was, self.baselines())


class Usage(Acknowledge):
    def test_without_terminals_nothing_is_read_or_written(self):
        self.installed_project()
        self.edit(SCRIPT, lambda data: data + b"#\n")
        before = self.snapshot()
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False):
            code = cli.main(["acknowledge", self.place], out, err, store_root=self.store_root,
                            stdin=io.StringIO("x\n"))
        self.assertEqual((1, ""), (code, out.getvalue()))
        self.assertIn("refused: acknowledge is owner-run", err.getvalue())
        self.assertEqual(before, self.snapshot())

    def test_an_unknown_option_is_a_usage_error(self):
        for tokens in (["--force"], ["a", "b"], ["--dir"], ["--dir", "x", "--dir", "y"], [""]):
            err = io.StringIO()
            code = cli.main(["acknowledge"] + tokens, io.StringIO(), err,
                            store_root=self.store_root, stdin=io.StringIO(""))
            self.assertEqual(2, code, tokens)
            self.assertIn("usage:", err.getvalue())

    def test_dir_names_the_target_like_the_positional_argument(self):
        self.installed_project()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["acknowledge", "--dir", self.place], out, err,
                        store_root=self.store_root, stdin=io.StringIO(""))
        self.assertEqual((0, "nothing to acknowledge\n"), (code, out.getvalue()))

    def test_the_command_is_listed_in_the_usage_text(self):
        err = io.StringIO()
        cli.main([], io.StringIO(), err, store_root=self.store_root)
        self.assertIn("acknowledge [<target> | --dir <path>]", err.getvalue())


class Terminal(base_tests.UpgradePreview):
    """The command run in a child process whose terminals are real pseudo-terminals."""

    def setUp(self):
        base_tests.UpgradePreview.setUp(self)
        self.store_root = os.path.join(self.root, ".config", "project-workbench")
        self.guarded = store.Store(self.store_root)
        self.guarded.ensure()

    def drive(self, answer, **kwargs):
        env = dict(os.environ, HOME=self.root, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1",
                   PATH=support.clean_path())
        argv = [sys.executable, "-B", "-m", "workbench", "acknowledge", self.place]
        return support.drive_pty(self, argv, env, self.root, answer, b"> ", **kwargs)

    def digest(self, shown):
        return [line for line in shown.splitlines() if line.startswith("digest: ")][0][8:20]

    def test_the_digest_typed_in_a_terminal_acknowledges(self):
        self.install(self.version())
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        code, output, error = self.drive(self.digest)
        self.assertEqual((0, ""), (code, error), output)
        self.assertIn("acknowledged 1 paths", output)
        self.assertEqual(self.baselines_hash(SCRIPT), self.file_hash(SCRIPT))

    def test_any_other_text_in_a_terminal_writes_nothing(self):
        self.install(self.version())
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        before = self.tree(self.store_root)
        code, output, error = self.drive("no")
        self.assertEqual(1, code, error)
        self.assertIn("cancelled: nothing was written", output)
        self.assertEqual(before, self.tree(self.store_root))

    def test_without_terminals_it_refuses(self):
        self.install(self.version())
        code, output, error = self.drive("x", stdin="pipe", stdout="pipe")
        self.assertEqual(1, code)
        self.assertIn("refused: acknowledge is owner-run", error)

    def baselines_hash(self, rel):
        return acknowledgement.read_baselines(self.guarded, self.project_id)[rel]

    def file_hash(self, rel):
        import hashlib
        return hashlib.sha256(self.read(rel)).hexdigest()


if __name__ == "__main__":
    unittest.main()
