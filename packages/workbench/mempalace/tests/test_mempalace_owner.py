"""`mempalace init` and `mempalace mine`, the owner's commands, and the project's palace setting, with a fake
`mempalace` (criteria 5 to 7 of plan `2026-10-24-mempalace-module`, increment C). No test starts a real
`mempalace`; the terminal is a pseudo-terminal."""

import json
import os
import signal
import subprocess
import sys
import time
import unittest
import unittest.mock

import support_mempalace

FORBIDDEN = ("--llm", "--llm-provider", "--llm-model", "--llm-endpoint", "--llm-api-key", "--accept-external-llm",
             "--daemon", "--direct", "--background", "--auto-mine", "--backend", "--palace", "--include-media")


class Owner(support_mempalace.Palace):
    def setUp(self):
        support_mempalace.Palace.setUp(self)
        self.corpus = os.path.join(self.base, "corpus")
        os.makedirs(self.corpus)

    def started(self):
        (call,) = self.calls()
        return call["argv"]


class Init(Owner):
    def test_init_passes_the_directory_and_no_llm_and_nothing_else(self):
        code, shown = self.owner("init", self.corpus)
        self.assertEqual(0, code, shown)
        self.assertEqual(["init", self.corpus, "--no-llm"], self.started())
        self.assertIn("note: init writes mempalace.yaml into %s" % self.corpus, shown)

    def test_yes_is_passed_only_when_the_owner_gives_it(self):
        self.assertEqual(0, self.owner("init", self.corpus, "--yes")[0])
        self.assertEqual(["init", self.corpus, "--no-llm", "--yes"], self.started())

    def test_a_relative_directory_is_read_against_the_current_directory(self):
        os.makedirs(os.path.join(self.root, "docs", "deep"))
        self.assertEqual(0, self.owner("init", "deep", cwd=os.path.join(self.root, "docs"))[0])
        self.assertEqual(os.path.join(self.root, "docs", "deep"), self.started()[1])

    def test_the_terminal_is_handed_to_the_program(self):
        self.assertEqual(0, self.owner("init", self.corpus)[0])
        self.assertEqual([True, True, True], self.calls()[0]["tty"])

    def test_the_program_exit_code_is_the_commands(self):
        self.control(code=3, stdout="partial\n")
        code, shown = self.owner("init", self.corpus)
        self.assertEqual(3, code)
        self.assertIn("partial", shown)

    def test_an_option_that_selects_a_provider_a_key_a_daemon_or_a_background_job_is_refused(self):
        for name in FORBIDDEN + ("--confirm", "--wing", "--mode", "--dry-run", "-y", "--YES"):
            self.refused("init", self.corpus, name, "x", contains="is not an option")

    def test_the_directory_is_required_once(self):
        self.refused("init", contains="needs the directory")
        self.refused("init", "--yes", contains="needs the directory")
        self.refused("init", self.corpus, self.corpus, contains="exactly one directory")
        self.refused("init", self.corpus, "--yes", "--yes", contains="given twice")


class Mine(Owner):
    def test_a_mine_is_a_dry_run_unless_the_owner_confirms(self):
        code, shown = self.owner("mine", self.corpus)
        self.assertEqual(0, code, shown)
        self.assertEqual(["mine", self.corpus, "--dry-run"], self.started())
        self.assertIn("note: this is a dry run and files nothing; add --confirm", shown)

    def test_confirm_removes_the_dry_run_and_says_what_a_first_real_mine_does(self):
        code, shown = self.owner("mine", self.corpus, "--confirm")
        self.assertEqual(0, code, shown)
        self.assertEqual(["mine", self.corpus], self.started())
        self.assertIn("downloads the embedding model", shown)
        self.assertIn("hallways.json", shown)

    def test_the_wing_and_the_mode_are_passed_from_their_allow_lists(self):
        self.assertEqual(0, self.owner("mine", self.corpus, "--wing", "proj", "--mode", "convos", "--confirm")[0])
        self.assertEqual(["mine", self.corpus, "--wing", "proj", "--mode", "convos"], self.started())

    def test_a_mode_outside_the_two_and_a_bad_wing_are_refused(self):
        for mode in ("extract", "", "PROJECTS", "projects;ls", "-x"):
            self.refused("mine", self.corpus, "--mode", mode, contains="--mode")
        for wing in ("", "-x", ".x", "a b", "x" * 65, "a/b"):
            self.refused("mine", self.corpus, "--wing", wing, contains="--wing")

    def test_an_option_the_helper_does_not_allow_is_refused(self):
        for name in FORBIDDEN + ("--yes", "--source", "--agent", "--limit", "--no-gitignore", "--extract",
                                 "--include-ignored", "--related-drawer-id", "--redetect-origin"):
            self.refused("mine", self.corpus, name, "x", contains="is not an option")

    def test_the_arguments_are_checked_for_shape(self):
        self.refused("mine", contains="needs the directory")
        self.refused("mine", self.corpus, self.corpus, contains="exactly one directory")
        self.refused("mine", self.corpus, "--wing", contains="needs a value")
        self.refused("mine", self.corpus, "--wing", "a", "--wing", "b", contains="given twice")
        self.refused("mine", self.corpus, "--confirm", "--confirm", contains="given twice")

    def test_the_program_may_run_for_longer_than_a_search_may(self):
        self.control(sleep=2, stdout="done\n")
        with unittest.mock.patch.object(self.helper, "TIMEOUT", 1):
            code, shown = self.owner("mine", self.corpus, "--confirm")
        self.assertEqual(0, code, shown)
        self.assertIn("done", shown)


