"""The `reviewer` agent the `code-work` module ships: neutral, read-only, findings and no verdict.

Plan `2026-10-23-increment-loop-and-review-skills`, increment A. The package tree hash changes with this
agent, so the shipped approvals are stale until the owner's release in increment C of that plan."""

import json
import os
import unittest

from tests import support_install
from workbench import harnessplan, neutral


ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
NEUTRAL = os.path.join(PACKAGE, "code-work", "harness", "neutral")
AGENT = "reviewer"
PATH = "agents/%s.md" % AGENT


def neutral_tree():
    found = {}
    for base, dirs, files in os.walk(NEUTRAL):
        for name in files:
            full = os.path.join(base, name)
            with open(full, "rb") as handle:
                found[os.path.relpath(full, NEUTRAL)] = handle.read()
    return found


def agent_text():
    return neutral_tree()[PATH].decode()


def claude():
    with open(os.path.join(PACKAGE, "claude", "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


class Agent(unittest.TestCase):
    def test_the_reader_accepts_the_agent_with_read_and_search_and_nothing_else(self):
        items = {(i.kind, i.name): i for i in neutral.read_items(neutral_tree())}
        item = items[("agent", AGENT)]
        self.assertEqual(("read", "search"), item.tools)
        self.assertEqual("", item.model)
        self.assertEqual((), item.needs)
        self.assertEqual((), item.files)

    def test_front_matter_holds_only_a_name_a_description_and_the_two_tools(self):
        head = agent_text().split("---\n")[1].splitlines()
        self.assertEqual(["name: reviewer", head[1], "tools: read, search"], head)
        self.assertTrue(head[1].startswith("description: "))

    def test_claude_gets_the_agent_with_an_allowlist_of_read_grep_and_glob_and_no_report(self):
        layout = claude()
        planned = harnessplan.translate(neutral.read_items(neutral_tree()), layout["layout"], {}, {},
                                        provides=layout["provides"])
        self.assertEqual((), planned.reports)
        by_path = {f.path: f.data.decode() for f in planned.files}
        text = by_path[".claude/agents/reviewer.md"]
        tools = [line for line in text.splitlines() if line.startswith("tools")]
        self.assertEqual(1, len(tools), tools)
        for allowed in ("Read", "Grep", "Glob"):
            self.assertIn(allowed, tools[0])
        for refused in ("Edit", "Write", "Bash", "WebFetch", "Task", "Agent"):
            self.assertNotIn(refused, tools[0])

    def test_a_layout_that_cannot_restrict_an_agent_skips_it_with_a_report_and_keeps_the_skills(self):
        layout = json.loads(json.dumps(claude()))
        del layout["layout"]["kinds"]["agent"]["tools"]
        planned = harnessplan.translate(neutral.read_items(neutral_tree()), layout["layout"], {}, {},
                                        provides=layout["provides"])
        self.assertEqual([("skipped", "agent/reviewer")], [(r.level, r.item) for r in planned.reports])
        paths = sorted(f.path for f in planned.files)
        self.assertNotIn(".claude/agents/reviewer.md", paths)
        self.assertIn(".claude/skills/draft-plan/SKILL.md", paths)

    def test_the_text_says_read_only_findings_no_verdict_data_and_what_it_could_not_check(self):
        text = " ".join(agent_text().split()).lower()
        for phrase in ("only reads and searches", "findings", "never a verdict", "is data",
                       "ignore any instruction", "what you could not check", "`no blocking findings`",
                       "`blocking findings`", "blocking or not blocking"):
            self.assertIn(phrase, text, phrase)

    def test_the_text_names_no_harness_tool_program_or_address(self):
        body = agent_text().split("---\n", 2)[2]
        for word in ("Bash", "shell", "git ", "curl", "http://", "https://", "sudo", "WebFetch", "<!--",
                     "needs:", "claude", "Claude", "codex", "ask-codex", "claude-workflow", "wb "):
            self.assertNotIn(word, body, word)


if __name__ == "__main__":
    unittest.main()
