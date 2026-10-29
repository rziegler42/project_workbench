"""``wb approve`` and ``wb pin`` at the level ``none``: no terminal, nothing typed, the attempt and the outcome logged.

Plan ``2026-10-27-a-level-for-every-command``, increment H (``docs/specs/command-permissions.md``, "One way to run at
``none``"). These commands make a package or a helper trusted, so at ``none`` an agent can do that. The project, its harness
and its rendering record are those of ``test_approve_levels``; the package to approve is the sample package of
``test_approve``. ``approve`` is machine-wide; ``pin`` is for one project, which must be the one the level was read for."""

import io
import json
import os
import shutil
import tempfile
import unittest
import unittest.mock

from tests.test_approve_levels import Ask
from workbench import approvals, approve, cli, levellog, pins, rendering, verify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sample-package")
VERIFY_PACKAGE, VERIFY_PACKAGES = verify.verify_package, verify.verify_packages
HELPER = "scripts/extra.sh"


class NoInput(io.StringIO):
    """A standard input that fails if it is read: nothing is asked at ``none``."""

    def readline(self, limit=-1):
        raise AssertionError("standard input was read")

    read = readlines = readline


class Base(Ask):
    KEY = "wb approve"

    def setUp(self):
        super().setUp()
        self.package_dir = os.path.join(self.root, "sample")
        shutil.copytree(FIXTURE, self.package_dir)
        self.put(HELPER, "#!/bin/sh\necho extra\n")

    def table(self, **table):
        self.guarded.write("settings", json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": table}).encode())

    def attach_at(self, level="none"):
        self.table(**{self.KEY: level} if level else {})
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        # The fixture treats its packages as first-party so that attach accepts them; a package approved here is verified as
        # an owner's would be.
        for name, original in (("verify_package", VERIFY_PACKAGE), ("verify_packages", VERIFY_PACKAGES)):
            patch = unittest.mock.patch.object(verify, name, original)
            patch.start()
            self.addCleanup(patch.stop)

    def log(self):
        if self.guarded.kind(levellog.LOG) != "file":
            return []
        return self.guarded.read(levellog.LOG).decode("ascii").splitlines()

    def go(self, argv, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        previous = os.getcwd()
        os.chdir(cwd or self.real)
        try:
            code = cli.main(list(argv), out, err, store_root=self.store_root, distribution=self.dist, stdin=NoInput())
        finally:
            os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def snapshot(self):
        return self.tree(self.store_root), self.log()

    def refused(self, argv, contains="owner-run", **kwargs):
        before = self.snapshot()
        code, out, err = self.go(argv, **kwargs)
        self.assertEqual(1, code, (out, err))
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertEqual(before, self.snapshot())
        return err


class ApproveAtNone(Base):
    def setUp(self):
        super().setUp()
        self.attach_at("none")

    def argv(self, *more):
        return ["approve", self.package_dir] + list(more)

    def facts(self):
        result = VERIFY_PACKAGE(self.package_dir, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        return result.packages[0], {m.name: m for m in result.modules}

    def test_it_approves_the_package_with_no_terminal_and_asks_nothing(self):
        info, modules = self.facts()
        code, out, err = self.go(self.argv())
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing is asked", out)
        self.assertIn("approved package %s" % info.name, out)
        self.assertTrue(approvals.check(self.guarded, "package", info.name, info.declaration_hash, info.tree_hash).approved)
        for name, item in modules.items():
            self.assertTrue(approvals.check(self.guarded, "module", "%s/%s" % (info.name, name), item.declaration_hash,
                                            item.tree_hash).approved, name)

    def test_the_record_is_the_one_a_terminal_approval_writes_with_the_level_as_its_via(self):
        info, modules = self.facts()
        code, out, err = self.go(self.argv())
        self.assertEqual(0, code)
        self.assertIn("approved package %s by %s (no gate)" % (info.name, self.who.text), out)
        record = approvals.check(self.guarded, "package", info.name, info.declaration_hash, info.tree_hash)
        self.assertEqual((self.who.text, "none"), (record.record.approver, record.record.via))
        self.assertEqual(sorted(modules), sorted(name for name, _, _ in record.record.modules))

    def test_a_missing_identity_refuses_with_nothing_recorded_and_nothing_logged(self):
        from workbench import identity
        info, _ = self.facts()
        with unittest.mock.patch.object(identity, "read", side_effect=identity.IdentityError("no identity here")):
            code, out, err = self.go(self.argv())
        self.assertEqual(1, code)
        self.assertIn("refused: no identity here", err)
        self.assertFalse(approvals.check(self.guarded, "package", info.name, info.declaration_hash,
                                         info.tree_hash).approved)
        self.assertEqual([], self.log_lines())

    def test_module_approves_only_that_module(self):
        info, modules = self.facts()
        name = sorted(modules)[0]
        self.assertEqual(0, self.go(self.argv("--module", name))[0])
        item = modules[name]
        self.assertTrue(approvals.check(self.guarded, "module", "%s/%s" % (info.name, name), item.declaration_hash,
                                        item.tree_hash).approved)
        self.assertFalse(approvals.check(self.guarded, "package", info.name, info.declaration_hash, info.tree_hash).approved)

    def test_the_log_has_the_attempt_before_the_record_and_the_outcome_after(self):
        info, _ = self.facts()
        seen = []
        original = approve._record

        def record(*args, **kwargs):
            seen.append(self.log())
            return original(*args, **kwargs)

        with unittest.mock.patch.object(approve, "_record", record):
            code, out, err = self.go(self.argv())
        self.assertEqual(0, code, (out, err))
        self.assertEqual(1, len(seen[0]))
        attempt, outcome = self.log()
        fields = attempt.split("\t")
        self.assertEqual(["wb approve", "none", "digest:" + info.tree_hash], fields[3:])
        self.assertEqual(["O", fields[1]], outcome.split("\t")[:2])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_an_approval_already_on_file_changes_nothing_and_writes_no_entry(self):
        self.assertEqual(0, self.go(self.argv())[0])
        log = self.log()
        before = self.tree(self.store_root)
        code, out, err = self.go(self.argv())
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("already approved", out)
        self.assertEqual((log, before), (self.log(), self.tree(self.store_root)))

    def test_a_package_that_does_not_verify_is_refused_and_nothing_is_written(self):
        os.unlink(os.path.join(self.package_dir, "package.json"))
        before = self.snapshot()
        code, out, err = self.go(self.argv())
        self.assertEqual(1, code, (out, err))
        self.assertIn("refused", err)
        self.assertEqual(before, self.snapshot())

    def test_a_package_that_changes_while_it_is_shown_is_not_recorded(self):
        original = approve._verify
        calls = []

        def verify_again(path, distribution):
            calls.append(path)
            if len(calls) == 2:
                with open(os.path.join(self.package_dir, "sample-notes", "scripts", "extra.txt"), "w") as handle:
                    handle.write("changed")
            return original(path, distribution)

        before = self.snapshot()
        with unittest.mock.patch.object(approve, "_verify", verify_again):
            code, out, err = self.go(self.argv())
        self.assertEqual(1, code, (out, err))
        self.assertIn("changed while it was shown", err)
        self.assertEqual(before, self.snapshot())

    def test_a_table_edited_after_attach_reads_block(self):
        self.table(**{self.KEY: "none", "wb pin": "none"})
        self.refused(self.argv())

    def test_a_missing_rendering_record_reads_block(self):
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        self.refused(self.argv())

    def test_a_harness_file_edited_after_attach_reads_block(self):
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "ab") as handle:
            handle.write(b" ")
        self.refused(self.argv())

    def test_a_directory_that_is_no_project_cannot_run_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.refused(self.argv(), cwd=tmp)

    def test_an_attempt_that_cannot_be_written_records_nothing(self):
        before = self.snapshot()
        with unittest.mock.patch.object(levellog, "begin", side_effect=levellog.LogError("the log is full")):
            code, out, err = self.go(self.argv())
        self.assertEqual(1, code, (out, err))
        self.assertIn("nothing was written", err)
        self.assertEqual(before, self.snapshot())

    def test_an_outcome_that_cannot_be_written_after_the_record_exits_3(self):
        info, _ = self.facts()
        with unittest.mock.patch.object(levellog, "finish", side_effect=levellog.OutcomeError("no space")):
            code, out, err = self.go(self.argv())
        self.assertEqual(3, code, (out, err))
        self.assertIn("outcome was not logged", err)
        self.assertTrue(approvals.check(self.guarded, "package", info.name, info.declaration_hash, info.tree_hash).approved)

    def test_nothing_but_the_approval_files_and_the_log_changed(self):
        before = set(self.tree(self.store_root))
        self.assertEqual(0, self.go(self.argv())[0])
        added = set(self.tree(self.store_root)) - before
        self.assertTrue(all(rel.startswith("packages/") or rel == levellog.LOG for rel in added), added)
        self.assertEqual({"level-log"}, {rel for rel in added if not rel.startswith("packages/")})


class ApproveNotAtNone(Base):
    def argv(self):
        return ["approve", self.package_dir]

    def test_it_refuses_without_a_terminal_at_the_default(self):
        self.attach_at(None)
        self.refused(self.argv())

    def test_it_refuses_without_a_terminal_at_block(self):
        self.attach_at("block")
        self.refused(self.argv())

    def test_the_other_key_at_none_does_not_let_it_run(self):
        self.table(**{"wb pin": "none"})
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.refused(self.argv())


class PinAtNone(Base):
    KEY = "wb pin"

    def setUp(self):
        super().setUp()
        self.attach_at("none")

    def argv(self, name="extra", project=None, root=None, *more):
        return ["pin", project or self.project_id, name, os.path.join(self.real, *HELPER.split("/")),
                "--root", root or self.real] + list(more)

    def test_it_pins_the_helper_with_no_terminal_and_asks_nothing(self):
        code, out, err = self.go(self.argv())
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("nothing is asked", out)
        pin = pins.lookup(self.guarded, self.project_id, "extra")
        with open(os.path.join(self.real, *HELPER.split("/")), "rb") as handle:
            digest = pins.hash_bytes(handle.read())
        self.assertEqual((HELPER, digest, self.who.text, None, "none"),
                         (pin.path, pin.sha256, pin.pinned_by, pin.kit, pin.via))
        self.assertIn("by %s (no gate)" % self.who.text, out)

    def test_a_missing_identity_refuses_with_no_pin_and_nothing_logged(self):
        from workbench import identity
        with unittest.mock.patch.object(identity, "read", side_effect=identity.IdentityError("no identity here")):
            code, out, err = self.go(self.argv())
        self.assertEqual(1, code)
        self.assertIn("refused: no identity here", err)
        self.assertNotIn("extra", pins.load(self.guarded, self.project_id))
        self.assertEqual([], self.log_lines())

    def test_the_kit_is_recorded_as_at_a_terminal(self):
        self.assertEqual(0, self.go(self.argv("extra", None, None, "--kit", "1"))[0])
        self.assertEqual(1, pins.lookup(self.guarded, self.project_id, "extra").kit)

    def test_the_log_has_the_attempt_before_the_pin_and_the_outcome_after(self):
        seen = []
        original = pins.set_pin

        def set_pin(*args, **kwargs):
            seen.append(self.log())
            return original(*args, **kwargs)

        with unittest.mock.patch.object(pins, "set_pin", set_pin):
            code, out, err = self.go(self.argv())
        self.assertEqual(0, code, (out, err))
        self.assertEqual(1, len(seen[0]))
        attempt, outcome = self.log()
        fields = attempt.split("\t")
        self.assertEqual(["wb pin", "none"], fields[3:5])
        self.assertRegex(fields[5], r"\Adigest:[0-9a-f]{64}\Z")
        self.assertEqual(pins.lookup(self.guarded, self.project_id, "extra").sha256, fields[5][len("digest:"):])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_a_pin_for_another_project_than_the_level_was_read_for_is_refused(self):
        other = "0" * 64
        before = self.snapshot()
        code, out, err = self.go(self.argv(project=other))
        self.assertEqual(1, code, (out, err))
        self.assertIn("not the project", err)
        self.assertEqual(before, self.snapshot())

    def test_a_root_that_is_not_the_project_the_level_was_read_for_is_refused(self):
        elsewhere = os.path.join(self.root, "elsewhere")
        os.makedirs(os.path.join(elsewhere, "scripts"))
        with open(os.path.join(elsewhere, *HELPER.split("/")), "w") as handle:
            handle.write("#!/bin/sh\necho other\n")
        before = self.snapshot()
        code, out, err = self.go(["pin", self.project_id, "extra", os.path.join(elsewhere, *HELPER.split("/")),
                                  "--root", elsewhere])
        self.assertEqual(1, code, (out, err))
        self.assertIn("not the one at the root given", err)
        self.assertEqual(before, self.snapshot())

    def test_a_root_spelled_through_a_link_and_dotdot_is_not_the_project_root(self):
        """`link/..` is the project for a path that follows links (`realpath`) and another directory for one that does not
        (`abspath`); the pin must not be read from one and compared as the other."""
        outer = os.path.join(self.root, "outer")
        os.makedirs(outer)
        os.symlink(os.path.join(self.real, "scripts"), os.path.join(outer, "link"))
        with open(os.path.join(outer, *HELPER.split("/")[-1:]), "w") as handle:
            handle.write("#!/bin/sh\necho other\n")
        before = self.snapshot()
        code, out, err = self.go(["pin", self.project_id, "extra", os.path.join(outer, HELPER.split("/")[-1]),
                                  "--root", os.path.join(outer, "link", "..")])
        self.assertEqual(1, code, (out, err))
        self.assertEqual(before, self.snapshot())
        self.assertNotIn("pinned", out)

    def test_a_helper_outside_the_root_is_refused_and_nothing_is_written(self):
        before = self.snapshot()
        code, out, err = self.go(["pin", self.project_id, "extra", os.path.join(self.root, "x"), "--root", self.real])
        self.assertEqual(1, code, (out, err))
        self.assertEqual(before, self.snapshot())

    def test_a_helper_that_changes_while_it_is_shown_is_not_pinned(self):
        original = pins._read_helper
        calls = []

        def read(root_abs, rel):
            calls.append(rel)
            data = original(root_abs, rel)
            if len(calls) == 1:
                self.put(HELPER, "#!/bin/sh\necho changed\n")
            return data

        before = self.snapshot()
        with unittest.mock.patch.object(pins, "_read_helper", read):
            code, out, err = self.go(self.argv())
        self.assertEqual(1, code, (out, err))
        self.assertIn("changed while it was shown", err)
        self.assertEqual(before, self.snapshot())

    def test_a_table_edited_after_attach_reads_block(self):
        self.table(**{self.KEY: "none", "wb approve": "none"})
        self.refused(self.argv())

    def test_a_directory_that_is_no_project_cannot_run_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.refused(self.argv(), cwd=tmp)

    def test_an_attempt_that_cannot_be_written_pins_nothing(self):
        before = self.snapshot()
        with unittest.mock.patch.object(levellog, "begin", side_effect=levellog.LogError("the log is full")):
            code, out, err = self.go(self.argv())
        self.assertEqual(1, code, (out, err))
        self.assertEqual(before, self.snapshot())

    def test_an_outcome_that_cannot_be_written_after_the_pin_exits_3(self):
        with unittest.mock.patch.object(levellog, "finish", side_effect=levellog.OutcomeError("no space")):
            code, out, err = self.go(self.argv())
        self.assertEqual(3, code, (out, err))
        self.assertEqual("extra", pins.lookup(self.guarded, self.project_id, "extra").name)


class PinNotAtNone(Base):
    KEY = "wb pin"

    def test_it_refuses_without_a_terminal_at_the_default(self):
        self.attach_at(None)
        self.refused(["pin", self.project_id, "extra", os.path.join(self.real, *HELPER.split("/")), "--root", self.real])

    def test_it_refuses_without_a_terminal_at_block(self):
        self.attach_at("block")
        self.refused(["pin", self.project_id, "extra", os.path.join(self.real, *HELPER.split("/")), "--root", self.real])


if __name__ == "__main__":
    unittest.main()