class Terminal(Owner):
    def test_a_command_that_is_not_run_from_a_terminal_starts_nothing(self):
        for argv in (("init", self.corpus), ("mine", self.corpus), ("mine", self.corpus, "--confirm")):
            self.refused(*argv, contains="only from a terminal")

    def test_a_terminal_for_input_alone_is_not_enough(self):
        import io
        _, tin, tout, terr = self.terminal()
        for stdin, out in ((tin, io.StringIO()), (io.BytesIO(b""), tout)):
            err = io.StringIO()
            self.assertEqual(1, self.helper.main(["init", self.corpus], stdin, out, err, self.root))
            self.assertIn("only from a terminal", err.getvalue())
        self.assertEqual([], self.calls())

    def test_a_closed_stream_is_not_a_terminal(self):
        import io
        _, tin, tout, terr = self.terminal()
        tin.close()
        err = io.StringIO()
        self.assertEqual(1, self.helper.main(["init", self.corpus], tin, tout, err, self.root))
        self.assertIn("only from a terminal", err.getvalue())
        self.assertEqual([], self.calls())


class Directory(Owner):
    def owner_refused(self, *args, contains):
        """A refusal of an owner command run from a terminal: nothing was started, and the text says why."""
        code, shown = self.owner(*args)
        self.assertEqual(1, code, shown)
        self.assertTrue(shown.startswith("note: ") or shown.startswith("refused: "), shown)
        self.assertIn("refused: ", shown)
        self.assertIn(contains, shown)
        self.assertEqual([], self.calls(), "the program was started")

    def test_a_directory_that_does_not_exist_or_is_not_one_is_refused(self):
        self.owner_refused("init", os.path.join(self.base, "nothing"), contains="does not exist")
        self.owner_refused("init", os.path.join(self.root, "docs", "plan.md"), contains="not a directory")
        self.owner_refused("init", "", contains="not a usable path")
        self.owner_refused("init", self.corpus + "\0x", contains="not a usable path")

    def test_a_link_to_a_directory_or_a_link_in_the_path_is_refused(self):
        os.symlink(self.corpus, os.path.join(self.base, "linked"))
        self.owner_refused("init", os.path.join(self.base, "linked"), contains="link")
        os.makedirs(os.path.join(self.corpus, "deep"))
        self.owner_refused("mine", os.path.join(self.base, "linked", "deep"), contains="link")

    def test_a_directory_in_git_or_the_workbench_directory_is_refused(self):
        os.makedirs(os.path.join(self.root, ".git", "x"))
        for name in (".git", ".git/x", ".workbench"):
            self.owner_refused("mine", os.path.join(self.root, name), contains=".git or .workbench")

    def test_the_project_root_and_a_directory_that_holds_it_need_the_explicit_flag(self):
        for target in (self.root, self.base, "."):
            self.owner_refused("init", target, contains="--allow-project-root")
            self.owner_refused("mine", target, contains="--allow-project-root")
        self.assertEqual(0, self.owner("mine", self.root, "--allow-project-root")[0])

    def test_a_directory_inside_the_project_is_accepted(self):
        self.assertEqual(0, self.owner("mine", os.path.join(self.root, "docs"))[0])
        self.assertEqual(os.path.join(self.root, "docs"), self.calls()[0]["argv"][1])

    def test_a_directory_that_cannot_be_entered_is_refused(self):
        folder = os.path.join(self.corpus, "locked")
        os.mkdir(folder)
        os.chmod(folder, 0)
        self.addCleanup(os.chmod, folder, 0o755)
        if os.access(folder, os.X_OK):
            self.skipTest("the permissions are not enforced for this user")
        self.owner_refused("mine", folder, contains="cannot be entered")


