"""``settings``: the checkpoint and cap values that apply to the project.

The project and its process module are synthetic: the module declares checkpoint and cap names the installer
under test knows nothing about, and the command only reads the declaration and the owner's settings."""

import hashlib
import io
import json
import os
import unittest
import unittest.mock

from tests import support_project
from tests.support_project import tool
from workbench import approvalcmd, cli, commands, manifest, rules, settingscmd

CHECKPOINTS = ["approve-plan", "beta"]
CAPS = [{"name": "rounds", "default": 3, "ceiling": 5}, {"name": "tries", "default": 1, "ceiling": 2}]
CHECKPOINT_LINES = "checkpoint approve-plan: stop\ncheckpoint beta: stop\n"
DEFAULTS = CHECKPOINT_LINES + "cap rounds: 3\ncap tries: 1\nlevel approve-plan: block\nlevel beta: block\n"


def process_module(**fields):
    module, files = tool()
    module.update(type="process", checkpoints=CHECKPOINTS, caps=CAPS)
    module.update(fields)
    return module, files


def snapshot(top):
    found = {}
    for base, dirs, files in os.walk(top):
        for name in dirs:
            found[os.path.relpath(os.path.join(base, name), top)] = "dir"
        for name in files:
            full = os.path.join(base, name)
            with open(full, "rb") as handle:
                found[os.path.relpath(full, top)] = (hashlib.sha256(handle.read()).hexdigest(),
                                                     os.stat(full).st_mtime_ns)
    return found


