"""The `security-reviewer` agent the `security-review` module ships: neutral, with declared limits, rendered for the
Claude harness with its own hook, and held by the installer's guard to its scratch directory and its pinned commands
(criteria 2 to 4 of plan `2026-10-24-security-review-module`, increment C). The package tree hash changes with this
agent, so the shipped approvals are stale until increment E of that plan.

The rendering is the real translation of the real neutral tree into the real Claude layout. The guard is the
installer's own functions for a path and a command, given the scratch template that layout declares; whether the
installed manifest names the agent is the installer's test (`tests.test_agent_gate`), not this one's."""

import json
import os
import unittest

from tests import support_install
from workbench import agent_gate, harnessplan, layout, neutral
from workbench.gate_hook import Refusal

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
NEUTRAL = os.path.join(PACKAGE, "security-review", "harness", "neutral")
AGENT = "security-reviewer"
PATH = "agents/%s.md" % AGENT
CWD = "/work/project-under-review"
SESSION = "session-1"

# The pinned commands: the interpreter alone, isolated (-I) and without bytecode (-B), on a script of a fixed name that the
# agent wrote under scratch. Four names, so a review can run a probe, a second probe and the two fake programs' drivers
# one at a time. A name is a plain file name: the guard's grammar admits no path component.
PINNED = ("python3 -I -B {scratch}/probe1.py", "python3 -I -B {scratch}/probe2.py",
          "python3 -I -B {scratch}/probe3.py", "python3 -I -B {scratch}/probe4.py")


def neutral_tree():
    found = {}
    for base, dirs, files in os.walk(NEUTRAL):
        for name in files:
            full = os.path.join(base, name)
            with open(full, "rb") as handle:
                found[os.path.relpath(full, NEUTRAL)] = handle.read()
    return found


