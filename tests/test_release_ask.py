"""``wb release-approvals`` at the level ``ask``: the digest check (Increment C of ``2026-10-30-release-approvals-at-ask``).

``docs/specs/command-permissions.md``, "`wb release-approvals` at `ask`". Without a terminal and at a verified ``ask`` the command
builds one release plan, compares the digest of that plan's preview with the one given and writes that same plan. The key does not
offer ``ask`` until Increment D, so the level is read through a patch of ``levelrun.level_now`` here; the project, its rendering
record and the level log are those of ``test_ack_recover_levels``. The release is of a small distribution of its own (the sample
package of the fixtures), not the synthetic one the project fixture installs from."""

import io
import json
import os
import shutil
import tempfile
import unittest
import unittest.mock

from tests.test_ack_recover_levels import Base, NoInput
from workbench import approvals, approve, cli, firstparty, levellog, levelrun, rendering, verify

# The project fixture patches the verifiers for its synthetic packages; a release reads real ones, so the originals are taken at
# import, before any fixture runs, and put back after the attach.
REAL_VERIFY_PACKAGE, REAL_VERIFY_PACKAGES = verify.verify_package, verify.verify_packages
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample-package")
KEY = "wb release-approvals"
NOTES = ("sample-notes", "files", "docs", "notes.md")