class Settings(support_project.Project):
    INSTALL = True

    def setUp(self):
        support_project.Project.setUp(self)
        if self.INSTALL:
            self.use()

    def use(self, **fields):
        """Install the project with a process module that declares the checkpoints and caps above, changed by `fields`."""
        self.MODULES = dict(support_project.Project.MODULES, tool=process_module(**fields))
        self.ready()

    def owner(self, document):
        self.guarded.write("settings", json.dumps(document).encode("utf-8"))

    def settings(self, *tokens, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        code = settingscmd.run(self.guarded, list(tokens), out, err, cwd=cwd or self.real)
        return code, out.getvalue(), err.getvalue()

    def refused(self, contains, **kwargs):
        code, out, err = self.settings(**kwargs)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        return err


class Printed(Settings):
    def test_the_defaults_print_with_every_checkpoint_stopping(self):
        self.assertEqual((0, DEFAULTS, ""), self.settings())

    def test_it_runs_from_a_directory_below_the_root(self):
        below = os.path.join(self.real, "docs", "deep")
        os.makedirs(below)
        self.assertEqual((0, DEFAULTS, ""), self.settings(cwd=below))

    def test_the_owners_values_apply(self):
        self.owner({"version": 1, "checkpoints": {"approve-plan": "delegate"}, "caps": {"rounds": 5, "tries": 2}})
        self.assertEqual((0, "checkpoint approve-plan: delegate\ncheckpoint beta: stop\ncap rounds: 5\ncap tries: 2\n"
                                "level approve-plan: delegated\nlevel beta: block\n", ""),
                         self.settings())

    def test_delegate_takes_effect_for_approve_plan_only(self):
        self.owner({"version": 1, "checkpoints": {"beta": "delegate"}})
        code, out, err = self.settings()
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.startswith("checkpoint approve-plan: stop\ncheckpoint beta: stop\n"), out)
        self.assertIn("settings: settings set the checkpoint beta to delegate; delegation has no effect for it, "
                      "so it stops\n", out)

    def test_anything_but_exactly_delegate_stops(self):
        self.owner({"version": 1, "checkpoints": {"approve-plan": "Delegate", "beta": "yes"}})
        code, out, _ = self.settings()
        self.assertEqual(0, code)
        self.assertTrue(out.startswith("checkpoint approve-plan: stop\ncheckpoint beta: stop\n"), out)
        self.assertEqual(2, out.count("settings: "))

    def test_a_cap_outside_its_range_uses_the_default_and_says_so(self):
        for value in (0, -1, 6, 10 ** 30):
            with self.subTest(value):
                self.owner({"version": 1, "caps": {"rounds": value}})
                code, out, err = self.settings()
                self.assertEqual((0, ""), (code, err))
                self.assertIn("cap rounds: 3\n", out)
                self.assertEqual(1, out.count("settings: "), out)

    def test_an_entry_the_module_does_not_declare_is_named_and_ignored(self):
        self.owner({"version": 1, "checkpoints": {"gamma": "delegate"}, "caps": {"other": 2}})
        code, out, _ = self.settings()
        self.assertEqual(0, code)
        self.assertTrue(out.startswith(DEFAULTS), out)
        self.assertIn("settings: settings set a checkpoint the process module does not declare: gamma", out)
        self.assertIn("settings: settings set a cap the process module does not declare: other", out)

    def test_a_damaged_file_prints_every_default_and_the_problem(self):
        for data in (b"{", b'{"version": 1, "caps": 2.5}', b'{"version": 3}', b"[]"):
            with self.subTest(data):
                self.guarded.write("settings", data)
                code, out, err = self.settings()
                self.assertEqual((0, ""), (code, err))
                self.assertTrue(out.startswith(DEFAULTS), out)
                self.assertIn("settings: ", out)
                self.assertEqual(data, self.guarded.read("settings"))

    def test_a_cap_that_is_not_an_integer_is_a_problem_and_the_default_applies(self):
        self.owner({"version": 1, "caps": {"rounds": "4", "tries": True}})
        code, out, _ = self.settings()
        self.assertEqual(0, code)
        self.assertTrue(out.startswith(DEFAULTS), out)
        self.assertEqual(2, out.count("settings: "), out)

    def test_a_level_line_is_printed_for_every_declared_key_after_the_caps(self):
        self.owner({"version": 2, "levels": {"approve-plan": "delegated"}})
        self.assertEqual((0, "checkpoint approve-plan: delegate\ncheckpoint beta: stop\ncap rounds: 3\ncap tries: 1\n"
                             "level approve-plan: delegated\nlevel beta: block\n", ""), self.settings())

    def test_the_checkpoint_lines_are_the_same_with_and_without_a_table(self):
        _, plain, _ = self.settings()
        self.owner({"version": 2, "levels": {"beta": "block"}})
        _, with_table, _ = self.settings()
        self.assertTrue(plain.startswith(CHECKPOINT_LINES) and with_table.startswith(CHECKPOINT_LINES))

    def test_a_key_in_both_takes_the_stricter_and_says_so(self):
        self.owner({"version": 2, "checkpoints": {"approve-plan": "delegate"}, "levels": {"approve-plan": "block"}})
        code, out, err = self.settings()
        self.assertEqual((0, ""), (code, err))
        self.assertIn("level approve-plan: block\n", out)
        self.assertEqual(1, out.count("settings: "), out)

    def test_a_level_that_is_not_offered_yet_reads_as_block_and_says_so(self):
        self.owner({"version": 2, "levels": {"beta": "ask"}})
        code, out, err = self.settings()
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.startswith(DEFAULTS), out)
        self.assertEqual(1, out.count("settings: "), out)

    def test_a_damaged_levels_table_prints_block_and_the_problem(self):
        self.owner({"version": 2, "checkpoints": {"approve-plan": "delegate"}, "levels": ["x"]})
        code, out, err = self.settings()
        self.assertEqual((0, ""), (code, err))
        self.assertIn("checkpoint approve-plan: stop\n", out)
        self.assertIn("level approve-plan: block\n", out)
        self.assertIn("settings: ", out)

    def test_a_version_1_file_prints_the_same_checkpoint_lines_as_before(self):
        self.owner({"version": 1, "checkpoints": {"approve-plan": "delegate"}})
        code, out, _ = self.settings()
        self.assertEqual(0, code)
        self.assertTrue(out.startswith("checkpoint approve-plan: delegate\ncheckpoint beta: stop\n"), out)


