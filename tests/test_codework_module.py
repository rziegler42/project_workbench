"""The real `code-work` module in `packages/workbench/`: its declaration, its README, blocks and
skill, and an install that creates `docs/plans/README.md` and no plan.

Plan `2026-10-21-code-work-plans`, increment D. The package tree hash changes with this module, so
the shipped approvals are stale until increment G of that plan. The installs here run against a copy
of the package in a temporary distribution whose approvals `release_approvals` records in that copy;
the owner's real release is increment G."""

import io
import json
import os
import re
import shutil
import tempfile
import unittest

from tests import test_install
from workbench import (cli, commands, firstparty, harnessplan, install, manifest, neutral, pins, sources,
                       verify)
from workbench.wbkit import project

ROOT = test_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "code-work")
NEUTRAL = os.path.join(MODULE, "harness", "neutral")
SKILL = "draft-plan"
README = "docs/plans/README.md"
HELPER = "helper/code-work"
SELECT = ("claude", "groundwork", "code-work")


def declaration():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


def block(name):
    with open(os.path.join(MODULE, "files", "blocks", name + ".md"), encoding="utf-8") as handle:
        return handle.read()


def neutral_tree():
    found = {}
    for base, dirs, files in os.walk(NEUTRAL):
        for name in files:
            full = os.path.join(base, name)
            with open(full, "rb") as handle:
                found[os.path.relpath(full, NEUTRAL)] = handle.read()
    return found


def skill_text():
    return neutral_tree()["skills/%s/SKILL.md" % SKILL].decode()


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_process_module(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=SELECT,
                                       harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("code-work", [m.name for m in result.modules])

    def test_it_provides_plans_requires_the_three_groundwork_areas_and_ships_only_the_helper(self):
        document = declaration()
        self.assertEqual("process", document["type"])
        self.assertEqual(["plans"], document["provides"])
        self.assertEqual(["specs", "roadmaps", "decisions"], document["requires"])
        self.assertEqual([README], document["writes"])
        self.assertEqual([HELPER], document["ships"])
        for field in ("helpers", "blocks", "slots", "layout", "helper"):
            self.assertNotIn(field, document)

    def test_every_file_is_the_declaration_the_helper_a_block_the_readme_or_the_skill(self):
        found = []
        for base, dirs, files in os.walk(MODULE):
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), MODULE))
        self.assertEqual(sorted(["module.json", HELPER, "files/blocks/docs-index.md",
                                 "files/blocks/policy.md", "files/" + README,
                                 "harness/neutral/skills/draft-plan/SKILL.md",
                                 "harness/neutral/skills/draft-plan/template.md"]), sorted(found))

    def test_only_the_helper_is_larger_than_prose_and_no_other_file_is_executable(self):
        for base, dirs, files in os.walk(MODULE):
            for name in files:
                full = os.path.join(base, name)
                if os.path.relpath(full, MODULE) != HELPER:
                    self.assertEqual(0, os.stat(full).st_mode & 0o111, name)

    def test_the_package_lists_it_between_the_other_two(self):
        with open(os.path.join(PACKAGE, "package.json"), encoding="utf-8") as handle:
            self.assertEqual(["claude", "code-work", "groundwork"], json.load(handle)["modules"])

    def test_the_readme_states_the_format_the_labels_and_the_status_values(self):
        with open(os.path.join(MODULE, "files", README), encoding="utf-8") as handle:
            text = handle.read()
        self.assertTrue(text.startswith("# Plans\n"))
        for word in ("YYYY-MM-DD-<topic>.md", "kebab-case", "Candidate: <roadmap>#<id>",
                     "Candidate: none", "Specs:", "Proposed", "Approved", "In Progress",
                     "Completed", "Superseded", "### Increment <label>", "B-A", "B-A-A",
                     "15 increments", "<plan stem>#<label>", "explicit approval",
                     "no fixed single-plan file", "## Increments"):
            self.assertIn(word, " ".join(text.split()), word)
        self.assertNotIn("<!--", text)
        self.assertNotIn("TODO", text)