class ReleaseAsk(Base):
    KEY = KEY

    def setUp(self):
        super().setUp()
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.rel = os.path.join(os.path.realpath(holder.name), "release")
        os.makedirs(os.path.join(self.rel, "workbench"))
        os.makedirs(os.path.join(self.rel, "packages"))
        self.package = os.path.join(self.rel, "packages", "sample")
        shutil.copytree(FIXTURE, self.package)
        path = os.path.join(self.package, "sample-notes", "module.json")
        with open(path) as handle:
            document = json.load(handle)
        document["provides"] = ["plans"]
        with open(path, "w") as handle:
            json.dump(document, handle)
        self.shipped = os.path.join(self.rel, "workbench", "shipped_approvals")

    def go(self, argv, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        previous = os.getcwd()
        os.chdir(cwd or self.real)
        try:
            code = cli.main(list(argv), out, err, store_root=self.store_root, distribution=self.rel, stdin=NoInput())
        finally:
            os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def real_verifiers(self):
        for name, real in (("verify_package", REAL_VERIFY_PACKAGE), ("verify_packages", REAL_VERIFY_PACKAGES)):
            restore = unittest.mock.patch.object(verify, name, real)
            restore.start()
            self.addCleanup(restore.stop)

    def level(self, level):
        """Attach (so that a rendering record exists) and read the level of the key as `level`."""
        self.attach_at("none")
        self.real_verifiers()

        def level_now(guarded, start, key):
            if os.path.realpath(start) != os.path.realpath(self.real):
                raise levelrun.Refusal("no project holds the directory")
            return level, self.project_id, self.real

        patch = unittest.mock.patch.object(levelrun, "level_now", level_now)
        patch.start()
        self.addCleanup(patch.stop)

    def digest(self):
        return firstparty.digest_of(firstparty.preview_text(firstparty.plan_release(self.rel)))

    def written(self):
        return os.path.isdir(os.path.join(self.shipped, "packages"))

    def refused(self, argv, contains=""):
        code, out, err = self.go(argv)
        self.assertEqual(1, code, (out, err))
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertFalse(self.written())
        self.assertEqual([], self.log())
        return err

    def edit(self):
        with open(os.path.join(self.package, *NOTES), "a") as handle:
            handle.write("changed\n")


class AtAsk(ReleaseAsk):
    def test_the_right_digest_writes_the_release_and_logs_the_attempt_with_it_and_the_outcome(self):
        self.level("ask")
        digest = self.digest()
        code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(0, code, (out, err))
        self.assertIn("wrote 3 approvals for 1 first-party packages", out)
        self.assertEqual(3, len(os.listdir(os.path.join(self.shipped, "packages"))))
        attempt, outcome = self.log()
        self.assertEqual([KEY, "ask", "digest:" + digest], attempt.split("\t")[3:])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])
        self.assertTrue(firstparty.is_first_party(self.package, self.rel))

    def test_no_digest_is_refused_and_names_the_preview_and_writes_nothing(self):
        self.level("ask")
        err = self.refused(["release-approvals"], "wb preview release-approvals")
        self.assertIn("--digest", err)

    def test_a_malformed_digest_is_refused(self):
        self.level("ask")
        for bad in ("", "abc", "0" * 31, "0" * 33, "A" * 32, "g" * 32, self.digest().upper()):
            with self.subTest(digest=bad):
                err = self.refused(["release-approvals", "--digest", bad], "32 lowercase hexadecimal characters")
                self.assertNotIn("not the one of the release plan", err)

    def test_a_wrong_digest_is_refused_and_writes_nothing(self):
        self.level("ask")
        self.refused(["release-approvals", "--digest", "0" * 32], "not the one of the release plan built now")

    def test_a_digest_of_an_earlier_preview_is_refused_after_a_package_changed(self):
        self.level("ask")
        earlier = self.digest()
        self.edit()
        self.refused(["release-approvals", "--digest", earlier], "not the one of the release plan built now")

    def test_a_refused_package_is_refused_with_its_reasons_and_writes_nothing(self):
        self.level("ask")
        with open(os.path.join(self.rel, "packages", "README"), "w") as handle:
            handle.write("x")
        self.refused(["release-approvals", "--digest", "0" * 32], "not a package directory")

    def test_a_package_changed_after_the_digest_was_checked_is_not_released_by_the_run(self):
        self.level("ask")
        digest = self.digest()
        decl, tree = firstparty._package_hashes(self.package, "sample")
        original = levelrun.apply_logged

        def after_the_check(*args, **kwargs):
            self.edit()  # between the digest check and the write
            return original(*args, **kwargs)

        with unittest.mock.patch.object(levelrun, "apply_logged", after_the_check):
            code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(0, code, (out, err))
        # The records name the hashes that were confirmed, so the tree as it is now is not trusted.
        self.assertTrue(approvals.check_package(firstparty.shipped_tree(self.rel), "sample", decl, tree).approved)
        self.assertFalse(firstparty.is_first_party(self.package, self.rel))

    def test_an_attempt_that_cannot_be_written_stops_before_any_record(self):
        self.level("ask")
        digest = self.digest()
        with unittest.mock.patch.object(levellog, "begin", side_effect=levellog.LogError("the log is full")):
            code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(1, code, (out, err))
        self.assertIn("the log is full", err)
        self.assertIn("nothing was written", err)
        self.assertFalse(self.written())
        self.assertEqual([], self.log())

    def test_a_failure_of_the_write_after_a_record_says_earlier_records_remain_and_exits_with_four(self):
        self.level("ask")
        digest = self.digest()
        with unittest.mock.patch.object(firstparty, "write_release",
                                        side_effect=firstparty.ReleaseError("disk full", 2)):
            code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(4, code, (out, err))
        self.assertIn("disk full", err)
        self.assertIn("records written before the failure remain", err)
        attempt, outcome = self.log()
        self.assertEqual(["refused", "stopped after writing (exit 4)"], outcome.split("\t")[3:])

    def test_a_second_run_with_the_new_digest_writes_nothing_more(self):
        self.level("ask")
        self.assertEqual(0, self.go(["release-approvals", "--digest", self.digest()])[0])
        before = self.tree(self.shipped)
        code, out, err = self.go(["release-approvals", "--digest", self.digest()])
        self.assertEqual(0, code, (out, err))
        self.assertEqual(before, self.tree(self.shipped))


