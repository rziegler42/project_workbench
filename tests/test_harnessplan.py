import copy
import hashlib
import unittest
from unittest import mock

from workbench import harnessplan, neutral
from tests.support_harness import AGENT, SYNTHETIC, COMMAND, SKILL, items, tree
from tests.test_layout import edit


def run(layout=SYNTHETIC, found=None, overrides=None, excludes=None, **kw):
    return harnessplan.translate(found if found is not None else items(), layout,
                                 overrides or {}, excludes or {}, **kw)


def by_path(result):
    return {f.path: f for f in result.files}


def levels(result, level):
    return [r for r in result.reports if r.level == level]


class Paths(unittest.TestCase):
    def test_each_kind_goes_to_the_path_of_the_layout(self):
        self.assertEqual(sorted(by_path(run())), [
            ".fixture/agents/reviewer.md", ".fixture/commands/ship.md",
            ".fixture/skills/sample/SKILL.md"])

    def test_bundled_files_follow_their_skill(self):
        found = items(**{"skills/sample/notes/ref.md": b"ref\n"})
        files = by_path(run(found=found))
        self.assertEqual(files[".fixture/skills/sample/notes/ref.md"].data, b"ref\n")

    def test_a_file_records_mode_hash_and_source(self):
        planned = by_path(run())[".fixture/skills/sample/SKILL.md"]
        self.assertEqual(planned.mode, 0o644)
        self.assertEqual(planned.sha256, hashlib.sha256(planned.data).hexdigest())
        self.assertEqual(planned.source, "skill/sample")

    def test_the_output_is_byte_identical_and_sorted(self):
        first, second = run(), run(found=list(reversed(items())))
        self.assertEqual(first.files, second.files)
        self.assertEqual(first.reports, second.reports)
        self.assertEqual([f.path for f in first.files], sorted(f.path for f in first.files))


class Rendering(unittest.TestCase):
    def test_a_skill(self):
        data = by_path(run())[".fixture/skills/sample/SKILL.md"].data
        self.assertEqual(data, b'---\nname: "sample"\ndescription: "A sample skill"\n---\n'
                               b"Do the thing.\n")

    def test_an_agent_has_a_mapped_allowlist(self):
        data = by_path(run())[".fixture/agents/reviewer.md"].data.decode()
        self.assertIn('tools: "Glob, Grep, Read"\n', data)
        self.assertIn('model: "sonnet"\n', data)
        self.assertTrue(data.endswith("---\nYou review.\n"))

    def test_a_command_maps_args_to_its_harness_field(self):
        data = by_path(run())[".fixture/commands/ship.md"].data.decode()
        self.assertIn('argument-hint: "[target]"\n', data)
        self.assertNotIn("args:", data)

    def test_every_value_is_quoted_so_it_stays_a_string(self):
        for word in ("null", "true", "123", "no", "~", "a: b", '"q"', "x # y", "back\\slash"):
            text = SKILL.replace(b"A sample skill", word.encode())
            data = by_path(run(found=neutral.read_items({"skills/sample/SKILL.md": text})))[
                ".fixture/skills/sample/SKILL.md"].data.decode()
            line = data.split("\n")[2]
            self.assertTrue(line.startswith('description: "') and line.endswith('"'), line)
        text = SKILL.replace(b"name: sample", b"name: null").replace(
            b"skills/sample", b"skills/null")
        found = neutral.read_items({"skills/null/SKILL.md": text})
        self.assertIn('name: "null"\n', by_path(run(found=found))[
            ".fixture/skills/null/SKILL.md"].data.decode())

    def test_a_quoted_value_decodes_to_the_original(self):
        import json
        for word in ('a "b" c', "back\\slash", "plain", "x: y # z"):
            quoted = harnessplan.quote(word)
            self.assertEqual(json.loads(quoted), word)

    def test_empty_optional_fields_are_not_written(self):
        text = AGENT.replace(b"model: sonnet\n", b"")
        found = neutral.read_items({"agents/reviewer.md": text})
        self.assertNotIn("model", by_path(run(found=found))[".fixture/agents/reviewer.md"]
                         .data.decode())

    def test_a_body_that_looks_like_front_matter_is_kept_whole(self):
        body = b"---\nname: other\n---\ntext\n"
        found = neutral.read_items({"skills/sample/SKILL.md": SKILL + body})
        data = by_path(run(found=found))[".fixture/skills/sample/SKILL.md"].data
        self.assertTrue(data.endswith(b"---\nDo the thing.\n" + body))


