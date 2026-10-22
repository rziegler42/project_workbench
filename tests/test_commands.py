"""``commands.resolve``: from a working directory, a command name and arguments to a launch request.

The resolver only reads. Every refusal is decided before any helper starts, and a patched launcher
proves that nothing in this file starts one."""

import json
import os
import unittest
import unittest.mock

from tests import support_project
from tests.support_project import HELPER_PATH, tool
from workbench import commands, hashing, launch, manifest


class Resolver(support_project.Project):
    def setUp(self):
        support_project.Project.setUp(self)
        for patched in (unittest.mock.patch.object(launch, "launch"),
                        unittest.mock.patch("subprocess.run")):
            mocked = patched.start()
            mocked.side_effect = AssertionError("the resolver started a program")
            self.addCleanup(patched.stop)

    def resolve(self, name="tool", args=("check",), start=None):
        return commands.resolve(self.guarded, start or self.real, name, list(args))

    def refused(self, contains, *args, **kwargs):
        with self.assertRaises(commands.CommandError) as caught:
            self.resolve(*args, **kwargs)
        self.assertIn(contains, str(caught.exception))
        return str(caught.exception)

    def module_json(self, name="tool"):
        return ".workbench/p/%s/module.json" % name

    def rewrite_declaration(self, change):
        """Edit the tool command's declaration in module.json and make the manifest agree, as a
        hostile commit could."""
        rel = self.module_json()
        declaration = json.loads(self.read(rel))
        change(declaration["commands"]["tool"])
        self.edit(rel, lambda data: json.dumps(declaration).encode())
        document = manifest.parse(self.read(".workbench/manifest.json"))
        for package in document["packages"]:
            for item in package["modules"]:
                if item["name"] == "tool":
                    item["declaration"] = hashing.declaration_hash(declaration)
        self.edit(".workbench/manifest.json", lambda data: manifest.serialize(document))


class Resolved(Resolver):
    def test_a_pinned_command_resolves_to_a_request(self):
        self.ready()
        self.pin()
        found = self.resolve("tool", ["check", "--x", "-y"])
        self.assertEqual(self.real, found.root)
        self.assertEqual(self.project_id, found.project_id)
        self.assertEqual("tool", found.name)
        self.assertEqual(["check", "--x", "-y"], found.arguments)
        self.assertIsNone(found.kit)

    def test_the_project_id_comes_from_the_manifest_that_was_parsed(self):
        self.ready()
        self.pin()
        with unittest.mock.patch.object(commands.project, "read_id",
                                        side_effect=AssertionError("read the manifest twice")):
            self.assertEqual(self.project_id, self.resolve().project_id)

    def test_it_resolves_from_a_directory_below_the_root(self):
        self.ready()
        self.pin()
        below = os.path.join(self.real, "docs", "deep")
        os.makedirs(below)
        self.assertEqual(self.real, self.resolve(start=below).root)

    def test_a_python_command_carries_its_kit_number(self):
        self.MODULES = dict(self.MODULES, tool=tool(
            {"tool": {"helper": HELPER_PATH, "runtime": "python", "kit": 1,
                      "arguments": ["check"]}}))
        self.ready()
        self.pin(kit=1)
        self.assertEqual(1, self.resolve().kit)

    def test_a_command_with_no_arguments_list_takes_none(self):
        self.MODULES = dict(self.MODULES, tool=tool({"tool": {"helper": HELPER_PATH}}))
        self.ready()
        self.pin()
        self.assertEqual([], self.resolve(args=[]).arguments)
        self.refused("takes no argument", args=["check"])

    def test_the_arguments_after_the_first_are_not_inspected(self):
        self.ready()
        self.pin()
        rest = ["report", "--", "-rf", "", "a b"]
        self.assertEqual(rest, self.resolve(args=rest).arguments)


