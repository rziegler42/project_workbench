"""The code checks for `remove` (`docs/specs/action-review.md`, "The checks"; the counterparts are those of
`docs/specs/safe-git.md`, "Each check of the approver, and where it goes").

Plan `2026-10-26-action-review-engine`, increment G. A check is a pure function of the `describe` object, so the checks
are tested on objects built by hand and on the objects the real `safe-git describe remove` prints for a scratch
repository."""

import copy
import io
import json
import os
import subprocess
import tempfile
import unittest

from tests import support_helpers, support_install

MODULE = os.path.join(support_install.ROOT, "packages", "workbench", "action-review")


def shipped(relative):
    with open(os.path.join(MODULE, *relative.split("/")), "rb") as handle:
        return handle.read()


FACTS = {
    "confirm": True, "recursive": False, "requested_paths": ["old.txt"], "target_paths": ["old.txt"],
    "file_targets": ["old.txt"], "directory_targets": [], "link_targets": [], "other_targets": [],
    "tracked_targets": [], "ignored_targets": [], "ignore_unknown_targets": [], "tracked_file_total": 0,
    "entry_total": 1, "size_total": 4, "omitted": [],
}
ALL = ("facts_complete", "confirm_present", "removal_valid", "ignore_status_known", "preview_matches_arguments",
       "no_git_metadata")

# The error codes of `describe remove` and the check each one fails (spec, "The checks").
CODES = {
    "removal_valid": ("usage", "path_duplicate", "path_refused", "target_missing", "recursive_required",
                      "repository_root_refused", "nested_repository", "other_filesystem", "tree_too_large",
                      "target_changed"),
    "no_git_metadata": ("git_metadata_refused",),
    "facts_complete": ("repository_unreadable",),
}
# What a commit refusal looks like to a removal: a code the removal never gives.
COMMIT_ONLY = ("head_mismatch", "head_unreadable", "subject_invalid", "path_unknown", "index_has_staged_changes",
               "repo_selects_program", "whitespace_errors")


def doc(ok=True, truncated=False, errors=(), **facts):
    return {"contract": 1, "action": "remove", "ok": ok, "truncated": truncated,
            "errors": [{"code": code, "message": "m"} for code in errors], "facts": dict(FACTS, **facts)}


def refused(*codes, **facts):
    """What a refusal looks like: the argument copies as given, no target, the totals omitted and the object truncated."""
    given = dict(FACTS, target_paths=[], file_targets=[], tracked_file_total=None, omitted=["entry_total", "size_total"])
    del given["entry_total"], given["size_total"]
    given.update(facts)
    return {"contract": 1, "action": "remove", "ok": False, "truncated": True,
            "errors": [{"code": code, "message": "m"} for code in codes], "facts": given}


def without_fact(document, name):
    result = copy.deepcopy(document)
    del result["facts"][name]
    return result


DERIVED = object()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("action-review")

    def rule(self, checks=ALL):
        return self.helper.Rule("safe-git-remove.json", ("wb", "run", "safe-git"), "remove", "safe-git", "remove",
                                {}, None, tuple(checks), "remove", (), None)

    def run_checks(self, document, positionals=DERIVED, **options):
        """The checks of the object. The paths the command names default to the ones the object says were requested,
        which is the honest case; a test of a dishonest object gives them."""
        if positionals is DERIVED:
            positionals = document["facts"].get("requested_paths", [])
        return self.helper.run_checks(self.rule(**options), document, positionals)


