"""The rule loader, the key and ambiguity rules, and the argument parse of `action-review`
(`docs/specs/action-review.md`, "The rule schema, the module and the checks").

Plan `2026-10-26-action-review-engine`, increment D. The helper is a private copy with nothing beside it, so these tests
build a small project whose installed rules directory holds the rule files under test."""

import copy
import io
import json
import os
import tempfile
import unittest
import unittest.mock

from tests import support_helpers, support_install
from workbench.wbkit import call

ROOT = support_install.ROOT
MODULE = os.path.join(ROOT, "packages", "workbench", "action-review")
RULES = os.path.join(MODULE, "rules")
INSTALLED = (".workbench", "workbench", "action-review", "rules")

COMMIT = {
    "format": 1, "spelling": ["wb", "run", "safe-git"], "subcommand": "commit", "module": "safe-git",
    "action": "commit",
    "flags": {"--expected-head": {"type": "value", "required": True}, "--subject": {"type": "value", "required": True},
              "--body": {"type": "value"}, "--trailer": {"type": "multi"}, "--leave-other-staged": {"type": "boolean"}},
    "positionals": {"name": "paths", "separator": True, "min": 1, "max": 61},
    "checks": ["head_matches", "facts_complete"], "rubric": "commit", "questions": ["message_matches_change"],
}
HEAD = "a" * 40
DESCRIBED = (b'{"contract":1,"action":"commit","ok":true,"truncated":false,"errors":[],"facts":{"omitted":[]}}\n')


def encode(document):
    return json.dumps(document).encode("utf-8")


def read_shipped(name):
    with open(os.path.join(RULES, name), "rb") as handle:
        return handle.read()


def make_project(root, files):
    """A directory that `project.find_root` accepts, with `files` ({name: bytes}) as its installed rules."""
    os.makedirs(os.path.join(root, ".git"))
    os.makedirs(os.path.join(root, *INSTALLED))
    with open(os.path.join(root, ".workbench", "manifest.json"), "wb") as handle:
        handle.write(b"{}")
    for name, data in files.items():
        with open(os.path.join(root, *INSTALLED, name), "wb") as handle:
            handle.write(data)
    return root


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("action-review")

    def project(self, files):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        return make_project(os.path.realpath(scratch.name), files)

    def loaded(self, files):
        return self.helper.load_rules(self.project(files))

    def rule_errors(self, loaded):
        return {name: why for name, why in loaded.errors}