class Refused(Resolver):
    def test_an_undeclared_first_argument(self):
        self.ready()
        self.pin()
        self.refused("is not an argument of", args=["delete"])

    def test_a_missing_first_argument(self):
        self.ready()
        self.pin()
        self.refused("needs one of", args=[])

    def test_an_unknown_command(self):
        self.ready()
        self.pin("other")
        self.refused("no installed module declares", "other")

    def test_a_name_that_is_not_a_command_name(self):
        self.ready()
        for name in ("", "../tool", "-tool", "to ol", "t" * 65):
            self.refused("", name)

    def test_an_unpinned_helper(self):
        self.ready()
        self.unpin("tool")
        self.refused("its owner pins")

    def test_a_pin_that_records_another_path(self):
        self.ready()
        self.pin(path="docs/README.md")
        self.refused("not the declared helper")

    def test_a_pin_that_records_a_helper_of_another_module(self):
        self.MODULES = dict(self.MODULES, other=tool({"other": {"helper": HELPER_PATH}}))
        self.ready()
        self.pin(path=self.installed("other"))
        self.refused("not the declared helper")

    def test_a_pin_that_records_no_kit_for_a_python_command(self):
        self.MODULES = dict(self.MODULES, tool=tool(
            {"tool": {"helper": HELPER_PATH, "runtime": "python", "kit": 1,
                      "arguments": ["check"]}}))
        self.ready()
        self.pin()
        self.refused("kit")

    def test_a_pin_that_records_a_kit_the_declaration_lacks(self):
        self.ready()
        self.pin(kit=1)
        self.refused("kit")

    def test_a_pin_that_records_another_kit_number(self):
        self.MODULES = dict(self.MODULES, tool=tool(
            {"tool": {"helper": HELPER_PATH, "runtime": "python", "kit": 1,
                      "arguments": ["check"]}}))
        self.ready()
        self.pin(kit=2)
        self.refused("kit")

    def test_a_commit_that_rewrites_the_declaration_and_manifest_to_exec_is_refused(self):
        """The case the security review found: the pin, not the project, says how it runs."""
        self.MODULES = dict(self.MODULES, tool=tool(
            {"tool": {"helper": HELPER_PATH, "runtime": "python", "kit": 1,
                      "arguments": ["check"]}}))
        self.ready()
        self.pin(kit=1)
        self.rewrite_declaration(lambda command: (command.pop("runtime"), command.pop("kit")))
        self.refused("kit")

    def test_outside_a_project(self):
        self.ready()
        self.pin()
        self.refused("not inside a workbench project", start=self.outside)

    def test_a_module_the_manifest_does_not_record(self):
        self.ready()
        self.pin("ghost", path=self.installed("ghost"), data=b"x")
        ghost = os.path.join(self.real, ".workbench", "p", "ghost")
        os.makedirs(ghost)
        with open(os.path.join(ghost, "module.json"), "wb") as handle:
            handle.write(self.read(self.module_json()))
        self.refused("no installed module declares", "ghost")

    def test_an_installed_declaration_that_no_longer_matches_the_manifest(self):
        self.ready()
        self.pin()
        self.edit(self.module_json(), lambda data: data.replace(b'"report"', b'"report", "evil"'))
        self.refused("changed since it was installed")

    def test_a_declaration_that_is_not_json(self):
        self.ready()
        self.pin()
        self.edit(self.module_json(), lambda data: b"{")
        self.refused("module.json")

    def test_a_declaration_that_is_a_symbolic_link(self):
        self.ready()
        self.pin()
        full = os.path.join(self.real, *self.module_json().split("/"))
        copy = os.path.join(self.outside, "module.json")
        os.rename(full, copy)
        os.symlink(copy, full)
        self.refused("module.json")

    def test_a_declaration_that_cannot_be_read(self):
        self.ready()
        self.pin()
        full = os.path.join(self.real, *self.module_json().split("/"))
        os.chmod(full, 0)
        self.addCleanup(os.chmod, full, 0o600)
        if os.access(full, os.R_OK):
            self.skipTest("this account reads files regardless of their mode")
        self.refused("module.json")

    def test_a_module_the_manifest_records_whose_declaration_file_is_gone(self):
        self.ready()
        self.pin()
        os.unlink(os.path.join(self.real, *self.module_json().split("/")))
        self.refused("module.json")

    def test_a_manifest_that_cannot_be_used(self):
        self.ready()
        self.pin()
        self.edit(".workbench/manifest.json", lambda data: data + b" ")
        self.refused("manifest")

    def test_a_command_that_two_modules_declare(self):
        self.ready()
        self.pin()
        real = commands._declared
        twice = lambda *args: real(*args) + real(*args)
        with unittest.mock.patch.object(commands, "_declared", twice):
            self.refused("more than one")


if __name__ == "__main__":
    unittest.main()