class Dropping(unittest.TestCase):
    def test_a_field_the_layout_does_not_map_is_dropped_with_a_warning(self):
        layout = edit(["kinds", "command", "fields"], {"name": "name", "description": "description"})
        result = run(layout)
        self.assertNotIn("[target]", by_path(result)[".fixture/commands/ship.md"].data.decode())
        warnings = levels(result, "warning")
        self.assertEqual([(w.item, "args" in w.message) for w in warnings], [("command/ship", True)])

    def test_nothing_is_reported_when_nothing_is_lost(self):
        self.assertEqual(run().reports, ())


class FailClosed(unittest.TestCase):
    def skipped(self, result, item="agent/reviewer"):
        self.assertNotIn(".fixture/agents/reviewer.md", by_path(result))
        found = [r for r in levels(result, "skipped") if r.item == item]
        self.assertEqual(len(found), 1, result.reports)
        return found[0].message

    def test_an_agent_without_a_tools_field_is_never_installed(self):
        fields = {"name": "name", "description": "description", "model": "model"}
        message = self.skipped(run(edit(["kinds", "agent", "fields"], fields)))
        self.assertIn("cannot be restricted", message)

    def test_an_agent_without_a_tools_table_is_never_installed(self):
        message = self.skipped(run(edit(["kinds", "agent", "tools"], None)))
        self.assertIn("cannot be restricted", message)

    def test_an_agent_none_of_whose_tools_can_be_expressed_is_never_installed(self):
        layout = edit(["kinds", "agent", "tools"], {"shell": ["Bash"]})
        self.assertIn("none of its tools", self.skipped(run(layout)))

    def test_a_tool_the_layout_cannot_grant_is_dropped_with_a_warning(self):
        layout = edit(["kinds", "agent", "tools"], {"read": ["Read"]})
        result = run(layout)
        data = by_path(result)[".fixture/agents/reviewer.md"].data.decode()
        self.assertIn('tools: "Read"\n', data)
        self.assertEqual([w.item for w in levels(result, "warning")], ["agent/reviewer"])
        self.assertIn("search", levels(result, "warning")[0].message)

    def test_no_agent_is_ever_written_without_a_tools_line(self):
        for layout in (SYNTHETIC, edit(["kinds", "agent", "tools"], {"read": ["Read"]})):
            for planned in run(layout).files:
                if planned.source.startswith("agent/"):
                    self.assertIn("\ntools: ", planned.data.decode())

    def test_a_kind_the_layout_lacks_is_skipped(self):
        layout = edit(["kinds", "command"], None)
        result = run(layout)
        self.assertNotIn(".fixture/commands/ship.md", by_path(result))
        self.assertEqual([r.item for r in levels(result, "skipped")], ["command/ship"])

    def test_a_kind_the_module_does_not_provide_is_skipped(self):
        result = run(provides=("instructions", "skills", "permissions"))
        self.assertEqual(sorted(r.item for r in levels(result, "skipped")),
                         ["agent/reviewer", "command/ship"])
        self.assertEqual(list(by_path(result)), [".fixture/skills/sample/SKILL.md"])

    def test_an_unverified_layout_is_refused(self):
        with self.assertRaises(harnessplan.PlanError) as caught:
            run(edit(["exclude"], []))
        self.assertIn("layout", str(caught.exception))


class Needs(unittest.TestCase):
    def found(self, needs):
        text = SKILL.replace(b"description: A sample skill\n",
                             b"description: A sample skill\nneeds: " + needs + b"\n")
        return neutral.read_items({"skills/sample/SKILL.md": text})

    def test_met_needs_install(self):
        result = run(found=self.found(b"hooks"))
        self.assertIn(".fixture/skills/sample/SKILL.md", by_path(result))

    def test_unmet_needs_skip_with_a_warning(self):
        result = run(found=self.found(b"hooks"),
                     provides=("instructions", "skills", "agents", "commands", "permissions"))
        self.assertEqual(by_path(result), {})
        skipped = levels(result, "skipped")
        self.assertEqual(len(skipped), 1)
        self.assertIn("hooks", skipped[0].message)