class Loading(Base):
    def one(self, document, name="safe-git-commit.json"):
        return self.loaded({name: encode(document)})

    def refused(self, document, name="safe-git-commit.json"):
        loaded = self.one(document, name)
        self.assertEqual([], loaded.rules, document)
        self.assertEqual([name], [n for n, _ in loaded.errors], document)
        return loaded

    def test_a_valid_rule_loads_with_every_field_read(self):
        loaded = self.one(COMMIT)
        self.assertEqual([], loaded.errors)
        (rule,) = loaded.rules
        self.assertEqual(("wb", "run", "safe-git"), rule.spelling)
        self.assertEqual(("commit", "safe-git", "commit"), (rule.subcommand, rule.module, rule.action))
        self.assertEqual(("value", True), tuple(rule.flags["--expected-head"]))
        self.assertEqual(("multi", False), tuple(rule.flags["--trailer"]))
        self.assertEqual(("paths", True, 1, 61), tuple(rule.positionals))
        self.assertEqual(("head_matches", "facts_complete"), rule.checks)
        self.assertEqual(("commit", ("message_matches_change",)), (rule.rubric, rule.questions))

    def test_the_shipped_rules_load_with_the_flags_of_the_real_commands(self):
        loaded = self.loaded({n: read_shipped(n) for n in ("safe-git-commit.json", "safe-git-remove.json")})
        self.assertEqual([], loaded.errors)
        by_action = {r.action: r for r in loaded.rules}
        self.assertEqual(["commit", "remove"], sorted(by_action))
        self.assertEqual({"--expected-head", "--subject", "--body", "--trailer", "--leave-other-staged"},
                         set(by_action["commit"].flags))
        self.assertEqual({"--confirm", "--recursive"}, set(by_action["remove"].flags))
        for rule in by_action.values():
            self.assertEqual(("wb", "run", "safe-git"), rule.spelling)
            self.assertTrue(rule.positionals.separator)
            self.assertEqual((1, 61), (rule.positionals.min, rule.positionals.max))
            self.assertIsNone(rule.lists)

    def test_a_missing_required_field_is_refused(self):
        for field in COMMIT:
            document = copy.deepcopy(COMMIT)
            del document[field]
            self.refused(document)

    def test_a_field_of_the_wrong_type_is_refused(self):
        wrong = {"format": "1", "spelling": "wb", "subcommand": 1, "module": ["safe-git"], "action": None,
                 "flags": [], "positionals": [], "checks": "head_matches", "rubric": 5, "questions": {}}
        for field, value in wrong.items():
            document = copy.deepcopy(COMMIT)
            document[field] = value
            self.refused(document)

    def test_a_format_the_engine_does_not_know_is_refused(self):
        for value in (0, 2, True, None, "1"):
            document = copy.deepcopy(COMMIT)
            document["format"] = value
            self.refused(document)
        self.refused_text(b'{"format": 1.0}')

    def refused_text(self, data, name="safe-git-commit.json"):
        loaded = self.loaded({name: data})
        self.assertEqual([], loaded.rules, data)
        self.assertEqual([name], [n for n, _ in loaded.errors], data)

    def test_an_unknown_field_is_refused_and_so_is_any_field_that_could_carry_a_command(self):
        for field in ("extra", "command", "verb", "path", "program", "argv", "exec"):
            document = copy.deepcopy(COMMIT)
            document[field] = "wb run safe-git commit"
            self.refused(document)

    def test_an_unknown_field_inside_a_flag_or_a_group_is_refused(self):
        document = copy.deepcopy(COMMIT)
        document["flags"]["--body"]["default"] = "x"
        self.refused(document)
        document = copy.deepcopy(COMMIT)
        document["positionals"]["extra"] = 1
        self.refused(document)

    def test_values_outside_their_forms_are_refused(self):
        cases = [
            ("subcommand", "Commit"), ("subcommand", "commit;rm"), ("subcommand", "c" * 33),
            ("spelling", []), ("spelling", ["wb", "run", "safe-git", "a", "b"]), ("spelling", ["wb", "-run", "safe-git"]),
            ("spelling", ["wb", "run safe-git"]), ("spelling", ["wb", "run", "x" * 65]), ("spelling", ["wb", 1]),
            ("spelling", ["wb", "run", "'quoted'"]),
            ("rubric", "Commit"), ("rubric", "c" * 65), ("rubric", ""),
            ("questions", ["Bad"]), ("questions", ["a", "a"]), ("questions", ["q%d" % i for i in range(17)]),
            ("questions", ["q" * 65]),
            ("checks", ["head_matches", "head_matches"]), ("checks", [""]), ("checks", [1]),
        ]
        for field, value in cases:
            document = copy.deepcopy(COMMIT)
            document[field] = value
            self.refused(document)

    def test_a_module_or_action_outside_its_form_is_refused_by_that_form_alone(self):
        # The file name and the spelling agree with the value, so only the form can refuse it.
        for module in ("-safe-git", "safe git", "s" * 65, ""):
            document = copy.deepcopy(COMMIT)
            document.update(module=module, spelling=["git"])
            self.refused(document, "%s-commit.json" % module)
        for action in ("Commit", "commit now", "c" * 33, "", "1commit"):
            document = copy.deepcopy(COMMIT)
            document.update(action=action, subcommand=action, spelling=["git"], module="git")
            self.refused(document, "git-%s.json" % action)
        for module, action in (("s" * 64, "c" * 32), ("9a._+-", "a")):
            document = copy.deepcopy(COMMIT)
            document.update(module=module, action=action, subcommand=action, spelling=["git"])
            self.assertEqual([], self.one(document, "%s-%s.json" % (module, action)).errors)

    def test_the_size_bounds_load_at_the_limit_and_refuse_over_it(self):
        document = copy.deepcopy(COMMIT)
        text = encode(document)
        self.assertEqual([], self.loaded({"safe-git-commit.json": text + b" " * (16384 - len(text))}).errors)
        self.refused_text(text + b" " * (16385 - len(text)))
        flags = {"--" + "f" * 32: {"type": "boolean"}}
        document["flags"] = flags
        self.assertEqual([], self.one(document).errors)
        self.assertEqual(64, len(self.loaded({"r%d-a.json" % i: b"{}" for i in range(64)}).errors))

    def test_a_list_holding_something_unhashable_is_a_rule_error_and_disturbs_no_other_key(self):
        for items in ([[1]], [{"a": 1}], [None], [[]]):
            document = copy.deepcopy(COMMIT)
            document["lists"] = {"credential_names": items}
            files = {"safe-git-commit.json": encode(document),
                     "safe-git-remove.json": read_shipped("safe-git-remove.json")}
            loaded = self.loaded(files)
            self.assertEqual(["safe-git-commit.json"], [n for n, _ in loaded.errors], items)
            self.assertEqual(["remove"], [r.action for r in loaded.rules], items)

    def test_a_hard_linked_rule_file_is_a_rule_error(self):
        root = self.project({"safe-git-commit.json": encode(COMMIT)})
        directory = os.path.join(root, *INSTALLED)
        os.link(os.path.join(directory, "safe-git-commit.json"), os.path.join(root, "elsewhere"))
        loaded = self.helper.load_rules(root)
        self.assertEqual([], loaded.rules)
        self.assertEqual(["safe-git-commit.json"], [n for n, _ in loaded.errors])

    def test_a_file_name_with_a_newline_cannot_forge_a_line_on_standard_error(self):
        name = "x\nrefused: approved.json"
        root = self.project({name: b"{}"})
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(["review", "git commit"], io.BytesIO(b""), out, err, root)
        self.assertEqual(1, code)
        lines = err.getvalue().splitlines()
        self.assertEqual(2, len(lines), lines)
        self.assertTrue(lines[0].startswith("rule error: 'x\\nrefused: approved.json': "), lines)
        self.assertTrue(lines[1].startswith("refused: "), lines)

    def test_a_check_that_does_not_exist_is_refused(self):
        for name in ("head_match", "HEAD_MATCHES", "no_such_check", "run_anything"):
            document = copy.deepcopy(COMMIT)
            document["checks"] = ["head_matches", name]
            self.refused(document)

    def test_every_check_the_spec_lists_is_known(self):
        names = ["head_matches", "repo_config_safe", "staging_state_ok", "paths_valid", "message_valid",
                 "paths_not_credentials", "paths_regular", "facts_complete", "no_secret_lines", "confirm_present",
                 "removal_valid", "ignore_status_known", "preview_matches_arguments", "no_git_metadata"]
        self.assertEqual(sorted(names), sorted(self.helper.CHECKS))
        document = copy.deepcopy(COMMIT)
        document["checks"] = names
        self.assertEqual([], self.one(document).errors)

    def test_more_than_32_checks_flags_or_entries_are_refused(self):
        document = copy.deepcopy(COMMIT)
        document["flags"] = {"--f%d" % i: {"type": "boolean"} for i in range(33)}
        self.refused(document)
        document = copy.deepcopy(COMMIT)
        document["flags"] = {"--f%d" % i: {"type": "boolean"} for i in range(32)}
        self.assertEqual([], self.one(document).errors)

    def test_a_flag_outside_its_form_or_of_an_unknown_type_is_refused(self):
        for flags in ({"subject": {"type": "value"}}, {"--Subject": {"type": "value"}}, {"--": {"type": "value"}},
                      {"--s" + "x" * 33: {"type": "value"}}, {"--subject": {"type": "string"}},
                      {"--subject": {}}, {"--subject": {"type": "value", "required": "yes"}}, {"--subject": "value"},
                      {"--subject=x": {"type": "value"}}):
            document = copy.deepcopy(COMMIT)
            document["flags"] = flags
            self.refused(document)

    def test_the_positional_group_must_be_one_group_in_bounds(self):
        bad = [{"name": "paths", "separator": True, "min": 3, "max": 2},
               {"name": "paths", "separator": True, "min": 0, "max": 62},
               {"name": "paths", "separator": True, "min": -1, "max": 2},
               {"name": "paths", "separator": 1, "min": 0, "max": 2},
               {"name": "paths", "separator": True, "min": True, "max": 2},
               {"name": "paths", "separator": True, "min": 0},
               {"name": "Paths", "separator": True, "min": 0, "max": 2},
               {"name": "paths", "separator": True, "min": 0.5, "max": 2},
               [{"name": "paths", "separator": True, "min": 0, "max": 2}] * 2, [], None]
        for value in bad:
            document = copy.deepcopy(COMMIT)
            document["positionals"] = value
            self.refused(document)
        for good in ({"name": "paths", "separator": False, "min": 0, "max": 0},
                     {"name": "paths", "separator": True, "min": 61, "max": 61}):
            document = copy.deepcopy(COMMIT)
            document["positionals"] = good
            self.assertEqual([], self.one(document).errors)

    def test_the_subcommand_must_equal_the_action(self):
        document = copy.deepcopy(COMMIT)
        document["subcommand"] = "remove"
        self.refused(document)

    def test_a_wb_run_spelling_must_end_with_the_module(self):
        document = copy.deepcopy(COMMIT)
        document["module"] = "other"
        self.refused(document, "other-commit.json")
        document["spelling"] = ["wb", "run", "other"]
        self.assertEqual([], self.one(document, "other-commit.json").errors)

    def test_another_spelling_is_matched_to_no_module(self):
        document = copy.deepcopy(COMMIT)
        document["spelling"] = ["git"]
        self.assertEqual([], self.one(document).errors)

    def test_the_file_name_must_be_module_dash_action_json(self):
        for name in ("commit.json", "safe-git-remove.json", "safe-git-commit.JSON.json", "Safe-git-commit.json"):
            loaded = self.one(COMMIT, name)
            self.assertEqual([], loaded.rules, name)
            self.assertEqual([name], [n for n, _ in loaded.errors], name)

    def test_a_list_name_outside_the_fixed_list_is_refused_and_the_lists_are_bounded(self):
        for lists in ({"other": ["a"]}, {"credential_names": "a"}, {"credential_names": ["a", "a"]},
                      {"credential_names": ["é"]}, {"credential_names": ["a" * 257]},
                      {"credential_names": ["a%d" % i for i in range(257)]}, {"credential_names": [1]},
                      {"credential_names": ["tab\t"]}, {"credential_names": [""]}, []):
            document = copy.deepcopy(COMMIT)
            document["lists"] = lists
            self.refused(document)
        document = copy.deepcopy(COMMIT)
        document["lists"] = {"credential_names": [".env"], "reviewer_facing_paths": ["AGENTS.md"]}
        (rule,) = self.one(document).rules
        self.assertEqual({".env"}, set(rule.lists["credential_names"]))

    def test_an_over_long_file_is_refused(self):
        document = copy.deepcopy(COMMIT)
        document["questions"] = []
        text = encode(document)[:-1] + b', "x": "' + b"a" * 16384 + b'"}'
        self.refused_text(text)

    def test_not_strict_json_is_refused(self):
        for data in (b"", b"[]", b"{", b'{"format": 1, "format": 1}', b'{"format": NaN}', b"\xff\xfe",
                     b'{"a": 1.5}', json.dumps(COMMIT).encode("utf-8") + b" trailing"):
            self.refused_text(data)

    def test_the_error_names_the_file_and_never_prints_the_content(self):
        loaded = self.loaded({"safe-git-commit.json": b'{"format": 1, "secret-value-xyz": 1}'})
        (name, why), = loaded.errors
        self.assertEqual("safe-git-commit.json", name)
        self.assertNotIn("secret-value-xyz", why)

    def test_a_directory_or_a_link_in_the_rules_is_a_rule_error_for_its_own_key(self):
        root = self.project({"safe-git-commit.json": encode(COMMIT)})
        directory = os.path.join(root, *INSTALLED)
        os.mkdir(os.path.join(directory, "safe-git-remove.json"))
        os.symlink("safe-git-commit.json", os.path.join(directory, "safe-git-push.json"))
        loaded = self.helper.load_rules(root)
        self.assertEqual(["commit"], [r.action for r in loaded.rules])
        self.assertEqual(["safe-git-push.json", "safe-git-remove.json"], sorted(n for n, _ in loaded.errors))

    def test_a_file_that_is_not_json_by_name_is_not_read(self):
        loaded = self.loaded({"safe-git-commit.json": encode(COMMIT), "notes.txt": b"anything", ".DS_Store": b"\0"})
        self.assertEqual([], loaded.errors)
        self.assertEqual(1, len(loaded.rules))

    def test_a_rules_directory_that_cannot_be_used_refuses_every_review(self):
        many = {"r%d-a.json" % i: b"{}" for i in range(65)}
        with self.assertRaises(self.helper.RulesUnavailable):
            self.loaded(many)
        document = copy.deepcopy(COMMIT)
        document["questions"] = []
        filler = encode(document)[:-1] + b', "x": "' + b"a" * 15500 + b'"}'
        big = {"r%d-a.json" % i: filler for i in range(17)}
        with self.assertRaises(self.helper.RulesUnavailable):
            self.loaded(big)

    def test_a_missing_rules_directory_or_project_refuses_every_review(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        with self.assertRaises(self.helper.RulesUnavailable):
            self.helper.load_rules(os.path.realpath(scratch.name))
        root = self.project({})
        os.rmdir(os.path.join(root, *INSTALLED))
        with self.assertRaises(self.helper.RulesUnavailable):
            self.helper.load_rules(root)


class Keys(Base):
    def files(self, **extra):
        files = {"safe-git-commit.json": encode(COMMIT), "safe-git-remove.json": read_shipped("safe-git-remove.json")}
        files.update(extra)
        return files

    def text(self, tail):
        return "wb run safe-git " + tail

    def read(self, files, text):
        return self.helper.read_command(self.loaded(files), text)

    def refusal(self, files, text):
        with self.assertRaises(self.helper.Unreviewable) as caught:
            self.read(files, text)
        return str(caught.exception)

    COMMAND = "commit --expected-head " + HEAD + " --subject 'Add it' -- a.txt"

    def test_one_matching_rule_reviews_and_gives_the_arguments_after_the_subcommand(self):
        rule, args = self.read(self.files(), self.text(self.COMMAND))
        self.assertEqual("commit", rule.action)
        self.assertEqual(["--expected-head", HEAD, "--subject", "Add it", "--", "a.txt"], args)

    def test_the_key_is_whole_words_never_a_text_prefix(self):
        for text in ("wb run safe-git commitx --", "wb run safe-gitx commit", "wb run safe-git commit-all -- a",
                     "wb run safe-git", "wb run", "wb run safe-git Commit", "wb runs safe-git commit",
                     "xwb run safe-git commit", "sudo wb run safe-git commit"):
            self.assertIn("no rule", self.refusal(self.files(), text), text)

    def test_a_word_is_compared_by_value_so_quoting_does_not_hide_a_command(self):
        rule, _ = self.read(self.files(), "'wb' run 'safe-git' 'commit' --expected-head " + HEAD
                            + " --subject x -- a")
        self.assertEqual("commit", rule.action)

    def test_a_retired_action_has_no_rule_and_is_refused(self):
        for text in ("ask-codex archive", "ask-codex archive --all", "safe-committer", "safe-committer commit -- a",
                     "amend-message", "claude-workflow commit --expected-head " + HEAD):
            self.assertIn("no rule", self.refusal(self.files(), text), text)

    def test_the_refusal_for_no_rule_names_no_rule(self):
        reason = self.refusal(self.files(), "ask-codex archive")
        self.assertNotIn("safe-git", reason)

    def test_two_files_with_one_key_refuse_both_and_not_the_others(self):
        first = copy.deepcopy(COMMIT)
        first.update(spelling=["git"], module="git")
        second = copy.deepcopy(first)
        second.update(module="other")
        files = {"git-commit.json": encode(first), "other-commit.json": encode(second),
                 "safe-git-remove.json": read_shipped("safe-git-remove.json")}
        loaded = self.loaded(files)
        reason = self.refusal(files, "git commit --expected-head " + HEAD + " --subject x -- a")
        self.assertIn("git-commit.json", reason)
        self.assertIn("other-commit.json", reason)
        self.assertEqual({"git-commit.json", "other-commit.json"}, {n for n, _ in loaded.errors})
        rule, _ = self.read(files, "wb run safe-git remove --confirm -- a")
        self.assertEqual("remove", rule.action)

    def test_two_rules_that_both_match_one_command_refuse_both(self):
        overlap = copy.deepcopy(COMMIT)
        overlap.update(spelling=["wb", "run"], subcommand="safe-git", module="run", action="safe-git",
                       flags={}, positionals={"name": "paths", "separator": False, "min": 0, "max": 61})
        files = self.files(**{"run-safe-git.json": encode(overlap)})
        reason = self.refusal(files, self.text(self.COMMAND))
        self.assertIn("safe-git-commit.json", reason)
        self.assertIn("run-safe-git.json", reason)

    def test_a_corrupt_neighbour_refuses_only_its_own_key(self):
        files = self.files(**{"safe-git-remove.json": b"{not json"})
        rule, _ = self.read(files, self.text(self.COMMAND))
        self.assertEqual("commit", rule.action)
        reason = self.refusal(files, self.text("remove --confirm -- a"))
        self.assertIn("safe-git-remove.json", reason)

    def test_a_rule_with_a_bad_field_but_a_good_key_refuses_that_key_from_its_words(self):
        bad = copy.deepcopy(COMMIT)
        bad["checks"] = ["no_such_check"]
        files = self.files(**{"safe-git-commit.json": encode(bad)})
        self.assertIn("safe-git-commit.json", self.refusal(files, self.text(self.COMMAND)))
        rule, _ = self.read(files, self.text("remove --confirm -- a"))
        self.assertEqual("remove", rule.action)

    def test_a_bad_rule_blocks_its_key_even_when_a_good_rule_has_the_same_key(self):
        bad = copy.deepcopy(COMMIT)
        bad.update(module="other", checks=["no_such_check"])
        files = self.files(**{"other-commit.json": encode(bad)})
        reason = self.refusal(files, self.text(self.COMMAND))
        self.assertIn("other-commit.json", reason)

    def test_a_file_with_an_unreadable_key_blocks_a_command_naming_its_words(self):
        files = self.files(**{"safe-git-push.json": b"{"})
        reason = self.refusal(files, "wb run safe-git push --force -- a")
        self.assertIn("safe-git-push.json", reason)
        self.assertIn("no rule", self.refusal(self.files(), "wb run safe-git push -- a"))

    def test_the_name_key_looks_only_at_the_first_five_words(self):
        files = self.files(**{"safe-git-push.json": b"{"})
        self.assertIn("no rule", self.refusal(files, "a b c d e safe-git push"))

    def test_main_reports_each_rule_error_with_its_file_name_before_the_refusal(self):
        root = self.project(self.files(**{"safe-git-remove.json": b"{"}))
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(["review", self.text(self.COMMAND)], io.BytesIO(b""), out, err, root)
        self.assertEqual((1, ""), (code, out.getvalue()))
        lines = err.getvalue().splitlines()
        self.assertTrue(lines[0].startswith("rule error: 'safe-git-remove.json': "), lines)
        self.assertTrue(lines[-1].startswith("refused: "), lines)
        self.assertEqual(1, sum(line.startswith("refused: ") for line in lines))

    def test_main_refuses_a_retired_action_before_any_describe_or_bridge_call(self):
        root = self.project({n: read_shipped(n) for n in ("safe-git-commit.json", "safe-git-remove.json")})
        for text in ("ask-codex archive", "safe-committer", "amend-message"):
            out, err = io.StringIO(), io.StringIO()
            code = self.helper.main(["review", text], io.BytesIO(b""), out, err, root)
            self.assertEqual((1, ""), (code, out.getvalue()), text)
            self.assertIn("no rule", err.getvalue(), text)

    def test_main_refuses_every_review_when_the_rules_cannot_be_used(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(["review", self.text(self.COMMAND)], io.BytesIO(b""), out, err,
                                os.path.realpath(scratch.name))
        self.assertEqual((1, ""), (code, out.getvalue()))
        self.assertTrue(err.getvalue().startswith("refused: "), err.getvalue())
        self.assertEqual(1, len(err.getvalue().splitlines()))

    def test_main_still_does_not_review_a_command_that_fits_a_rule(self):
        root = self.project({n: read_shipped(n) for n in ("safe-git-commit.json", "safe-git-remove.json")})
        out, err = io.StringIO(), io.StringIO()
        described = []

        def fake(*args, **kwargs):
            described.append(args)
            return call.Result(0, DESCRIBED, b"", False, False)

        with unittest.mock.patch.object(self.helper.call, "run_command", fake):
            code = self.helper.main(["review", self.text(self.COMMAND)], io.BytesIO(b""), out, err, root)
        self.assertEqual((1, ""), (code, out.getvalue()))
        self.assertIn("not built", err.getvalue())
        self.assertEqual(1, len(described))


class Arguments(Base):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with tempfile.TemporaryDirectory() as scratch:
            root = make_project(os.path.realpath(scratch), {n: read_shipped(n) for n in
                                                              ("safe-git-commit.json", "safe-git-remove.json")})
            cls.loaded_rules = cls.helper.load_rules(root)

    def read(self, text):
        return self.helper.read_command(self.loaded_rules, text)

    def refused(self, text, why=""):
        with self.assertRaises(self.helper.Unreviewable) as caught:
            self.read(text)
        self.assertIn(why, str(caught.exception), text)

    HEAD_SUBJECT = "--expected-head " + HEAD + " --subject x"

    def commit(self, middle, tail="-- a b"):
        return " ".join(part for part in ("wb run safe-git commit", middle, tail) if part)

    def test_the_arguments_come_back_in_the_order_given(self):
        _, args = self.read(self.commit("--subject x --trailer 'A: b' --leave-other-staged --expected-head " + HEAD
                                       + " --trailer 'C: d' --body 'long text'", "-- z a"))
        self.assertEqual(["--subject", "x", "--trailer", "A: b", "--leave-other-staged", "--expected-head", HEAD,
                          "--trailer", "C: d", "--body", "long text", "--", "z", "a"], args)

    def test_a_multi_flag_may_repeat_and_a_missing_one_is_fine(self):
        self.read(self.commit(self.HEAD_SUBJECT))
        self.read(self.commit(self.HEAD_SUBJECT + " --trailer 'A: b' --trailer 'A: b'"))

    def test_an_undeclared_flag_is_refused(self):
        self.refused(self.commit(self.HEAD_SUBJECT + " --force"), "not declared")
        self.refused(self.commit(self.HEAD_SUBJECT + " --no-verify"), "not declared")
        self.refused(self.commit(self.HEAD_SUBJECT + " -n"), "not declared")

    def test_name_equals_value_is_refused_as_an_undeclared_flag(self):
        self.refused(self.commit("--expected-head=" + HEAD + " --subject x"), "not declared")
        self.refused(self.commit(self.HEAD_SUBJECT + " --body=x"), "not declared")

    def test_a_quoted_word_is_never_a_flag(self):
        self.refused(self.commit(self.HEAD_SUBJECT + " '--force'"), "dash")
        self.refused(self.commit(self.HEAD_SUBJECT + " --body '--x'"), "dash")

    def test_a_repeated_single_valued_flag_is_refused(self):
        self.refused(self.commit(self.HEAD_SUBJECT + " --subject y"), "more than once")
        self.refused(self.commit(self.HEAD_SUBJECT + " --leave-other-staged --leave-other-staged"), "more than once")
        self.refused(self.commit(self.HEAD_SUBJECT + " --body a --body b"), "more than once")

    def test_a_missing_required_flag_is_refused(self):
        self.refused(self.commit("--subject x"), "--expected-head")
        self.refused(self.commit("--expected-head " + HEAD), "--subject")
        self.refused(self.commit("--body x"), "required")

    def test_a_flag_with_no_value_or_a_flag_for_a_value_is_refused(self):
        self.refused("wb run safe-git commit --expected-head " + HEAD + " --subject", "value")
        self.refused(self.commit("--expected-head " + HEAD + " --subject --body x"), "value")
        self.refused(self.commit("--expected-head " + HEAD + " --subject --"), "value")
        self.refused(self.commit("--expected-head --subject x"), "value")

    def test_a_boolean_flag_takes_no_value(self):
        _, args = self.read("wb run safe-git remove --confirm --recursive -- a")
        self.assertEqual(["--confirm", "--recursive", "--", "a"], args)
        self.refused("wb run safe-git remove --confirm yes -- a", "where a flag is expected")

    def test_the_separator_is_required_and_only_once(self):
        self.refused("wb run safe-git commit " + self.HEAD_SUBJECT, "separator")
        self.refused(self.commit(self.HEAD_SUBJECT, "-- a -- b"), "second")
        self.refused(self.commit(self.HEAD_SUBJECT, "-- a --"), "second")

    def test_a_flag_word_after_the_separator_is_refused_not_taken_as_a_path(self):
        self.refused(self.commit(self.HEAD_SUBJECT, "-- --leave-other-staged"), "flag")
        self.refused(self.commit(self.HEAD_SUBJECT, "-- a --subject"), "flag")
        self.refused(self.commit(self.HEAD_SUBJECT, "-- -x"), "not declared")

    def test_a_loose_word_where_a_flag_is_expected_is_refused(self):
        self.refused(self.commit(self.HEAD_SUBJECT + " stray"), "where a flag is expected")

    def test_the_count_of_positionals_is_bounded(self):
        self.refused(self.commit(self.HEAD_SUBJECT, "--"), "at least")
        self.refused(self.commit(self.HEAD_SUBJECT, ""), "separator")
        _, args = self.read(self.commit(self.HEAD_SUBJECT, "-- " + " ".join("p%d" % i for i in range(53))))
        self.assertEqual(53 + 5, len(args))

    def test_a_command_of_more_than_61_arguments_is_unreviewable(self):
        paths = " ".join("p%d" % i for i in range(60))
        self.refused(self.commit(self.HEAD_SUBJECT, "-- " + paths), "arguments")
        self.read("wb run safe-git remove -- " + " ".join("p%d" % i for i in range(60)))
        self.refused("wb run safe-git remove -- " + " ".join("p%d" % i for i in range(61)), "arguments")

    def test_a_group_without_a_separator_takes_the_loose_words_after_the_flags(self):
        document = copy.deepcopy(COMMIT)
        document.update(positionals={"name": "paths", "separator": False, "min": 1, "max": 2}, flags={
            "--force": {"type": "boolean"}})
        document.update(spelling=["git"], module="git")
        loose = self.helper.load_rules(make_project_dir(self, {"git-commit.json": encode(document)}))
        rule, args = self.helper.read_command(loose, "git commit --force a b")
        self.assertEqual(["--force", "a", "b"], args)
        for text in ("git commit --force", "git commit a b c", "git commit a --force", "git commit -- a"):
            with self.assertRaises(self.helper.Unreviewable, msg=text):
                self.helper.read_command(loose, text)

    def test_a_text_outside_the_grammar_is_unreviewable_before_any_rule_is_looked_at(self):
        for text in ("wb run safe-git commit  x", "wb run safe-git commit $(x)", "wb run safe-git commit 'x"):
            self.refused(text)

    def test_the_real_assignment_and_zsh_expansion_hazards_stay_refused(self):
        self.refused("A=1 wb run safe-git remove -- a", "assignment")
        self.refused("wb run safe-git remove -- =cmd", "equals")


def make_project_dir(case, files):
    scratch = tempfile.TemporaryDirectory()
    case.addCleanup(scratch.cleanup)
    return make_project(os.path.realpath(scratch.name), files)


if __name__ == "__main__":
    unittest.main()