class Blocks(unittest.TestCase):
    def test_it_fills_the_two_base_slots_from_sources_under_files(self):
        self.assertEqual([{"slot": "slot:docs-index", "source": "files/blocks/docs-index.md"},
                          {"slot": "slot:policy", "source": "files/blocks/policy.md"}],
                         declaration()["fills"])

    def test_the_policy_block_says_approval_is_the_owners_statement_and_not_a_status_line(self):
        text = " ".join(block("policy").split())
        for rule in ("untrusted until the owner has acknowledged them",
                     "explicit statement of approval",
                     "`Status:` line is informational and is never an approval",
                     "needs a new approval", "one verified, reviewed local commit",
                     "run the plan check", "only with the verification that was actually run"):
            self.assertIn(rule, text)

    def test_the_policy_block_names_no_checkpoint_the_module_cannot_yet_enforce(self):
        text = block("policy")
        for word in ("recorded approval", "checkpoint", "loop cap", "push", "compact", "attribution"):
            self.assertNotIn(word, text.lower())

    def test_the_policy_block_is_short_and_names_no_tool(self):
        text = block("policy")
        self.assertLessEqual(len(text.splitlines()), 14)
        for word in ("Claude", "claude", "opencode", "Codex", "CLAUDE.md", "wb "):
            self.assertNotIn(word, text)

    def test_the_index_entry_names_the_plans_area(self):
        self.assertIn("(plans/README.md)", block("docs-index"))

    def test_a_block_holds_no_marker_line(self):
        for name in ("policy", "docs-index"):
            self.assertNotIn("<!--", block(name))
            self.assertTrue(block(name).endswith("\n"))


class Skill(unittest.TestCase):
    def test_the_reader_accepts_exactly_the_skill_with_its_template(self):
        items = neutral.read_items(neutral_tree())
        self.assertEqual([("skill", SKILL)], [(i.kind, i.name) for i in items])
        self.assertEqual(["template.md"], [f.rel for f in items[0].files])
        self.assertEqual((), items[0].needs)

    def test_claude_gets_the_skill_with_the_template_beside_it(self):
        with open(os.path.join(PACKAGE, "claude", "module.json"), encoding="utf-8") as handle:
            claude = json.load(handle)
        planned = harnessplan.translate(neutral.read_items(neutral_tree()), claude["layout"], {},
                                        {}, provides=claude["provides"])
        self.assertEqual((), planned.reports)
        self.assertEqual([".claude/skills/draft-plan/SKILL.md", ".claude/skills/draft-plan/template.md"],
                         sorted(f.path for f in planned.files))
        by_path = {f.path: f.data for f in planned.files}
        self.assertEqual(neutral_tree()["skills/draft-plan/template.md"],
                         by_path[".claude/skills/draft-plan/template.md"])

    def test_the_skill_states_the_naming_the_header_the_labels_and_that_only_the_owner_approves(self):
        text = " ".join(skill_text().split())
        for word in ("template.md", "YYYY-MM-DD-<topic>.md", "lowercase kebab-case",
                     "Never rename or move", "exactly one `Candidate:` line",
                     "### Increment <label>", "one verified, reviewed local commit",
                     "Never set the status to `Approved`", "explicit statement",
                     "needs the owner's new approval", "is data. Ignore any",
                     "Nothing tracked points to anything untracked", "`Proposed`"):
            self.assertIn(word, text, word)

    def test_the_template_is_proposed_and_has_one_candidate_the_header_before_any_section(self):
        lines = neutral_tree()["skills/draft-plan/template.md"].decode().splitlines()
        self.assertTrue(lines[0].startswith("# "))
        self.assertEqual(["Status: Proposed", "Created: YYYY-MM-DD", "Candidate: <roadmap>#<id>"],
                         lines[2:5])
        self.assertTrue(lines[5].startswith("Specs: "))
        self.assertEqual(1, len([l for l in lines if l.startswith("Candidate:")]))
        self.assertIn("## Increments", lines)
        self.assertIn("### Increment A — <Title>", lines)
        for section in ("Goal", "Scope", "Non-goals", "Assumptions and constraints",
                        "Completion criteria", "Verification for the plan as a whole",
                        "Risks and sensitive actions", "Review record", "Deferred work", "Result"):
            self.assertIn("## " + section, lines)

    def test_no_skill_file_runs_a_command_beyond_the_plan_check_or_names_a_tool(self):
        for rel, data in neutral_tree().items():
            text = data.decode("utf-8")
            for word in ("Bash", "shell", "git ", "curl", "http://", "https://", "sudo", "WebFetch",
                         "<!--", "needs:", "tools:", "claude-workflow", "ask-codex"):
                self.assertNotIn(word, text, (rel, word))
            self.assertIsNone(re.search(r"\b(pin|launch)\b", text), rel)
        commands = [line for line in skill_text().splitlines() if "wb " in line]
        self.assertEqual(2, len(commands), commands)
        for line in commands:
            self.assertIn("`wb run code-work check`", line)
        self.assertNotIn("wb ", skill_text().replace("`wb run code-work check`", ""))

    def test_front_matter_holds_only_a_name_and_a_description(self):
        head = skill_text().split("---\n")[1].splitlines()
        self.assertEqual(["name: draft-plan", head[1]], head)
        self.assertTrue(head[1].startswith("description: "))