class Overrides(unittest.TestCase):
    def test_an_override_replaces_one_item_only(self):
        own = {"SKILL.md": b"hand written\n", "extra.txt": b"x"}
        result = run(overrides={("skill", "sample"): own})
        files = by_path(result)
        self.assertEqual(files[".fixture/skills/sample/SKILL.md"].data, b"hand written\n")
        self.assertEqual(files[".fixture/skills/sample/extra.txt"].data, b"x")
        self.assertIn(".fixture/agents/reviewer.md", files)
        self.assertEqual([r.item for r in levels(result, "overridden")], ["skill/sample"])

    def test_an_override_drops_the_neutral_bundled_files(self):
        found = items(**{"skills/sample/notes/ref.md": b"ref\n"})
        result = run(found=found, overrides={("skill", "sample"): {"SKILL.md": b"own\n"}})
        self.assertNotIn(".fixture/skills/sample/notes/ref.md", by_path(result))

    def test_an_agent_override_is_one_file(self):
        own = b"---\ntools: Read\n---\nown\n"
        result = run(overrides={("agent", "reviewer"): {"reviewer.md": own}})
        self.assertEqual(by_path(result)[".fixture/agents/reviewer.md"].data, own)

    def test_an_agent_override_without_a_tools_line_is_never_installed(self):
        for data in (b"---\nname: reviewer\ndescription: x\n---\nbody\n", b"no front matter\n",
                     b'---\ntools: ""\n---\n', b"---\nname: x\n---\ntools: Read\n"):
            result = run(overrides={("agent", "reviewer"): {"reviewer.md": data}})
            self.assertNotIn(".fixture/agents/reviewer.md", by_path(result))
            self.assertEqual([r.item for r in levels(result, "skipped")], ["agent/reviewer"])

    def test_an_agent_override_is_held_to_a_strict_tools_line(self):
        head = b"---\nname: a\n"
        bad = [head + b"tools: # nothing\n---\n", head + b"tools: null\n---\n",
               head + b"tools: ~\n---\n", head + b"tools: []\n---\n",
               head + b"tools: |\n---\n", head + b"tools: *\n---\n",
               head + b"tools: Read\ntools: Read\n---\n", head + b"tools: Read\n",
               head + b"tools: Read\n---\r\ntools: Read\n", head + b"tools: Read\n--- \ntools: Read\n",
               head + b'tools: "Read\n---\n', head + b"tools: Read, Bogus\n---\n",
               head + b"description: 'x\ntools: Read'\ntools:\n---\n",
               head + b" tools: Read\n---\n", head + b"tools: ''  # x\n---\n"]
        for data in bad:
            result = run(overrides={("agent", "reviewer"): {"reviewer.md": data}})
            self.assertNotIn(".fixture/agents/reviewer.md", by_path(result), data)

    def test_a_value_that_can_swallow_the_tools_line_is_refused(self):
        for opening in (b'description: "x', b"description: 'x", b"description: [x",
                        b"description: {x", b"description: x---", b"description: |",
                        b"description: >", b"description: &a x", b"description: *a",
                        b"description: !!str x", b"description: a: b", b"description: x #c",
                        b"description: x:", b"description: @x", b"description: -x"):
            data = b"---\nname: a\n" + opening + b"\ntools: Read\nmodel: y\n---\n"
            result = run(overrides={("agent", "reviewer"): {"reviewer.md": data}})
            self.assertNotIn(".fixture/agents/reviewer.md", by_path(result), data)

    def test_a_key_the_layout_does_not_map_is_refused(self):
        for line in (b"hooks: {PreToolUse: x}", b"allowed-tools: Bash", b"permissionmode: x",
                     b"mcpservers: x", b"skills: x"):
            data = b"---\nname: a\ntools: Read\n" + line + b"\n---\n"
            result = run(overrides={("agent", "reviewer"): {"reviewer.md": data}})
            self.assertNotIn(".fixture/agents/reviewer.md", by_path(result), data)

    def test_non_ascii_and_control_characters_in_the_front_matter_are_refused(self):
        for char in ("\u2028", "\u2029", "\u0085", "\u00a0", "\x0b", "\x0c", "\x1c", "\t"):
            for line in ("model: x%stools:%s Bash" % (char, char), "tools: Read%s,Bash" % char,
                         "tools: Read,%sBash" % char, "description: a%s" % char,
                         'description: "a%s\\ntools:%s Bash"' % (char, char),
                         'description: "a%s"' % char):
                data = ("---\nname: a\ntools: Read\n%s\n---\n" % line).encode("utf-8")
                result = run(overrides={("agent", "reviewer"): {"reviewer.md": data}})
                self.assertNotIn(".fixture/agents/reviewer.md", by_path(result), repr(line))

    def test_a_repeated_key_or_a_non_string_plain_value_is_refused(self):
        for lines in ("name: a\nname: b", "description: d\ndescription: e", "model: x\nmodel: y",
                      "name: null", "name: 0x10", "model: true", "model: 1e3", "model: ~",
                      "model: 12", "model: No"):
            data = ("---\ntools: Read\n%s\n---\n" % lines).encode()
            result = run(overrides={("agent", "reviewer"): {"reviewer.md": data}})
            self.assertNotIn(".fixture/agents/reviewer.md", by_path(result), lines)

    def test_a_double_quoted_json_string_value_is_accepted(self):
        data = b'---\nname: "a"\ndescription: "x: y # z"\ntools: "Read"\n---\nb\n'
        result = run(overrides={("agent", "reviewer"): {"reviewer.md": data}})
        self.assertIn(".fixture/agents/reviewer.md", by_path(result))

    def test_good_agent_overrides_are_installed(self):
        for line in (b"tools: Read", b'tools: "Read, Grep"', b"tools: Read,Grep"):
            data = b"---\nname: a\n" + line + b"\n---\nbody\n"
            result = run(overrides={("agent", "reviewer"): {"reviewer.md": data}})
            self.assertIn(".fixture/agents/reviewer.md", by_path(result), data)

    def test_an_agent_override_is_skipped_when_the_layout_cannot_restrict(self):
        own = b"---\ntools: Read\n---\n"
        for layout in (edit(["kinds", "agent", "tools"], None),
                       edit(["kinds", "agent", "fields"], {"name": "name",
                                                          "description": "description"})):
            result = run(layout, overrides={("agent", "reviewer"): {"reviewer.md": own}})
            self.assertNotIn(".fixture/agents/reviewer.md", by_path(result))

    def test_an_agent_override_with_a_tools_line_is_installed(self):
        own = b'---\ntools: "Read"\n---\nbody\n'
        result = run(overrides={("agent", "reviewer"): {"reviewer.md": own}})
        self.assertEqual(by_path(result)[".fixture/agents/reviewer.md"].data, own)

    def test_a_non_text_exclusion_reason_is_an_error(self):
        with self.assertRaises(harnessplan.PlanError):
            run(excludes={("command", "ship"): None})

    def test_items_may_be_any_iterable(self):
        self.assertEqual(len(run(found=iter(items())).files), 3)

    def test_an_override_with_the_wrong_files_is_an_error(self):
        for key, files in ((("agent", "reviewer"), {"other.md": b"x"}),
                           (("agent", "reviewer"), {"reviewer.md": b"x", "b.md": b"y"}),
                           (("skill", "sample"), {"other.md": b"x"}),
                           (("skill", "sample"), {}),
                           (("skill", "sample"), {"SKILL.md": b"x", "../up": b"y"}),
                           (("skill", "sample"), {"SKILL.md": b"x", "/abs": b"y"}),
                           (("skill", "sample"), {"SKILL.md": "text"})):
            with self.assertRaises(harnessplan.PlanError, msg=files):
                run(overrides={key: files})

    def test_an_override_with_no_neutral_item_is_an_error(self):
        with self.assertRaises(harnessplan.PlanError) as caught:
            run(overrides={("skill", "ghost"): {"SKILL.md": b"x"}})
        self.assertIn("skill/ghost", str(caught.exception))

    def test_an_item_both_overridden_and_excluded_is_an_error(self):
        with self.assertRaises(harnessplan.PlanError) as caught:
            run(overrides={("skill", "sample"): {"SKILL.md": b"x"}},
                excludes={("skill", "sample"): "no"})
        self.assertIn("both", str(caught.exception))

    def test_an_override_of_an_item_with_unmet_needs_is_skipped_too(self):
        text = SKILL.replace(b"description: A sample skill\n",
                             b"description: A sample skill\nneeds: hooks\n")
        found = neutral.read_items({"skills/sample/SKILL.md": text})
        result = run(found=found, overrides={("skill", "sample"): {"SKILL.md": b"x"}},
                     provides=("skills",))
        self.assertEqual(by_path(result), {})
        self.assertEqual(len(levels(result, "skipped")), 1)


