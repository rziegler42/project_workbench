"""The check runner: from a project to the report of every recorded module's checks.

The modules are synthetic (``support_project``). Each check helper is a kit helper that appends its
own name to a log, so a test can show what ran, in which order, and that a refused check ran nothing."""

import io
import os
import tempfile
import unittest
import unittest.mock

from tests import support_project
from workbench import check, checks, cli, launch, pins

LOG = '''
import os
with open(os.environ["WB_TEST_LOG"], "a") as handle:
    handle.write("%s\\n" % __file__.rsplit("/", 1)[-1])
'''


def helper(body="", name="x"):
    """A kit helper: it logs its own name, then runs `body`."""
    return (LOG + body).encode()


def module(*names, bodies=None):
    """A module shipping check helpers `helper/<name>` and declaring them, kit 1, in this order."""
    bodies = bodies or {}
    fields = {"ships": ["helper/%s" % n for n in names],
              "checks": [{"helper": "helper/%s" % n, "kit": 1} for n in names]}
    return fields, {"helper/%s" % n: helper(bodies.get(n, "")) for n in names}


class Checks(support_project.Project):
    MODULES = {"h": (support_project.HARNESS, {}), "a": module("lint")}

    def setUp(self):
        support_project.Project.setUp(self)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.log = os.path.join(os.path.realpath(holder.name), "ran.log")
        patch = unittest.mock.patch.dict(os.environ, {"WB_TEST_LOG": self.log})
        patch.start()
        self.addCleanup(patch.stop)

    def pin_check(self, module_name, name, kit=1):
        self.pin(name=name, path=self.installed(module_name, "helper/%s" % name), kit=kit)

    def ran(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as handle:
            return handle.read().split()

    def run_all(self):
        return checks.run_all(self.guarded, self.real)

    def sections(self):
        return [(s.label, s.problems, s.warnings) for s in self.run_all()]


class Runs(Checks):
    def test_a_pinned_check_reports_its_lines_under_the_module(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "a": module("lint", bodies={
            "lint": 'print("problem: a is wrong")\nprint("warning: b is odd")\nprint("problem: c")\n'})}
        self.ready()
        self.pin_check("a", "lint")
        self.assertEqual([("p/a", ["a is wrong", "c"], ["b is odd"])], self.sections())
        self.assertEqual(["lint"], self.ran())

    def test_a_check_that_reports_nothing_is_clean(self):
        self.ready()
        self.pin_check("a", "lint")
        self.assertEqual([("p/a", [], [])], self.sections())

    def test_a_project_whose_modules_declare_no_checks_has_no_section(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "tool": support_project.tool()}
        self.ready()
        self.assertEqual([], self.run_all())

    def test_a_directory_that_is_not_a_project_has_no_section(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            self.assertEqual([], checks.run_all(self.guarded, os.path.realpath(elsewhere)))

    def test_the_helper_runs_from_the_project_root(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "a": module("lint", bodies={
            "lint": 'import os\nprint("warning: " + os.getcwd())\n'})}
        self.ready()
        self.pin_check("a", "lint")
        self.assertEqual([self.real], self.run_all()[0].warnings)

    def test_the_order_is_the_manifests_and_not_the_order_of_installing(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "b": module("two"), "a": module("one", "uno")}
        self.ready()
        for module_name, name in (("b", "two"), ("a", "one"), ("a", "uno")):
            self.pin_check(module_name, name)
        self.run_all()
        self.assertEqual(["one", "uno", "two"], self.ran())
        self.assertEqual(["p/a", "p/b"], [s.label for s in self.run_all()])


class OutputIsBounded(Checks):
    installed_once = False

    def check(self, body):
        """The only section after the module's one helper is replaced by `body` and pinned again."""
        if not self.installed_once:
            self.MODULES = {"h": (support_project.HARNESS, {}), "a": module("lint")}
            self.ready()
            self.installed_once = True
        self.edit(self.installed("a", "helper/lint"), lambda data: helper(body))
        self.pin_check("a", "lint")
        [section] = self.run_all()
        return section

    def only_problem(self, body, contains):
        section = self.check(body)
        self.assertEqual(1, len(section.problems), section.problems)
        self.assertEqual([], section.warnings)
        self.assertIn(contains, section.problems[0])
        self.assertTrue(section.problems[0].isprintable(), section.problems[0])
        return section.problems[0]

    def test_a_line_in_another_form_fails_the_check(self):
        for body in ('print("hello")\n', 'print("error: x")\n', 'print("problem:x")\n', 'print()\n',
                     'print("problem: ok")\nprint("note: x")\n', 'print("PROBLEM: x")\n',
                     'print(" problem: x")\n', 'print("problem: ")\n'):
            with self.subTest(body):
                self.only_problem(body, "the check lint failed")

    def test_a_non_zero_exit_fails_the_check_and_shows_the_start_of_what_it_said(self):
        text = self.only_problem('print("problem: before")\nimport sys\nsys.exit(3)\n', "the check lint failed")
        self.assertIn("exit 3", text)

    def test_a_traceback_fails_the_check(self):
        text = self.only_problem('raise RuntimeError("boom")\n', "the check lint failed")
        self.assertIn("RuntimeError: boom", text)

    def test_output_that_is_not_text_fails_the_check(self):
        self.only_problem('import sys\nsys.stdout.buffer.write(b"problem: \\xff\\xfe\\n")\n', "not text")

    def test_exit_zero_with_no_output_is_clean(self):
        self.assertEqual(([], []), self.check("")[1:])

    def test_hostile_text_is_cleaned_and_cannot_start_a_line(self):
        section = self.check('print("problem: \\x1b[31mred\\x1b[0m \\u202e hi")\n'
                             'print("warning: a\\x00b")\n')
        self.assertEqual(1, len(section.problems))
        self.assertEqual(1, len(section.warnings))
        for text in section.problems + section.warnings:
            self.assertTrue(text.isascii() and text.isprintable(), text)

    def test_a_long_line_is_cut(self):
        section = self.check('print("problem: " + "a" * 5000)\n')
        self.assertEqual(1, len(section.problems))
        self.assertLessEqual(len(section.problems[0]), checks.MAX_LINE)

    def test_more_lines_than_the_bound_are_not_all_taken(self):
        section = self.check('for n in range(%d):\n    print("warning: w%%d" %% n)\n' % (checks.MAX_LINES + 50))
        self.assertEqual(checks.MAX_LINES, len(section.warnings))
        self.assertEqual(1, len(section.problems))
        self.assertIn("more than %d lines" % checks.MAX_LINES, section.problems[0])

    def test_output_over_the_byte_limit_stops_the_helper(self):
        with unittest.mock.patch.object(checks, "CAPTURE_LIMIT", 2000):
            self.only_problem('import sys\nwhile True:\n    sys.stdout.write("warning: " + "z" * 100 + "\\n")\n',
                              "more than 2000 bytes")

    def test_a_helper_that_does_not_finish_in_time_is_stopped(self):
        with unittest.mock.patch.object(checks, "TIMEOUT", 1):
            self.only_problem("import time\ntime.sleep(60)\n", "did not finish within 1 second")


class Refused(Checks):
    def test_an_unpinned_check_is_a_problem_and_nothing_ran(self):
        self.ready()
        self.unpin()
        [section] = self.run_all()
        self.assertEqual(("p/a", []), (section.label, section.warnings))
        self.assertEqual(1, len(section.problems))
        self.assertIn("the check lint is not pinned", section.problems[0])
        self.assertEqual([], self.ran())

    def test_a_changed_helper_is_a_problem_and_does_not_run(self):
        self.ready()
        self.pin_check("a", "lint")
        self.edit(self.installed("a", "helper/lint"), lambda data: data + b"\nprint('problem: changed')\n")
        [section] = self.run_all()
        self.assertIn("has changed since it was pinned", section.problems[0])
        self.assertEqual([], self.ran())

    def test_a_pin_for_another_path_is_a_problem(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "a": module("lint"), "b": module("other")}
        self.ready()
        self.pin(name="lint", path=self.installed("b", "helper/other"), kit=1)
        found = dict((label, problems) for label, problems, _ in self.sections())
        self.assertIn("not the declared helper", found["p/a"][0])
        self.assertEqual(1, len(found["p/a"]))

    def test_a_pin_without_the_kit_or_with_another_is_a_problem(self):
        self.ready()
        for kit in (None, 2):
            with self.subTest(kit=kit):
                self.pin_check("a", "lint", kit=kit)
                [section] = self.run_all()
                self.assertIn("kit", section.problems[0])
                self.assertEqual([], self.ran())

    def test_a_refused_check_does_not_stop_the_others(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "a": module("one", "two")}
        self.ready()
        self.unpin("one")
        self.pin_check("a", "two")
        [section] = self.run_all()
        self.assertEqual(1, len(section.problems))
        self.assertIn("one", section.problems[0])
        self.assertEqual(["two"], self.ran())

    def test_a_module_whose_declaration_changed_is_a_problem_for_that_module_only(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "a": module("one"), "b": module("two")}
        self.ready()
        self.pin_check("a", "one")
        self.pin_check("b", "two")
        self.edit(".workbench/p/a/module.json", lambda data: data.replace(b'"checks"', b'"checkz"'))
        found = dict((label, problems) for label, problems, _ in self.sections())
        self.assertIn("has changed since it was installed", found["p/a"][0])
        self.assertEqual([], found["p/b"])
        self.assertEqual(["two"], self.ran())

    def test_a_manifest_that_cannot_be_read_is_a_problem_not_a_silence(self):
        self.ready()
        self.edit(".workbench/manifest.json", lambda data: b"{")
        [section] = self.run_all()
        self.assertEqual("manifest", section.label)
        self.assertEqual(1, len(section.problems))


if __name__ == "__main__":
    unittest.main()


class Command(Checks):
    """`wb check` prints the module sections after the installer's own findings."""

    def check(self):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", self.place], out, err, store_root=self.store_root, home=self.home)
        return code, out.getvalue(), err.getvalue()

    def lines(self, text, prefix):
        return [line for line in text.splitlines() if line.startswith(prefix)]

    def with_body(self, body):
        self.MODULES = {"h": (support_project.HARNESS, {}), "a": module("lint", bodies={"lint": body})}
        self.ready()
        self.pin_check("a", "lint")

    def test_the_lines_appear_under_the_module_name(self):
        self.with_body('print("problem: bad")\nprint("warning: odd")\n')
        code, out, err = self.check()
        self.assertEqual(["problem: p/a: bad"], [l for l in self.lines(err, "problem: ") if "p/a" in l])
        self.assertEqual(["warning: p/a: odd"], self.lines(err, "warning: p/a"))
        self.assertEqual(1, code)

    def test_a_problem_is_counted_and_a_warning_is_not(self):
        self.with_body('print("problem: bad")\nprint("warning: odd")\n')
        with unittest.mock.patch.object(check, "examine", return_value=check.Report(None, ["own"], [], "m")):
            code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertTrue(out.endswith("check found 2 problems\n"), out)

    def test_a_warning_alone_does_not_fail_the_check(self):
        self.with_body('print("warning: odd")\n')
        with unittest.mock.patch.object(check, "examine", return_value=check.Report("none", [], [], "m")):
            code, out, err = self.check()
        self.assertEqual((0, "warning: p/a: odd\n"), (code, err))
        self.assertTrue(out.endswith("check found no problems\n"), out)

    def test_an_unpinned_helper_is_a_problem_and_the_rest_still_run(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "a": module("lint", "style")}
        self.ready()
        self.unpin("lint")
        self.pin_check("a", "style")
        with unittest.mock.patch.object(check, "examine", return_value=check.Report(None, [], [], "m")):
            code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: p/a: the check lint is not pinned", err)
        self.assertEqual(["style"], self.ran())
        self.assertTrue(out.endswith("check found 1 problem\n"), out)

    def test_a_project_without_module_checks_prints_what_it_printed_before(self):
        self.MODULES = {"h": (support_project.HARNESS, {}), "a": ({}, {})}
        self.ready()
        # Hand-written documents are nobody's to check unless a recorded module declares the check.
        os.makedirs(os.path.join(self.place, "docs", "specs"))
        with open(os.path.join(self.place, "docs", "specs", "Bad_Name.md"), "w") as handle:
            handle.write("no status\n")
        with unittest.mock.patch.object(check, "examine", return_value=check.Report(None, [], [], "m")):
            code, out, err = self.check()
        self.assertEqual((0, "", ), (code, err))
        self.assertEqual("harness: none attached in %s\nm\ncheck found no problems\n" % self.real, out)
