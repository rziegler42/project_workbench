"""The real `review-engine` module in `packages/workbench/`: its declaration and its file list (conformance
checklist item 1 of `docs/specs/review-engine.md`). Plan `2026-10-23-review-engine`, increment C.

The package is new, so it has no shipped approval until the plan's last increment."""

import json
import os
import re
import unittest

from tests import support_install
from workbench import verify

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "review-engine")
HELPER = "helper/review-engine"


def declaration():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module_beside_a_bridge(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("review-engine", "ask-codex"),
                                       harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("review-engine", [m.name for m in result.modules])

    def test_it_is_refused_without_a_bridge_and_the_refusal_names_the_capability(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("review-engine",), harness_required=False)
        self.assertFalse(result.accepted)
        self.assertTrue(any("model-bridge" in str(p) for p in result.problems))

    def test_it_provides_peer_review_and_requires_a_model_bridge_hard(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        self.assertEqual(["peer-review"], document["provides"])
        self.assertEqual(["model-bridge"], document["requires"])
        self.assertEqual([HELPER], document["ships"])
        for field in ("writes", "fills", "checks", "helpers", "blocks", "slots", "layout"):
            self.assertNotIn(field, document)

    def test_the_command_has_its_own_name_and_only_the_arguments_built_so_far(self):
        self.assertEqual(["review-engine"], list(declaration()["commands"]))
        command = declaration()["commands"]["review-engine"]
        self.assertEqual(["status", "init"], command["arguments"])
        self.assertEqual((HELPER, "python", 1), (command["helper"], command["runtime"], command["kit"]))
        self.assertNotIn("owner", command)

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
            self.assertIn("review-engine", json.load(handle)["modules"])


class Helper(unittest.TestCase):
    def text(self):
        with open(os.path.join(MODULE, HELPER), encoding="utf-8") as handle:
            return handle.read()

    def test_it_imports_only_the_standard_library_and_the_kit(self):
        imported = set(re.findall(r"^(?:import|from) ([a-z_.]+)", self.text(), re.M))
        self.assertEqual({"collections", "contextlib", "errno", "fcntl", "hashlib", "hmac", "json", "os", "re",
                          "sys", "unicodedata", "wbkit"}, imported)

    def test_it_opens_no_connection_and_names_no_vendor_or_other_module(self):
        text = self.text()
        for word in ("socket", "urllib", "http", "ssl", "subprocess", "codex", "claude", "gemini", "safe-git",
                     "code-work", "groundwork"):
            self.assertNotIn(word, text, word)


if __name__ == "__main__":
    unittest.main()