class AtOtherLevels(ReleaseAsk):
    def test_a_digest_at_none_is_refused_before_the_run_and_writes_nothing(self):
        self.level("none")
        self.refused(["release-approvals", "--digest", self.digest()], "takes no digest")

    def test_a_run_at_none_without_a_digest_still_goes_on_and_is_logged(self):
        self.level("none")
        code, out, err = self.go(["release-approvals"])
        self.assertEqual(0, code, (out, err))
        self.assertTrue(self.written())
        attempt, outcome = self.log()
        self.assertEqual([KEY, "none", ""], attempt.split("\t")[3:])

    def test_a_digest_at_a_terminal_is_refused_and_a_terminal_run_without_one_goes_on(self):
        self.level("ask")
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: True):
            code, out, err = self.go(["release-approvals", "--digest", self.digest()])
            self.assertEqual(1, code, (out, err))
            self.assertIn("without a terminal", err)
            self.assertFalse(self.written())
            code, out, err = self.go(["release-approvals"])
        self.assertEqual(0, code, (out, err))
        self.assertTrue(self.written())
        self.assertEqual([], self.log())

    def test_where_no_level_can_be_read_the_run_goes_on_as_before_and_is_not_logged(self):
        self.level("ask")
        for argv in (["release-approvals", "--digest", "0" * 32], ["release-approvals"]):
            with self.subTest(argv=argv), tempfile.TemporaryDirectory() as tmp:
                shutil.rmtree(self.shipped, ignore_errors=True)
                code, out, err = self.go(argv, cwd=tmp)
                # No project: the level reads as nothing, no digest is checked and the command goes on as it always did.
                # This is the limit the spec states, not a refusal: the owner's own runs without a terminal take this path.
                self.assertEqual(0, code, (out, err))
                self.assertIn("wrote 3 approvals", out)
                self.assertTrue(self.written())
                self.assertEqual([], self.log())

    def test_at_block_the_command_goes_on_as_before_with_or_without_a_digest_and_is_not_logged(self):
        # The harness denies the agent at block; the command never refused itself, and a digest is not read there.
        self.level("block")
        for argv in (["release-approvals"], ["release-approvals", "--digest", "0" * 32]):
            with self.subTest(argv=argv):
                shutil.rmtree(self.shipped, ignore_errors=True)
                code, out, err = self.go(argv)
                self.assertEqual(0, code, (out, err))
                self.assertTrue(self.written())
                self.assertEqual([], self.log())


