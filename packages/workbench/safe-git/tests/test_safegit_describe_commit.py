"""`safe-git describe commit`, refusals and scalar facts (plan `2026-10-25-safe-git-describe`, increment D;
`docs/specs/safe-git.md`, "Describe", "Errors" and "Facts of `describe commit`").

Real repositories, built on the fixtures of the `commit` tests. Each refusal is checked twice: `describe` reports it as data
with its code, and the real `commit` given the same arguments refuses it. Every call is checked by what it leaves behind:
no commit, nothing staged, and the repository byte for byte the same. The change lists and the diff are increment E."""

import io
import json
import os
import unittest
import unittest.mock

import support_git
import test_safegit_commit as C
import test_safegit_describe_remove as DR
from support_git import git, needs_git

H = C.H


@needs_git
class Describe(C.Commit):
    def argv(self, subject, *paths, body=None, trailers=(), leave=False, expected=None):
        args = ["--expected-head", self.first if expected is None else expected, "--subject", subject]
        if body is not None:
            args += ["--body", body]
        for trailer in trailers:
            args += ["--trailer", trailer]
        if leave:
            args.append("--leave-other-staged")
        return args + ["--"] + list(paths)

    def describe(self, args, cwd=None, path=None, home=None):
        """The object `describe commit <args>` prints; the exit status is 0 and standard error is empty."""
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.dict(os.environ, self.environment(path, home), clear=True):
            code = H.main(["describe", "commit"] + list(args), out, err, cwd or self.repo)
        self.assertEqual((0, ""), (code, err.getvalue()))
        text = out.getvalue()
        self.assertEqual(1, text.count("\n"))
        built = json.loads(text)
        self.assertEqual(["contract", "action", "ok", "truncated", "errors", "facts"], list(built))
        self.assertEqual((1, "commit"), (built["contract"], built["action"]))
        return built

    def codes(self, built):
        return [error["code"] for error in built["errors"]]

    def refused(self, code, args, cwd=None, path=None, head=True):
        """`describe` gives exactly `code` for `args`, the real `commit` refuses them, and nothing changed."""
        before = DR.snapshot(self.repo)
        built = self.describe(args, cwd=cwd, path=path)
        self.assertEqual([code], self.codes(built), built)
        self.assertFalse(built["ok"])
        self.assertTrue(0 < len(built["errors"][0]["message"]) <= 500)
        self.assertRefused(self.commit(*args, cwd=cwd, path=path))
        self.assertEqual(before, DR.snapshot(self.repo))
        if head:
            self.assertEqual(self.first, self.head())
        return built