class Excludes(unittest.TestCase):
    def test_an_excluded_item_is_not_installed_and_is_reported_with_its_reason(self):
        result = run(excludes={("command", "ship"): "not for this harness"})
        self.assertNotIn(".fixture/commands/ship.md", by_path(result))
        excluded = levels(result, "excluded")
        self.assertEqual([(r.item, r.message) for r in excluded],
                         [("command/ship", "not for this harness")])

    def test_excluding_an_item_that_does_not_exist_is_an_error(self):
        with self.assertRaises(harnessplan.PlanError) as caught:
            run(excludes={("command", "ghost"): "why"})
        self.assertIn("command/ghost", str(caught.exception))


class Collisions(unittest.TestCase):
    def test_two_items_on_one_path_are_an_error(self):
        # The validator forbids two kinds sharing a directory, so the translator is also
        # checked against a layout that it was not given the chance to refuse.
        layout = copy.deepcopy(SYNTHETIC)
        layout["kinds"]["command"]["path"] = ".fixture/agents/{name}.md"
        text = COMMAND.replace(b"name: ship", b"name: reviewer")
        found = neutral.read_items({"agents/reviewer.md": AGENT, "commands/reviewer.md": text})
        with mock.patch.object(harnessplan.layout, "problems", return_value=[]):
            with self.assertRaises(harnessplan.PlanError) as caught:
                harnessplan.translate(found, layout, {}, {})
        self.assertIn("same path", str(caught.exception))

    def test_paths_that_differ_only_in_case_are_an_error(self):
        with self.assertRaises(harnessplan.PlanError) as caught:
            run(overrides={("skill", "sample"): {"SKILL.md": b"x", "A.md": b"1", "a.md": b"2"}})
        self.assertIn("collide", str(caught.exception))

    def test_a_file_that_is_also_a_directory_is_an_error(self):
        with self.assertRaises(harnessplan.PlanError):
            run(overrides={("skill", "sample"): {"SKILL.md": b"x", "a": b"1", "a/b": b"2"}})


