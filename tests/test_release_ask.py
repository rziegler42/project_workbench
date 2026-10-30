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
from workbench import approvals, approve, cli, firstparty, levellog, levelrun, verify

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

    def level(self, level):
        """Attach (so that a rendering record exists) and read the level of the key as `level`."""
        self.attach_at("none")
        for name, real in (("verify_package", REAL_VERIFY_PACKAGE), ("verify_packages", REAL_VERIFY_PACKAGES)):
            restore = unittest.mock.patch.object(verify, name, real)
            restore.start()
            self.addCleanup(restore.stop)
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

    def test_a_failure_of_the_write_is_a_refused_outcome_that_says_earlier_records_remain(self):
        self.level("ask")
        digest = self.digest()
        with unittest.mock.patch.object(firstparty, "write_release", side_effect=firstparty.ReleaseError("disk full")):
            code, out, err = self.go(["release-approvals", "--digest", digest])
        self.assertEqual(1, code, (out, err))
        self.assertIn("disk full", err)
        self.assertIn("records written before the failure remain", err)
        attempt, outcome = self.log()
        self.assertEqual("refused", outcome.split("\t")[3])

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


if __name__ == "__main__":
    unittest.main()
