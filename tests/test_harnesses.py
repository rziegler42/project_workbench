"""The harnesses the workbench knows, and what `wb check` takes from them.

Every harness here is a synthetic module of a synthetic distribution, with made-up names and paths, so the
tests prove the mechanism without any shipped module being present."""

import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

from tests import support
from workbench import (__version__, check, declarations, firstparty, harnesses, layout, localmanifest, manifest, projectfs,
                       target)

DEMO = {
    "root": {"file": "DEMO.md", "import": "AGENTS.md"},
    "kinds": {"skill": {"path": ".demo/skills/{name}/SKILL.md",
                        "fields": {"name": "name", "description": "description"}}},
    "hooks": "none",
    "exclude": ["DEMO.md", ".demo/"],
    "tolerated": [".demo/shared.json", ".demo/skills/keep.json", ".demo/skills/cache",
                 ".demo/nested/cfg.json"],
}
OTHER = {
    "root": {"file": "OTHER.md", "import": "AGENTS.md"},
    "kinds": {"command": {"path": ".other/commands/{name}.md",
                          "fields": {"name": "name", "description": "description"}}},
    "hooks": "none",
    "exclude": ["OTHER.md", ".other/"],
}
TOP = {
    "kinds": {"skill": {"path": "tskills/{name}/SKILL.md",
                        "fields": {"name": "name", "description": "description"}}},
    "hooks": "none",
    "exclude": ["tskills/"],
}
PLAIN = {"name": "plain", "version": "0.1.0", "description": "A module that is not a harness."}


def harness(name, document, provides):
    return {"name": name, "version": "0.1.0", "type": "harness", "description": "A %s harness." % name,
            "provides": provides, "layout": document}


def write_package(dist, name, modules, directory=None):
    """`modules` maps a module name to its declaration."""
    root = os.path.join(dist, "packages", directory or name)
    os.makedirs(root)
    with open(os.path.join(root, "package.json"), "w") as handle:
        json.dump({"name": name, "version": "0.1.0", "contract": 1, "modules": sorted(modules)}, handle)
    for module, declaration in modules.items():
        os.makedirs(os.path.join(root, module))
        with open(os.path.join(root, module, "module.json"), "w") as handle:
            json.dump(declaration, handle)
    return root


