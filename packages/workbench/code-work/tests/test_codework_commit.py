"""The helper's `commit` (plan `2026-10-22-code-work-commit`, increment B).

Real git and real repositories. Each refusal is checked by what it leaves behind: HEAD, the index and the
work tree are as they were. The contract tested is written out in the plan under "The contract ported"."""

import io
import json
import os
import stat
import tempfile
import unittest
import unittest.mock

from tests import support_helpers

import support_git
from support_git import REAL_GIT, git, needs_git

H = support_helpers.load("code-work")
STANDARD = "/usr/bin" + os.pathsep + "/bin" + os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"
ALLOWED = {"rev-parse", "diff", "ls-files", "add", "commit", "reset", "show", "diff-tree", "config", "status"}
FORBIDDEN = {"push", "fetch", "checkout", "switch", "merge", "rebase", "tag", "branch", "pull", "clone"}


@needs_git
class Commit(support_git.Repo):
    def setUp(self):
        super().setUp()
        self.home = os.path.join(self.scratch, "home")
        os.mkdir(self.home)
        with open(os.path.join(self.home, ".gitconfig"), "w") as handle:
            handle.write("[user]\n\tname = Owner\n\temail = owner@example.invalid\n")
        self.first = self.head()

    def head(self):
        return git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def index(self):
        return git(self.repo, "ls-files", "-s").stdout

    def environment(self, path=None, home=None):
        return {"PATH": path or STANDARD, "HOME": home or self.home}

    def commit(self, *args, expected=None, path=None, home=None, cwd=None):
        """Run `code-work commit <args>`; return ``(exit code, stdout, stderr)``."""
        out, err = io.StringIO(), io.StringIO()
        argv = ["commit"] + list(args)
        with unittest.mock.patch.dict(os.environ, self.environment(path, home), clear=True):
            code = H.main(argv, out, err, cwd or self.repo)
        return code, out.getvalue(), err.getvalue()

    def simple(self, subject, *paths, body=None, trailers=(), leave=False, expected=None, **more):
        args = ["--expected-head", self.first if expected is None else expected, "--subject", subject]
        if body is not None:
            args += ["--body", body]
        for trailer in trailers:
            args += ["--trailer", trailer]
        if leave:
            args.append("--leave-other-staged")
        return self.commit(*args, "--", *paths, **more)

    def assertRefused(self, result, text=None):
        code, out, err = result
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        if text:
            self.assertIn(text, err)

    def assertUntouched(self, index=None):
        self.assertEqual(self.first, self.head())
        self.assertEqual(self.index() if index is None else index, self.index())


class Success(Commit):
    def test_a_modified_file_is_committed_with_a_subject_a_body_and_a_trailer(self):
        self.write("a.txt", "two\n")
        code, out, err = self.simple("Change a", "a.txt", body="Why.\n\nMore.", trailers=["Plan: x#A"])
        self.assertEqual((0, ""), (code, err))
        report = json.loads(out)
        self.assertEqual(self.head(), report["committed"])
        self.assertEqual(("Change a", ["a.txt"]), (report["subject"], report["paths"]))
        self.assertEqual("Change a\n\nWhy.\n\nMore.\n\nPlan: x#A\n",
                         git(self.repo, "log", "-1", "--format=%B").stdout.rstrip("\n") + "\n")
        self.assertEqual([self.first], git(self.repo, "rev-parse", "HEAD^@").stdout.split())
        self.assertEqual("", git(self.repo, "diff", "--cached", "--name-only").stdout)

    def test_a_new_file_and_a_deleted_file_are_committed_together(self):
        self.write("b.txt", "new\n")
        os.unlink(os.path.join(self.repo, "a.txt"))
        code, out, err = self.simple("Swap", "a.txt", "b.txt")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["a.txt", "b.txt"], sorted(git(self.repo, "show", "--name-only", "--format=", "HEAD",
                                                         "--no-renames").stdout.split()))
        self.assertEqual("b.txt\n", git(self.repo, "ls-files").stdout)

    def test_a_file_in_a_subdirectory_is_committed_from_a_directory_below_the_root(self):
        self.write("sub/c.txt", "c\n")
        self.assertEqual(0, self.simple("Add c", "sub/c.txt", cwd=os.path.join(self.repo, "sub"))[0])

    def test_the_other_staged_work_stays_staged_with_the_option(self):
        self.write("a.txt", "two\n")
        self.write("other.txt", "o\n")
        git(self.repo, "add", "other.txt")
        code, out, err = self.simple("Only a", "a.txt", leave=True)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual("other.txt\n", git(self.repo, "diff", "--cached", "--name-only").stdout)
        self.assertEqual(["a.txt"], git(self.repo, "show", "--name-only", "--format=", "HEAD").stdout.split())

    def test_the_message_is_stored_as_given_when_git_would_clean_it(self):
        self.write("a.txt", "two\n")
        self.assertEqual(0, self.simple("S", "a.txt", body="line  \n\n\n\nafter")[0])
        self.assertEqual("S\n\nline\n\nafter\n", git(self.repo, "log", "-1", "--format=%B").stdout.rstrip("\n") + "\n")