class Checking(Base):
    def test_a_good_removal_object_fails_no_check(self):
        self.assertEqual((), self.run_checks(doc()))

    def test_the_result_is_a_tuple_of_check_names_in_the_order_of_the_engines_list_not_the_rule(self):
        bad = doc(confirm=False, ignore_unknown_targets=["old.txt"], requested_paths=["a/.git/b"])
        failed = self.run_checks(bad, checks=tuple(reversed(ALL)))
        self.assertEqual(("confirm_present", "ignore_status_known", "preview_matches_arguments", "no_git_metadata"),
                         failed)
        self.assertIsInstance(failed, tuple)

    def test_a_check_the_rule_does_not_name_is_not_run(self):
        self.assertEqual(("confirm_present",), self.run_checks(doc(confirm=False), checks=("confirm_present",)))
        self.assertEqual((), self.run_checks(doc(confirm=False), checks=("no_git_metadata",)))

    def test_confirm_present(self):
        self.assertEqual(("confirm_present",), self.run_checks(doc(confirm=False)))

    def test_ignore_status_known(self):
        self.assertEqual(("ignore_status_known",), self.run_checks(doc(ignore_unknown_targets=["old.txt"])))
        self.assertEqual((), self.run_checks(doc(ignored_targets=["old.txt"])))

    def test_preview_matches_arguments_fails_when_the_lists_differ_in_any_way(self):
        for facts in ({"target_paths": ["other.txt"]}, {"target_paths": []}, {"target_paths": ["old.txt", "b.txt"]},
                      {"requested_paths": ["old.txt", "b.txt"]}, {"target_paths": ["OLD.txt"]},
                      {"target_paths": ["./old.txt"]}):
            self.assertEqual(("preview_matches_arguments",), self.run_checks(doc(**facts)), facts)

    def test_preview_matches_arguments_reads_the_order_and_the_repeats(self):
        both = {"requested_paths": ["a", "b"]}
        self.assertEqual((), self.run_checks(doc(target_paths=["a", "b"], **both)))
        self.assertEqual(("preview_matches_arguments",), self.run_checks(doc(target_paths=["b", "a"], **both)))
        self.assertEqual(("preview_matches_arguments",),
                         self.run_checks(doc(target_paths=["a", "a", "b"], **both)))

    def test_the_checks_read_the_paths_the_command_names_and_not_only_the_object(self):
        # Security pass, finding 9: an ok object with empty paths passed both checks for a command that removes `.git`.
        empty = doc(requested_paths=[], target_paths=[])
        self.assertEqual(("preview_matches_arguments", "no_git_metadata"), self.run_checks(empty, [".git"]))
        elsewhere = doc(requested_paths=["old.txt"], target_paths=["old.txt"])
        self.assertEqual(("preview_matches_arguments",), self.run_checks(elsewhere, ["build/out"]))
        self.assertEqual(("preview_matches_arguments",), self.run_checks(elsewhere, ["old.txt", "old.txt"]))
        self.assertEqual((), self.run_checks(elsewhere, ["old.txt"]))

    def test_a_git_segment_in_the_commands_own_path_fails_even_when_the_object_hides_it(self):
        hidden = doc(requested_paths=["x"], target_paths=["x"])
        self.assertEqual(("preview_matches_arguments", "no_git_metadata"), self.run_checks(hidden, ["a/.GIT/b"]))

    def test_without_the_commands_paths_the_two_checks_cannot_pass(self):
        self.assertEqual(("facts_complete", "preview_matches_arguments", "no_git_metadata"),
                         self.run_checks(doc(), None))

    def test_the_paths_a_command_names_are_those_after_the_separator_and_never_a_flag_value(self):
        remove = self.helper.build_rule("safe-git-remove.json", json.loads(shipped("rules/safe-git-remove.json")))
        commit = self.helper.build_rule("safe-git-commit.json", json.loads(shipped("rules/safe-git-commit.json")))
        self.assertEqual(["a", "b"], self.helper.command_positionals(remove, ["--confirm", "--recursive", "--", "a", "b"]))
        self.assertEqual(["--confirm"], self.helper.command_positionals(remove, ["--", "--confirm"]))
        self.assertEqual(["a.txt"], self.helper.command_positionals(
            commit, ["--expected-head", "a" * 40, "--subject", "--", "--trailer", "--", "--", "a.txt"]))
        self.assertEqual([], self.helper.command_positionals(remove, ["--confirm"]))

    def test_no_git_metadata_sees_a_git_segment_in_any_case_and_any_place(self):
        for path in (".git", ".GIT", ".Git", "a/.git", "a/.git/config", ".git/hooks/x", "a/.GiT/b", "a/b/.git"):
            document = doc(requested_paths=[path], target_paths=[path])
            self.assertEqual(("no_git_metadata",), self.run_checks(document), path)

    def test_no_git_metadata_checks_each_requested_path(self):
        paths = ["old.txt", "x/.git/y"]
        self.assertEqual(("no_git_metadata",), self.run_checks(doc(requested_paths=paths, target_paths=paths)))

    def test_no_git_metadata_passes_a_name_that_only_contains_git(self):
        for path in (".gitignore", ".github/x", "git", "a.git", ".gitx/y", "sub/legit.git/a", ".git.", "git~1"):
            document = doc(requested_paths=[path], target_paths=[path])
            self.assertEqual((), self.run_checks(document), path)

    def test_no_git_metadata_reads_a_backslash_or_a_trailing_space_as_part_of_a_name(self):
        for path in ("a\\.git", ".git "):
            document = doc(requested_paths=[path], target_paths=[path])
            self.assertEqual((), self.run_checks(document), path)

    def test_an_object_that_is_not_ok_fails_the_check_that_each_error_code_names(self):
        for name, codes in CODES.items():
            for code in codes:
                failed = self.run_checks(refused(code))
                self.assertIn(name, failed, code)

    def test_a_plain_git_segment_refused_by_path_refused_fails_removal_valid_and_no_git_metadata(self):
        failed = self.run_checks(refused("path_refused", requested_paths=["x/.GIT/y"]))
        self.assertIn("removal_valid", failed)
        self.assertIn("no_git_metadata", failed)

    def test_every_removal_refusal_fails_facts_complete_because_the_object_is_truncated(self):
        for codes in CODES.values():
            for code in codes:
                self.assertIn("facts_complete", self.run_checks(refused(code)), code)

    def test_a_code_that_maps_to_a_check_the_rule_does_not_name_fails_facts_complete(self):
        failed = self.run_checks(refused("target_missing"), checks=("confirm_present",))
        self.assertEqual(("facts_complete",), failed[-1:])
        self.assertNotIn("removal_valid", failed)

    def test_an_error_code_with_no_mapping_for_a_removal_fails_facts_complete(self):
        for code in ("no_such_code",) + COMMIT_ONLY:
            document = doc(ok=False, errors=(code,))
            self.assertEqual(("facts_complete",), self.run_checks(document), code)

    def test_ok_false_with_no_error_fails_facts_complete(self):
        self.assertIn("facts_complete", self.run_checks(doc(ok=False)))

    def test_facts_complete_fails_on_truncated(self):
        self.assertEqual(("facts_complete",), self.run_checks(doc(truncated=True)))

    def test_facts_complete_does_not_read_binary_paths_of_a_removal(self):
        self.assertEqual((), self.run_checks(doc(binary_paths=["a.bin"])))
        self.assertEqual((), self.run_checks(doc()))

    def test_a_fact_that_a_check_reads_and_that_is_absent_fails_that_check_and_facts_complete(self):
        for name, check in (("confirm", "confirm_present"), ("ignore_unknown_targets", "ignore_status_known"),
                            ("target_paths", "preview_matches_arguments"), ("requested_paths", "no_git_metadata")):
            failed = self.run_checks(without_fact(doc(), name))
            self.assertIn(check, failed, name)
            self.assertIn("facts_complete", failed, name)

    def test_a_fact_of_the_wrong_type_fails_that_check_and_facts_complete(self):
        for facts, check in (({"confirm": "yes"}, "confirm_present"), ({"confirm": None}, "confirm_present"),
                             ({"ignore_unknown_targets": None}, "ignore_status_known"),
                             ({"ignore_unknown_targets": "old.txt"}, "ignore_status_known"),
                             ({"target_paths": "old.txt"}, "preview_matches_arguments"),
                             ({"requested_paths": [1]}, "no_git_metadata"), ({"requested_paths": None},
                                                                              "no_git_metadata")):
            failed = self.run_checks(doc(**facts))
            self.assertIn(check, failed, facts)
            self.assertIn("facts_complete", failed, facts)

    def test_a_fact_that_no_check_reads_does_not_matter(self):
        self.assertEqual((), self.run_checks(without_fact(doc(), "size_total")))
        self.assertEqual((), self.run_checks(doc(extra_thing="x")))

    def test_the_failed_checks_hold_only_names_of_the_fixed_list(self):
        bad = doc(confirm=False, truncated=True, ignore_unknown_targets=["a"], target_paths=[])
        for name in self.run_checks(bad):
            self.assertIn(name, self.helper.CHECKS)