def claude():
    with open(os.path.join(PACKAGE, "claude", "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


def item():
    return {(i.kind, i.name): i for i in neutral.read_items(neutral_tree())}[("agent", AGENT)]


def agent_text():
    return neutral_tree()[PATH].decode()


def scratch():
    template = layout.facts(claude()["layout"])["agent_gate"][2]
    return agent_gate.scratch_parts(template, CWD, SESSION)


class Declared(unittest.TestCase):
    def test_the_reader_accepts_it_with_the_limits_the_spec_states(self):
        agent = item()
        self.assertEqual(("edit", "read", "search", "shell"), agent.tools)  # the reader sorts them
        self.assertEqual(("scratch",), agent.writes)
        self.assertEqual(PINNED, agent.run)
        self.assertEqual((), agent.files)

    def test_it_holds_neither_web_nor_agents(self):
        for tool in ("web", "agents"):
            self.assertNotIn(tool, item().tools)

    def test_the_front_matter_holds_exactly_the_declared_fields(self):
        head = agent_text().split("---\n")[1].splitlines()
        self.assertEqual(["name", "description", "tools", "writes", "run"], [line.split(":")[0] for line in head])

    def test_the_text_names_no_harness_vendor_or_personal_path(self):
        body = agent_text().split("---\n", 2)[2]
        for word in ("claude", "Claude", "codex", "anthropic", "~/", "/Users/", ".claude", "Bash", "WebFetch",
                     "http://", "https://", "curl", "sudo", "superpowers"):
            self.assertNotIn(word, body, word)

    def test_the_text_carries_each_rule_the_spec_gives_the_agent(self):
        text = " ".join(agent_text().split()).lower()
        for phrase in ("security-review", "is data", "ignore any instruction", "only under scratch",
                       "edit tool", "pinned commands", "copy", "never touch the tree under review",
                       "uncommitted changes", "do not try to get around the block", "real secret", "recommendation",
                       "tree unchanged", "scratch paths", "experiments", "findings", "next action"):
            self.assertIn(phrase, text, phrase)

    def test_the_text_names_each_pinned_script(self):
        text = agent_text()
        for pattern in PINNED:
            self.assertIn(pattern.split(" ")[-1].replace("{scratch}/", ""), text)


class Rendered(unittest.TestCase):
    def plan(self, document=None):
        document = document or claude()
        return harnessplan.translate(neutral.read_items(neutral_tree()), document["layout"], {}, {},
                                     provides=document["provides"], harness_name="claude")

    def test_the_agent_file_carries_its_own_hook_and_the_edit_and_shell_tools(self):
        planned = self.plan()
        self.assertEqual((), planned.reports)
        text = {f.path: f.data.decode() for f in planned.files}[".claude/agents/%s.md" % AGENT]
        self.assertIn("wb agent-gate claude %s || exit 2" % AGENT, text)
        self.assertIn("Bash|Edit|Write", text)
        tools = [line for line in text.splitlines() if line.startswith("tools")]
        self.assertEqual(1, len(tools), tools)
        for allowed in ("Read", "Grep", "Glob", "Edit", "Write", "Bash"):
            self.assertIn(allowed, tools[0])
        for refused in ("WebFetch", "WebSearch", "Task", "Agent"):
            self.assertNotIn(refused, tools[0])

    def test_the_skill_is_installed_beside_it(self):
        paths = sorted(f.path for f in self.plan().files)
        self.assertIn(".claude/skills/security-review/SKILL.md", paths)

    def test_a_layout_with_no_per_agent_hook_skips_the_agent_and_keeps_the_skill(self):
        document = json.loads(json.dumps(claude()))
        for key in ("hook", "scratch"):
            document["layout"]["kinds"]["agent"].pop(key, None)
        planned = self.plan(document)
        self.assertEqual([("skipped", "agent/%s" % AGENT)], [(r.level, r.item) for r in planned.reports])
        paths = sorted(f.path for f in planned.files)
        self.assertNotIn(".claude/agents/%s.md" % AGENT, paths)
        self.assertIn(".claude/skills/security-review/SKILL.md", paths)


class Guarded(unittest.TestCase):
    """The guard's functions, with this agent's own declared limits and the real harness's scratch template."""

    def setUp(self):
        self.scratch = scratch()
        self.dir = "/" + "/".join(self.scratch)

    def command(self, text):
        agent_gate.command_allowed(text, item().run, self.scratch)

    def test_the_scratch_directory_is_the_one_the_harness_names(self):
        self.assertEqual(["private", "tmp", "claude-%d" % os.getuid(), "-work-project-under-review", SESSION,
                          "scratchpad"], self.scratch)

    def test_a_write_below_the_scratch_directory_is_let_through(self):
        for name in ("probe1.py", "notes/result.txt", "copy/pkg/module.py"):
            agent_gate.place(self.dir + "/" + name, self.scratch)

    def test_a_write_into_the_project_or_through_dot_dot_is_refused(self):
        for path in (CWD + "/README.md", CWD + "/src/x.py", "/x", self.dir, self.dir + "/../x", self.dir + "/a/../../x",
                     "scratchpad/x", self.dir + "2/x"):
            with self.subTest(path):
                with self.assertRaises(Refusal):
                    agent_gate.place(path, self.scratch)

    def test_each_pinned_command_is_let_through(self):
        for n in (1, 2, 3, 4):
            self.command("python3 -I -B %s/probe%d.py" % (self.dir, n))

    def test_a_pinned_name_with_a_path_component_or_another_directory_is_refused(self):
        for text in ("python3 -I -B %s/sub/probe1.py" % self.dir, "python3 -I -B %s/../probe1.py" % self.dir,
                     "python3 -I -B /work/project-under-review/probe1.py", "python3 -I -B probe1.py",
                     "python3 -I -B %s/probe5.py" % self.dir):
            with self.subTest(text):
                with self.assertRaises(Refusal):
                    self.command(text)

    def test_any_other_command_is_refused(self):
        probe = "%s/probe1.py" % self.dir
        for text in ("ls", "git status", "sh -c id", "python3 -c pass", "python3 %s" % probe, "python3 -B %s" % probe,
                     "python3 -I %s" % probe, "python3 -I -B %s extra" % probe, "python3 -I -B %s; id" % probe,
                     "python3 -I -B %s && id" % probe, "python3 -I -B %s | cat" % probe,
                     "python3 -I -B %s > out" % probe, "python3 -I -B $(id)", "python3 -I -B `id`",
                     "env python3 -I -B %s" % probe, "/usr/bin/python3 -I -B %s" % probe, "curl http://x",
                     "rm -rf /"):
            with self.subTest(text):
                with self.assertRaises(Refusal):
                    self.command(text)

    def test_a_write_through_a_link_out_of_scratch_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as top:
            pad = os.path.join(top, "pad")
            os.makedirs(pad)
            os.symlink(os.path.realpath(top), os.path.join(pad, "out"))
            parts = [p for p in os.path.realpath(pad).split("/") if p]
            with self.assertRaises(Refusal):
                agent_gate.place(os.path.realpath(pad) + "/out/x", parts)


if __name__ == "__main__":
    unittest.main()