class Arguments(Commit):
    def test_each_malformed_command_line_is_refused(self):
        a = ["--expected-head", self.first, "--subject", "S"]
        for argv in (a + ["a.txt"],                              # no --
                     a + ["--"],                                 # no path
                     ["--subject", "S", "--", "a.txt"],           # no expected head
                     ["--expected-head", self.first, "--", "a.txt"],  # no subject
                     a + ["--subject", "T", "--", "a.txt"],       # repeated
                     a + ["--expected-head", self.first, "--", "a.txt"],
                     a + ["--body", "b", "--body", "c", "--", "a.txt"],
                     a + ["--force", "--", "a.txt"],              # unknown
                     a + ["--subject=S", "--", "a.txt"],
                     a + ["--leave-other-staged", "--leave-other-staged", "--", "a.txt"],
                     ["--subject"], ["--expected-head"], []):
            with self.subTest(argv=argv):
                self.assertRefused(self.commit(*argv))
        self.assertUntouched()

    def test_the_hash_must_be_the_full_lower_case_hash_of_head(self):
        self.write("a.txt", "two\n")
        for value in (self.first[:12], self.first.upper(), "HEAD", "none", "", "0" * 40, self.first + "0"):
            with self.subTest(value=value):
                self.assertRefused(self.simple("S", "a.txt", expected=value))
        self.assertUntouched()

    def test_more_paths_than_the_limit_are_refused(self):
        self.assertRefused(self.simple("S", *["f%d" % n for n in range(H.MAX_PATHS + 1)]), "more than")

    def test_a_directory_that_is_not_a_repository_is_refused(self):
        self.assertRefused(self.simple("S", "a.txt", cwd=self.scratch))


class Paths(Commit):
    def refuse(self, *paths, text=None):
        index = self.index()
        self.assertRefused(self.simple("S", *paths), text)
        self.assertUntouched(index)

    def test_paths_that_are_not_exact_names_are_refused(self):
        self.write("a.txt", "two\n")
        for path in ("", ".", "..", "./a.txt", "a//b", "a/../a.txt", "/etc/passwd", "*", "a.*", "a.tx[t]", "a?txt",
                     ":(glob)*", ":!a.txt", "-x", "-a.txt", "sub\\a.txt", ".git", ".git/config", ".GIT/config",
                     ".Git/HEAD", "a.txt\n", "a\tb", ".git ", ".git."):
            with self.subTest(path=path):
                self.refuse(path)
                self.refuse("a.txt", path)

    def test_a_directory_is_refused(self):
        self.write("sub/c.txt", "c\n")
        self.refuse("sub", text="not a file")

    def test_a_path_that_does_not_exist_and_is_not_tracked_is_refused(self):
        self.refuse("nothing.txt", text="not tracked")

    def test_an_ignored_untracked_file_is_committed_only_when_named_and_is_then_just_added(self):
        # Git refuses to add an ignored file without -f: the staged set then lacks it, and nothing is left.
        self.write(".gitignore", "skip.txt\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-q", "-m", "ignore")
        self.first = self.head()
        self.write("skip.txt", "x\n")
        self.refuse("skip.txt")

    def test_a_name_with_odd_but_printable_characters_is_committed_literally(self):
        self.write(" lead space.txt", "x\n")
        self.write("dollar$name.txt", "x\n")
        self.assertEqual(0, self.simple("S", " lead space.txt", "dollar$name.txt")[0])

    def test_the_same_file_named_twice_or_in_two_spellings_is_refused(self):
        self.write("a.txt", "two\n")
        self.refuse("a.txt", "a.txt", text="twice")
        self.refuse("a.txt", "A.TXT", text="twice")

    def test_a_link_as_the_file_is_refused(self):
        os.symlink("/etc/hosts", os.path.join(self.repo, "ln"))
        self.refuse("ln", text="symlink")

    def test_a_tracked_file_replaced_by_a_link_is_refused(self):
        os.unlink(os.path.join(self.repo, "a.txt"))
        os.symlink("/etc/hosts", os.path.join(self.repo, "a.txt"))
        self.refuse("a.txt", text="symlink")

    def test_a_path_through_a_link_to_a_directory_is_refused(self):
        outside = os.path.join(self.scratch, "outside")
        os.mkdir(outside)
        with open(os.path.join(outside, "f.txt"), "w") as handle:
            handle.write("x\n")
        os.symlink(outside, os.path.join(self.repo, "via"))
        self.refuse("via/f.txt", text="symlink")

    def test_a_path_whose_parent_is_a_file_is_refused(self):
        self.refuse("a.txt/b", text="not a file")

    def test_a_path_in_a_nested_repository_is_refused(self):
        nested = os.path.join(self.repo, "vendor")
        os.mkdir(nested)
        git(nested, "init", "-q")
        self.write("vendor/f.txt", "x\n")
        self.refuse("vendor/f.txt", text="nested repository")

    def test_a_path_in_a_directory_that_holds_a_git_file_is_refused(self):
        self.write("vendor/.git", "gitdir: /elsewhere\n")
        self.write("vendor/f.txt", "x\n")
        self.refuse("vendor/f.txt", text="nested repository")

    def test_a_file_with_more_than_one_deleted_state_is_still_exact(self):
        # A tracked file deleted from the work tree is committed as a deletion.
        os.unlink(os.path.join(self.repo, "a.txt"))
        self.assertEqual(0, self.simple("Drop a", "a.txt")[0])
        self.assertEqual("", git(self.repo, "ls-files").stdout)