class Distribution(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.dist = os.path.join(self.base, "dist")
        os.makedirs(os.path.join(self.dist, "workbench"))

    def package(self, name="pkg", modules=None, **kwargs):
        return write_package(self.dist, name, modules if modules is not None else {
            "demo": harness("demo", DEMO, ["instructions", "skills"]),
            "other": harness("other", OTHER, ["instructions", "commands"]), "plain": PLAIN}, **kwargs)

    def release(self):
        firstparty.release_approvals(self.dist)


class Known(Distribution):
    def test_the_layouts_are_the_verified_ones(self):
        self.assertEqual([], layout.problems(DEMO))
        self.assertEqual([], layout.problems(OTHER))

    def test_each_first_party_harness_module_gives_its_facts_and_a_plain_module_gives_none(self):
        self.package()
        self.release()
        self.assertEqual({"demo": layout.facts(DEMO), "other": layout.facts(OTHER)},
                         harnesses.known(self.dist))
        self.assertEqual(("DEMO.md", ".demo"), harnesses.known(self.dist)["demo"]["roots"])
        self.assertEqual((".demo/skills",), harnesses.known(self.dist)["demo"]["generated"])

    def test_a_package_with_no_shipped_record_is_not_known(self):
        self.package()
        self.assertEqual({}, harnesses.known(self.dist))

    def test_a_first_party_package_changed_since_release_is_not_known(self):
        root = self.package()
        self.release()
        with open(os.path.join(root, "plain", "extra.txt"), "w") as handle:
            handle.write("x")
        self.assertEqual({}, harnesses.known(self.dist))

    def test_a_package_that_changes_after_it_is_loaded_is_not_known(self):
        root = self.package()
        self.release()
        real = declarations.load_package

        def load_then_change(path, first_party=False):
            loaded = real(path, first_party=first_party)
            with open(os.path.join(root, "plain", "extra.txt"), "w") as handle:
                handle.write("x")
            return loaded

        with unittest.mock.patch.object(declarations, "load_package", load_then_change):
            self.assertEqual({}, harnesses.known(self.dist))

    def test_a_link_to_a_package_is_not_known_and_does_not_hide_the_real_one(self):
        root = self.package()
        self.release()
        os.symlink(root, os.path.join(self.dist, "packages", "linked"))
        self.assertEqual({"demo", "other"}, set(harnesses.known(self.dist)))
        shutil.rmtree(root)
        self.assertEqual({}, harnesses.known(self.dist))

    def test_a_package_whose_name_differs_from_its_directory_is_not_known(self):
        root = self.package()
        self.release()
        shutil.copytree(root, os.path.join(self.dist, "packages", "copy"))
        self.assertEqual({"demo", "other"}, set(harnesses.known(self.dist)))
        shutil.rmtree(root)
        self.assertEqual({}, harnesses.known(self.dist))

    def test_a_layout_that_does_not_verify_is_not_known(self):
        self.package()
        self.release()
        with unittest.mock.patch.object(layout, "problems", lambda document: ["broken"]):
            self.assertEqual({}, harnesses.known(self.dist))

    def test_no_packages_directory_and_an_empty_one_give_none(self):
        self.assertEqual({}, harnesses.known(self.dist))
        os.makedirs(os.path.join(self.dist, "packages"))
        self.assertEqual({}, harnesses.known(self.dist))

    def test_a_file_among_the_packages_does_not_hide_the_harnesses(self):
        self.package()
        self.release()
        with open(os.path.join(self.dist, "packages", "README"), "w") as handle:
            handle.write("x")
        self.assertEqual({"demo", "other"}, set(harnesses.known(self.dist)))

    def test_a_package_that_does_not_load_is_not_known(self):
        self.package()
        self.release()
        real = declarations.load_package
        error = declarations.DeclarationError("package", "pkg", "x", "y")
        with unittest.mock.patch.object(
                declarations, "load_package",
                lambda *args, **kwargs: real(*args, **kwargs)._replace(problems=[error])):
            self.assertEqual({}, harnesses.known(self.dist))

    def test_an_unreadable_packages_directory_gives_none(self):
        self.package()
        self.release()
        with unittest.mock.patch.object(os, "listdir", side_effect=PermissionError("no")):
            self.assertEqual({}, harnesses.known(self.dist))

    def test_a_name_two_packages_declare_is_refused_and_the_others_stay(self):
        self.package()
        again = harness("demo", DEMO, ["instructions", "skills"])
        again["description"] = "The same name in another package."
        self.package("second", {"demo": again})
        self.release()
        loaded = harnesses.load(self.dist)
        self.assertEqual({"other"}, set(loaded.found))
        self.assertEqual(("demo",), loaded.refused)


class Project(Distribution):
    """A project directory with the files of one attached harness, in a real git repository."""

    def setUp(self):
        Distribution.setUp(self)
        support.forbid_real_store(self)
        self.place = os.path.join(self.base, "project")
        os.makedirs(self.place)
        self.store_root = os.path.join(self.base, "store")
        self.git("init", "-q", "--template=")
        self.write(".workbench/manifest.json", manifest.serialize({
            "base": "0" * 64, "files": [], "packages": [], "seed": manifest.new_seed(), "version": 1,
            "workbench": __version__}))

    def git(self, *args):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        done = subprocess.run(["git"] + list(args), cwd=self.place, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        self.assertEqual(0, done.returncode, done.stderr)

    def write(self, rel, data=b"x\n"):
        full = os.path.join(self.place, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data)

    def attach(self, name, paths):
        """Write `paths` and the scratch record that attach would have written for them."""
        files = []
        for rel in paths:
            data = ("generated " + rel + "\n").encode()
            self.write(rel, data)
            files.append({"hash": hashlib.sha256(data).hexdigest(), "path": rel})
        files.sort(key=lambda item: item["path"])
        self.write(localmanifest.PATH, localmanifest.serialize({
            "files": files, "format": 1, "harness": name, "module_version": "0.1.0",
            "source": "local:pkg", "tree": "0" * 64, "workbench": __version__}))

    def examine(self):
        with target.open_target(self.place, self.store_root, home=self.base) as held:
            return check.examine(projectfs.Writer(held), self.dist)

    def command(self):
        out, err = io.StringIO(), io.StringIO()
        guarded = unittest.mock.Mock(root=self.store_root)
        with unittest.mock.patch.object(check.checks, "run_all", lambda *args: ()):
            code = check.run(guarded, check.Command(self.place), out, err, self.dist)
        return code, out.getvalue(), err.getvalue()


DEMO_FILES = ["DEMO.md", ".demo/skills/sample/SKILL.md"]


class Checked(Project):
    def setUp(self):
        Project.setUp(self)
        self.package()
        self.release()

    def test_a_clean_project_has_no_problem_and_no_warning(self):
        self.attach("demo", DEMO_FILES)
        report = self.examine()
        self.assertEqual(("demo", [], []), (report.harness, report.problems, report.warnings))

    def test_a_file_below_a_generated_directory_that_attach_did_not_write_is_a_problem(self):
        self.attach("demo", DEMO_FILES)
        self.write(".demo/skills/other/SKILL.md")
        self.assertEqual([".demo/skills/other/SKILL.md: not a file attach wrote"],
                         self.examine().problems)

    def test_a_kind_directory_at_the_top_is_scanned_for_strays_and_not_for_entries_beside_it(self):
        self.package("toppkg", {"top": harness("top", TOP, ["skills"])})
        self.release()
        self.attach("top", ["tskills/a/SKILL.md"])
        self.assertEqual(([], []), (self.examine().problems, self.examine().warnings))
        self.write("tskills/b/SKILL.md")
        self.assertEqual(["tskills/b/SKILL.md: not a file attach wrote"], self.examine().problems)

    def test_a_tolerated_path_below_a_generated_directory_is_not_a_stray(self):
        self.attach("demo", DEMO_FILES)
        self.write(".demo/skills/keep.json")
        report = self.examine()
        self.assertEqual(([], []), (report.problems, report.warnings))

    def test_everything_below_a_tolerated_directory_is_not_a_stray(self):
        self.attach("demo", DEMO_FILES)
        self.write(".demo/skills/cache/deep/file.bin")
        self.write(".demo/skills/cached/file.bin")
        self.assertEqual([".demo/skills/cached/file.bin: not a file attach wrote"],
                         self.examine().problems)

    def test_an_unknown_entry_beside_a_tolerated_one_warns_and_the_tolerated_ones_do_not(self):
        self.attach("demo", DEMO_FILES)
        self.write(".demo/shared.json")
        self.write(".demo/nested/cfg.json")
        self.write(".demo/hooks/x.sh")
        report = self.examine()
        self.assertEqual([], report.problems)
        self.assertEqual([".demo/hooks: not written by attach; the harness may run or read it"],
                         report.warnings)

    def test_a_name_beside_a_tolerated_one_is_not_excused(self):
        self.attach("demo", DEMO_FILES)
        self.write(".demo/shared.json.bak")
        self.assertEqual([".demo/shared.json.bak: not written by attach; the harness may run or read it"],
                         self.examine().warnings)

    def test_a_file_of_another_known_harness_is_a_problem_beside_an_attached_one(self):
        self.attach("demo", DEMO_FILES)
        self.write("OTHER.md")
        os.mkdir(os.path.join(self.place, ".other"))
        self.assertEqual(["OTHER.md belongs to the harness other, not to the attached demo",
                          ".other belongs to the harness other, not to the attached demo"],
                         self.examine().problems)

    def test_a_file_of_a_known_harness_beside_none_attached_is_a_warning(self):
        self.write("OTHER.md")
        report = self.examine()
        self.assertEqual((None, []), (report.harness, report.problems))
        self.assertEqual(["OTHER.md belongs to the harness other, and no harness is attached to this "
                          "clone"], report.warnings)

    def test_a_harness_the_workbench_does_not_know_gets_one_warning_and_no_scan(self):
        self.attach("gone", ["GONE.md"])
        self.write(".demo/skills/other/SKILL.md")
        report = self.examine()
        self.assertEqual(["gone is not a harness this workbench knows, so its files were not scanned"],
                         report.warnings)
        self.assertEqual([".demo belongs to the harness demo, not to the attached gone"],
                         report.problems)

    def test_an_ambiguous_harness_name_is_reported_as_such(self):
        again = harness("demo", DEMO, ["instructions", "skills"])
        again["description"] = "The same name in another package."
        self.package("second", {"demo": again})
        self.release()
        self.attach("demo", DEMO_FILES)
        warnings = self.examine().warnings
        self.assertEqual(["demo is declared by more than one first-party package, so its files were "
                          "not scanned"], warnings)

    def test_tracked_output_of_a_known_harness_is_a_problem(self):
        self.attach("demo", DEMO_FILES)
        self.write("OTHER.md")
        self.write(".other/commands/x.md")
        self.git("add", "-f", "--", "OTHER.md", ".other/commands/x.md", "DEMO.md")
        found = self.examine().problems
        for path, harness_ in (("OTHER.md", "other"), (".other/commands/x.md", "other"),
                               ("DEMO.md", "demo")):
            self.assertIn("%s: tracked by git, but it looks like output of the harness %s"
                          % (path, harness_), found)

    def test_a_document_pointing_into_a_known_harness_directory_is_a_problem(self):
        self.attach("demo", DEMO_FILES)
        self.write("README.md", b"[notes](.other/notes.md)\n")
        self.git("add", "-f", "--", "README.md")
        self.assertIn("README.md: points to .other/notes.md, which git does not track",
                      self.examine().problems)

    def test_the_command_reports_the_harness_and_uses_the_given_distribution(self):
        self.attach("demo", DEMO_FILES)
        self.write(".demo/skills/other/SKILL.md")
        code, out, err = self.command()
        self.assertEqual(1, code)
        self.assertIn("harness: demo attached in", out)
        self.assertIn("problem: .demo/skills/other/SKILL.md: not a file attach wrote", err)

    def test_with_no_packages_nothing_is_scanned_and_the_attached_harness_is_unknown(self):
        shutil.rmtree(os.path.join(self.dist, "packages"))
        self.attach("demo", DEMO_FILES)
        self.write("OTHER.md")
        report = self.examine()
        self.assertEqual([], report.problems)
        self.assertEqual(["demo is not a harness this workbench knows, so its files were not scanned"],
                         report.warnings)


if __name__ == "__main__":
    unittest.main()
