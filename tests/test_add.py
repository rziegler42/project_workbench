import io
import os
import unittest
import unittest.mock

from tests import test_upgrade_preview as base_tests
from workbench import acknowledgement, approve, cli, fetch, manifest, projectfs

HARNESS = base_tests.HARNESS
NOTES = base_tests.NOTES
FILL = base_tests.FILL
MANIFEST = ".workbench/manifest.json"
POLICY_A = ".workbench/p/a/policy.md"
SCRIPT = base_tests.SCRIPT


def acknowledge_file(case, rel):
    """Stand in for `wb acknowledge`: make the baseline of `rel` what the file is now."""
    import hashlib
    baselines = acknowledgement.read_baselines(case.guarded, case.project_id)
    baselines[rel] = hashlib.sha256(case.read(rel)).hexdigest()
    case.guarded.write("projects/%s/baselines" % case.project_id, acknowledgement._canonical(
        {"baselines": baselines, "format": 1}))


class Add(base_tests.UpgradePreview):
    """A project with the harness and notes, and a package that also offers module `a`."""

    MODULES = {"h": (HARNESS, {}), "notes": NOTES}

    def setUp(self):
        base_tests.UpgradePreview.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)

    def ready(self, **offered):
        """The project installed from the two-module package; returns the richer package."""
        self.install(self.version())
        richer = self.version(**offered)
        self.approve(richer)
        self.warm(richer)
        return richer

    def preview_add(self, *args):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "add", self.place] + list(args), out, err,
                        store_root=self.store_root)
        return code, out.getvalue(), err.getvalue()

    def add(self, *args, answer=None, place=None):
        out, err = io.StringIO(), io.StringIO()

        class Ask(io.StringIO):
            def readline(this, *a):
                if answer is not None:
                    return answer + "\n"
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:12] + "\n"

        code = cli.main(["add", place or self.place] + list(args), out, err,
                        store_root=self.store_root, stdin=Ask(""))
        return code, out.getvalue(), err.getvalue()

    def snapshot(self):
        return self.tree(self.place), self.tree(self.store_root)

    def baselines(self):
        return acknowledgement.read_baselines(self.guarded, self.project_id)

    def keys(self):
        return {(p["name"], m["name"]) for p in manifest.parse(self.read(MANIFEST))["packages"]
                for m in p["modules"]}


