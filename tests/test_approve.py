import hashlib
import io
import os
import pty
import select
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

import support
import unittest.mock

from workbench import approvals, approve, cli, declarations, request, store, verify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sample-package")
PROMPT = b"Anything else cancels and records nothing.\r\n> "
TIMEOUT = 30


def listing(top):
    found = {}
    for base, dirs, files in os.walk(top):
        for name in dirs + files:
            full = os.path.join(base, name)
            info = os.lstat(full)
            digest = ""
            if stat.S_ISREG(info.st_mode):
                with open(full, "rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
            found[os.path.relpath(full, top)] = (stat.S_IMODE(info.st_mode), digest, info.st_mtime_ns)
    return found


class Base(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.home = os.path.join(self.base, "home")
        os.makedirs(self.home)
        self.store = store.Store(os.path.join(self.home, ".config", "project-workbench"))
        self.store.ensure()
        self.path = os.path.join(self.base, "pkg")
        shutil.copytree(FIXTURE, self.path)

    def facts(self):
        result = verify.verify_package(self.path, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        return result.packages[0], {m.name: m for m in result.modules}

    def drive(self, args, answer=None, between=None, stdin="pty", stdout="pty", path=None):
        """Run `approve` in a child process whose terminals are real pseudo-terminals.

        `answer` is typed at the prompt; `between` runs once the prompt has appeared and
        before the answer is typed (to change the package while the owner reads).
        """
        master, slave = pty.openpty()
        env = dict(os.environ, HOME=self.home, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.Popen(
            [sys.executable, "-B", "-m", "workbench", "approve"] + list(args),
            stdin=slave if stdin == "pty" else subprocess.PIPE,
            stdout=slave if stdout == "pty" else subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, cwd=self.base)
        os.close(slave)
        output, sent = b"", False
        deadline = time.time() + TIMEOUT
        try:
            while time.time() < deadline:
                ready, _, _ = select.select([master], [], [], 0.2)
                if not ready:
                    if proc.poll() is not None:
                        break
                    continue
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    chunk = b""
                if not chunk:
                    break
                output += chunk
                if not sent and PROMPT in output:
                    sent = True
                    if between:
                        between()
                    os.write(master, (answer + "\n").encode())
            else:
                proc.kill()
                self.fail("the command did not finish: %r" % output[-300:])
            if stdin != "pty":
                proc.stdin.close()
            code = proc.wait(timeout=TIMEOUT)
            piped = proc.stdout.read() if stdout != "pty" else b""
            error = proc.stderr.read()
        finally:
            os.close(master)
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            if proc.stdin is not None:
                proc.stdin.close()
            proc.stderr.close()
            if stdout != "pty":
                proc.stdout.close()
        return code, (output + piped).decode("utf-8", "replace"), error.decode("utf-8", "replace")

    def approved_module(self, name):
        _, modules = self.facts()
        module = modules[name]
        return approvals.check_module(self.store, "sample/" + name, module.declaration_hash,
                                      module.tree_hash).approved

    def approved_package(self):
        info, _ = self.facts()
        return approvals.check_package(self.store, "sample", info.declaration_hash,
                                       info.tree_hash).approved

    def nothing_recorded(self):
        self.assertEqual(os.listdir(os.path.join(self.store.root, "packages")), [])


class PackageApprovalTest(Base):
    def test_the_correct_text_records_the_package_and_every_module(self):
        info, modules = self.facts()
        code, output, error = self.drive([self.path], answer=info.tree_hash[:12])
        self.assertEqual((code, error), (0, ""), output)
        self.assertIn("approved package sample", output)
        self.assertIn("approved module sample/sample-harness", output)
        self.assertIn("approved module sample/sample-notes", output)
        self.assertTrue(self.approved_package())
        self.assertTrue(self.approved_module("sample-harness"))
        self.assertTrue(self.approved_module("sample-notes"))
        record = approvals.check_package(self.store, "sample", info.declaration_hash,
                                         info.tree_hash).record
        self.assertEqual(record.approver, approve.approver_name())
        self.assertEqual(sorted(m[0] for m in record.modules), ["sample-harness", "sample-notes"])

    def test_the_request_is_printed_before_the_prompt(self):
        info, _ = self.facts()
        _, output, _ = self.drive([self.path], answer="no")
        self.assertIn("package sample 1.0.0", output)
        self.assertIn("HIGH RISK: it is a harness module", output)
        self.assertIn(info.tree_hash, output)
        self.assertLess(output.index("tree hash:"), output.index("type the first 12 characters"))

    def test_any_other_text_cancels_and_records_nothing(self):
        info, _ = self.facts()
        token = info.tree_hash[:12]
        for answer in ("", "yes", "y", "approve", token[:11], token + "0", token.upper(),
                       "0" * 12, info.declaration_hash[:12], token[::-1]):
            with self.subTest(answer=answer):
                code, output, _ = self.drive([self.path], answer=answer)
                self.assertEqual(code, 1)
                self.assertIn("cancelled: nothing was recorded", output)
                self.nothing_recorded()

    def test_a_module_tree_hash_does_not_approve_the_package(self):
        _, modules = self.facts()
        code, output, _ = self.drive([self.path], answer=modules["sample-notes"].tree_hash[:12])
        self.assertEqual(code, 1)
        self.assertIn("cancelled: nothing was recorded", output)
        self.nothing_recorded()

    def test_a_package_that_changes_while_it_is_shown_records_nothing(self):
        info, _ = self.facts()

        def change():
            with open(os.path.join(self.path, "sample-notes", "files", "docs", "notes.md"), "a") as h:
                h.write("changed after the request was shown\n")

        code, output, error = self.drive([self.path], answer=info.tree_hash[:12], between=change)
        self.assertEqual(code, 1, output)
        self.assertIn("changed while it was shown", error)
        self.nothing_recorded()

    def test_a_package_made_invalid_while_it_is_shown_records_nothing(self):
        info, _ = self.facts()

        def break_it():
            with open(os.path.join(self.path, "sample-notes", "stray.txt"), "w") as handle:
                handle.write("x")

        code, _, error = self.drive([self.path], answer=info.tree_hash[:12], between=break_it)
        self.assertEqual(code, 1)
        self.assertIn("changed while it was shown", error)
        self.nothing_recorded()

    def test_approving_again_keeps_the_first_record_and_says_so(self):
        info, _ = self.facts()
        self.assertEqual(self.drive([self.path], answer=info.tree_hash[:12])[0], 0)
        first = approvals.check_package(self.store, "sample", info.declaration_hash,
                                        info.tree_hash).record
        time.sleep(1.1)
        code, output, _ = self.drive([self.path], answer=info.tree_hash[:12])
        self.assertEqual(code, 0)
        self.assertIn("already approved package sample", output)
        self.assertIn(first.time, output)
        again = approvals.check_package(self.store, "sample", info.declaration_hash,
                                        info.tree_hash).record
        self.assertEqual(again, first)

    def test_the_package_is_not_changed_and_nothing_is_written_beside_it(self):
        info, _ = self.facts()
        def everything_but_the_store():
            return {k: v for k, v in listing(self.base).items()
                    if not k.startswith(os.path.join("home", ".config", "project-workbench"))}

        before = everything_but_the_store()
        self.assertEqual(self.drive([self.path], answer=info.tree_hash[:12])[0], 0)
        self.assertEqual(everything_but_the_store(), before)


class WhatIsShownIsWhatIsRecordedTest(Base):
    def test_the_request_is_rendered_from_the_verification_not_from_a_second_read(self):
        calls = []
        real = declarations.load_package

        def counting(*args, **kwargs):
            calls.append(args)
            return real(*args, **kwargs)

        with unittest.mock.patch.object(declarations, "load_package", counting):
            result, text, token, what = approve.build(self.path, None)
        self.assertEqual(len(calls), 1, "only the verification may read the declarations")
        info, _ = self.facts()
        self.assertEqual((token, what), (info.tree_hash[:12], "package"))
        self.assertIn("module sample/sample-notes 1.2.0", text)

    def test_the_modules_rendered_are_the_very_objects_that_were_hashed(self):
        seen = {}
        real = request.render_package

        def spy(name, version, package_hashes, entries, source=None):
            seen["entries"] = entries
            return real(name, version, package_hashes, entries, source)

        with unittest.mock.patch.object(request, "render_package", spy):
            result, _, _, _ = approve.build(self.path, None)
        hashed = {m.name: m for m in result.modules}
        for module, verified, executable in seen["entries"]:
            self.assertIs(module, hashed[module.name].module)
            self.assertEqual(executable, set(hashed[module.name].executable))

    def test_the_description_shown_is_the_one_whose_hash_is_recorded(self):
        result, text, _, _ = approve.build(self.path, None)
        (info,) = result.packages
        notes = next(m for m in result.modules if m.name == "sample-notes")
        from workbench import hashing
        self.assertEqual(hashing.declaration_hash(notes.module.declaration), notes.declaration_hash)
        self.assertIn(notes.module.description, text)

    def test_a_module_request_is_rendered_from_the_hashed_module_too(self):
        _, text, token, what = approve.build(self.path, "sample-notes")
        _, modules = self.facts()
        self.assertEqual((token, what), (modules["sample-notes"].tree_hash[:12], "module"))
        self.assertNotIn("module sample/sample-harness", text)

    def test_an_unknown_module_cannot_be_built(self):
        with self.assertRaises(approve._Refused) as caught:
            approve.build(self.path, "nope")
        self.assertIn("no module", str(caught.exception))

    def test_a_package_with_a_problem_cannot_be_built(self):
        with open(os.path.join(self.path, "sample-notes", "stray.txt"), "w") as handle:
            handle.write("x")
        with self.assertRaises(approve._Refused) as caught:
            approve.build(self.path, None)
        self.assertIn("unaccounted-file", str(caught.exception))


class RecordingTest(Base):
    def record(self, module_name=None):
        info, modules = self.facts()
        out, err = io.StringIO(), io.StringIO()
        code = approve._record(self.store, info, modules, module_name, out, err)
        return code, out.getvalue(), err.getvalue()

    def test_a_second_approval_in_the_same_second_still_says_already_approved(self):
        self.assertEqual(self.record()[0], 0)
        code, output, _ = self.record()
        self.assertEqual(code, 0)
        self.assertIn("already approved package sample", output)
        self.assertNotIn("\napproved", "\n" + output)

    def test_a_first_approval_says_approved(self):
        code, output, _ = self.record()
        self.assertEqual(code, 0)
        self.assertIn("approved package sample", output)
        self.assertNotIn("already", output)

    def test_a_failure_writing_the_package_record_names_what_was_written(self):
        def fail(*args, **kwargs):
            raise approvals.ApprovalError("simulated failure")

        with unittest.mock.patch.object(approvals, "record_package", fail):
            code, output, error = self.record()
        self.assertEqual(code, 1)
        self.assertIn("simulated failure", error)
        self.assertIn("the approval was not completed", error)
        self.assertIn("module sample/sample-harness", error)
        self.assertIn("module sample/sample-notes", error)
        self.assertTrue(self.approved_module("sample-harness"))
        self.assertTrue(self.approved_module("sample-notes"))
        self.assertFalse(self.approved_package())

    def test_a_failure_on_the_first_module_writes_nothing(self):
        def fail(*args, **kwargs):
            raise approvals.ApprovalError("simulated failure")

        with unittest.mock.patch.object(approvals, "record_module", fail):
            code, _, error = self.record()
        self.assertEqual(code, 1)
        self.assertIn("Records written by this run: none", error)
        self.nothing_recorded()


def run_git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    done = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.test",
         "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"] + list(args),
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if done.returncode != 0:
        raise AssertionError("git %s: %s" % (args, done.stderr.decode()))
    return done.stdout.decode().strip()


class SourceBase(Base):
    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.base, "source")
        shutil.copytree(FIXTURE, self.repo)
        run_git(self.repo, "init", "-q", "--template=")
        self.commit1 = self.commit_all("first")
        self.cache = os.path.join(self.store.root, "cache")

    def commit_all(self, message):
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-q", "-m", message, "--allow-empty")
        return run_git(self.repo, "rev-parse", "HEAD")

    def package_record(self, decl_tree=None):
        info, _ = self.facts()
        decl, tree = decl_tree or (info.declaration_hash, info.tree_hash)
        return approvals.check_package(self.store, "sample", decl, tree)

    def cached(self):
        return sorted(name for name in os.listdir(self.cache))


class SourceApprovalTest(SourceBase):
    def test_a_source_is_downloaded_shown_and_approved_with_the_commit_pinned(self):
        info, _ = self.facts()
        code, output, error = self.drive(["--source", self.repo, "--ref", "main"],
                                         answer=info.tree_hash[:12])
        self.assertEqual((code, error), (0, ""), output)
        self.assertIn("Downloading", output)
        self.assertIn(self.commit1, output)
        self.assertIn("downloaded copy:", output)
        self.assertIn("approved package sample", output)
        self.assertIn("pinned commit " + self.commit1, output)
        record = self.package_record()
        self.assertTrue(record.approved)
        self.assertEqual(record.record.commit, self.commit1)
        self.assertTrue(self.approved_module("sample-harness"))
        self.assertTrue(self.approved_module("sample-notes"))
        self.assertEqual(len(self.cached()), 1)

    def test_the_hash_to_type_is_the_one_of_the_downloaded_copy(self):
        info, _ = self.facts()
        _, output, _ = self.drive(["--source", self.repo], answer="no")
        self.assertIn("tree hash:        " + info.tree_hash, output)
        self.assertIn("cancelled: nothing was recorded", output)

    def test_the_default_ref_is_head(self):
        info, _ = self.facts()
        code, output, _ = self.drive(["--source", self.repo], answer=info.tree_hash[:12])
        self.assertEqual(code, 0, output)
        self.assertEqual(self.package_record().record.commit, self.commit1)

    def test_a_ref_that_moved_to_different_content_is_not_approved(self):
        info, _ = self.facts()
        self.assertEqual(self.drive(["--source", self.repo, "--ref", "main"],
                                    answer=info.tree_hash[:12])[0], 0)
        with open(os.path.join(self.repo, "sample-notes", "files", "docs", "notes.md"), "a") as h:
            h.write("moved\n")
        commit2 = self.commit_all("second")
        self.assertNotEqual(commit2, self.commit1)

        # The old token no longer matches what the ref now gives.
        code, output, _ = self.drive(["--source", self.repo, "--ref", "main"],
                                     answer=info.tree_hash[:12])
        self.assertEqual(code, 1)
        self.assertIn("cancelled: nothing was recorded", output)
        self.assertIn(commit2, output)
        # Two module records and the package record from the first approval, and no more.
        self.assertEqual(len(self.package_records_in_store()), 3)

        # The new content has no approval, and the pinned commit's content still has one.
        moved = verify.verify_package(self.copy_of(commit2), harness_required=False)
        self.assertTrue(moved.accepted)
        new = moved.packages[0]
        self.assertNotEqual(new.tree_hash, info.tree_hash)
        self.assertFalse(approvals.check_package(self.store, "sample", new.declaration_hash,
                                                 new.tree_hash).approved)
        self.assertTrue(self.package_record().approved)
        # Fetching the pinned commit again gives the approved content.
        code, output, _ = self.drive(["--source", self.repo, "--ref", self.commit1],
                                     answer=info.tree_hash[:12])
        self.assertEqual(code, 0, output)
        self.assertIn("already approved package sample", output)
        self.assertEqual(self.package_record().record.commit, self.commit1)

    def copy_of(self, commit):
        """The downloaded package whose fetch.json names `commit`."""
        import json
        for directory in self.cached():
            with open(os.path.join(self.cache, directory, "fetch.json")) as handle:
                if json.load(handle)["commit"] == commit:
                    return os.path.join(self.cache, directory, "package")
        self.fail("no downloaded copy of " + commit)

    def package_records_in_store(self):
        return os.listdir(os.path.join(self.store.root, "packages"))

    def test_declining_records_nothing_and_keeps_the_downloaded_copy(self):
        code, output, _ = self.drive(["--source", self.repo], answer="no")
        self.assertEqual(code, 1)
        self.nothing_recorded()
        (directory,) = self.cached()
        kept = os.path.join(self.cache, directory, "package", "package.json")
        self.assertTrue(os.path.isfile(kept))
        self.assertIn("downloaded copy is kept at", output)
        self.assertIn(os.path.join(self.cache, directory, "package"), output)

    def test_a_downloaded_copy_that_fails_verification_records_nothing(self):
        with open(os.path.join(self.repo, "sample-notes", "stray.txt"), "w") as handle:
            handle.write("x")
        self.commit_all("stray")
        code, output, error = self.drive(["--source", self.repo], answer="x")
        self.assertEqual(code, 1)
        self.assertIn("unaccounted-file", error)
        self.assertIn("downloaded copy is kept at", error)
        self.assertNotIn("type the first", output)
        self.nothing_recorded()
        self.assertEqual(len(self.cached()), 1)

    def test_a_download_that_fails_records_nothing_and_leaves_the_cache_empty(self):
        code, _, error = self.drive(["--source", self.repo, "--ref", "no-such-branch"], answer="x")
        self.assertEqual(code, 1)
        self.assertIn("the download failed", error)
        self.nothing_recorded()
        self.assertEqual(self.cached(), [])

    def test_a_source_that_is_not_allowed_is_refused_before_anything_is_fetched(self):
        for source in ("ext::sh -c id", "http://example.invalid/x", "git://example.invalid/x"):
            with self.subTest(source=source):
                code, _, error = self.drive(["--source", source], answer="x")
                self.assertEqual(code, 1)
                self.assertIn("the download failed", error)
        self.nothing_recorded()
        self.assertEqual(self.cached(), [])

    def test_nothing_is_downloaded_when_the_terminal_test_fails(self):
        code, output, error = self.drive(["--source", self.repo], answer="x", stdin="pipe")
        self.assertEqual(code, 1)
        self.assertIn("owner-run", error)
        self.assertNotIn("Downloading", output)
        self.assertEqual(self.cached(), [])
        self.nothing_recorded()

    def test_a_downloaded_copy_that_changes_while_it_is_shown_records_nothing(self):
        info, _ = self.facts()

        def tamper():
            (directory,) = self.cached()
            path = os.path.join(self.cache, directory, "package", "sample-notes", "files", "docs", "notes.md")
            os.chmod(path, 0o644)
            with open(path, "a") as handle:
                handle.write("changed after it was shown\n")

        code, output, error = self.drive(["--source", self.repo], answer=info.tree_hash[:12],
                                         between=tamper)
        self.assertEqual(code, 1, output)
        self.assertIn("changed while it was shown", error)
        self.nothing_recorded()

    def test_a_module_from_a_source_has_no_package_record_and_no_pin(self):
        _, modules = self.facts()
        code, output, _ = self.drive(["--source", self.repo, "--module", "sample-notes"],
                                     answer=modules["sample-notes"].tree_hash[:12])
        self.assertEqual(code, 0, output)
        self.assertTrue(self.approved_module("sample-notes"))
        self.assertFalse(self.package_record().approved)
        self.assertNotIn("pinned commit", output)

    def test_the_same_content_from_another_commit_is_the_same_approval(self):
        info, _ = self.facts()
        self.assertEqual(self.drive(["--source", self.repo], answer=info.tree_hash[:12])[0], 0)
        commit2 = self.commit_all("history only")
        self.assertNotEqual(commit2, self.commit1)
        code, output, _ = self.drive(["--source", self.repo], answer=info.tree_hash[:12])
        self.assertEqual(code, 0, output)
        self.assertIn("already approved package sample", output)
        self.assertIn(commit2, output)
        self.assertEqual(self.package_record().record.commit, self.commit1)
        self.assertIn("kept the earlier pin " + self.commit1, output)
        self.assertIn("this download was commit " + commit2, output)

    def test_a_local_approval_is_kept_when_the_same_content_is_approved_from_a_source(self):
        info, _ = self.facts()
        self.assertEqual(self.drive([self.path], answer=info.tree_hash[:12])[0], 0)
        code, output, _ = self.drive(["--source", self.repo], answer=info.tree_hash[:12])
        self.assertEqual(code, 0, output)
        self.assertIn("already approved package sample", output)
        self.assertIn("no commit is pinned", output)
        self.assertIsNone(self.package_record().record.commit)


class SourceUsageTest(SourceBase):
    def usage(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["approve"] + list(argv), out, err, store_root=self.store.root)
        return code, err.getvalue()

    def test_exactly_one_of_a_package_and_a_source_is_required(self):
        for argv in ([], [self.path, "--source", self.repo], ["--ref", "main"]):
            with self.subTest(argv=argv):
                code, error = self.usage(*argv)
                self.assertEqual(code, 2)
                self.assertIn("usage:", error)

    def test_ref_goes_with_a_source(self):
        code, error = self.usage(self.path, "--ref", "main")
        self.assertEqual(code, 2)
        self.assertIn("--ref goes with --source", error)

    def test_empty_values_are_usage_errors(self):
        for argv in (["--source", ""], ["--source", self.repo, "--ref", ""],
                     ["--source", self.repo, "--module", ""], [""]):
            with self.subTest(argv=argv):
                self.assertEqual(self.usage(*argv)[0], 2)

    def test_nothing_is_downloaded_or_recorded_on_a_usage_error(self):
        self.usage(self.path, "--source", self.repo)
        self.assertEqual(self.cached(), [])
        self.nothing_recorded()


class ModuleApprovalTest(Base):
    def test_one_module_with_its_own_hash_records_only_that_module(self):
        _, modules = self.facts()
        code, output, error = self.drive([self.path, "--module", "sample-notes"],
                                         answer=modules["sample-notes"].tree_hash[:12])
        self.assertEqual((code, error), (0, ""), output)
        self.assertTrue(self.approved_module("sample-notes"))
        self.assertFalse(self.approved_module("sample-harness"))
        self.assertFalse(self.approved_package())
        self.assertIn("module sample/sample-notes 1.2.0", output)
        self.assertNotIn("module sample/sample-harness", output)

    def test_the_package_hash_does_not_approve_a_single_module(self):
        info, _ = self.facts()
        code, output, _ = self.drive([self.path, "--module", "sample-notes"],
                                     answer=info.tree_hash[:12])
        self.assertEqual(code, 1)
        self.assertIn("cancelled: nothing was recorded", output)
        self.nothing_recorded()

    def test_a_harness_module_is_approved_on_its_own_record_only(self):
        _, modules = self.facts()
        code, output, _ = self.drive([self.path, "--module", "sample-harness"],
                                     answer=modules["sample-harness"].tree_hash[:12])
        self.assertEqual(code, 0, output)
        self.assertIn("HIGH RISK: it is a harness module", output)
        self.assertTrue(self.approved_module("sample-harness"))
        self.assertFalse(self.approved_package())

    def test_an_unknown_module_is_refused_before_the_prompt(self):
        code, output, error = self.drive([self.path, "--module", "nope"], answer="x")
        self.assertEqual(code, 1)
        self.assertIn("no module", error)
        self.assertNotIn("type the first", output)
        self.nothing_recorded()


class RefusalTest(Base):
    def test_piped_input_is_refused_even_with_a_terminal_for_output(self):
        info, _ = self.facts()
        code, output, error = self.drive([self.path], answer=info.tree_hash[:12], stdin="pipe")
        self.assertEqual(code, 1)
        self.assertIn("owner-run", error)
        self.assertNotIn("type the first", output)
        self.nothing_recorded()

    def test_piped_output_is_refused_even_with_a_terminal_for_input(self):
        info, _ = self.facts()
        code, output, error = self.drive([self.path], answer=info.tree_hash[:12], stdout="pipe")
        self.assertEqual(code, 1)
        self.assertIn("owner-run", error)
        self.nothing_recorded()

    def test_both_piped_is_refused(self):
        code, _, error = self.drive([self.path], answer="x", stdin="pipe", stdout="pipe")
        self.assertEqual(code, 1)
        self.assertIn("owner-run", error)
        self.nothing_recorded()

    def test_in_process_streams_that_are_not_terminals_are_refused(self):
        info, _ = self.facts()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["approve", self.path], out, err, store_root=self.store.root,
                        stdin=io.StringIO(info.tree_hash[:12] + "\n"))
        self.assertEqual(code, 1)
        self.assertIn("owner-run", err.getvalue())
        self.assertEqual(out.getvalue(), "")
        self.nothing_recorded()

    def test_the_terminal_test_is_on_file_descriptors_not_the_environment(self):
        info, _ = self.facts()
        env = dict(os.environ, HOME=self.home, PYTHONPATH=ROOT, TERM="xterm", CI="", PS1="$ ")
        done = subprocess.run(
            [sys.executable, "-B", "-m", "workbench", "approve", self.path],
            input=(info.tree_hash[:12] + "\n").encode(), env=env, cwd=self.base,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(done.returncode, 1)
        self.nothing_recorded()

    def test_there_is_no_yes_option(self):
        for flag in ("--yes", "-y", "--force", "--confirm", "--hash"):
            with self.subTest(flag=flag):
                out, err = io.StringIO(), io.StringIO()
                code = cli.main(["approve", self.path, flag], out, err, store_root=self.store.root)
                self.assertEqual(code, 2)
        self.nothing_recorded()

    def test_a_package_that_fails_verification_records_nothing_and_shows_no_prompt(self):
        with open(os.path.join(self.path, "sample-notes", "stray.txt"), "w") as handle:
            handle.write("x")
        code, output, error = self.drive([self.path], answer="x")
        self.assertEqual(code, 1)
        self.assertIn("unaccounted-file", error)
        self.assertIn("nothing was recorded", error)
        self.assertNotIn("type the first", output)
        self.nothing_recorded()

    def test_a_package_given_as_a_symbolic_link_is_refused(self):
        link = os.path.join(self.base, "link")
        os.symlink(self.path, link)
        code, output, error = self.drive([link], answer="x")
        self.assertEqual(code, 1)
        self.assertIn("symbolic link", error)
        self.assertNotIn("type the first", output)
        self.nothing_recorded()

    def test_a_missing_package_is_refused(self):
        code, _, error = self.drive([os.path.join(self.base, "nowhere")], answer="x")
        self.assertEqual(code, 1)
        self.assertIn("refused:", error)
        self.nothing_recorded()

    def test_empty_arguments_are_usage_errors(self):
        for argv in (["approve", ""], ["approve", self.path, "--module", ""], ["approve"]):
            with self.subTest(argv=argv):
                out, err = io.StringIO(), io.StringIO()
                self.assertEqual(cli.main(argv, out, err, store_root=self.store.root), 2)
        self.nothing_recorded()


class ApproverTest(unittest.TestCase):
    def test_the_approver_is_a_short_printable_name(self):
        name = approve.approver_name()
        self.assertTrue(name and len(name) <= 64 and name.isprintable())

    def test_the_approver_does_not_come_from_the_environment(self):
        saved = {k: os.environ.get(k) for k in ("USER", "LOGNAME", "LNAME", "USERNAME")}
        self.addCleanup(lambda: [os.environ.__setitem__(k, v) if v is not None
                                 else os.environ.pop(k, None) for k, v in saved.items()])
        before = approve.approver_name()
        for key in saved:
            os.environ[key] = "someone-else"
        self.assertEqual(approve.approver_name(), before)


if __name__ == "__main__":
    unittest.main()