class OtherModules(Settings):
    INSTALL = False

    def test_the_declaration_order_is_kept(self):
        self.use(checkpoints=["zed", "ant"], caps=CAPS[::-1])
        self.assertEqual((0, "checkpoint zed: stop\ncheckpoint ant: stop\ncap tries: 1\ncap rounds: 3\n"
                          "level zed: block\nlevel ant: block\n", ""),
                         self.settings())

    def test_a_module_that_declares_none_prints_nothing(self):
        self.use(checkpoints=[], caps=[])
        self.assertEqual((0, "", ""), self.settings())

    def test_no_process_module(self):
        self.ready()
        self.refused("no installed module is a process module")


class Refused(Settings):
    def test_outside_a_project(self):
        self.refused("not inside a workbench project", cwd=self.outside)

    def test_two_process_modules(self):
        """The installer refuses a second process module, so the second is simulated: a project must
        still be refused if a hostile commit managed to record two."""
        real = commands.installed_module

        def installed(held, package, item):
            return real(held, package, dict(item, name="tool"))._replace(name=item["name"])

        document = manifest.parse(self.read(".workbench/manifest.json"))
        document["packages"][0]["modules"].append(dict(document["packages"][0]["modules"][-1], name="other"))
        with unittest.mock.patch.object(approvalcmd.manifest, "parse", return_value=document), \
                unittest.mock.patch.object(commands, "installed_module", installed), \
                unittest.mock.patch.object(commands, "is_installed", lambda *args: True):
            err = self.refused("more than one installed module is a process module")
        self.assertIn("p/other", err)
        self.assertIn("p/tool", err)

    def test_a_declaration_changed_since_install(self):
        path = ".workbench/p/tool/module.json"
        self.edit(path, lambda data: data.replace(b'"approve-plan"', b'"omega"'))
        self.refused("has changed since it was installed")

    def test_an_argument_is_a_usage_error(self):
        for tokens in (("x",), ("--help",), ("",)):
            with self.subTest(tokens):
                self.assertEqual((2, "", settingscmd.USAGE), self.settings(*tokens))


class Writes(Settings):
    def test_the_project_and_the_store_are_byte_identical_after_a_run(self):
        self.owner({"version": 1, "checkpoints": {"approve-plan": "delegate"}})
        before = snapshot(self.real), snapshot(self.store_root)
        self.assertEqual(0, self.settings()[0])
        self.assertEqual(before, (snapshot(self.real), snapshot(self.store_root)))

    def test_nothing_is_started(self):
        with unittest.mock.patch("subprocess.run", side_effect=AssertionError("ran")), \
                unittest.mock.patch("subprocess.Popen", side_effect=AssertionError("ran")):
            self.assertEqual(0, self.settings()[0])


class FromTheCommandLine(Settings):
    def run_cli(self, *argv, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        before = os.getcwd()
        os.chdir(cwd or self.real)
        self.addCleanup(os.chdir, before)
        code = cli.main(list(argv), out, err, store_root=self.store_root, distribution=self.dist)
        return code, out.getvalue(), err.getvalue()

    def test_it_runs_from_the_command_line(self):
        self.assertEqual((0, DEFAULTS, ""), self.run_cli("settings"))

    def test_no_argument_and_no_option(self):
        for argv in (("settings", "x"), ("settings", "--help"), ("settings", "-x"), ("settings", "")):
            with self.subTest(argv):
                code, out, err = self.run_cli(*argv)
                self.assertEqual((2, ""), (code, out))
                self.assertIn("usage: wb settings", err)

    def test_a_store_with_no_settings_file_gains_only_the_seeded_one(self):
        self.run_cli("settings")  # the launcher is written for this distribution
        os.remove(os.path.join(self.store_root, "settings"))
        before, project = snapshot(self.store_root), snapshot(self.real)
        self.assertEqual((0, DEFAULTS, ""), self.run_cli("settings"))
        after = snapshot(self.store_root)
        self.assertEqual({"settings"}, set(after) - set(before))
        self.assertEqual(before, {key: after[key] for key in before})
        self.assertEqual(project, snapshot(self.real))

    def test_the_classification_lists_it_as_agent_safe(self):
        self.assertIn("settings", rules.AGENT_SAFE)
        self.assertNotIn("settings", rules.OWNER_RUN)


if __name__ == "__main__":
    unittest.main()