class Preview(Add):
    def test_a_new_module_is_previewed_and_nothing_is_written(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        before = self.snapshot()
        code, out, err = self.preview_add("--package", richer, "--select", "a")
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("command: add\n", out)
        self.assertIn("p/a 1.0.0 (module): new", out)
        self.assertIn("create %s" % POLICY_A, out)
        self.assertIn("AGENTS.md block p/a slot:policy", out)
        self.assertTrue(out.endswith("preview only: nothing was written\n"))
        self.assertEqual(before, self.snapshot())
        fetch.fetch.assert_not_called()

    def test_a_module_the_project_has_is_refused_and_upgrade_is_named(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        before = self.snapshot()
        for token in ("notes", "p/notes"):
            code, out, err = self.preview_add("--package", richer, "--select", token)
            self.assertEqual((1, ""), (code, out))
            self.assertIn("is already installed", err)
            self.assertIn("wb upgrade", err)
        self.assertEqual(before, self.snapshot())

    def test_a_changed_installed_module_is_refused_not_replaced(self):
        richer = self.ready(a=FILL(b"Rule A\n"), notes=base_tests.NOTES2)
        before = self.snapshot()
        code, out, err = self.preview_add("--package", richer, "--select", "a")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("add never changes an installed module: p/notes", err)
        self.assertIn("use upgrade", err)
        self.assertEqual(before, self.snapshot())

    def test_an_edited_installed_file_does_not_let_the_module_move_on(self):
        self.install(self.version())
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        acknowledge_file(self, SCRIPT)
        richer = self.version(a=FILL(b"Rule A\n"), notes=base_tests.NOTES2)
        self.approve(richer)
        self.warm(richer)
        before = self.snapshot()
        code, out, err = self.preview_add("--package", richer, "--select", "a")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("add never changes an installed module", err)
        self.assertEqual(before, self.snapshot())

    def test_a_package_from_another_origin_does_not_take_over_the_record(self):
        self.install(self.version(), source="https://example.test/orig.git", ref="main",
                     commit="a" * 40)
        richer = self.version(a=FILL(b"Rule A\n"))
        self.approve(richer)
        self.warm(richer)
        before = self.snapshot()
        code, out, err = self.preview_add("--package", richer, "--select", "a")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("add never changes where an installed package comes from", err)
        self.assertIn("use upgrade", err)
        self.assertEqual(before, self.snapshot())

    def test_a_harness_cannot_be_added(self):
        richer = self.ready(h2=(HARNESS, {}))
        code, out, err = self.preview_add("--package", richer, "--select", "h2")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("a harness is attached, not added", err)

    def test_a_second_process_module_is_refused(self):
        self.MODULES = dict(self.MODULES, proc=({"type": "process"}, {}))
        self.install(self.version())
        richer = self.version(proc2=({"type": "process"}, {}))
        self.approve(richer)
        self.warm(richer)
        code, out, err = self.preview_add("--package", richer, "--select", "proc2")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("process", err)

    def test_a_new_module_may_require_an_installed_capability(self):
        self.MODULES = dict(self.MODULES, base=({"provides": ["p:x"]}, {}))
        self.install(self.version())
        richer = self.version(needs=({"requires": ["p:x"]}, {}))
        self.approve(richer)
        self.warm(richer)
        code, out, err = self.preview_add("--package", richer, "--select", "needs")
        self.assertEqual((0, ""), (code, err), out)

    def test_a_new_module_requiring_an_absent_capability_is_refused(self):
        richer = self.ready(needs=({"requires": ["p:missing"]}, {}))
        code, out, err = self.preview_add("--package", richer, "--select", "needs")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("p:missing", err)

    def test_a_new_module_that_conflicts_with_an_installed_one_is_refused(self):
        dup = ({"writes": ["docs/notes.md"]}, {"files/docs/notes.md": b"# Other\n"})
        richer = self.ready(dup=dup)
        before = self.snapshot()
        code, out, err = self.preview_add("--package", richer, "--select", "dup")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("docs/notes.md", err)
        self.assertEqual(before, self.snapshot())

    def test_a_module_that_is_not_approved_is_refused(self):
        self.install(self.version())
        richer = self.version(a=FILL(b"Rule A\n"))
        self.warm(richer)
        code, out, err = self.preview_add("--package", richer, "--select", "a")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("not approved", err)

    def test_an_unacknowledged_edit_is_refused(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        self.edit("AGENTS.md", lambda data: data + b"mine\n")
        code, out, err = self.preview_add("--package", richer, "--select", "a")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("run `wb acknowledge` yourself", err)

    def test_a_selection_is_required(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        for tokens in (["--package", richer], ["--select", "a"]):
            err = io.StringIO()
            code = cli.main(["preview", "add", self.place] + tokens, io.StringIO(), err,
                            store_root=self.store_root)
            self.assertEqual(2, code, tokens)

    def test_a_module_of_a_new_package_is_previewed(self):
        old = self.version()
        self.install(old)
        other = self.package("q", {"m": FILL(b"Rule M\n")})
        self.approve(other)
        self.warm(other)
        code, out, err = self.preview_add("--package", old, "--package", other, "--select", "m")
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("q/m 1.0.0 (module): new", out)


class Writing(Add):
    def test_the_module_is_added_end_to_end(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        agents = self.read("AGENTS.md")
        code, out, err = self.add("--package", richer, "--select", "a")
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(b"Rule A\n", self.read(POLICY_A))
        after = self.read("AGENTS.md")
        self.assertIn(b"<!-- BEGIN p/a slot:policy -->\nRule A\n<!-- END p/a slot:policy -->\n",
                      after)
        self.assertEqual(agents, after.replace(
            b"<!-- BEGIN p/a slot:policy -->\nRule A\n<!-- END p/a slot:policy -->\n", b""))
        self.assertIn(("p", "a"), self.keys())
        self.assertIn(POLICY_A, self.baselines())
        self.assertFalse(os.path.exists(os.path.join(self.place, *projectfs.MARKER.split("/"))))
        self.assertIn("nothing was committed", out)
        self.assertEqual((0, "nothing to acknowledge\n", ""), self.acknowledge_run())
        code, out, err = self.add("--package", richer, "--select", "a")
        self.assertEqual(1, code)
        self.assertIn("is already installed", err)

    def acknowledge_run(self):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["acknowledge", self.place], out, err, store_root=self.store_root,
                        stdin=io.StringIO(""))
        return code, out.getvalue(), err.getvalue()

    def test_a_fill_into_a_slot_without_a_marker_is_appended(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        self.edit("AGENTS.md", lambda data: data.replace(b"<!-- @slot: policy -->\n", b""))
        code, out, err = self.acknowledge_with_answer()
        self.assertEqual((0, ""), (code, err), out)
        before = self.read("AGENTS.md")
        code, out, err = self.add("--package", richer, "--select", "a")
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("append AGENTS.md block p/a slot:policy", out)
        after = self.read("AGENTS.md")
        self.assertTrue(after.startswith(before))
        self.assertTrue(after.endswith(b"<!-- END p/a slot:policy -->\n<!-- @slot: policy -->\n"))

    def acknowledge_with_answer(self):
        out, err = io.StringIO(), io.StringIO()

        class Ask(io.StringIO):
            def readline(this, *a):
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][0]
                return digest[len("digest: "):][:12] + "\n"

        code = cli.main(["acknowledge", self.place], out, err, store_root=self.store_root,
                        stdin=Ask(""))
        return code, out.getvalue(), err.getvalue()

    def test_a_wrong_answer_writes_nothing(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        before = self.snapshot()
        code, out, err = self.add("--package", richer, "--select", "a", answer="no")
        self.assertEqual((1, ""), (code, err))
        self.assertIn("cancelled: nothing was written", out)
        self.assertEqual(before, self.snapshot())

    def test_without_terminals_it_refuses_and_reads_nothing(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        before = self.snapshot()
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False):
            code = cli.main(["add", self.place, "--package", richer, "--select", "a"], out, err,
                            store_root=self.store_root, stdin=io.StringIO("x\n"))
        self.assertEqual((1, ""), (code, out.getvalue()))
        self.assertIn("refused: add is owner-run", err.getvalue())
        self.assertIn("`preview add`", err.getvalue())
        self.assertEqual(before, self.snapshot())

    def test_a_module_of_a_new_package_is_recorded_with_its_package(self):
        old = self.version()
        self.install(old)
        other = self.package("q", {"m": FILL(b"Rule M\n")})
        self.approve(other)
        self.warm(other)
        code, out, err = self.add("--package", old, "--package", other, "--select", "m")
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual({("p", "h"), ("p", "notes"), ("q", "m")}, self.keys() | {("p", "h")})
        names = [p["name"] for p in manifest.parse(self.read(MANIFEST))["packages"]]
        self.assertEqual(["p", "q"], names)

    def test_nothing_installed_is_changed_by_an_add(self):
        richer = self.ready(a=FILL(b"Rule A\n"))
        before = {path: self.read(path) for path in
                  (SCRIPT, "docs/notes.md", "docs/README.md", ".workbench/p/notes/module.json")}
        code, out, err = self.add("--package", richer, "--select", "a")
        self.assertEqual((0, ""), (code, err), out)
        for path, data in before.items():
            self.assertEqual(data, self.read(path))


if __name__ == "__main__":
    unittest.main()