class RealRemove(Base):
    """The objects the real `safe-git describe remove` prints for a scratch repository."""

    def setUp(self):
        self.safe_git = support_helpers.load("safe-git")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = os.path.realpath(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.write("keep.txt", "keep\n")
        self.write(".gitignore", "ign.txt\n")
        self.git("add", "keep.txt", ".gitignore")
        self.git("commit", "-q", "-m", "first")
        self.write("old.txt", "old\n")
        self.write("d/a.txt", "a\n")
        self.write("d/sub/b.txt", "b\n")
        self.write("ign.txt", "ignored\n")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.dir, check=True, capture_output=True, text=True).stdout

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text)

    def described(self, *words):
        out, err = io.StringIO(), io.StringIO()
        code = self.safe_git.main(["describe", "remove", *words], out, err, self.dir)
        self.assertEqual(0, code, err.getvalue()[:200])
        return self.helper.read_description(out.getvalue().encode("utf-8"), "remove")

    def checked(self, *words):
        return self.run_checks(self.described(*words))

    def test_a_confirmed_file_removal_fails_no_check(self):
        self.assertEqual((), self.checked("--confirm", "--", "old.txt"))

    def test_a_tracked_file_an_ignored_file_and_a_recursive_directory_fail_no_check(self):
        self.assertEqual((), self.checked("--confirm", "--", "keep.txt", "ign.txt"))
        self.assertEqual((), self.checked("--confirm", "--recursive", "--", "d"))
        self.assertEqual((), self.checked("--confirm", "--", "d/a.txt", "old.txt"))

    def test_no_confirm(self):
        self.assertEqual(("confirm_present",), self.checked("--", "old.txt"))

    def test_a_directory_without_recursive(self):
        failed = self.checked("--confirm", "--", "d")
        self.assertIn("removal_valid", failed)
        self.assertIn("preview_matches_arguments", failed)

    def test_a_target_that_does_not_exist(self):
        self.assertIn("removal_valid", self.checked("--confirm", "--", "missing.txt"))

    def test_a_path_named_twice_and_overlapping_targets(self):
        self.assertIn("removal_valid", self.checked("--confirm", "--", "old.txt", "old.txt"))
        self.assertIn("removal_valid", self.checked("--confirm", "--recursive", "--", "d", "d/a.txt"))

    def test_a_path_the_shared_check_refuses(self):
        for path in ("*.txt", "-x", "d/", "d/./a.txt", ":old.txt", "a\\b", "/etc/passwd", "../x"):
            self.assertIn("removal_valid", self.checked("--confirm", "--", path), path)

    def test_a_usage_refusal(self):
        self.assertIn("removal_valid", self.checked("--confirm"))

    def test_a_git_segment_in_any_case_or_spelling(self):
        for path in (".git", ".GIT", "a/.Git", ".git/config", "x/.git/hooks/y", "git~1", ".git."):
            failed = self.checked("--confirm", "--recursive", "--", path)
            self.assertIn("removal_valid", failed, path)
        for path in (".git", ".GIT", "a/.Git", ".git/config", "x/.git/hooks/y"):
            self.assertIn("no_git_metadata", self.checked("--confirm", "--recursive", "--", path), path)

    def test_a_name_that_only_looks_like_git_metadata_is_not_one(self):
        self.write(".GITx", "x\n")
        self.assertEqual((), self.checked("--confirm", "--", ".GITx"))

    def test_a_truncated_object_declines(self):
        big = os.path.join(self.dir, "big")
        os.makedirs(big)
        for number in range(10001):
            with open(os.path.join(big, "f%d" % number), "w"):
                pass
        document = self.described("--confirm", "--recursive", "--", "big")
        self.assertTrue(document["truncated"])
        self.assertEqual(("facts_complete",), self.run_checks(document))


if __name__ == "__main__":
    unittest.main()
