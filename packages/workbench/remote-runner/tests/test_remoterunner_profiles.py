"""The `remote-runner` module's declaration and `profiles` command (conformance checklist items 1 and 2 of
`docs/specs/remote-runner.md`). Plan `2026-10-24-remote-runner-module`, increment B."""

import ast
import io
import json
import os
import sys
import unittest
import unittest.mock

import support_remote
from support_remote import FILE, VALID
from tests import support_install
from workbench import verify

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "remote-runner")
HELPERS = ("helper/remote-runner", "helper/remote-runner-check")


def declaration():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


def imports(path):
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add(node.module.split(".")[0])
    return found


def region(path):
    """The text between the two markers that fence the project-file rules in a helper."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    start = text.index("# --- the project file ---")
    end = text.index("# --- end of the project file ---")
    return text[start:end]


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("remote-runner",),
                                       harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("remote-runner", [m.name for m in result.modules])

    def test_it_is_a_plain_module_that_provides_requires_fills_and_writes_nothing(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        for field in ("provides", "requires", "fills", "writes", "slots", "blocks", "layout", "helpers"):
            self.assertNotIn(field, document)

    def test_it_ships_two_helpers_and_declares_the_command_and_the_check(self):
        document = declaration()
        self.assertEqual(sorted(HELPERS), sorted(document["ships"]))
        self.assertEqual({"remote-runner": {"helper": "helper/remote-runner", "runtime": "python", "kit": 1,
                                            "arguments": ["profiles", "recommend", "status", "artifacts",
                                                          "submit", "fetch", "fetch-overwrite"],
                                            "owner": ["fetch-overwrite"],
                                            "asks": ["submit", "fetch"]}}, document["commands"])
        self.assertEqual([{"helper": "helper/remote-runner-check", "kit": 1}], document["checks"])

    def test_it_asks_for_submit_and_fetch_and_fetch_overwrite_stays_owner_run(self):
        import types
        from workbench import declarations, harnessplan, harnessstage
        self.assertEqual(["submit", "fetch"], declaration()["commands"]["remote-runner"]["asks"])
        loaded = declarations.load_package(PACKAGE, first_party=True)
        module = [m for m in loaded.modules if m.name == "remote-runner"][0]
        self.assertEqual(("submit", "fetch"), module.commands[0].asks)
        self.assertEqual(("fetch-overwrite",), module.commands[0].owner)
        installed = [types.SimpleNamespace(module=module, type="module")]
        found = harnessstage.ask_rules(installed)
        self.assertEqual({"ask"}, {rule.action for rule in found})
        with open(os.path.join(PACKAGE, "claude", "module.json"), encoding="utf-8") as handle:
            layout = json.load(handle)["layout"]
        permissions = json.loads(harnessplan.render_permissions(
            harnessstage.owner_rules(installed) + found, layout, "/Users/tester/.config/project-workbench", "/Users/tester"))["permissions"]
        deny, ask = permissions["deny"], permissions["ask"]
        for text in ("wb run remote-runner submit", "wb run remote-runner submit *", "wb run remote-runner fetch",
                     "wb run remote-runner fetch *", "python3 -B -m workbench run remote-runner fetch *"):
            self.assertIn("Bash(%s)" % text, ask)
        for text in ("wb run remote-runner status", "wb run remote-runner profiles", "wb run remote-runner fetch-overwrite"):
            self.assertNotIn("Bash(%s)" % text, ask)
        self.assertIn("Bash(wb run remote-runner fetch-overwrite)", deny)

    def test_every_file_is_the_declaration_a_helper_or_the_skill(self):
        found = []
        for base, dirs, files in os.walk(MODULE):
            if base == MODULE:
                dirs.remove("tests")  # the module's own tests are not part of what it installs
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), MODULE))
        self.assertEqual(sorted(["module.json", *HELPERS, "harness/neutral/skills/run-remote-job/SKILL.md"]),
                         sorted(found))

    def test_the_package_lists_it(self):
        with open(os.path.join(PACKAGE, "package.json"), encoding="utf-8") as handle:
            self.assertIn("remote-runner", json.load(handle)["modules"])

    def test_the_helpers_import_the_standard_library_and_the_kit_and_no_network(self):
        allowed = set(sys.stdlib_module_names) | {"wbkit"}
        for helper in HELPERS:
            found = imports(os.path.join(MODULE, helper))
            self.assertLessEqual(found, allowed, helper)
            self.assertIn("tomllib", found, helper)
            self.assertFalse(found & {"socket", "urllib", "http", "ctypes", "shutil", "tempfile"}, helper)

    def test_only_the_command_helper_can_start_a_program(self):
        self.assertIn("subprocess", imports(os.path.join(MODULE, HELPERS[0])))
        self.assertNotIn("subprocess", imports(os.path.join(MODULE, HELPERS[1])))

    def test_the_two_helpers_carry_the_same_rules_for_the_project_file(self):
        self.assertEqual(region(os.path.join(MODULE, HELPERS[0])), region(os.path.join(MODULE, HELPERS[1])))


def changed(old, new):
    return VALID.replace(old, new)


BAD = {
    "not UTF-8": b"\xff\xfe\x00",
    "not TOML": "project = [",
    "arrays nested too deep for the reader": "x = " + "[" * 5000 + "]" * 5000,
    "a repeated key": VALID + '\n[project]\nid = "again"\n',
    "a repeated key in a table": changed('id = "project-workbench"', 'id = "a"\nid = "b"'),
    "an unknown top-level key": 'extra = 1\n' + VALID,
    "a table of another name": VALID + '\n[other]\nx = 1\n',
    "an unknown project key": changed('id = "project-workbench"', 'id = "a"\nname = "b"'),
    "no project": VALID.replace('[project]\nid = "project-workbench"\n', ""),
    "no project id": changed('id = "project-workbench"', ""),
    "a project id that is not a string": changed('"project-workbench"', "7"),
    "a project id with a leading dash": changed("project-workbench", "-a"),
    "a project id with a space": changed("project-workbench", "a b"),
    "a project id of 65 characters": changed("project-workbench", "a" * 65),
    "no profiles": '[project]\nid = "a"\n',
    "profiles that is not a table": '[project]\nid = "a"\nprofiles = 3\n',
    "an empty profiles table": '[project]\nid = "a"\n[profiles]\n',
    "a profile that is not a table": '[project]\nid = "a"\n[profiles]\nfast = "make"\n',
    "a profile name with a space": changed("[profiles.full]", '[profiles."bad name"]'),
    "a profile name with a leading dash": changed("[profiles.full]", '[profiles."-x"]'),
    "a profile name of 65 characters": changed("[profiles.full]", "[profiles.%s]" % ("a" * 65)),
    "an unknown profile key": changed('command = "make test-fast"', 'command = "make"\ncolour = 1'),
    "no command": '[project]\nid = "a"\n[profiles.fast]\nx = 1\n',
    "a profile with only requirements": '[project]\nid = "a"\n[profiles.fast.requirements]\nos = "linux"\n',
    "a command that is not a string": changed('"make test-fast"', "5"),
    "an empty command": changed('"make test-fast"', '""'),
    "a command with a newline": changed('"make test-fast"', '"make\\nrm -rf x"'),
    "a command with a tab": changed('"make test-fast"', '"make\\ttest"'),
    "a command with a non-ASCII letter": changed('"make test-fast"', '"make \\u00e9"'),
    "a command of 4097 characters": changed('"make test-fast"', '"%s"' % ("a" * 4097)),
    "requirements that is not a table": '[project]\nid = "a"\n[profiles.fast]\ncommand = "x"\nrequirements = 1\n',
    "an unknown requirement": changed("os = \"linux\"", 'gpu = "x"'),
    "os that is not a string": changed('os = "linux"', "os = 1"),
    "os of 65 characters": changed('os = "linux"', 'os = "%s"' % ("a" * 65)),
    "os with a non-ASCII letter": changed('os = "linux"', 'os = "lin\\u00fcx"'),
    "a zero core count": changed("min_cpu_cores = 4", "min_cpu_cores = 0"),
    "a negative core count": changed("min_cpu_cores = 4", "min_cpu_cores = -1"),
    "a core count that is a boolean": changed("min_cpu_cores = 4", "min_cpu_cores = true"),
    "a core count that is a string": changed("min_cpu_cores = 4", 'min_cpu_cores = "4"'),
    "an infinite core count": changed("min_cpu_cores = 4", "min_cpu_cores = inf"),
    "a core count that is not a number": changed("min_cpu_cores = 4", "min_cpu_cores = nan"),
    "a core count over a million": changed("min_cpu_cores = 4", "min_cpu_cores = 1000001"),
    "a memory size of zero": changed("min_memory_gib = 8", "min_memory_gib = 0"),
    "a memory size that is a boolean": changed("min_memory_gib = 8", "min_memory_gib = false"),
    "labels that is not a list": changed('labels = ["test"]', 'labels = "test"'),
    "33 labels": changed('labels = ["test"]', "labels = [%s]" % ", ".join('"l%d"' % i for i in range(33))),
    "a label that is not a string": changed('labels = ["test"]', "labels = [1]"),
    "a label with a leading dot": changed('labels = ["test"]', 'labels = [".x"]'),
    "a label with a space": changed('labels = ["test"]', 'labels = ["a b"]'),
    "a label of 65 characters": changed('labels = ["test"]', 'labels = ["%s"]' % ("a" * 65)),
    "65 profiles": '[project]\nid = "a"\n' + "".join('[profiles.p%d]\ncommand = "x"\n' % i for i in range(65)),
}


class Rules(support_remote.Project):
    def parse(self, data):
        return self.helper.parse_project_file(data if isinstance(data, bytes) else data.encode("utf-8"))

    def test_the_example_is_accepted_in_file_order_with_the_requirements_it_names(self):
        self.assertEqual({
            "project": "project-workbench",
            "profiles": [
                {"name": "fast", "command": "make test-fast",
                 "requirements": {"min_cpu_cores": 4, "min_memory_gib": 8, "labels": ["test"], "os": "linux"}},
                {"name": "full", "command": "python3 -B -W error tests/run_all.py", "requirements": {}}]},
            self.parse(VALID))

    def test_the_bounds_themselves_are_accepted(self):
        text = ('[project]\nid = "%s"\n' % ("a" * 64)
                + "".join('[profiles.p%d]\ncommand = "x"\n' % i for i in range(63))
                + '[profiles.%s]\ncommand = "%s"\n' % ("b" * 64, "c" * 4096)
                + '[profiles.%s.requirements]\nos = "%s"\narch = "x"\nmin_cpu_cores = 1000000\n'
                  'min_memory_gib = 0.5\nlabels = [%s]\n'
                  % ("b" * 64, "o" * 64, ", ".join('"%s"' % ("l" * 64) for _ in range(32))))
        found = self.parse(text)
        self.assertEqual(64, len(found["profiles"]))
        self.assertEqual({"os": "o" * 64, "arch": "x", "min_cpu_cores": 1000000, "min_memory_gib": 0.5,
                          "labels": ["l" * 64] * 32}, found["profiles"][-1]["requirements"])

    def test_each_refused_case_is_refused_with_a_reason_that_repeats_nothing_of_the_file(self):
        for label, data in BAD.items():
            with self.subTest(label):
                with self.assertRaises(self.helper.ProjectFileError) as caught:
                    self.parse(data)
                reason = str(caught.exception)
                self.assertTrue(reason and reason.isascii() and reason.isprintable() and len(reason) <= 200,
                                reason)

    def test_a_refusal_does_not_echo_a_value_the_file_holds(self):
        secret = "SECRET-MARKER"
        for text in (changed("make test-fast", "%s\\n" % secret), changed("[profiles.full]", '[profiles."%s x"]' % secret),
                     changed("project-workbench", "%s x" % secret), changed('"test"', '"%s x"' % secret),
                     changed('"linux"', '"%s \\u00e9"' % secret), '%s = 1\n' % secret,
                     VALID + '\n[%s]\nx = 1\n' % secret, "%s\n" % secret):
            with self.assertRaises(self.helper.ProjectFileError) as caught:
                self.parse(text)
            self.assertNotIn(secret, str(caught.exception))


class Command(support_remote.Project):
    def run_it(self, *args, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        code = self.helper.main(list(args), out, err, cwd or self.root)
        return code, out.getvalue(), err.getvalue()

    def test_profiles_prints_one_json_line(self):
        self.write(FILE, VALID)
        before = self.snapshot()
        code, out, err = self.run_it("profiles")
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.endswith("\n") and "\n" not in out[:-1])
        document = json.loads(out)
        self.assertEqual(["format", "project", "profiles"], list(document))
        self.assertEqual(1, document["format"])
        self.assertEqual("project-workbench", document["project"])
        self.assertEqual(["fast", "full"], [p["name"] for p in document["profiles"]])
        self.assertEqual(before, self.snapshot())

    def test_it_works_from_a_folder_below_the_project_root(self):
        self.write(FILE, VALID)
        code, out, err = self.run_it("profiles", cwd=os.path.join(self.root, "sub"))
        self.assertEqual((0, ""), (code, err))

    def test_an_absent_file_is_refused_with_the_reason(self):
        code, out, err = self.run_it("profiles")
        self.assertEqual((1, ""), (code, out))
        self.assertEqual("refused: no project file (.workbench/remote-runner.toml)\n", err)

    def test_a_folder_outside_a_project_is_refused(self):
        code, out, err = self.run_it("profiles", cwd=self.base)
        self.assertEqual((1, ""), (code, out))
        self.assertTrue(err.startswith("refused: "), err)

    def test_a_link_an_oversize_file_and_a_directory_are_refused_and_change_nothing(self):
        outside = os.path.join(self.base, "outside.toml")
        with open(outside, "w") as handle:
            handle.write(VALID)
        full = os.path.join(self.root, *FILE.split("/"))
        cases = {
            "a link": lambda: os.symlink(outside, full),
            "a directory": lambda: os.mkdir(full),
            "a file over 65,536 bytes": lambda: self.write(FILE, VALID + "#" * (65536 - len(VALID) + 1)),
        }
        for label, make in cases.items():
            with self.subTest(label):
                make()
                before = self.snapshot()
                code, out, err = self.run_it("profiles")
                self.assertEqual((1, ""), (code, out))
                self.assertTrue(err.startswith("refused: ") and err.count("\n") == 1, err)
                self.assertEqual(before, self.snapshot())
                if os.path.islink(full) or os.path.isfile(full):
                    os.unlink(full)
                else:
                    os.rmdir(full)

    def test_a_file_of_exactly_the_bound_is_read(self):
        self.write(FILE, VALID + "#" * (65536 - len(VALID)))
        self.assertEqual(65536, os.path.getsize(os.path.join(self.root, *FILE.split("/"))))
        self.assertEqual(0, self.run_it("profiles")[0])

    def test_a_refused_file_is_reported_without_its_content(self):
        self.write(FILE, VALID + "\nSECRET-MARKER = 1\n")
        before = self.snapshot()
        code, out, err = self.run_it("profiles")
        self.assertEqual((1, ""), (code, out))
        self.assertTrue(err.startswith("refused: "))
        self.assertNotIn("SECRET-MARKER", err)
        self.assertEqual(before, self.snapshot())

    def test_any_other_argument_list_is_refused(self):
        self.write(FILE, VALID)
        for args in ((), ("profiles", "x"), ("profiles", "--all"), ("log", "j"), ("cancel",), ("remotes",),
                     ("prune",), ("PROFILES",), ("",)):
            with self.subTest(args):
                code, out, err = self.run_it(*args)
                self.assertEqual((1, ""), (code, out))
                self.assertTrue(err.startswith("refused: usage: remote-runner "), err)

    def test_a_program_of_the_same_name_on_the_path_is_never_started(self):
        outside = os.path.join(self.base, "outside")
        os.mkdir(outside)
        marker = os.path.join(outside, "ran")
        program = os.path.join(outside, "remote-runner")
        with open(program, "w") as handle:
            handle.write("#!/bin/sh\necho ran >> %s\n" % marker)
        os.chmod(program, 0o755)
        self.write(FILE, VALID)
        with unittest.mock.patch.dict(os.environ, {"PATH": outside + os.pathsep + os.environ.get("PATH", "")}):
            self.assertEqual(0, self.run_it("profiles")[0])
            self.assertEqual(1, self.run_it("profiles", "x")[0])
        self.assertFalse(os.path.exists(marker))


if __name__ == "__main__":
    unittest.main()