class Message(Commit):
    def setUp(self):
        super().setUp()
        self.write("a.txt", "two\n")

    def refuse(self, subject="S", body=None, trailers=(), text=None):
        index = self.index()
        self.assertRefused(self.simple(subject, "a.txt", body=body, trailers=trailers), text)
        self.assertUntouched(index)

    def test_attribution_is_refused_in_the_subject_the_body_and_a_trailer(self):
        for text in ("Co-Authored-By: Claude <noreply@anthropic.com>", "Generated with Claude Code",
                     "written by Claude", "assisted-by: Anthropic", "see https://claude.ai/code/session_1",
                     "noreply@anthropic.com", "Authored-by: claude", "Co-Authored-By: the claude team"):
            with self.subTest(text=text):
                self.refuse(subject=text, text="attribution")
                self.refuse(body=text, text="attribution")
                self.refuse(trailers=[text if H._TRAILER.match(text) else "X: " + text], text="attribution")

    def test_attribution_is_found_through_look_alike_letters_zero_width_characters_and_folding(self):
        for text in ("Co-Authored-By: Clаude", "Co-Authored-By: Сlaude", "Co-Authored-By: Cla​ude",
                     "Co-Authored-By: Ｃｌａｕｄｅ", "generated by Clаude",
                     "Co-Authored-By: Αnthropic".replace("Α", "αn").replace("αnnthropic", "anthropic"),
                     "Co-Authored-By:\n  Claude", "Co-Authored-By​: Claude", "Generated-By:\n\tClaude"):
            with self.subTest(text=text):
                self.refuse(body=text)       # refused as attribution or as an unreadable look-alike

    def test_the_gaps_a_review_found_in_the_attribution_check_are_closed(self):
        for text in ("Co\u2011Authored\u2011By: Claude", "Co\u2013Authored\u2013By: Claude", "Co authored by: Claude",
                     "Generated  with Claude", "Generated\twith Claude", "Generated\nwith Claude",
                     "Generated with [Claude Code]", "Generated with **Claude**", "Cl\u034faude generated by Claude",
                     "Generated by Cl\ufe0faude", "Generated by Cl\u0336aude", "Generated by Cl\u3164aude",
                     "Written by Cl\u0501ude".replace("\u0501ude", "au\u0501e"), "Generated by Cla\u057de",
                     "Generated by Cla\u03c5de", "Generated by Claud\u00e9", "Written using Claude",
                     "Drafted by Claude", "Powered by Claude", "AI-assisted (Claude)", "Claude-Session: x",
                     "noreply+1@anthropic.com", "Assisted by: Claude", "Co\u2212Authored\u2212By: Claude"):
            with self.subTest(text=text):
                self.refuse(body=text)
                self.refuse(subject=text)

    def test_the_gaps_a_second_review_found_are_closed(self):
        for text in ("Co-Authored-By: Cl\x01aude", "Co-Authored-By: Cl\x7faude", "Co-Authored-By: Cl\ue000aude",
                     "Co-Authored-By: Cl\U000f0000aude", "Generated by Cl\u2800aude", "Generated by Cl\u1680aude",
                     "Co-Authored-By: Cl\u0251ude", "Co-Authored-By: \u1d04laude", "Co-Authored-By: C\u0142aude",
                     "Co-developed-by: Claude", "Signed-off-by: Claude", "Built with Claude Code",
                     "Claude wrote this", "Claude Session: https://x", "see claude.ai/?session=x",
                     "see claude.ai:443/code/x", "see claude\u3002ai/code/x", "see claude.ai/api/x"):
            with self.subTest(text=text):
                self.refuse(body=text)

    def test_ordinary_japanese_korean_and_mixed_latin_text_is_committed(self):
        self.write("a.txt", "two\n")
        for subject in ("\u65e5\u672c\u8a9e\u306e\u30c6\u30b9\u30c8", "\ud55c\uae00\u6f22\u5b57", "API\u3092\u4fee\u6b63", "\u00b5s timer"):
            with self.subTest(subject=subject):
                self.assertEqual(0, self.simple(subject, "a.txt")[0])
                self.write("a.txt", subject + "\n")
                self.first = self.head()

    def test_a_combining_mark_no_letter_holds_is_refused_even_without_a_name(self):
        self.refuse(body="x\u0345 y", text="combining")

    def test_a_long_line_of_repeats_is_checked_in_bounded_time(self):
        import time
        started = time.monotonic()
        request = H.Request()
        request.subject, request.body = "S", "co-authored-by: " * 6000
        H.refuse_attribution(request)        # nothing in it names a tool, and the scan is bounded
        self.assertLess(time.monotonic() - started, 5)

    def test_text_that_only_resembles_attribution_is_committed(self):
        self.assertEqual(0, self.simple("Fix the claude.ai docs link rules", "a.txt",
                                        body="Reviewed by Alice. Café menu, naïve résumé.")[0])

    def test_a_subject_that_is_not_one_clean_line_is_refused(self):
        for subject in ("", "   ", "a\nb", "a\rb", "a\0b", "x" * (H.MAX_SUBJECT + 1), "x" * 100000):
            with self.subTest(subject=subject[:20]):
                self.refuse(subject=subject)

    def test_a_body_that_is_empty_or_holds_a_nul_is_refused(self):
        for body in ("", "  \n ", "a\0b", "x" * (H.MAX_BODY + 1)):
            with self.subTest(body=body[:20]):
                self.refuse(body=body)

    def test_a_trailer_must_be_one_key_value_line(self):
        for trailer in ("no colon", "Key:", "Key:   ", "Key: a\nOther: b", "Key: a\0", ": value", "9Key: v", "Key: v\r",
                        "A B: v", "K" * 70 + ": v", "Key: " + "v" * 1100):
            with self.subTest(trailer=trailer[:20]):
                self.refuse(trailers=[trailer], text="trailer")

    def test_too_many_trailers_are_refused(self):
        self.refuse(trailers=["K: v"] * (H.MAX_TRAILERS + 1), text="trailers")