class Environment(Owner):
    def test_the_program_gets_the_same_short_environment_and_a_private_directory_that_is_removed(self):
        secrets = {"MEMPALACE_PALACE_PATH": "/x", "MEMPALACE_EMBEDDING_API_URL": "http://x", "OPENAI_API_KEY": "k",
                   "ANTHROPIC_API_KEY": "k", "GITHUB_TOKEN": "t", "GIT_DIR": "/x", "XDG_CONFIG_HOME": "/x"}
        with unittest.mock.patch.dict(os.environ, dict(secrets, LANG="C.UTF-8", LC_ALL="C")):
            self.assertEqual(0, self.owner("mine", self.corpus, "--confirm")[0])
        (call,) = self.calls()
        self.assertEqual({"HOME", "LANG", "LC_ALL", "PATH", "PYTHONDONTWRITEBYTECODE"}, set(call["env"]))
        self.assertEqual(self.outside, call["env"]["PATH"])
        self.assertTrue(os.path.realpath(call["cwd"]).startswith(self.temp + os.sep), call["cwd"])
        self.assertEqual([], os.listdir(self.temp))

    def test_a_program_inside_the_project_is_never_run_for_an_owner_command(self):
        os.remove(os.path.join(self.outside, "mempalace"))
        inside = os.path.join(self.root, "bin")
        os.makedirs(inside)
        self.fake(inside)
        self.path([inside], TMPDIR=self.temp, HOME=self.home)
        code, shown = self.owner("init", self.corpus)
        self.assertEqual(1, code)
        self.assertIn("not found in a trusted PATH entry", shown)
        self.assertEqual([], self.calls(inside))

    def test_a_temporary_directory_inside_the_project_is_refused(self):
        self.path([self.outside], TMPDIR=os.path.join(self.root, "docs"), HOME=self.home)
        code, shown = self.owner("init", self.corpus)
        self.assertEqual(1, code)
        self.assertIn("temporary directory", shown)
        self.assertEqual([], self.calls())

    def test_the_project_is_the_same_after_every_kind_of_call(self):
        before = self.tree()
        self.owner("init", self.corpus, "--yes")
        self.owner("mine", self.corpus)
        self.owner("mine", self.corpus, "--confirm")
        self.control(code=2)
        self.owner("mine", self.corpus, "--confirm")
        self.assertEqual(before, self.tree())
        self.assertEqual([], os.listdir(self.temp))

    def test_a_terminate_signal_stops_the_program_and_removes_the_scratch_directory(self):
        self.control(hang=True)
        helper = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "helper", "mempalace")
        workbench = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))), "workbench")
        master, tin, tout, terr = self.terminal()
        env = {"PATH": self.outside, "TMPDIR": self.temp, "HOME": self.home, "PYTHONPATH": workbench}
        process = subprocess.Popen([sys.executable, "-B", helper, "mine", self.corpus, "--confirm"], cwd=self.root,
                                   env=env, stdin=tin, stdout=tout, stderr=terr)
        self.addCleanup(process.kill)
        pids = os.path.join(self.outside, "pids")
        for _ in range(100):
            if os.path.exists(pids) and self.calls():
                break
            time.sleep(0.1)
        else:
            self.fail("the program did not start")
        time.sleep(0.2)
        with open(pids) as handle:
            grandchild = int(handle.read())
        self.addCleanup(self.reap, grandchild)
        program = self.calls()[0]["pid"]
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=30)
        for _ in range(50):
            try:
                os.kill(program, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            self.fail("the program is still running")
        self.assertFalse(os.path.exists(self.calls()[0]["cwd"]))

    @staticmethod
    def reap(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


class Setting(Owner):
    """`.workbench/mempalace.json` and the palace it names."""

    def write(self, text, name="mempalace.json"):
        with open(os.path.join(self.root, ".workbench", name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def setting(self, **fields):
        document = {"format": 1, "palace": os.path.join(self.base, "palace")}
        document.update(fields)
        self.write(json.dumps(document))

    def every_command(self):
        """The four commands, each as (what to call it with, how to run it)."""
        return (("status", lambda: self.run_helper("status")),
                ("search", lambda: self.search()),
                ("init", lambda: self.owner("init", self.corpus)),
                ("mine", lambda: self.owner("mine", self.corpus)))

    def test_with_no_setting_the_program_is_not_told_a_palace(self):
        for _, run in self.every_command():
            run()
        for call in self.calls():
            self.assertNotIn("--palace", call["argv"])

    def test_a_valid_setting_is_passed_before_the_command_for_all_four(self):
        self.setting()
        palace = os.path.join(self.base, "palace")
        for name, run in self.every_command():
            self.assertEqual(0, run()[0], name)
        for call, name in zip(self.calls(), ("status", "search", "init", "mine")):
            self.assertEqual(["--palace", palace, name], call["argv"][:3])

    def test_a_setting_that_is_wrong_in_any_way_stops_every_command_before_the_program_starts(self):
        bad = {
            "malformed": "{", "empty": "", "not an object": "[]", "extra key": '{"format":1,"palace":"/x","a":1}',
            "missing palace": '{"format":1}', "missing format": '{"palace":"/x"}', "format two": '{"format":2,"palace":"/x"}',
            "format string": '{"format":"1","palace":"/x"}', "format true": '{"format":true,"palace":"/x"}',
            "format float": '{"format":1.0,"palace":"/x"}', "relative": '{"format":1,"palace":"palace"}',
            "dot dot": '{"format":1,"palace":"/x/../y"}', "double slash": '{"format":1,"palace":"/x//y"}',
            "trailing slash": '{"format":1,"palace":"/x/"}', "empty palace": '{"format":1,"palace":""}',
            "palace number": '{"format":1,"palace":5}', "control": '{"format":1,"palace":"/x\\u0007y"}',
            "newline": '{"format":1,"palace":"/x\\ny"}', "duplicate key": '{"format":1,"format":1,"palace":"/x"}',
            "long": json.dumps({"format": 1, "palace": "/" + "a" * 600}),
            "oversized": '{"format":1,"palace":"/x","pad":"%s"}' % ("x" * 5000), "nan": '{"format":NaN,"palace":"/x"}',
        }
        for label, text in bad.items():
            self.write(text)
            for name, run in self.every_command():
                if name in ("init", "mine"):
                    code, shown = run()
                    self.assertIn("mempalace.json", shown, (label, name))
                else:
                    code, out, err = run()
                    self.assertIn("mempalace.json", err, (label, name))
                self.assertEqual(1, code, (label, name))
        self.assertEqual([], self.calls())

    def test_a_setting_that_is_a_link_or_a_directory_is_refused(self):
        target = os.path.join(self.base, "elsewhere.json")
        with open(target, "w") as handle:
            handle.write('{"format":1,"palace":"/x"}')
        os.symlink(target, os.path.join(self.root, ".workbench", "mempalace.json"))
        self.refused("status", contains="mempalace.json")
        os.remove(os.path.join(self.root, ".workbench", "mempalace.json"))
        os.mkdir(os.path.join(self.root, ".workbench", "mempalace.json"))
        self.refused("status", contains="mempalace.json")
        self.assertEqual([], self.calls())

    def test_a_setting_file_is_read_from_the_project_root_whatever_the_current_directory(self):
        self.setting()
        self.assertEqual(0, self.run_helper("status", cwd=os.path.join(self.root, "docs"))[0])
        self.assertEqual(os.path.join(self.base, "palace"), self.calls()[0]["argv"][1])

    def test_a_directory_that_is_not_a_project_is_refused(self):
        self.refused("status", cwd=self.base, contains="not inside a workbench project")


class RecordedModel(Setting):
    def palace(self, text=None, link=False):
        folder = os.path.join(self.base, "palace")
        os.makedirs(folder, exist_ok=True)
        self.setting()
        if text is not None:
            path = os.path.join(folder, "mempalace_embedder.json")
            if link:
                if os.path.lexists(path):
                    os.remove(path)
                other = os.path.join(self.base, "other.json")
                with open(other, "w") as handle:
                    handle.write(text)
                os.symlink(other, path)
            else:
                with open(path, "w") as handle:
                    handle.write(text)

    GOOD = '{"mempalace_drawers": {"model_name": "minilm", "dimension": 0}, "mempalace_closets": {"model_name": "minilm"}}'

    def test_a_palace_recorded_as_minilm_or_not_recorded_yet_is_searched(self):
        self.palace(self.GOOD)
        self.assertEqual(0, self.search()[0])
        os.remove(os.path.join(self.base, "palace", "mempalace_embedder.json"))
        self.assertEqual(0, self.search()[0])

    def test_a_palace_recorded_with_another_model_or_unreadably_starts_nothing(self):
        for text in ('{"mempalace_drawers": {"model_name": "gemma", "dimension": 768}}', "{", "[]", "{}",
                     '{"mempalace_drawers": 5}', '{"mempalace_drawers": {"model_name": ["minilm"]}}'):
            self.palace(text)
            self.refused_search(contains="")
        self.palace(self.GOOD, link=True)
        self.refused_search(contains="mempalace_embedder.json")
        self.assertEqual([], self.calls())

    def test_the_other_model_is_named_without_its_control_characters(self):
        self.palace('{"mempalace_drawers": {"model_name": "bad\\u001b[31mname"}}')
        err = self.refused_search(contains="only minilm is cached")
        self.assertNotIn("\x1b", err)

    def test_status_does_not_look_at_the_recorded_model(self):
        self.palace('{"mempalace_drawers": {"model_name": "gemma"}}')
        self.assertEqual(0, self.run_helper("status")[0])


if __name__ == "__main__":
    unittest.main()