class AtAskFromTheOwnersSettings(ReleaseAsk):
    """Increment D: the level is the owner's setting, rendered at attach and read back through the rendering record, with no patch
    of the level reading."""

    def owners(self, level):
        self.attach_at(level)
        self.real_verifiers()

    def plan(self):
        table, _, _ = rendering.current_table(self.guarded, self.real)
        return rendering.plan(table)

    def test_the_owners_ask_is_read_back_and_settings_prints_it(self):
        self.owners("ask")
        code, out, err = self.go(["settings"])
        self.assertEqual(0, code, (out, err))
        self.assertIn("level wb release-approvals: ask\n", out)
        self.assertEqual([], [line for line in out.splitlines() if line.startswith("settings: ")])

    def test_at_ask_the_launcher_spellings_are_asked_for_and_the_interpreter_spellings_stay_denied(self):
        self.owners("ask")
        plan = self.plan()
        self.assertEqual("ask", plan.keys[KEY])
        self.assertIn("wb release-approvals", plan.ask)
        self.assertIn("wb release-approvals *", plan.ask)
        self.assertIn("wb release-approvals *", plan.open)
        self.assertNotIn("wb release-approvals *", plan.deny)
        self.assertNotIn("python3 -m workbench release-approvals *", plan.ask + plan.open)
        # The interpreter spellings are denied by the owner-run list, which the opened patterns do not include.
        self.assertIn("Bash(python3 -m workbench release-approvals", self.rendered())

    def permissions(self):
        return json.loads(self.rendered())["permissions"]

    SPELLINGS = ("Bash(wb release-approvals)", "Bash(wb release-approvals *)")
    INTERPRETER = "Bash(python3 -m workbench release-approvals *)"

    def test_the_rendered_file_at_ask_asks_for_the_launcher_spellings_and_denies_the_interpreter(self):
        self.owners("ask")
        permissions = self.permissions()
        for spelling in self.SPELLINGS:
            self.assertIn(spelling, permissions["ask"])
            self.assertNotIn(spelling, permissions["deny"])
        self.assertIn(self.INTERPRETER, permissions["deny"])
        self.assertNotIn(self.INTERPRETER, permissions["ask"])

    def test_the_rendered_file_at_block_denies_every_spelling(self):
        self.owners("block")
        permissions = self.permissions()
        for spelling in self.SPELLINGS + (self.INTERPRETER,):
            self.assertIn(spelling, permissions["deny"])
            self.assertNotIn(spelling, permissions["ask"])

    def test_the_rendered_file_at_none_neither_asks_for_nor_denies_the_launcher_spellings(self):
        self.owners("none")
        permissions = self.permissions()
        for spelling in self.SPELLINGS:
            self.assertNotIn(spelling, permissions["ask"] + permissions["deny"])
        self.assertIn(self.INTERPRETER, permissions["deny"])

    def test_at_block_every_spelling_is_denied(self):
        self.owners("block")
        plan = self.plan()
        self.assertEqual("deny", plan.keys[KEY])
        self.assertIn("wb release-approvals *", plan.deny)
        self.assertIn("python3 -m workbench release-approvals *", plan.deny)
        self.assertNotIn("wb release-approvals *", plan.ask)

    def test_at_none_the_launcher_spelling_is_open_and_the_interpreter_spellings_stay_denied(self):
        self.owners("none")
        plan = self.plan()
        self.assertEqual("none", plan.keys[KEY])
        self.assertIn("wb release-approvals *", plan.open)
        self.assertNotIn("wb release-approvals *", plan.ask + plan.deny)
        self.assertNotIn("python3 -m workbench release-approvals *", plan.open)
        text = self.rendered()
        self.assertNotIn("Bash(wb release-approvals", text)
        self.assertIn("Bash(python3 -m workbench release-approvals", text)

    def test_at_ask_without_a_patch_a_bare_run_is_refused_and_the_right_digest_writes(self):
        self.owners("ask")
        self.refused(["release-approvals"], "wb preview release-approvals")
        digest = self.digest()
        code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(0, code, (out, err))
        self.assertTrue(self.written())
        attempt, outcome = self.log()
        self.assertEqual([KEY, "ask", "digest:" + digest], attempt.split("\t")[3:])
        self.assertEqual(["done", "written"], outcome.split("\t")[3:])

    def test_the_equals_form_is_accepted_and_a_repeated_digest_is_refused_whatever_the_values(self):
        self.owners("ask")
        digest = self.digest()
        self.refused(["release-approvals", "--digest=" + "0" * 32], "not the one of the release plan")
        for argv in (["--digest", digest, "--digest", "0" * 32], ["--digest", "0" * 32, "--digest=" + digest],
                     ["--digest", digest, "--digest", digest]):
            with self.subTest(argv=argv):
                self.refused(["release-approvals"] + argv, "once")
        code, out, err = self.go(["release-approvals", "--digest=" + digest])
        self.assertEqual(0, code, (out, err))
        attempt, _ = self.log()
        self.assertEqual("digest:" + digest, attempt.split("\t")[5])

    def requires_the_digest_all_the_same(self):
        # `ask` is rendered and the record was sound before the edit; the owner's own setting, in the guarded store, still says
        # ask, so the digest is required although the verified level now reads block.
        self.refused(["release-approvals"], "wb preview release-approvals")
        digest = self.digest()
        code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(0, code, (out, err))
        self.assertTrue(self.written())
        attempt, outcome = self.log()
        self.assertEqual([KEY, "ask", "digest:" + digest], attempt.split("\t")[3:])

    def test_an_edit_of_the_harness_file_does_not_let_a_bare_run_through_while_the_owner_says_ask(self):
        # Security review of Increments B to D (Medium): an agent that edits the harness file with a Bash write makes `ask` read
        # `block`, which used to skip the digest check.
        self.owners("ask")
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "a") as handle:
            handle.write("\n")
        self.requires_the_digest_all_the_same()

    def test_removing_the_local_manifest_does_not_let_a_bare_run_through_while_the_owner_says_ask(self):
        self.owners("ask")
        path = os.path.join(self.real, ".workbench", "local", "harness.json")
        self.assertTrue(os.path.isfile(path), path)
        os.remove(path)
        self.requires_the_digest_all_the_same()

    def test_from_a_directory_that_is_no_project_the_owners_ask_still_requires_the_digest(self):
        self.owners("ask")
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.go(["release-approvals"], cwd=tmp)
            self.assertEqual(1, code, (out, err))
            self.assertIn("wb preview release-approvals", err)
            self.assertFalse(self.written())
            code, out, err = self.go(["release-approvals", "--digest", self.digest()], cwd=tmp)
        self.assertEqual(0, code, (out, err))
        self.assertTrue(self.written())

    def fails_closed_with(self, text):
        """The owner's settings are damaged (`text` replaces the file) and the verified level cannot be read (the directory is no
        project): the digest is still required, because the check must not turn itself off when the owner's own settings cannot
        be read (security review, second look)."""
        self.owners("ask")
        self.guarded.write("settings", text.encode())
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.go(["release-approvals"], cwd=tmp)
            self.assertEqual(1, code, (out, err))
            self.assertIn("settings are damaged", err)
            self.assertIn("wb settings", err)
            self.assertFalse(self.written())
            code, out, err = self.go(["release-approvals", "--digest", self.digest()], cwd=tmp)
        self.assertEqual(0, code, (out, err))
        self.assertTrue(self.written())
        attempt, outcome = self.log()
        self.assertEqual([KEY, "ask"], attempt.split("\t")[3:5])

    def test_a_settings_file_that_is_not_json_fails_closed_for_the_key(self):
        self.fails_closed_with("not json")

    def test_a_levels_entry_that_is_not_an_object_fails_closed_for_the_key(self):
        self.fails_closed_with(json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": ["x"]}))

    def test_an_invalid_key_name_among_the_levels_fails_closed_for_the_key(self):
        self.fails_closed_with(json.dumps({"version": 2, "checkpoints": {}, "floor": [],
                                           "levels": {"wb release-approvals": "none", "Not A Key": "ask"}}))

    def test_settings_that_are_sound_and_say_none_still_go_on_as_before_from_a_directory_that_is_no_project(self):
        self.owners("none")
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.go(["release-approvals"], cwd=tmp)
        self.assertEqual(0, code, (out, err))
        self.assertTrue(self.written())
        self.assertEqual([], self.log())

    def test_where_the_level_is_forced_to_block_and_the_owners_setting_is_not_ask_the_command_goes_on_as_before(self):
        self.attach_at("block")
        self.real_verifiers()
        code, out, err = self.go(["release-approvals"])
        self.assertEqual(0, code, (out, err))
        self.assertTrue(self.written())
        self.assertEqual([], self.log())

    def test_a_part_way_failure_after_a_record_was_written_is_logged_as_stopped_after_writing(self):
        self.owners("ask")
        os.makedirs(self.shipped)
        decl, tree = firstparty._package_hashes(self.package, "sample")
        # A record for the package hashes under another subject: the modules are written first and the package record refuses.
        approvals.record_package(firstparty._ShippedWriter(self.shipped), "other", decl, tree, [], "workbench-release",
                                 firstparty.RELEASE_TIME)
        digest = self.digest()
        code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(4, code, (out, err))
        self.assertIn("records written before the failure remain", err)
        attempt, outcome = self.log()
        self.assertEqual(["refused", "stopped after writing (exit 4)"], outcome.split("\t")[3:])

    def test_a_failure_before_any_record_is_logged_as_refused_before_writing(self):
        self.owners("ask")
        digest = self.digest()
        with unittest.mock.patch.object(firstparty, "write_release",
                                        side_effect=firstparty.ReleaseError("could not write", 0)):
            code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(1, code, (out, err))
        self.assertNotIn("remain", err)
        self.assertEqual(["refused", "refused before writing"], self.log()[1].split("\t")[3:])

    def test_a_setting_of_ask_for_an_installer_command_that_does_not_offer_it_is_still_read_as_block(self):
        # `wb attach` offers block and none only: `ask` there is noted and read as block, as it was before this plan.
        self.attach_at("ask", key="wb attach")
        self.real_verifiers()
        code, out, err = self.go(["settings"])
        self.assertEqual(0, code, (out, err))
        self.assertIn("level wb attach: block\n", out)


if __name__ == "__main__":
    unittest.main()