class Codes(Describe):
    def setUp(self):
        super().setUp()
        self.write("a.txt", "two\n")

    def test_usage(self):
        base = ["--expected-head", self.first, "--subject", "S"]
        for argv in (base + ["a.txt"], base + ["--"], ["--subject", "S", "--", "a.txt"],
                     ["--expected-head", self.first, "--", "a.txt"], base + ["--subject", "T", "--", "a.txt"],
                     base + ["--body", "b", "--body", "c", "--", "a.txt"], base + ["--force", "--", "a.txt"],
                     base + ["--subject=S", "--", "a.txt"],
                     base + ["--leave-other-staged", "--leave-other-staged", "--", "a.txt"],
                     ["--subject"], ["--expected-head"], [],
                     self.argv("S", *["f%d" % number for number in range(H.MAX_PATHS + 1)])):
            with self.subTest(argv=argv[:6]):
                self.refused("usage", argv)

    def test_expected_head_invalid(self):
        for value in (self.first[:12], self.first.upper(), "HEAD", "", self.first + "0"):
            with self.subTest(value=value):
                self.refused("expected_head_invalid", self.argv("S", "a.txt", expected=value))

    def test_head_mismatch(self):
        self.refused("head_mismatch", self.argv("S", "a.txt", expected="0" * 40))
        self.refused("head_mismatch", self.argv("S", "a.txt", expected="none"))

    def test_head_unreadable(self):
        git(self.repo, "symbolic-ref", "HEAD", "refs/heads/ünï")
        self.refused("head_unreadable", self.argv("S", "a.txt", expected="none"), head=False)

    def test_subject_invalid(self):
        for subject in ("", "   ", "a\nb", "a\rb", "x" * (H.MAX_SUBJECT + 1)):
            with self.subTest(subject=subject[:20]):
                self.refused("subject_invalid", self.argv(subject, "a.txt"))

    def test_body_invalid(self):
        for body in ("", "  \n ", "a\0b", "x" * (H.MAX_BODY + 1)):
            with self.subTest(body=body[:20]):
                self.refused("body_invalid", self.argv("S", "a.txt", body=body))

    def test_trailer_invalid(self):
        self.refused("trailer_invalid", self.argv("S", "a.txt", trailers=["K: v"] * (H.MAX_TRAILERS + 1)))
        for trailer in ("no colon", "K:v", "K: ", "K: v\nL: w", "K: " + "v" * H.MAX_TRAILER, "1K: v"):
            with self.subTest(trailer=trailer[:20]):
                self.refused("trailer_invalid", self.argv("S", "a.txt", trailers=[trailer]))

    def test_message_character_refused(self):
        for text in ("xͅ y", "Claᴜde", "wаrd Claude", "a⠀b", "a\x01b"):
            with self.subTest(text=text):
                self.refused("message_character_refused", self.argv("S", "a.txt", body=text))

    def test_attribution_refused(self):
        for text in ("Co-Authored-By: Claude <noreply@anthropic.com>", "Generated with Claude Code",
                     "written by Claude"):
            with self.subTest(text=text):
                self.refused("attribution_refused", self.argv(text, "a.txt"))
                self.refused("attribution_refused", self.argv("S", "a.txt", body=text))

    def test_the_message_checks_are_not_made_where_attribution_is_allowed(self):
        self.write(".workbench/safe-git.json", '{"format": 1, "attribution": "allow"}\n')
        built = self.describe(self.argv("Co-Authored-By: Claude", "a.txt"))
        self.assertTrue(built["ok"], built)
        self.assertTrue(built["facts"]["attribution_allowed"])

    def test_setting_invalid(self):
        for text in ("{", "[]", '{"format": 1}', '{"format": 2, "attribution": "allow"}',
                     '{"format": 1, "attribution": "maybe"}', '{"format": 1, "attribution": "allow", "x": 1}',
                     '{"format": true, "attribution": "allow"}', " " * 5000):
            with self.subTest(text=text[:30]):
                self.write(".workbench/safe-git.json", text)
                self.refused("setting_invalid", self.argv("S", "a.txt"))

    def test_setting_invalid_for_a_link(self):
        os.makedirs(os.path.join(self.repo, ".workbench"))
        os.symlink("/etc/hosts", os.path.join(self.repo, ".workbench", "safe-git.json"))
        self.refused("setting_invalid", self.argv("S", "a.txt"))

    def test_repo_selects_program(self):
        hook = os.path.join(self.repo, ".git", "hooks", "pre-commit")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        with open(hook, "w") as handle:
            handle.write("#!/bin/sh\nexit 0\n")
        os.chmod(hook, 0o755)
        built = self.refused("repo_selects_program", self.argv("S", "a.txt"))
        self.assertEqual(["hook:pre-commit"], built["facts"]["program_findings"])
        os.unlink(hook)
        self.config("core.fsmonitor", "/bin/true")
        built = self.refused("repo_selects_program", self.argv("S", "a.txt"))
        self.assertEqual(["core.fsmonitor"], built["facts"]["program_findings"])

    def test_operation_in_progress(self):
        gitdir = os.path.join(self.repo, ".git")
        for name in ("MERGE_HEAD", "REVERT_HEAD", "CHERRY_PICK_HEAD", "rebase-merge", "rebase-apply"):
            with self.subTest(name=name):
                path = os.path.join(gitdir, name)
                if name.startswith("rebase"):
                    os.mkdir(path)
                else:
                    with open(path, "w") as handle:
                        handle.write(self.first + "\n")
                self.refused("operation_in_progress", self.argv("S", "a.txt"))
                if name.startswith("rebase"):
                    os.rmdir(path)
                else:
                    os.unlink(path)

    def test_path_unmerged(self):
        branch = git(self.repo, "symbolic-ref", "--short", "HEAD").stdout.strip()
        git(self.repo, "switch", "-q", "-c", "other")
        self.write("a.txt", "theirs\n")
        git(self.repo, "commit", "-q", "-am", "theirs")
        git(self.repo, "switch", "-q", branch)
        self.write("a.txt", "ours\n")
        git(self.repo, "commit", "-q", "-am", "ours")
        git(self.repo, "merge", "other", check=False)
        os.unlink(os.path.join(self.repo, ".git", "MERGE_HEAD"))
        self.first = self.head()
        self.write("a.txt", "resolved\n")
        self.refused("path_unmerged", self.argv("S", "a.txt"))

    def test_path_in_nested_repository(self):
        nested = os.path.join(self.repo, "vendor")
        os.mkdir(nested)
        git(nested, "init", "-q")
        self.write("vendor/f.txt", "x\n")
        self.refused("path_in_nested_repository", self.argv("S", "vendor/f.txt"))
        self.write("other/.git", "gitdir: /elsewhere\n")
        self.write("other/f.txt", "x\n")
        self.refused("path_in_nested_repository", self.argv("S", "other/f.txt"))

    def test_path_not_a_file(self):
        self.write("sub/c.txt", "c\n")
        os.symlink("/etc/hosts", os.path.join(self.repo, "ln"))
        outside = os.path.join(self.scratch, "outside")
        os.mkdir(outside)
        self.write("../outside/f.txt", "x\n")
        os.symlink(outside, os.path.join(self.repo, "via"))
        for path in ("sub", "ln", "via/f.txt", "a.txt/b"):
            with self.subTest(path=path):
                self.refused("path_not_a_file", self.argv("S", path))
        os.unlink(os.path.join(self.repo, "a.txt"))
        os.symlink("/etc/hosts", os.path.join(self.repo, "a.txt"))
        self.refused("path_not_a_file", self.argv("S", "a.txt"))

    def test_path_unknown(self):
        self.refused("path_unknown", self.argv("S", "nothing.txt"))

    def test_path_duplicate(self):
        self.refused("path_duplicate", self.argv("S", "a.txt", "a.txt"))
        self.refused("path_duplicate", self.argv("S", "a.txt", "A.TXT"))

    def test_path_refused(self):
        for path in ("", ".", "..", "./a.txt", "a//b", "a/../a.txt", "/etc/passwd", "*", "a.*", "a.tx[t]", "a?txt",
                     ":(glob)*", "-x", "-a.txt", "sub\\a.txt", ".git", ".git/config", ".GIT/config", "a.txt\n",
                     "a\tb", ".git ", ".git."):
            with self.subTest(path=path):
                self.refused("path_refused", self.argv("S", path))
                self.refused("path_refused", self.argv("S", "a.txt", path))

    def test_index_unreadable(self):
        real = H.run

        def odd(argv, cwd, **kwargs):
            if argv[1:3] == ["ls-files", "-s"] and argv[3:] == ["-z"]:
                return unittest.mock.Mock(returncode=0, stdout="100644 abc\ta.txt\0", stderr="")
            return real(argv, cwd, **kwargs)

        with unittest.mock.patch.object(H, "run", odd):
            built = self.describe(self.argv("S", "a.txt"))
        self.assertEqual(["index_unreadable"], self.codes(built))

    def test_index_has_staged_changes(self):
        self.write("other.txt", "o\n")
        git(self.repo, "add", "other.txt")
        index = self.index()
        built = self.describe(self.argv("S", "a.txt"))
        self.assertEqual(["index_has_staged_changes"], self.codes(built))
        self.assertEqual(["other.txt"], built["facts"]["staged_paths"])
        self.assertRefused(self.commit(*self.argv("S", "a.txt")))
        self.assertEqual(index, self.index())

    def test_path_already_staged(self):
        git(self.repo, "add", "a.txt")
        built = self.describe(self.argv("S", "a.txt", leave=True))
        self.assertEqual(["path_already_staged"], self.codes(built))
        self.assertEqual(["a.txt"], built["facts"]["staged_paths"])
        self.assertRefused(self.commit(*self.argv("S", "a.txt", leave=True)))

    def test_whitespace_errors(self):
        self.write("a.txt", "two \n")
        self.refused("whitespace_errors", self.argv("S", "a.txt"))

    def test_repository_unreadable(self):
        self.refused("repository_unreadable", self.argv("S", "a.txt"), cwd=self.scratch)
        self.refused("repository_unreadable", self.argv("S", "a.txt"), path=self.outside)

    def test_a_root_that_cannot_be_opened_for_the_setting_is_an_unreadable_repository(self):
        def broken(*args, **kwargs):
            raise H.safefs.SafeFsError("the root cannot be opened safely")

        with unittest.mock.patch.object(H.safefs, "Root", broken):
            built = self.describe(self.argv("S", "a.txt"))
        self.assertEqual(["repository_unreadable"], self.codes(built))

    def test_a_git_failure_in_the_whitespace_check_is_not_reported_as_whitespace(self):
        self.write("a.txt", "two\n")
        real = H.run

        def failing(argv, cwd, **kwargs):
            if argv[1] == "diff" and "--check" in argv and "--cached" not in argv:
                return unittest.mock.Mock(returncode=128, stdout="fatal: bad", stderr="")
            return real(argv, cwd, **kwargs)

        with unittest.mock.patch.object(H, "run", failing):
            built = self.describe(self.argv("S", "a.txt"))
        self.assertEqual(["repository_unreadable"], self.codes(built))

    def test_every_refusal_of_the_commit_checks_carries_a_code(self):
        """A refusal with no code would stop `describe` with no object, which the engine reads as a decline."""
        empty = H.Request()
        empty.subject = ""
        for call in (lambda: H.parse_commit([]), lambda: H.validate_expected("x"), lambda: H.validate_message(empty)):
            with self.assertRaises(H.Refused) as caught:
                call()
            self.assertIsNotNone(caught.exception.code)


