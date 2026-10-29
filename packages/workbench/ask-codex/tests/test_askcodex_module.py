"""The real `ask-codex` module in `packages/workbench/`: its declaration and its file list, and what the helper
refuses before it starts anything (conformance checklist items 1 to 3 and 7 of `docs/specs/model-bridge.md`).

Plan `2026-10-22-ask-codex-bridge`, increment C. The package tree hash changes with this module, so the shipped
approvals are stale until increment D of that plan."""

import io
import json
import os
import re
import unittest

from tests import support_install
from workbench import verify

import support_codex

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "ask-codex")
HELPER = "helper/ask-codex"


def declaration():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("ask-codex",), harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("ask-codex", [m.name for m in result.modules])

    def test_it_provides_a_model_bridge_requires_nothing_and_ships_only_the_helper(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        self.assertEqual(["model-bridge"], document["provides"])
        self.assertEqual([HELPER], document["ships"])
        for field in ("requires", "writes", "fills", "checks", "helpers", "blocks", "slots", "layout"):
            self.assertNotIn(field, document)

    def test_the_command_takes_ask_as_its_only_argument(self):
        self.assertEqual(["ask-codex"], list(declaration()["commands"]))
        command = declaration()["commands"]["ask-codex"]
        self.assertEqual(["ask"], command["arguments"])
        self.assertEqual((HELPER, "python", 1), (command["helper"], command["runtime"], command["kit"]))

    def test_it_asks_before_the_login_file_is_read(self):
        import types
        from workbench import declarations, harnessplan, harnessstage, neutral
        self.assertEqual(["~/.codex/auth.json"], declaration()["ask_reads"])
        loaded = declarations.load_package(PACKAGE, first_party=True)
        module = [m for m in loaded.modules if m.name == "ask-codex"][0]
        self.assertEqual(("~/.codex/auth.json",), module.ask_reads)
        found = harnessstage.ask_rules([types.SimpleNamespace(module=module, type="module")])
        self.assertEqual([neutral.Rule("ask", "read", "~/.codex/auth.json")], found)
        with open(os.path.join(PACKAGE, "claude", "module.json"), encoding="utf-8") as handle:
            layout = json.load(handle)["layout"]
        permissions = json.loads(harnessplan.render_permissions(
            found, layout, "/Users/tester/.config/project-workbench", "/Users/tester"))["permissions"]
        deny, ask = permissions["deny"], permissions["ask"]
        self.assertIn("Read(//Users/tester/.codex/auth.json)", ask)

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
            self.assertIn("ask-codex", json.load(handle)["modules"])

    def test_the_helper_opens_no_connection_and_names_no_other_vendor_or_module(self):
        with open(os.path.join(MODULE, HELPER), encoding="utf-8") as handle:
            text = handle.read()
        imported = set(re.findall(r"^(?:import|from) ([a-z_.]+)", text, re.M))
        self.assertEqual({"json", "os", "re", "selectors", "shutil", "signal", "stat", "subprocess", "sys",
                          "tempfile", "time", "unicodedata", "wbkit"}, imported)
        for word in ("socket", "urllib", "http", "ssl", "claude", "gemini", "safe-git", "code-work",
                     "groundwork", "wb run"):
            self.assertNotIn(word, text, word)


class Prompt(support_codex.Bridge):
    def test_a_prompt_that_is_missing_empty_or_blank_is_refused(self):
        for prompt in (b"", b"  \n\t\n"):
            self.refused(prompt=prompt, contains="empty")

    def test_a_prompt_that_is_not_utf8_or_is_too_large_is_refused(self):
        self.refused(prompt=b"\xff\xfe text", contains="UTF-8")
        self.refused(prompt=b"x" * (self.helper.MAX_PROMPT + 1), contains="larger than")

    def test_a_prompt_at_the_bound_is_accepted(self):
        document = self.document(prompt=b"x" * self.helper.MAX_PROMPT)
        self.assertTrue(document["ok"])
        self.assertEqual(self.helper.MAX_PROMPT, len(self.calls()[0]["stdin"]))


class Options(support_codex.Bridge):
    def test_a_name_that_is_not_an_option_or_is_given_twice_or_has_no_value(self):
        self.refused("--sandbox", "danger-full-access", contains="not an option")
        self.refused("-m", "x", contains="not an option")
        self.refused("--model", "a", "--model", "b", contains="given twice")
        self.refused("--model", contains="needs a value")
        self.refused("--effort", "low", "--timeout", contains="needs a value")
        self.refused("extra", contains="not an option")
        self.refused("--MODEL", "a", contains="not an option")

    def test_a_model_outside_the_charset_or_length_is_refused(self):
        for bad in ("", "a b", "a;b", "$(x)", "a/b", "-x", "--effort", "m\n", "x" * 65, "é", "a=b"):
            self.refused("--model", bad, contains="--model")

    def test_a_model_at_the_limits_is_accepted(self):
        for good in ("gpt-5", "a", "o3.mini:high_1", "x" * 64):
            self.assertTrue(self.document("--model", good)["ok"], good)

    def test_an_effort_outside_the_three_levels_is_refused(self):
        for bad in ("", "LOW", "max", "minimal", "low ", "none"):
            self.refused("--effort", bad, contains="--effort")

    def test_a_timeout_out_of_range_or_not_a_plain_number_is_refused(self):
        for bad in ("0", "3601", "-1", "1.5", "1e2", "abc", "", "+5", "٣", "00001", "10000", " 5"):
            self.refused("--timeout", bad, contains="--timeout")

    def test_a_timeout_at_the_limits_is_accepted(self):
        for good in ("1", "3600", "0600"):
            self.assertTrue(self.document("--timeout", good)["ok"], good)

    def test_the_first_argument_must_be_ask(self):
        out, err = io.StringIO(), io.StringIO()
        for argv in ([], ["review"], ["--model", "x"], ["ASK"]):
            self.assertEqual(1, self.helper.main(argv, io.BytesIO(b"x"), out, err, self.root))
        self.assertEqual("", out.getvalue())
        self.assertEqual(4, err.getvalue().count("refused: usage: ask-codex ask"))
        self.assertEqual([], self.calls())

    def test_a_directory_that_is_not_a_project_is_refused(self):
        self.refused(cwd=self.base, contains="not inside a workbench project")


class Paths(support_codex.Bridge):
    def setUp(self):
        support_codex.Bridge.setUp(self)
        os.makedirs(os.path.join(self.root, "src", "deep"))
        with open(os.path.join(self.root, "schema.json"), "w") as handle:
            handle.write('{"type": "object"}')
        os.symlink(os.path.join(self.root, "src"), os.path.join(self.root, "linked"))
        os.symlink(os.path.join(self.root, "schema.json"), os.path.join(self.root, "schema-link.json"))
        os.symlink(self.outside, os.path.join(self.root, "away"))
        os.makedirs(os.path.join(self.base, "elsewhere"))
        with open(os.path.join(self.base, "elsewhere", "schema.json"), "w") as handle:
            handle.write("{}")

    def test_a_root_or_schema_outside_the_project_is_refused(self):
        self.refused("--root", self.base, contains="outside the project")
        self.refused("--root", os.path.join(self.base, "elsewhere"), contains="outside the project")
        self.refused("--root", self.root + "-sibling", contains="outside the project")
        self.refused("--schema", os.path.join(self.base, "elsewhere", "schema.json"), contains="outside")
        self.refused("--root", "..", contains="parent directory")
        self.refused("--root", "src/../../elsewhere", contains="parent directory")
        self.refused("--schema", "../elsewhere/schema.json", contains="parent directory")

    def test_a_link_in_any_component_is_refused(self):
        self.refused("--root", "linked", contains="link")
        self.refused("--root", "linked/deep", contains="link")
        self.refused("--root", "away", contains="link")
        self.refused("--root", os.path.join(self.root, "linked"), contains="link")
        self.refused("--schema", "schema-link.json", contains="link")
        self.refused("--schema", "linked/schema.json", contains="link")

    def test_a_path_that_does_not_exist_or_is_the_wrong_kind_is_refused(self):
        self.refused("--root", "nothing", contains="does not exist")
        self.refused("--root", "schema.json", contains="not a directory")
        self.refused("--schema", "nothing.json", contains="does not exist")
        self.refused("--schema", "src", contains="not a regular file")
        self.refused("--root", "", contains="not a usable path")
        self.refused("--schema", "src\0x", contains="not a usable path")

    def test_a_schema_that_is_not_one_json_object_or_is_too_large_is_refused(self):
        for index, text in enumerate(("[]", "7", "not json", "", "\xff", " " * 3)):
            name = "bad%d.json" % index
            with open(os.path.join(self.root, name), "w", encoding="latin-1") as handle:
                handle.write(text)
            self.refused("--schema", name, contains="not a JSON object")
        with open(os.path.join(self.root, "big.json"), "w") as handle:
            handle.write('{"a": "%s"}' % ("x" * self.helper.MAX_SCHEMA))
        self.refused("--schema", "big.json", contains="larger than")

    def test_a_relative_path_is_read_against_the_project_root_and_the_program_starts_there(self):
        sub = os.path.join(self.root, "src")
        self.assertTrue(self.document("--root", "src/deep", cwd=sub)["ok"])
        call = self.calls()[0]
        self.assertEqual(os.path.join(self.root, "src", "deep"), os.path.realpath(call["cwd"]))
        self.assertEqual(os.path.join(self.root, "src", "deep"), call["argv"][call["argv"].index("--cd") + 1])

    def test_an_absolute_path_inside_the_project_is_accepted(self):
        self.assertTrue(self.document("--root", os.path.join(self.root, "src"))["ok"])
        self.assertEqual(os.path.join(self.root, "src"), os.path.realpath(self.calls()[0]["cwd"]))

    def test_by_default_the_program_starts_in_the_project_root(self):
        self.assertTrue(self.document(cwd=os.path.join(self.root, "src"))["ok"])
        self.assertEqual(self.root, os.path.realpath(self.calls()[0]["cwd"]))


if __name__ == "__main__":
    unittest.main()
