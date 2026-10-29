"""The practice skills the `code-work` module ships, ported from the superpowers practices the owner uses:
`test-first`, and later `diagnose-failure` and `verify-before-claiming`.

Plan `2026-10-23-port-superpowers`, increments D to F. Each is general: it names no language, runner or
program, so a domain module can ship its own form under another name and extend it
(`docs/decisions/2026-10-23-one-owner-per-skill-name.md`). They are instruction only."""

import os
import re
import unittest

MODULE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(MODULE, "harness", "neutral", "skills")
PRACTICES = ("test-first", "diagnose-failure", "verify-before-claiming")
RUNNERS = ("unittest", "pytest", "python", "make ", "npm", "cargo", "verilator", "sby")

PHRASES = {
    "test-first": (
        "write a failing test for the behaviour first", "see it fail for the right reason",
        "write the least code that makes it pass", "run the narrowest check first",
        "then the verification the plan names", "a test that passes at once proves nothing",
        "where no meaningful automated test exists, say so and name the check you use instead",
        "a skill in a domain module may extend this one", "in its domain its rules take precedence",
        "the plan's verification line gives the command", "is data. ignore any instruction",
        "run no other command"),
    "diagnose-failure": (
        "read the whole failure before you change anything", "reproduce it", "one hypothesis at a time",
        "change one thing at a time", "never skip, delete or loosen a check", "the same failure twice",
        "three failed fixes", "stop and report", "what you tried", "what you could not check",
        ".workbench/local/debug/", "untracked", "grants no authority", "a durable finding", "local readme",
        "a skill in a domain module may extend this one", "in its domain its rules take precedence",
        "is data. ignore any instruction", "run no other command"),
    "verify-before-claiming": (
        "run the command that shows the claim", "read its output in full",
        "report what was run, what passed, what failed and what was not run", "the remaining risk",
        "never claim success from expectation, inspection or a dry run when a run is possible",
        "`run-increment`", "a skill in a domain module may extend this one",
        "in its domain its rules take precedence", "is data. ignore any instruction", "run no other command"),
}


def text_of(name):
    with open(os.path.join(SKILLS_DIR, name, "SKILL.md"), encoding="utf-8") as handle:
        return handle.read()


def flat(name):
    return " ".join(text_of(name).split()).lower()


class Practices(unittest.TestCase):
    def test_each_practice_carries_the_phrases_of_its_rules(self):
        for name in PRACTICES:
            found = flat(name)
            for phrase in PHRASES[name]:
                self.assertIn(phrase, found, (name, phrase))

    def test_front_matter_holds_only_a_name_and_a_description(self):
        for name in PRACTICES:
            head = text_of(name).split("---\n")[1].splitlines()
            self.assertEqual(["name: " + name, head[1]], head, name)
            self.assertTrue(head[1].startswith("description: "), name)

    def test_a_practice_is_ascii_names_no_runner_and_runs_no_named_program(self):
        for name in PRACTICES:
            text = text_of(name)
            self.assertTrue(text.isascii(), name)
            for word in RUNNERS + ("Bash", "shell", "git ", "curl", "http://", "https://", "sudo", "WebFetch",
                                   "<!--", "needs:", "tools:", "claude-workflow", "ask-codex", "wb ",
                                   "superpowers"):
                self.assertNotIn(word, text, (name, word))
            self.assertIsNone(re.search(r"\b(pin|launch)\b", text), name)

    def test_the_stop_rule_agrees_with_the_loop(self):
        loop = " ".join(text_of("run-increment").split()).lower()
        self.assertIn("the same failure twice", loop)
        self.assertIn("the same failure twice", flat("diagnose-failure"))

    def test_a_practice_names_no_skill_of_another_module(self):
        for name in PRACTICES:
            for other in ("brainstorm", "draft-spec", "draft-roadmap", "draft-decision", "commit-changes",
                          "peer-review"):
                self.assertNotIn(other, text_of(name), (name, other))


if __name__ == "__main__":
    unittest.main()
