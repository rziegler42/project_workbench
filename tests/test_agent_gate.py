"""``agent-gate <harness> <agent>``: the guard a confined agent's hook runs.

The project, its module and its agents are synthetic, and so is the harness layout: its scratch directory is a
template under the test's own directory, so a test can make links and unreadable folders in it. The installer under
test knows no module or agent."""

import io
import json
import os
import re
import stat
import time
import unittest
import unittest.mock

from tests import support_harness, support_project, test_attach
from tests.support_project import tool
from workbench import agent_gate, cli, gate_hook, harnesses, rules

CHECKER = (b"---\nname: checker\ndescription: Runs a check\ntools: read, edit, shell\nwrites: scratch\n"
           b"run: python3 {scratch}/check.py, python3 {scratch}/check.py --fast, make test\n---\nCheck.\n")
WRITER = b"---\nname: writer\ndescription: Writes notes\ntools: read, edit\nwrites: scratch\n---\nWrite.\n"
RUNNER = b"---\nname: runner\ndescription: Runs one thing\ntools: read, shell\nrun: make test\n---\nRun.\n"
PLAIN = b"---\nname: plain\ndescription: Reads\ntools: read, search\n---\nRead.\n"
AGENTS = {"checker": CHECKER, "writer": WRITER, "runner": RUNNER, "plain": PLAIN}
AGENT_PATH = ".workbench/p/tool/harness/neutral/agents/%s.md"
SESSION = "sess-1"
NAME = "fixture"


def module():
    fields, files = tool()
    files = dict(files, **{"harness/neutral/agents/%s.md" % name: data for name, data in AGENTS.items()})
    return fields, files