class State(Commit):
    def test_a_merge_revert_cherry_pick_or_rebase_in_progress_is_refused_before_anything_is_staged(self):
        self.write("a.txt", "two\n")
        gitdir = os.path.join(self.repo, ".git")
        for name in ("MERGE_HEAD", "REVERT_HEAD", "CHERRY_PICK_HEAD", "rebase-merge", "rebase-apply"):
            with self.subTest(name=name):
                path = os.path.join(gitdir, name)
                if name.startswith("rebase"):
                    os.mkdir(path)
                else:
                    with open(path, "w") as handle:
                        handle.write(self.first + "\n")
                self.assertRefused(self.simple("S", "a.txt"), "in progress")
                self.assertEqual("", git(self.repo, "diff", "--cached", "--name-only").stdout)
                self.assertUntouched()
                (os.rmdir if name.startswith("rebase") else os.unlink)(path)

    def test_a_tracked_name_that_is_a_link_under_another_spelling_is_refused(self):
        if os.path.exists(os.path.join(self.repo, "A.TXT")):
            pass
        nfc, nfd = "\u00e9.txt", "e\u0301.txt"
        self.write(nfc, "x\n")
        git(self.repo, "add", nfc)
        git(self.repo, "commit", "-q", "-m", "accent")
        self.first = self.head()
        full = os.path.join(self.repo, nfd)
        if sorted(os.listdir(self.repo)).count(nfc) != 1 or not os.path.exists(full):
            self.skipTest("this filesystem keeps the two spellings apart")
        os.unlink(full)
        os.symlink("/etc/hosts", full)
        self.assertRefused(self.simple("S", nfc))
        self.assertUntouched()

    def test_a_cleanup_setting_in_the_repository_does_not_change_the_stored_message(self):
        self.write("a.txt", "two\n")
        self.config("commit.cleanup", "strip")
        self.assertEqual(0, self.simple("S", "a.txt", body="# kept\nline")[0])
        self.assertEqual("S\n\n# kept\nline", git(self.repo, "log", "-1", "--format=%B").stdout.strip())

    def test_a_moved_head_is_refused(self):
        self.write("a.txt", "two\n")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "moved")
        index = self.index()
        self.assertRefused(self.simple("S", "a.txt"), "HEAD moved")
        self.assertEqual(index, self.index())

    def test_staged_work_is_refused_without_the_option(self):
        self.write("a.txt", "two\n")
        self.write("other.txt", "o\n")
        git(self.repo, "add", "other.txt")
        index = self.index()
        self.assertRefused(self.simple("S", "a.txt"), "already holds staged")
        self.assertUntouched(index)

    def test_a_named_path_that_is_already_staged_is_refused(self):
        self.write("a.txt", "two\n")
        git(self.repo, "add", "a.txt")
        index = self.index()
        self.assertRefused(self.simple("S", "a.txt", leave=True), "already staged")
        self.assertUntouched(index)

    def test_a_named_path_with_no_change_is_refused(self):
        self.assertRefused(self.simple("S", "a.txt"), "no change")
        self.assertUntouched()

    def test_whitespace_errors_in_the_named_files_are_refused_and_nothing_is_staged(self):
        self.write("a.txt", "trailing   \n")
        self.assertRefused(self.simple("S", "a.txt"), "whitespace")
        self.assertUntouched()

    def test_a_repository_that_would_run_a_program_is_refused_and_the_program_does_not_run(self):
        self.write("a.txt", "two\n")
        marker = os.path.join(self.scratch, "ran")
        hook = os.path.join(self.repo, ".git", "hooks", "pre-commit")
        with open(hook, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
        os.chmod(hook, 0o755)
        self.assertRefused(self.simple("S", "a.txt"), "hook:pre-commit")
        self.assertFalse(os.path.exists(marker))
        self.assertUntouched()

    def test_a_signing_program_set_in_the_repository_is_refused(self):
        self.write("a.txt", "two\n")
        self.config("commit.gpgsign", "true")
        self.assertRefused(self.simple("S", "a.txt"), "commit.gpgsign")
        self.assertUntouched()

    def test_a_failed_commit_unstages_the_named_paths_and_says_so(self):
        self.write("a.txt", "two\n")
        bare = os.path.join(self.scratch, "nohome")
        os.mkdir(bare)       # no identity: git cannot make the commit after it has staged the file
        self.config("user.useConfigOnly", "true")
        result = self.simple("S", "a.txt", home=bare)
        self.assertRefused(result, "unstaged")
        self.assertUntouched()
        with open(os.path.join(self.repo, "a.txt")) as handle:
            self.assertEqual("two\n", handle.read())


class Races(Commit):
    def mover(self, on, also=""):
        """A `git` that makes another commit just before it runs the subcommand `on` (with `also` among its
        arguments, when given)."""
        script = os.path.join(self.outside, "git")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\nif [ \"$1\" = '%s' ] && case \" $* \" in *' %s'*) true;; *) false;; esac; then\n"
                         "  export GIT_AUTHOR_NAME=x GIT_AUTHOR_EMAIL=x@e"
                         " GIT_COMMITTER_NAME=x GIT_COMMITTER_EMAIL=x@e\n"
                         "  new=$('%s' commit-tree -p HEAD -m moved 'HEAD^{tree}')\n  '%s' update-ref HEAD \"$new\"\nfi\n"
                         "exec '%s' \"$@\"\n" % (on, also or "", REAL_GIT, REAL_GIT, REAL_GIT))
        os.chmod(script, 0o755)
        return self.outside + os.pathsep + STANDARD

    def test_head_moving_just_before_the_commit_is_reported_as_failed_and_names_the_commit(self):
        self.write("a.txt", "two\n")
        code, out, err = self.simple("S", "a.txt", path=self.mover("commit"))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("HEAD moved during the commit", err)
        self.assertIn(self.head()[:12], err)
        self.assertIn("nothing was undone", err)
        self.assertEqual(["a.txt"], git(self.repo, "show", "--name-only", "--format=", "HEAD").stdout.split())

    def test_head_moving_after_the_last_check_before_the_commit_is_named_as_such(self):
        self.write("a.txt", "two\n")
        code, out, err = self.simple("S", "a.txt", path=self.mover("commit"))
        self.assertIn("HEAD moved", err)

    def test_head_moving_after_the_staged_set_is_checked_is_refused_before_the_commit(self):
        self.write("a.txt", "two\n")
        code, out, err = self.simple("S", "a.txt", path=self.mover("diff", "--cached --check --no-ext-diff"))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("HEAD moved just before the commit", err)
        self.assertEqual("moved", git(self.repo, "log", "-1", "--format=%s").stdout.strip())

    def test_head_moving_before_the_first_check_is_refused_by_it(self):
        self.write("a.txt", "two\n")
        code, out, err = self.simple("S", "a.txt", path=self.mover("config"))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("HEAD moved before the commit was started", err)

    def test_head_moving_while_the_files_are_staged_is_refused_and_the_index_is_not_reset(self):
        self.write("a.txt", "two\n")
        code, out, err = self.simple("S", "a.txt", path=self.mover("add"))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("HEAD moved", err)
        self.assertIn("left as it is", err)
        self.assertEqual("a.txt\n", git(self.repo, "diff", "--cached", "--name-only").stdout)


class Runs(Commit):
    def test_only_the_listed_git_commands_run_on_success_and_on_every_failure(self):
        self.recording_git()
        path = self.outside + os.pathsep + STANDARD
        self.write("a.txt", "two\n")
        self.simple("S", "a.txt", path=path)
        self.write("a.txt", "trailing   \n")
        self.simple("S", "a.txt", expected="0" * 40, path=path)
        self.simple("S", "a.txt", path=path)
        self.config("user.useConfigOnly", "true")
        self.simple("S", "a.txt", home=os.path.join(self.scratch, "nohome"), path=path)
        seen = {arguments[0] for arguments, _ in self.runs()}
        self.assertTrue(seen)
        self.assertLessEqual(seen, ALLOWED)
        self.assertFalse(seen & FORBIDDEN)

    def test_a_reset_runs_only_with_the_named_paths_after_a_failure(self):
        self.recording_git()
        path = self.outside + os.pathsep + STANDARD
        self.write("a.txt", "two\n")
        self.config("user.useConfigOnly", "true")
        self.simple("S", "a.txt", home=os.path.join(self.scratch, "nohome"), path=path)
        resets = [arguments for arguments, _ in self.runs() if arguments[0] == "reset"]
        self.assertEqual([["reset", "-q", "--", "a.txt"]], resets)

    def test_the_caller_environment_does_not_reach_git(self):
        self.recording_git()
        path = self.outside + os.pathsep + STANDARD
        self.write("a.txt", "two\n")
        hostile = {"GIT_DIR": "/nonexistent", "GIT_INDEX_FILE": "/nonexistent", "GIT_WORK_TREE": "/nonexistent",
                   "GIT_EXEC_PATH": "/nonexistent", "GIT_CONFIG_COUNT": "1", "GIT_SSH_COMMAND": "evil"}
        with unittest.mock.patch.dict(os.environ, dict(self.environment(path), **hostile), clear=True):
            out, err = io.StringIO(), io.StringIO()
            code = H.main(["commit", "--expected-head", self.first, "--subject", "S", "--", "a.txt"], out, err, self.repo)
        self.assertEqual(0, code, err.getvalue())
        for _, environment in self.runs():
            self.assertFalse([name for name in hostile if name in environment])


class Surface(unittest.TestCase):
    def test_the_read_only_subcommands_still_take_no_arguments(self):
        err = io.StringIO()
        self.assertEqual(1, H.main(["check", "x"], io.StringIO(), err, tempfile.gettempdir()))
        self.assertIn("usage", err.getvalue())


if __name__ == "__main__":
    unittest.main()