class Bounds(unittest.TestCase):
    def test_an_override_is_bounded_like_a_neutral_tree(self):
        big = b"x" * (neutral.MAX_FILE_BYTES + 1)
        with self.assertRaises(harnessplan.PlanError):
            run(overrides={("skill", "sample"): {"SKILL.md": b"x", "big": big}})
        many = {"SKILL.md": b"x"}
        many.update({"f%d" % n: b"x" for n in range(neutral.MAX_BUNDLED + 1)})
        with self.assertRaises(harnessplan.PlanError):
            run(overrides={("skill", "sample"): many})


class Root(unittest.TestCase):
    def test_the_root_file_is_the_import_line_and_nothing_else(self):
        planned = harnessplan.render_root(SYNTHETIC)
        self.assertEqual((planned.path, planned.data), ("FIXTURE.md", b"@AGENTS.md\n"))
        self.assertEqual((planned.mode, planned.source), (0o644, "root"))
        self.assertEqual(planned.sha256, hashlib.sha256(b"@AGENTS.md\n").hexdigest())

    def test_a_layout_without_a_root_file_has_none(self):
        layout = edit(("root",), "none")
        layout["exclude"] = [".fixture/"]
        self.assertIsNone(harnessplan.render_root(layout))

    def test_the_import_and_the_file_come_from_the_layout(self):
        layout = edit(("root",), {"file": "ROOT.md", "import": "POLICY.md"})
        layout["exclude"] = ["ROOT.md", ".fixture/"]
        planned = harnessplan.render_root(layout)
        self.assertEqual((planned.path, planned.data), ("ROOT.md", b"@POLICY.md\n"))

    def test_a_layout_that_is_refused_renders_nothing(self):
        with self.assertRaises(harnessplan.PlanError):
            harnessplan.render_root(edit(("root",), {"file": "../x", "import": "AGENTS.md"}))


if __name__ == "__main__":
    unittest.main()
