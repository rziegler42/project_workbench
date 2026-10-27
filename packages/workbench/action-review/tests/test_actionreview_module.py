"""The real `action-review` module in `packages/workbench/`: its declaration, its file list and what the skeleton
helper refuses (`docs/specs/action-review.md`, "The rule schema, the module and the checks").

Plan `2026-10-26-action-review-engine`, increment B, and increment D for the shipped rules. The package tree hash changes
with this module, so the shipped approvals are stale until the owner runs `release-approvals`."""

import io
import json
import os
import re
import unittest

from tests import support_helpers, support_install
from workbench import declarations as d
from workbench import rules, verify

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "action-review")
HELPER = "helper/action-review"
RULES = ("rules/safe-git-commit.json", "rules/safe-git-remove.json")
DATA = ("rubric/rubric.md", "reply-schema.json")


def declaration():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module_beside_a_bridge(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("action-review", "ask-codex"),
                                       harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("action-review", [m.name for m in result.modules])

    def test_it_is_refused_without_a_bridge_and_the_refusal_names_the_capability(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("action-review",), harness_required=False)
        self.assertFalse(result.accepted)
        self.assertTrue(any("model-bridge" in str(p) for p in result.problems))

    def test_it_provides_action_review_and_requires_a_model_bridge_hard(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        self.assertEqual(["action-review"], document["provides"])
        self.assertEqual(["model-bridge"], document["requires"])
        # The files are listed, not their directory: a shipped item named `rules` is a word the installer may not use.
        self.assertEqual([HELPER, *RULES, *DATA], document["ships"])
        for field in ("writes", "fills", "checks", "helpers", "blocks", "slots", "layout"):
            self.assertNotIn(field, document)

    def test_the_command_has_its_own_name_and_review_as_its_only_argument(self):
        self.assertEqual(["action-review"], list(declaration()["commands"]))
        command = declaration()["commands"]["action-review"]
        self.assertEqual(["review"], command["arguments"])
        self.assertEqual((HELPER, "python", 1), (command["helper"], command["runtime"], command["kit"]))

    def test_no_argument_is_owner_run_because_review_reads_and_prints_and_writes_nothing(self):
        self.assertNotIn("owner", declaration()["commands"]["action-review"])
        parsed = d.parse_module(json.dumps(declaration()).encode("utf-8"), "workbench", "action-review",
                                first_party=True).commands[0]
        self.assertEqual((), parsed.owner)
        self.assertEqual([], rules.command_owner_patterns("action-review", parsed.owner))

    def test_every_file_is_the_declaration_the_helper_or_a_shipped_rule(self):
        found = []
        for base, dirs, files in os.walk(MODULE):
            if base == MODULE:
                dirs.remove("tests")  # the module's own tests are not part of what it installs
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), MODULE))
        self.assertEqual(sorted(["module.json", HELPER, *RULES, *DATA]), sorted(found))

    def test_the_package_lists_it(self):
        with open(os.path.join(PACKAGE, "package.json"), encoding="utf-8") as handle:
            self.assertIn("action-review", json.load(handle)["modules"])


class Helper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("action-review")

    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(list(argv), io.BytesIO(b""), out, err, os.getcwd())
        return code, out.getvalue(), err.getvalue()

    def test_a_missing_or_unknown_argument_is_refused_with_a_usage_line_and_nothing_on_standard_output(self):
        for argv in ((), ("status",), ("Review",), ("",), ("--log-row",)):
            code, out, err = self.call(*argv)
            self.assertEqual((1, ""), (code, out), argv)
            self.assertTrue(err.startswith("refused: usage: action-review review"), (argv, err))
            self.assertEqual(1, len(err.splitlines()), argv)

    def test_a_command_outside_a_project_is_refused_for_want_of_rules(self):
        code, out, err = self.call("review", "wb run safe-git commit")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("no rule is trusted", err)

    def test_it_imports_only_the_standard_library_and_the_kit(self):
        imported = set(re.findall(r"^(?:import|from) ([a-z_.]+)", self.text(), re.M))
        self.assertEqual({"collections", "fnmatch", "hashlib", "json", "math", "os", "re", "secrets", "sys", "wbkit"},
                         imported)

    def test_it_starts_no_process_and_opens_no_connection(self):
        text = self.text()
        for word in ("subprocess", "socket", "urllib", "http", "ssl", "os.system", "os.exec", "os.popen"):
            self.assertNotIn(word, text, word)

    def text(self):
        with open(os.path.join(MODULE, HELPER), encoding="utf-8") as handle:
            return handle.read()


if __name__ == "__main__":
    unittest.main()