class Facts(Describe):
    def test_the_facts_of_a_valid_commit_are_the_values_the_real_command_acts_on(self):
        self.write("a.txt", "two\n")
        built = self.describe(self.argv("Change a", "a.txt", body="Why.\n\nMore.", trailers=["Plan: x#A"]))
        self.assertTrue(built["ok"], built)
        self.assertEqual([], built["errors"])
        self.assertFalse(built["truncated"])
        facts = built["facts"]
        self.assertEqual(self.first, facts["head"])
        self.assertEqual(self.first, facts["expected_head"])
        self.assertEqual((False, 1), (facts["leave_other_staged"], facts["path_count"]))
        self.assertEqual("Change a", facts["subject"])
        self.assertEqual(["Plan: x#A"], facts["trailers"])
        self.assertEqual("Why.\n\nMore.", facts["body"])
        self.assertFalse(facts["attribution_allowed"])
        self.assertEqual([], facts["program_findings"])
        self.assertEqual([], facts["staged_paths"])
        self.assertEqual(["a.txt"], facts["requested_paths"])
        self.assertEqual(["a.txt"], facts["paths"])
        self.assertEqual([], facts["omitted"])
        self.assertEqual(["head", "expected_head", "leave_other_staged", "path_count", "subject", "trailers", "body",
                          "attribution_allowed", "program_findings", "staged_paths", "requested_paths", "paths",
                          "omitted"], list(facts))
        self.assertEqual(0, self.commit(*self.argv("Change a", "a.txt", body="Why.\n\nMore.",
                                                    trailers=["Plan: x#A"]))[0])

    def test_a_commit_on_a_branch_with_no_commit_has_a_null_head_and_expects_none(self):
        git(self.repo, "symbolic-ref", "HEAD", "refs/heads/fresh")
        git(self.repo, "rm", "--cached", "-q", "a.txt")
        built = self.describe(self.argv("S", "a.txt", expected="none"))
        self.assertTrue(built["ok"], built)
        self.assertEqual((None, "none"), (built["facts"]["head"], built["facts"]["expected_head"]))

    def test_the_other_staged_work_is_named_and_the_option_is_reported(self):
        self.write("a.txt", "two\n")
        self.write("other.txt", "o\n")
        git(self.repo, "add", "other.txt")
        built = self.describe(self.argv("S", "a.txt", leave=True))
        self.assertTrue(built["ok"], built)
        self.assertEqual(["other.txt"], built["facts"]["staged_paths"])
        self.assertTrue(built["facts"]["leave_other_staged"])

    def test_the_attribution_setting_is_reported(self):
        self.write("a.txt", "two\n")
        for text, value in (('{"format": 1, "attribution": "allow"}\n', True),
                            ('{"format": 1, "attribution": "refuse"}\n', False)):
            self.write(".workbench/safe-git.json", text)
            self.assertEqual(value, self.describe(self.argv("S", "a.txt"))["facts"]["attribution_allowed"])

    def test_a_refusal_before_the_paths_are_checked_keeps_the_copies_and_what_was_found(self):
        self.write("a.txt", "two\n")
        built = self.describe(self.argv("S", "a.txt", "nothing.txt", trailers=["K: v"]))
        facts = built["facts"]
        self.assertEqual(["path_unknown"], self.codes(built))
        self.assertEqual((self.first, self.first), (facts["head"], facts["expected_head"]))
        self.assertEqual(2, facts["path_count"])
        self.assertEqual(["a.txt", "nothing.txt"], facts["requested_paths"])
        self.assertEqual([], facts["paths"])
        self.assertEqual([], facts["staged_paths"])
        self.assertEqual(["K: v"], facts["trailers"])

    def test_a_refused_command_line_keeps_what_was_given_and_has_nothing_else(self):
        built = self.describe(["--leave-other-staged", "--force", "--", "a.txt", "b.txt"])
        facts = built["facts"]
        self.assertEqual(["usage"], self.codes(built))
        self.assertEqual((True, 2, ["a.txt", "b.txt"]),
                         (facts["leave_other_staged"], facts["path_count"], facts["requested_paths"]))
        for name in ("head", "expected_head", "subject", "body", "attribution_allowed"):
            self.assertIsNone(facts[name], name)
        for name in ("trailers", "program_findings", "staged_paths", "paths"):
            self.assertEqual([], facts[name], name)

    def test_a_value_that_looks_like_the_separator_or_an_option_is_read_as_the_real_command_reads_it(self):
        self.write("a.txt", "two\n")
        head = ["--expected-head", self.first]
        built = self.describe(head + ["--subject", "--", "--", "a.txt"])
        self.assertTrue(built["ok"], built)
        facts = built["facts"]
        self.assertEqual(("--", 1, ["a.txt"], ["a.txt"], False),
                         (facts["subject"], facts["path_count"], facts["requested_paths"], facts["paths"],
                          facts["leave_other_staged"]))
        built = self.describe(head + ["--subject", "--leave-other-staged", "--", "a.txt"])
        self.assertTrue(built["ok"], built)
        self.assertEqual((False, "--leave-other-staged", 1),
                         (built["facts"]["leave_other_staged"], built["facts"]["subject"],
                          built["facts"]["path_count"]))
        built = self.describe(head + ["--body", "--", "--subject", "S", "--leave-other-staged", "--", "a.txt"])
        self.assertTrue(built["facts"]["leave_other_staged"])
        self.assertEqual("--", built["facts"]["body"])
        self.assertEqual(1, built["facts"]["path_count"])
        self.assertEqual(0, self.commit(*(head + ["--subject", "--", "--", "a.txt"]))[0])

    def test_a_refused_command_line_with_such_values_is_counted_as_the_parser_counts(self):
        built = self.describe(["--subject", "--leave-other-staged", "--force", "--", "a.txt", "b.txt"])
        self.assertEqual(["usage"], self.codes(built))
        self.assertEqual((False, 2, ["a.txt", "b.txt"]),
                         (built["facts"]["leave_other_staged"], built["facts"]["path_count"],
                          built["facts"]["requested_paths"]))
        built = self.describe(["--expected-head", "--", "--leave-other-staged", "--force"])
        self.assertEqual((True, 0, []), (built["facts"]["leave_other_staged"], built["facts"]["path_count"],
                                         built["facts"]["requested_paths"]))

    def test_an_expected_head_that_is_not_valid_is_null_and_one_that_is_valid_is_kept(self):
        self.write("a.txt", "two\n")
        self.assertIsNone(self.describe(self.argv("S", "a.txt", expected="HEAD"))["facts"]["expected_head"])
        built = self.describe(self.argv("S", "a.txt", expected="0" * 40))
        self.assertEqual("0" * 40, built["facts"]["expected_head"])
        self.assertEqual(self.first, built["facts"]["head"])

    def test_a_long_body_is_left_out_whole_and_named(self):
        self.write("a.txt", "two\n")
        built = self.describe(self.argv("S", "a.txt", body="x" * 40000))
        self.assertTrue(built["ok"])
        self.assertTrue(built["truncated"])
        self.assertNotIn("body", built["facts"])
        self.assertEqual(["body"], built["facts"]["omitted"])

    def test_many_paths_leave_the_lists_out_whole_and_named(self):
        for number in range(201):
            self.write("many/f%d" % number, "x\n")
        built = self.describe(self.argv("S", *["many/f%d" % number for number in range(201)]))
        self.assertTrue(built["truncated"])
        self.assertEqual(["requested_paths", "paths"], built["facts"]["omitted"])
        self.assertEqual(201, built["facts"]["path_count"])