class Guarded(support_project.Project):
    MODULES = {"h": (test_attach.HARNESS, {}), "tool": module()}

    def setUp(self):
        support_project.Project.setUp(self)
        self.ready()
        self.top = os.path.realpath(os.path.join(self.root, "scratches"))
        os.makedirs(self.top)
        layout = json.loads(json.dumps(support_harness.SYNTHETIC))
        layout["kinds"]["agent"]["hook"] = {"key": "hooks", "event": "PreToolUse", "timeout": 20, "block_code": 2}
        layout["kinds"]["agent"]["scratch"] = self.top + "/s-{uid}/{cwd_key}/{session_id}/pad"
        self.gdist = support_harness.distribution(os.path.join(self.root, "guarded"), layout)
        key = re.sub(r"[^A-Za-z0-9]", "-", self.real)
        self.pad = os.path.join(self.top, "s-%d" % os.getuid(), key, SESSION, "pad")

    # --- the call
    def payload(self, tool_name="Write", cwd=None, session=SESSION, **tool_input):
        return json.dumps({"hook_event_name": "PreToolUse", "cwd": self.real if cwd is None else cwd, "session_id": session,
                           "tool_name": tool_name, "tool_input": tool_input})

    def call(self, text, agent="checker", harness=NAME, dist=None, stdin=None):
        err = io.StringIO()
        code = cli.main(["agent-gate", harness, agent], io.StringIO(), err, store_root=self.store_root,
                        distribution=dist or self.gdist, stdin=stdin or io.StringIO(text))
        return code, err.getvalue()

    def write(self, path, agent="checker", tool_name="Write", **kwargs):
        return self.call(self.payload(tool_name, file_path=path), agent, **kwargs)

    def run_command(self, command, agent="checker", **kwargs):
        return self.call(self.payload("Bash", command=command), agent, **kwargs)

    def allowed(self, result):
        self.assertEqual((0, ""), result)

    def refused(self, result, contains=""):
        code, err = result
        self.assertEqual(2, code, err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertEqual(1, err.count("\n"), err)
        self.assertIn(contains, err)
        if not contains.startswith("the gate failed"):
            self.assertNotIn("the gate failed", err, "refused by a crash, not by a check")
        return err

    def make(self, *rel):
        full = os.path.join(self.pad, *rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        return full

    def make_file(self, *rel, data=b"x"):
        full = self.make(*rel)
        with open(full, "wb") as handle:
            handle.write(data)
        return full

    def inside(self, name):
        return os.path.join(self.pad, name)


class Writes(Guarded):
    def test_a_new_file_in_a_scratch_directory_that_does_not_exist_yet(self):
        self.assertFalse(os.path.exists(self.top + "/s-%d" % os.getuid()))
        self.allowed(self.write(self.inside("notes.txt")))
        self.allowed(self.write(self.inside("deep/er/notes.txt")))

    def test_an_existing_file_and_folder(self):
        self.make_file("old.txt")
        self.make_file("sub", "old.txt")
        self.allowed(self.write(self.inside("old.txt"), tool_name="Edit"))
        self.allowed(self.write(self.inside("sub/old.txt")))

    def test_a_large_write_is_not_refused_for_its_size(self):
        text = self.payload("Write", file_path=self.inside("big.txt"), content="y" * (1024 * 1024))
        self.allowed(self.call(text))

    def test_nothing_is_written_by_the_guard(self):
        before = (self.content(), self.content(self.store_root), self.content(self.top))
        self.allowed(self.write(self.inside("notes.txt")))
        self.refused(self.write(self.real + "/x.txt"))
        self.assertEqual(before, (self.content(), self.content(self.store_root), self.content(self.top)))

    def test_outside_the_scratch_directory(self):
        os.makedirs(self.pad)
        for path in (self.real + "/src/x.py", os.path.join(self.outside, "x"), "/x", self.top + "/x",
                     os.path.dirname(self.pad) + "/x", os.path.dirname(self.pad) + "/other/pad/x",
                     self.pad + "2/x", self.pad[:-1] + "/x"):
            with self.subTest(path):
                self.refused(self.write(path), "not below the scratch directory")

    def test_the_scratch_directory_itself(self):
        os.makedirs(self.pad)
        self.refused(self.write(self.pad), "scratch directory itself")
        self.refused(self.write(self.pad + "/"), "empty part")

    def test_dot_dot_and_dot_and_empty_parts(self):
        os.makedirs(self.pad)
        for path in (self.pad + "/../x", self.pad + "/sub/../../x", self.pad + "/./x", self.pad + "//x",
                     self.pad + "/x/", self.pad + "/x/..", self.pad + "/.."):
            with self.subTest(path):
                self.refused(self.write(path), "empty part, '.' or '..'")

    def test_a_relative_path_and_a_missing_or_wrong_field(self):
        self.refused(self.write("x.txt"), "not absolute")
        self.refused(self.write("pad/x.txt"), "not absolute")
        self.refused(self.write(""), "no path")
        self.refused(self.call(self.payload("Write")), "no path")
        self.refused(self.call(self.payload("Write", notebook_path=self.inside("x"))), "no path")
        for value in (None, 7, True, [self.inside("x")], {"a": 1}):
            with self.subTest(value):
                self.refused(self.write(value), "no path")

    def test_a_control_character_or_an_overlong_path(self):
        for path in (self.inside("a\0b"), self.inside("a\nb"), self.inside("a\tb"), self.inside("a\x7fb"),
                     self.inside("a\x1bb")):
            with self.subTest(repr(path)):
                self.refused(self.write(path), "control character")
        self.refused(self.write(self.inside("n" * agent_gate.MAX_TARGET)), "too long")

    def test_another_spelling_of_the_scratch_directory(self):
        os.makedirs(self.pad)
        upper = os.path.join(os.path.dirname(self.pad), "PAD", "x")
        self.refused(self.write(upper), "another way")
        self.refused(self.write(self.pad.replace(SESSION, SESSION.upper()) + "/x"), "another way")
        self.refused(self.write(self.pad.replace("pad", "p\u0430d") + "/x"), "not below")

    def test_another_spelling_is_refused_even_when_the_directory_does_not_exist(self):
        self.refused(self.write(os.path.join(os.path.dirname(self.pad), "Pad", "x")), "another way")

    def test_a_link_in_a_part_that_exists(self):
        os.makedirs(self.pad)
        os.makedirs(os.path.join(self.outside, "dir"))
        target_file = os.path.join(self.outside, "file")
        with open(target_file, "w") as handle:
            handle.write("keep")
        os.symlink(os.path.join(self.outside, "dir"), self.inside("link"))
        os.symlink(target_file, self.inside("filelink"))
        os.symlink(self.inside("nowhere"), self.inside("dangling"))
        for path in ("link/x", "link", "filelink", "dangling", "link/sub/x"):
            with self.subTest(path):
                self.refused(self.write(self.inside(path)), "symbolic link")
        with open(target_file) as handle:
            self.assertEqual("keep", handle.read())

    def test_the_scratch_directory_or_an_ancestor_is_a_link(self):
        parent = os.path.dirname(self.pad)
        os.makedirs(parent)
        os.symlink(self.outside, self.pad)
        self.refused(self.write(self.inside("x")), "symbolic link")
        os.remove(self.pad)
        shared = os.path.join(self.outside, "shared")
        os.makedirs(shared)
        os.rmdir(parent)
        os.symlink(shared, parent)
        self.refused(self.write(self.inside("x")), "symbolic link")

    def test_a_part_that_cannot_be_examined_is_a_refusal_and_not_outside(self):
        os.makedirs(self.pad)
        os.chmod(self.pad, 0)
        self.addCleanup(os.chmod, self.pad, stat.S_IRWXU)
        self.refused(self.write(self.inside("x")), "cannot be examined")

    def test_the_tool_must_be_one_the_agent_holds(self):
        for name in ("Read", "NotebookEdit", "Task", "Agent", "write", "WRITE", "Write ", "", "Bash\n"):
            with self.subTest(name):
                self.refused(self.call(self.payload(name, file_path=self.inside("x"))), "not one the agent")
        self.refused(self.write(self.inside("x"), agent="runner"), "not one the agent")
        self.refused(self.run_command("make test", agent="writer"), "not one the agent")

    def test_writes_and_run_are_judged_independently(self):
        self.allowed(self.write(self.inside("x"), agent="writer"))
        self.allowed(self.run_command("make test", agent="runner"))


class Commands(Guarded):
    def check(self, *rest):
        return " ".join(["python3", self.inside("check.py")] + list(rest))

    def test_a_pinned_command(self):
        self.allowed(self.run_command(self.check()))
        self.allowed(self.run_command(self.check("--fast")))
        self.allowed(self.run_command("make test"))

    def test_nothing_is_run(self):
        marker = self.inside("ran")
        os.makedirs(self.pad)
        with open(self.inside("check.py"), "w") as handle:
            handle.write("open(%r, 'w').close()\n" % marker)
        self.allowed(self.run_command(self.check()))
        self.assertFalse(os.path.exists(marker))

    def test_a_character_outside_the_safe_set(self):
        for char in ";&|$`()<>\"'\\*?[]{}~#!^,\n\t\r\0\x1b\x7f\u00e9\uff50":
            for command in ("make test" + char, "make" + char + "test", char + "make test", self.check() + char + "id"):
                with self.subTest(repr(command)):
                    self.refused(self.run_command(command))

    def test_the_safe_set_holds_even_if_a_pattern_were_to_spell_the_character(self):
        for char in ";&|$`()<>\"'\\\n{}*":
            with self.subTest(repr(char)):
                command = "make" + char + "test"
                with self.assertRaises(gate_hook.Refusal):
                    agent_gate.command_allowed(command, (command,), ["scratch"])

    def test_a_field_the_guard_does_not_know_is_refused(self):
        self.allowed(self.call(self.payload("Bash", command="make test", description="d", timeout=5)))
        for extra in ({"dangerouslyDisableSandbox": True}, {"unknown": 1}, {"file_path": "/x"}):
            with self.subTest(extra):
                self.refused(self.call(self.payload("Bash", command="make test", **extra)), "does not know")

    def test_spaces_must_be_single_and_inside(self):
        for command in ("make  test", " make test", "make test ", "make\u00a0test", "  ", " "):
            with self.subTest(repr(command)):
                self.refused(self.run_command(command))

    def test_an_argument_the_pattern_does_not_spell(self):
        for rest in (("--slow",), ("--fast", "--fast"), ("-c", "import os"), ("extra",), ("--fast=1",), ("-",)):
            with self.subTest(rest):
                self.refused(self.run_command(self.check(*rest)), "matches none")
        self.refused(self.run_command("make"), "matches none")
        self.refused(self.run_command("make test -j"), "matches none")
        self.refused(self.run_command("make -f evil test"), "matches none")
        self.refused(self.run_command("make test", agent="writer"))

    def test_another_program_or_spelling(self):
        for command in ("python3.99 %s" % self.inside("check.py"), "python %s" % self.inside("check.py"),
                        "/usr/bin/python3 %s" % self.inside("check.py"), "MAKE test", "make TEST", "make test.",
                        "echo make test", "env make test"):
            with self.subTest(command):
                self.refused(self.run_command(command))

    def test_the_placeholder_names_one_file_directly_in_the_scratch_directory(self):
        os.makedirs(self.pad)
        other = os.path.join(self.outside, "check.py")
        for path in (other, "/tmp/check.py", "check.py", "./check.py", "{scratch}/check.py",
                     self.inside("other.py"), self.inside("sub/check.py"), self.inside("../check.py"),
                     self.inside("check.py/"), self.inside(".check.py"), self.inside("CHECK.PY"),
                     os.path.join(os.path.dirname(self.pad), "PAD", "check.py"),
                     os.path.join(os.path.dirname(self.pad), "other", "pad", "check.py"), self.pad + "2/check.py"):
            with self.subTest(path):
                self.refused(self.run_command("python3 " + path))

    def test_a_link_where_the_placeholder_names_a_file(self):
        os.makedirs(self.pad)
        outside = os.path.join(self.outside, "check.py")
        with open(outside, "w") as handle:
            handle.write("print(1)\n")
        os.symlink(outside, self.inside("check.py"))
        self.refused(self.run_command(self.check()), "symbolic link")
        os.remove(self.inside("check.py"))
        self.allowed(self.run_command(self.check()))

    def test_a_link_in_the_scratch_directory_on_the_way(self):
        os.makedirs(os.path.dirname(self.pad))
        os.symlink(self.outside, self.pad)
        self.refused(self.run_command(self.check()), "symbolic link")

    def test_not_a_string_or_too_long(self):
        for value in (None, 7, ["make", "test"], {"a": 1}, True, ""):
            with self.subTest(value):
                self.refused(self.call(self.payload("Bash", command=value)), "no command")
        self.refused(self.call(self.payload("Bash")), "no command")
        self.refused(self.call(self.payload("Bash", cmd="make test")), "does not know")
        self.refused(self.run_command("make " + "t" * agent_gate.MAX_COMMAND), "longer than")

    def test_a_command_of_exactly_the_limit_is_judged_by_the_patterns(self):
        self.refused(self.run_command("a" * agent_gate.MAX_COMMAND), "matches none")


class Input(Guarded):
    def test_what_is_not_one_object(self):
        for text in ("", " ", "null", "[]", "[{}]", "7", '"x"', "{", "{} {}", "{}{}", "not json", "\0",
                     '{"cwd": "/", "cwd": "/"}', "\ufeff{}"):
            with self.subTest(text):
                self.refused(self.call(text))

    def test_a_missing_or_mistyped_field(self):
        whole = json.loads(self.payload("Write", file_path=self.inside("x")))
        self.allowed(self.call(json.dumps(whole)))
        for key in ("cwd", "session_id", "tool_name", "tool_input"):
            for value in (None, 7, [], {}, True) if key != "tool_input" else (None, 7, [], "x", True):
                with self.subTest((key, value)):
                    given = dict(whole, **{key: value})
                    self.refused(self.call(json.dumps(given)))
            with self.subTest(("missing", key)):
                self.refused(self.call(json.dumps({k: v for k, v in whole.items() if k != key})), "needs a string")

    def test_a_session_id_that_cannot_name_a_directory(self):
        for session in ("", "a/b", "..", ".", "a b", "a\nb", "x" * 65, "\u00e9", "a.b", "../x", "a\0"):
            with self.subTest(repr(session)):
                self.refused(self.call(self.payload("Write", session=session, file_path=self.inside("x"))),
                             "session id")

    def test_another_session_cannot_use_this_directory(self):
        other = os.path.join(os.path.dirname(self.pad), "sess-2", "pad", "x")
        self.refused(self.write(other), "not below")
        self.refused(self.call(self.payload("Write", session="sess-2", file_path=self.inside("x"))), "not below")

    def test_a_working_directory_that_is_not_a_plain_absolute_path(self):
        for cwd in ("", "relative", ".", "..", self.real + "/..", self.real + "/./", self.real + "//", self.real + "\0"):
            with self.subTest(repr(cwd)):
                self.refused(self.call(self.payload("Write", cwd=cwd, file_path=self.inside("x"))))

    def test_a_working_directory_outside_any_project(self):
        self.refused(self.call(self.payload("Write", cwd=self.outside, file_path=self.inside("x"))))

    def test_a_working_directory_with_a_character_the_scratch_name_cannot_hold(self):
        odd = os.path.join(self.real, "caf\u00e9")
        os.makedirs(odd)
        self.refused(self.call(self.payload("Write", cwd=odd, file_path=self.inside("x"))),
                     "scratch directory's name")

    def test_every_other_character_of_the_working_directory_becomes_a_dash(self):
        for name in ("has space", "under_score", "dot.ted", "plus+and=eq"):
            with self.subTest(name):
                there = os.path.join(self.real, name)
                os.makedirs(there)
                key = re.sub(r"[^A-Za-z0-9]", "-", there)
                theirs = os.path.join(self.top, "s-%d" % os.getuid(), key, SESSION, "pad", "x")
                self.allowed(self.call(self.payload("Write", cwd=there, file_path=theirs)))
                self.refused(self.call(self.payload("Write", cwd=there, file_path=self.inside("x"))), "not below")

    def test_a_working_directory_inside_the_project_names_another_scratch_directory(self):
        sub = os.path.join(self.real, "src")
        os.makedirs(sub)
        self.refused(self.call(self.payload("Write", cwd=sub, file_path=self.inside("x"))), "not below")
        key = re.sub(r"[^A-Za-z0-9]", "-", sub)
        theirs = os.path.join(self.top, "s-%d" % os.getuid(), key, SESSION, "pad", "x")
        self.allowed(self.call(self.payload("Write", cwd=sub, file_path=theirs)))

    def test_too_large_an_input(self):
        text = self.payload("Write", file_path=self.inside("x"), content="")
        big = text[:-3] + '"y": "' + "z" * gate_hook.MAX_TRANSPORT + '"}}'
        self.refused(self.call(big), "within")

    def test_a_placeholder_in_the_working_directory_is_not_filled_in_again(self):
        self.assertEqual(["a", "-p-q", "s"], agent_gate.scratch_parts("/a/{cwd_key}/{session_id}", "/p/q", "s"))
        self.assertEqual(["a", "-p-q", "s", "{session_id}"],
                         agent_gate.scratch_parts("/a/{cwd_key}/{session_id}/{session_id}", "/p/q", "s")[:3]
                         + ["{session_id}"])


class Forged(Guarded):
    """The agent builds a project of its own in the directory it can write in, with a manifest and an agent file that
    agree, and moves the working directory there."""

    def forge(self):
        import shutil
        copy = os.path.join(self.top, "forged")
        shutil.copytree(self.real, copy, symlinks=True)
        path = os.path.join(copy, *(AGENT_PATH % "checker").split("/"))
        with open(path, "wb") as handle:
            handle.write(CHECKER.replace(b"make test", b"sh"))
        with open(os.path.join(copy, ".workbench", "manifest.json")) as handle:
            document = json.load(handle)
        import hashlib
        for entry in document["files"]:
            if entry["path"] == AGENT_PATH % "checker":
                entry["hash"] = hashlib.sha256(CHECKER.replace(b"make test", b"sh")).hexdigest()
        with open(os.path.join(copy, ".workbench", "manifest.json"), "w") as handle:
            json.dump(document, handle, sort_keys=True, indent=1)
        return copy

    def test_a_project_inside_the_directory_the_agent_can_write_in_is_not_used(self):
        copy = self.forge()
        key = re.sub(r"[^A-Za-z0-9]", "-", copy)
        theirs = os.path.join(self.top, "s-%d" % os.getuid(), key, SESSION, "pad")
        self.refused(self.call(self.payload("Bash", cwd=copy, command="sh")), "inside the directory")
        self.refused(self.call(self.payload("Write", cwd=copy, file_path=os.path.join(theirs, "x"))),
                     "inside the directory")

    def test_a_working_directory_below_it_is_not_used_even_when_the_root_is_found_elsewhere(self):
        os.makedirs(self.pad)
        self.refused(self.call(self.payload("Write", cwd=self.pad, file_path=self.inside("x"))),
                     "inside the directory")

    def test_a_link_into_it_is_followed_before_the_comparison(self):
        copy = self.forge()
        alias = os.path.join(self.outside, "alias")
        os.symlink(copy, alias)
        self.refused(self.call(self.payload("Bash", cwd=alias, command="sh")), "inside the directory")


class Lookup(Guarded):
    def test_an_unknown_or_unconfined_agent(self):
        self.refused(self.write(self.inside("x"), agent="nobody"), "exactly one is needed")
        self.refused(self.write(self.inside("x"), agent="plain"), "not a confined agent")
        self.refused(self.run_command("make test", agent="plain"), "not a confined agent")

    def test_a_harness_the_workbench_does_not_know_or_without_a_per_agent_hook(self):
        self.refused(self.write(self.inside("x"), harness="nothing"), "not a known harness")
        self.refused(self.write(self.inside("x"), dist=self.dist), "not a known harness")

    def test_the_shape_of_the_input_is_checked_before_the_project_is_looked_up(self):
        with unittest.mock.patch.object(agent_gate, "declared") as looked:
            for cwd, session in (("relative", SESSION), (self.real + "/..", SESSION), (self.real, "a/b"), ("", SESSION)):
                with self.subTest((cwd, session)):
                    self.refused(self.call(self.payload("Write", cwd=cwd, session=session,
                                                        file_path=self.inside("x"))))
        looked.assert_not_called()

    def test_the_arguments_are_checked_before_anything_is_read(self):
        for argv in ([], ["fixture"], ["fixture", "checker", "extra"], ["Fixture", "checker"], ["fixture", "Checker"],
                     ["fixture", "../checker"], ["fixture", "-checker"], ["", "checker"], ["fixture", "a" * 65],
                     ["fixture", "checker.md"]):
            with self.subTest(argv):
                err = io.StringIO()
                code = cli.main(["agent-gate"] + argv, io.StringIO(), err, store_root=self.store_root,
                                distribution=self.gdist, stdin=io.StringIO("{}"))
                self.assertEqual((2, agent_gate.USAGE), (code, err.getvalue()))

    def test_an_agent_file_changed_since_it_was_installed_is_not_read(self):
        path = os.path.join(self.real, *(AGENT_PATH % "checker").split("/"))
        with open(path, "wb") as handle:
            handle.write(CHECKER.replace(b"make test", b"sh"))
        self.refused(self.run_command("sh"), "changed since it was installed")
        self.refused(self.write(self.inside("x")), "changed since it was installed")

    def test_a_removed_agent_file_is_not_found(self):
        os.remove(os.path.join(self.real, *(AGENT_PATH % "checker").split("/")))
        self.refused(self.write(self.inside("x")), "No such file")

    def test_an_agent_file_that_is_a_link_is_not_read(self):
        path = os.path.join(self.real, *(AGENT_PATH % "checker").split("/"))
        os.remove(path)
        loose = os.path.join(self.outside, "checker.md")
        with open(loose, "wb") as handle:
            handle.write(CHECKER)
        os.symlink(loose, path)
        self.refused(self.write(self.inside("x")), "not a regular file (symlink)")

    def test_a_module_declaration_changed_since_it_was_installed(self):
        path = os.path.join(self.real, ".workbench", "p", "tool", "module.json")
        with open(path, "rb") as handle:
            data = handle.read()
        with open(path, "wb") as handle:
            handle.write(data.replace(b"tool", b"tool ", 1) if b"tool" in data else data + b" ")
        self.refused(self.write(self.inside("x")), "changed since it was installed")

    def test_the_rendered_agent_file_is_never_consulted(self):
        rendered = os.path.join(self.real, ".fixture", "agents")
        os.makedirs(rendered)
        with open(os.path.join(rendered, "checker.md"), "w") as handle:
            handle.write("---\nname: checker\ndescription: x\ntools: read, edit, shell\nwrites: scratch\n"
                         "run: sh\n---\n")
        self.refused(self.run_command("sh"), "matches none")


class Ending(Guarded):
    def test_an_unforeseen_error_is_a_refusal(self):
        with unittest.mock.patch.object(agent_gate, "declared", side_effect=RuntimeError("boom")):
            self.refused(self.write(self.inside("x")), "the gate failed (RuntimeError)")
        with unittest.mock.patch.object(agent_gate, "scratch_parts", side_effect=KeyError("boom")):
            self.refused(self.write(self.inside("x")), "the gate failed (KeyError)")

    def test_the_deadline_is_a_refusal(self):
        err = io.StringIO()
        started = time.monotonic()
        with unittest.mock.patch.object(agent_gate, "declared", side_effect=lambda *a: time.sleep(10)):
            code = agent_gate.run(io.StringIO(self.payload("Write", file_path=self.inside("x"))), err,
                                  lambda: agent_gate.known(self.gdist, NAME), "checker", deadline=0.3)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(2, code)
        self.assertTrue(err.getvalue().startswith("refused: the gate did not finish within 0.3 seconds"))

    def test_a_refusal_is_one_line_and_never_echoes_control_text(self):
        err = self.refused(self.call(self.payload("Write\x1b[31m\nrefused: allowed", file_path=self.inside("x"))))
        self.assertNotIn("\x1b", err)

    def test_the_prepare_step_is_inside_the_deadline_and_the_refusal(self):
        err = io.StringIO()

        def broken():
            raise OSError("no")

        self.assertEqual(2, agent_gate.run(io.StringIO("{}"), err, broken, "checker"))
        self.assertTrue(err.getvalue().startswith("refused: the gate failed (OSError)"))

    def test_the_command_is_agent_safe_and_routed(self):
        self.assertIn("agent-gate", rules.AGENT_SAFE)
        self.assertNotIn("agent-gate", rules.OWNER_RUN)

    def test_the_harness_facts_carry_the_layout_entry(self):
        facts = harnesses.known(self.gdist)[NAME]["agent_gate"]
        self.assertEqual((("Edit", "Write"), ("Bash",), self.top + "/s-{uid}/{cwd_key}/{session_id}/pad"), facts)
        self.assertEqual((), harnesses.known(self.dist)[NAME]["agent_gate"])


if __name__ == "__main__":
    unittest.main()
