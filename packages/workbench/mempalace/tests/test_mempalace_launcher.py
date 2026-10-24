"""`mempalace` through the launcher: installed as a first-party module and pinned, then run (criterion 8 of plan
`2026-10-24-mempalace-module`, increment B). The program is a fake; no test starts a real `mempalace`, so every
`PATH` here holds only the fake and a `python3` link.

The package tree hash changes with this module, so the shipped approvals are stale until increment E of that plan.
The installs here run against a copy of the package in a temporary distribution whose approvals
`release_approvals` records in that copy."""

import io
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

from tests import support_install
from workbench import commands, firstparty, launch, pins
from workbench.wbkit import project

import support_mempalace

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "mempalace")
HELPER = "helper/mempalace"
SELECT = ("claude", "mempalace")


def real_helper():
    with open(os.path.join(MODULE, HELPER), "rb") as handle:
        return handle.read()


class Launcher(support_install.InstallBase):
    """Install the real module into an empty project, as a released copy of the package, and run it."""

    def setUp(self):
        support_install.InstallBase.setUp(self)
        self.dist = os.path.join(self.root, "dist")
        shutil.copytree(os.path.join(ROOT, "packages"), os.path.join(self.dist, "packages"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(ROOT, "base"), os.path.join(self.dist, "base"))
        os.makedirs(os.path.join(self.dist, "workbench"))
        done = firstparty.release_approvals(self.dist)
        self.assertEqual(1, done.packages)
        self.package_path = os.path.join(self.dist, "packages", "workbench")
        self.assertTrue(firstparty.is_first_party(self.package_path, self.dist))
        self.home = os.path.join(self.root, "home")
        os.makedirs(os.path.dirname(os.path.join(self.home, *self.MODEL)))
        with open(os.path.join(self.home, *self.MODEL), "w") as handle:
            handle.write("model")
        self.vendor = os.path.join(self.root, "fakes", "vendor")
        self.tools = os.path.join(self.root, "fakes", "tools")
        for folder in (self.vendor, self.tools):
            os.makedirs(folder)
        script = os.path.join(self.vendor, "mempalace")
        with open(script, "w") as handle:
            handle.write(support_mempalace.FAKE.format(python=sys.executable))
        os.chmod(script, 0o755)
        os.symlink(sys.executable, os.path.join(self.tools, "python3"))
        self.control(stdout=support_mempalace.RESULT)

    MODEL = (".cache", "chroma", "onnx_models", "all-MiniLM-L6-v2", "onnx", "model.onnx")

    def control(self, **fields):
        import json
        with open(os.path.join(self.vendor, "control.json"), "w") as handle:
            json.dump(fields, handle)

    def calls(self):
        import json
        try:
            with open(os.path.join(self.vendor, "calls.jsonl")) as handle:
                return [json.loads(line) for line in handle]
        except FileNotFoundError:
            return []

    def install(self, place, select=SELECT):
        from workbench import install, sources
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(self.package_path, None)], list(select))
        code = install.run(self.guarded, command, support_install.Typist(out, support_install.correct),
                           out, err, distribution=self.dist, seed=support_install.SEED, home=self.home)
        return code, out.getvalue(), err.getvalue()

    def helper_run(self, place, *arguments):
        """``(code, standard output, standard error)`` of the pinned helper, run from `place` with only the fakes on
        its `PATH` and a `HOME` whose model is cached."""
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        os.chdir(place)
        with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            with unittest.mock.patch.dict(os.environ, {"PATH": os.pathsep.join([self.vendor, self.tools]),
                                                       "HOME": self.home}):
                code = launch.launch(self.guarded, project.read_id(place), "mempalace", os.path.realpath(place),
                                     list(arguments), stdin=stdin, stdout=out, stderr=err)
            out.seek(0)
            err.seek(0)
            return code, out.read().decode(), err.read().decode()

    def test_the_helper_lands_in_the_module_namespace_byte_for_byte(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        self.assertEqual(real_helper(), self.read(place, ".workbench", "workbench", "mempalace", "helper",
                                                  "mempalace"))

    def test_install_pins_the_helper_through_the_kit_for_the_new_command(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        pin = pins.lookup(self.guarded, project.read_id(place), "mempalace")
        self.assertEqual((".workbench/workbench/mempalace/" + HELPER, "workbench install", 1),
                         (pin.path, pin.pinned_by, pin.kit))
        self.assertEqual(pins.hash_bytes(real_helper()), pin.sha256)

    def test_the_installed_and_pinned_helper_answers_a_status_and_a_search(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        code, shown, err = self.helper_run(place, "status")
        self.assertEqual(("", 0), (err, code), shown)
        self.assertIn(support_mempalace.RESULT.strip("\n"), shown)
        self.assertTrue(shown.startswith("<<recalled-data "))
        code, shown, err = self.helper_run(place, "search", "--wing", "proj", "--", "why SQLite")
        self.assertEqual(("", 0), (err, code), shown)
        self.assertEqual(["status"], self.calls()[0]["argv"])
        self.assertEqual(["search", "--results", "5", "--wing", "proj", "--", "why SQLite"], self.calls()[1]["argv"])

    def test_another_argument_is_refused_by_the_launcher_and_the_program_is_not_started(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        for argument in ("mine", "init", "wake-up", "--help", "serve", "sweep"):
            errors = io.StringIO()
            self.assertEqual(1, commands.run(self.guarded, ["mempalace", argument], errors, cwd=place))
            self.assertIn("is not an argument of the command", errors.getvalue())
        self.assertEqual([], self.calls())

    def test_a_capability_the_module_does_not_provide_is_refused_by_the_launcher(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        errors = io.StringIO()
        self.assertEqual(1, commands.run(self.guarded, ["--provides", "commit", "mempalace", "status"], errors,
                                         cwd=place))
        self.assertIn("does not provide commit", errors.getvalue())
        self.assertEqual([], self.calls())

    def test_an_edited_helper_is_refused_and_nothing_is_started(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        with open(os.path.join(place, ".workbench", "workbench", "mempalace", *HELPER.split("/")), "ab") as handle:
            handle.write(b"\n# edited\n")
        with self.assertRaises(launch.LaunchError) as caught:
            self.helper_run(place, "status")
        self.assertIn("has changed since it was pinned", str(caught.exception))
        self.assertEqual([], self.calls())

    def test_the_module_writes_only_its_declaration_and_its_helper_and_names_no_project_path(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        found = sorted(os.path.relpath(os.path.join(base, name), place)
                       for base, _, files in os.walk(place) if ".git" not in base.split(os.sep)
                       for name in files if "mempalace" in os.path.join(base, name).lower())
        self.assertEqual([".workbench/workbench/mempalace/helper/mempalace",
                          ".workbench/workbench/mempalace/module.json"], found)


if __name__ == "__main__":
    unittest.main()