class Inert(Describe):
    def test_nothing_changes_after_a_valid_call_or_a_refused_one(self):
        self.write("a.txt", "two\n")
        self.write("other.txt", "o\n")
        git(self.repo, "add", "other.txt")
        before = DR.snapshot(self.repo)
        for args in (self.argv("S", "a.txt", leave=True), self.argv("S", "a.txt"), self.argv("S", "missing"),
                     ["--force"], self.argv("S", "a.txt", expected="0" * 40)):
            with self.subTest(args=args[:4]):
                self.describe(args)
                self.assertEqual(before, DR.snapshot(self.repo))
        self.assertEqual(self.first, self.head())

    def test_only_read_commands_run(self):
        self.write("a.txt", "two\n")
        directory = self.recording_git()
        path = directory + os.pathsep + C.STANDARD
        built = self.describe(self.argv("S", "a.txt"), path=path)
        self.assertTrue(built["ok"], built)
        commands = {arguments[0] for arguments, _ in self.runs()}
        self.assertTrue(commands)
        self.assertLessEqual(commands, {"rev-parse", "ls-files", "diff", "config"})
        self.assertTrue(all(H.git_shape_ok(["git"] + arguments) for arguments, _ in self.runs()))

    def test_the_whitespace_check_does_not_refresh_the_index(self):
        self.write("a.txt", "two\n")
        directory = self.recording_git()
        self.describe(self.argv("S", "a.txt"), path=directory + os.pathsep + C.STANDARD)
        checks = [environment for arguments, environment in self.runs()
                  if arguments[0] == "diff" and "--check" in arguments]
        self.assertEqual(1, len(checks))
        self.assertEqual("0", checks[0].get("GIT_OPTIONAL_LOCKS"))

    def test_a_repository_that_selects_a_program_runs_none_of_them(self):
        self.write("a.txt", "two\n")
        marker = os.path.join(self.scratch, "ran")
        script = os.path.join(self.outside, "tool")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
        os.chmod(script, 0o755)
        for key in ("core.fsmonitor", "core.editor", "core.pager", "diff.external", "core.hooksPath",
                    "core.askPass", "core.sshCommand", "commit.gpgsign"):
            self.config(key, script if key != "commit.gpgsign" else "true")
        for hook in ("pre-commit", "commit-msg", "post-commit", "fsmonitor-watchman", "reference-transaction"):
            hook_path = os.path.join(self.repo, ".git", "hooks", hook)
            os.makedirs(os.path.dirname(hook_path), exist_ok=True)
            with open(hook_path, "w") as handle:
                handle.write("#!/bin/sh\ntouch '%s'\n" % marker)
            os.chmod(hook_path, 0o755)
        self.write(".gitattributes", "a.txt filter=bad diff=bad\n")
        self.config("filter.bad.clean", script)
        self.config("filter.bad.smudge", script)
        self.config("diff.bad.textconv", script)
        built = self.describe(self.argv("S", "a.txt"))
        self.assertFalse(built["ok"])
        self.assertEqual(["repo_selects_program"], self.codes(built))
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(self.first, self.head())


if __name__ == "__main__":
    unittest.main()