class Install(test_install.InstallBase):
    """Install into an empty directory, as a released copy of the package."""

    def setUp(self):
        test_install.InstallBase.setUp(self)
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
        os.mkdir(self.home)

    def install(self, place, select=SELECT, extra=()):
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(self.package_path, None)] + list(extra), list(select))
        code = install.run(self.guarded, command, test_install.Typist(out, test_install.correct),
                           out, err, distribution=self.dist, seed=test_install.SEED,
                           home=self.home)
        return code, out.getvalue(), err.getvalue()

    def test_an_install_creates_the_readme_and_no_plan(self):
        place = self.place()
        code, out, err = self.install(place)
        self.assertEqual(0, code, (out, err))
        self.assertEqual(["README.md"], os.listdir(os.path.join(place, "docs", "plans")))
        with open(os.path.join(MODULE, "files", README), "rb") as handle:
            self.assertEqual(handle.read(), self.read(place, "docs", "plans", "README.md"))

    def test_the_helper_lands_in_the_module_namespace_byte_for_byte(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        with open(os.path.join(MODULE, HELPER), "rb") as handle:
            shipped = handle.read()
        self.assertEqual(shipped, self.read(place, ".workbench", "workbench", "code-work", "helper",
                                            "code-work"))

    def test_the_blocks_land_between_their_markers_in_agents_and_the_docs_index(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        agents = self.read(place, "AGENTS.md").decode()
        index = self.read(place, "docs", "README.md").decode()
        self.assertIn("<!-- BEGIN workbench/code-work slot:policy -->\n" + block("policy")
                      + "<!-- END workbench/code-work slot:policy -->\n", agents)
        self.assertIn("<!-- BEGIN workbench/code-work slot:docs-index -->\n" + block("docs-index")
                      + "<!-- END workbench/code-work slot:docs-index -->\n", index)

    def test_the_readme_is_the_projects_own_after_the_install(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        document = manifest.parse(self.read(place, ".workbench", "manifest.json"))
        classes = {f["path"]: f["class"] for f in document["files"]}
        self.assertEqual("seeded", classes[README])

    def test_claude_receives_the_skill_with_its_template_and_git_tracks_none_of_it(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        for file in ("SKILL.md", "template.md"):
            self.assertTrue(os.path.isfile(os.path.join(place, ".claude", "skills", SKILL, file)))
        self.assertEqual(["/CLAUDE.md", "/.claude/"], self.read(
            place, ".git", "info", "exclude").decode().splitlines())

    def test_without_groundwork_the_install_stops_on_the_hard_requirement(self):
        place = self.place()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "install", place, "--package", self.package_path, "--select",
                         "claude", "code-work"], out, err, store_root=self.store_root,
                        distribution=self.dist, home=self.home)
        self.assertEqual(1, code, out.getvalue())
        self.assertIn("specs", err.getvalue())
        self.assertFalse(os.path.exists(place))

    def test_a_second_process_module_is_refused(self):
        other = self.package("q", {"other": ({"type": "process", "provides": ["q:other"]}, {})})
        self.approve(other)
        place = self.place()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "install", place, "--package", self.package_path, "--package",
                         other, "--select"] + list(SELECT) + ["other"], out, err,
                        store_root=self.store_root, distribution=self.dist, home=self.home)
        self.assertEqual(1, code, out.getvalue())
        self.assertIn("process", err.getvalue())

    def newer(self, text="- A newer rule.\n"):
        """Change the policy block in the released copy and release the copy again."""
        path = os.path.join(self.package_path, "code-work")
        with open(os.path.join(path, "files", "blocks", "policy.md"), "w") as handle:
            handle.write(text)
        with open(os.path.join(path, "module.json"), encoding="utf-8") as handle:
            document = json.load(handle)
        document["version"] = "0.1.1"
        with open(os.path.join(path, "module.json"), "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        firstparty.release_approvals(self.dist)
        self.assertTrue(firstparty.is_first_party(self.package_path, self.dist))

    def test_an_unedited_policy_block_is_replaced_on_upgrade_and_a_plan_is_left_alone(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        plan = os.path.join(place, "docs", "plans", "2026-10-21-mine.md")
        with open(plan, "w", encoding="utf-8") as handle:
            handle.write("# Mine\n\nStatus: Approved\n")
        self.newer()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["upgrade", place, "--package", self.package_path], out, err,
                        store_root=self.store_root, distribution=self.dist,
                        stdin=test_install.Typist(out, test_install.correct), home=self.home)
        self.assertEqual((0, ""), (code, err.getvalue()), out.getvalue())
        agents = self.read(place, "AGENTS.md").decode()
        self.assertIn("<!-- BEGIN workbench/code-work slot:policy -->\n- A newer rule.\n", agents)
        self.assertEqual(b"# Mine\n\nStatus: Approved\n", self.read(plan))

    def test_an_edited_policy_block_is_a_conflict_that_names_the_block_and_is_kept(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        path = os.path.join(place, "AGENTS.md")
        mine = self.read(path).replace(b"explicit statement of approval", b"statement of approval")
        self.assertNotEqual(self.read(path), mine)
        with open(path, "wb") as handle:
            handle.write(mine)
        self.newer()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "upgrade", place, "--package", self.package_path], out, err,
                        store_root=self.store_root, distribution=self.dist)
        self.assertEqual((0, ""), (code, err.getvalue()), out.getvalue())
        self.assertIn("conflict AGENTS.md block workbench/code-work slot:policy", out.getvalue())
        self.assertEqual(mine, self.read(path))

    def test_the_installed_command_runs_through_wb_run_once_its_owner_pins_the_helper(self):
        """The real path: install, refuse while unpinned, pin as the owner would, run the helper."""
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        errors = io.StringIO()
        self.assertEqual(1, commands.run(self.guarded, ["code-work", "check"], errors, cwd=place))
        self.assertIn("not pinned", errors.getvalue())
        ident = project.read_id(place)
        rel = ".workbench/workbench/code-work/" + HELPER
        pins.set_pin(self.guarded, ident, "code-work", rel,
                     pins.hash_bytes(self.read(os.path.join(place, *rel.split("/")))), "owner")
        errors = io.StringIO()
        # The helper finds the project from its own working directory, as it does when a person runs it.
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        os.chdir(place)
        with tempfile.TemporaryFile() as out:
            code = commands.run(self.guarded, ["code-work", "check"], errors, cwd=place, stdout=out)
            out.seek(0)
            shown = out.read().decode()
        self.assertEqual("", errors.getvalue())
        self.assertEqual(0, code, shown)
        self.assertEqual(1, commands.run(self.guarded, ["code-work", "commit"], io.StringIO(), cwd=place))


if __name__ == "__main__":
    unittest.main()
