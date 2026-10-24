"""The real `mempalace` module in `packages/workbench/`: its declaration and its file list (criterion 2 of plan
`2026-10-24-mempalace-module`, increment B). The package tree hash changes with this module, so the shipped
approvals are stale until increment E of that plan."""

import json
import os
import re
import unittest

from tests import support_install
from workbench import verify

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "mempalace")
HELPER = "helper/mempalace"


def declaration():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("mempalace",), harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("mempalace", [m.name for m in result.modules])

    def test_it_provides_memory_recall_requires_nothing_and_expects_the_program(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        self.assertEqual(["memory-recall"], document["provides"])
        self.assertEqual(["mempalace"], document["helpers"])
        self.assertEqual([HELPER], document["ships"])
        for field in ("requires", "writes", "blocks", "slots", "layout", "checks", "approval"):
            self.assertNotIn(field, document)

    def test_the_command_takes_only_the_two_read_commands(self):
        self.assertEqual(["mempalace"], list(declaration()["commands"]))
        command = declaration()["commands"]["mempalace"]
        self.assertEqual(["status", "search"], command["arguments"])
        self.assertNotIn("owner", command)
        self.assertEqual((HELPER, "python", 1), (command["helper"], command["runtime"], command["kit"]))

    def test_every_file_is_the_declaration_or_the_helper(self):
        found = []
        for base, dirs, files in os.walk(MODULE):
            if base == MODULE:
                dirs.remove("tests")  # the module's own tests are not part of what it installs
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), MODULE))
        self.assertEqual(sorted(["module.json", HELPER]), sorted(found))

    def test_the_package_lists_it(self):
        with open(os.path.join(PACKAGE, "package.json"), encoding="utf-8") as handle:
            self.assertIn("mempalace", json.load(handle)["modules"])

    def test_the_helper_opens_no_connection_and_names_no_other_module_or_the_wrapped_writes(self):
        with open(os.path.join(MODULE, HELPER), encoding="utf-8") as handle:
            text = handle.read()
        imported = set(re.findall(r"^(?:import|from) ([a-z_.]+)", text, re.M))
        self.assertEqual({"os", "re", "secrets", "selectors", "shutil", "signal", "stat", "subprocess", "sys",
                          "tempfile", "time", "unicodedata", "wbkit"}, imported)
        for word in ("socket", "urllib", "http", "ssl", "claude", "codex", "safe-git", "code-work",
                     "groundwork", "--include-media", "--backend", "wake-up", "--llm", "--palace"):
            self.assertNotIn(word, text, word)


if __name__ == "__main__":
    unittest.main()
