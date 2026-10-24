import unittest

from workbench import neutral
from tests.support_harness import AGENT, COMMAND, SKILL, tree


def refused(case, files, text=""):
    with case.assertRaises(neutral.NeutralError) as caught:
        neutral.read_items(files)
    case.assertIn(text, str(caught.exception))
    return str(caught.exception)


class ValidItems(unittest.TestCase):
    def test_reads_all_three_kinds(self):
        items = {(i.kind, i.name): i for i in neutral.read_items(tree())}
        self.assertEqual(sorted(items), [("agent", "reviewer"), ("command", "ship"),
                                         ("skill", "sample")])
        agent = items[("agent", "reviewer")]
        self.assertEqual(agent.tools, ("read", "search"))
        self.assertEqual(agent.model, "sonnet")
        self.assertEqual(agent.description, "Reviews changes")
        self.assertEqual(agent.body, "You review.\n")
        self.assertEqual(items[("command", "ship")].args, "[target]")
        self.assertEqual(items[("skill", "sample")].files, ())

    def test_skill_bundled_files_carry_hashes(self):
        files = tree(**{"skills/sample/notes/ref.md": b"ref\n", "skills/sample/run.sh": b"x"})
        skill = [i for i in neutral.read_items(files) if i.kind == "skill"][0]
        self.assertEqual([f.rel for f in skill.files], ["notes/ref.md", "run.sh"])
        self.assertEqual(skill.files[0].data, b"ref\n")
        self.assertEqual(len(skill.files[0].sha256), 64)

    def test_tools_and_needs_are_sorted(self):
        data = AGENT.replace(b"read, search", b"search, read")
        self.assertEqual(neutral.read_items({"agents/reviewer.md": data})[0].tools,
                         ("read", "search"))

    def test_needs_are_read_as_a_set(self):
        text = SKILL.replace(b"A sample skill\n", b"A sample skill\nneeds: hooks, permissions\n")
        item = neutral.read_items({"skills/sample/SKILL.md": text})[0]
        self.assertEqual(item.needs, ("hooks", "permissions"))

    def test_empty_tree_has_no_items(self):
        self.assertEqual(neutral.read_items({}), [])


class Paths(unittest.TestCase):
    def test_escaping_and_odd_paths_are_refused(self):
        for rel in ("skills/../x/SKILL.md", "/skills/x/SKILL.md", "skills/x/../../SKILL.md",
                    "skills/x/.git/config", "skills/x/a\\b", "skills/x/a:b", "skills/x//y"):
            refused(self, {"skills/x/SKILL.md": SKILL.replace(b"sample", b"x"), rel: b"x"})

    def test_unknown_kind_or_stray_file_is_refused(self):
        refused(self, {"hooks/x.md": AGENT}, "hooks")
        refused(self, {"README.md": b"x"}, "README.md")
        refused(self, {"agents/sub/x.md": AGENT}, "agents/sub/x.md")
        refused(self, {"agents/reviewer.txt": AGENT}, "reviewer.txt")
        refused(self, {"skills/loose.md": SKILL}, "skills/loose.md")

    def test_a_skill_without_its_file_is_refused(self):
        refused(self, {"skills/sample/notes.md": b"x"}, "SKILL.md")

    def test_case_variants_collide(self):
        refused(self, {"skills/sample/SKILL.md": SKILL, "skills/sample/skill.md": b"x"},
                "collide")
        refused(self, {"skills/sample/SKILL.md": SKILL, "skills/sample/Notes/a": b"1",
                       "skills/sample/notes/a": b"2"}, "collide")

    def test_bad_names_are_refused(self):
        for name in ("Upper", "a b", "x_y", "-x", "", "a" * 65, "\u0430bc", "x.md"):
            why = "valid name" if name else ""  # an empty skill name is a '//' path
            body = AGENT.replace(b"reviewer", name.encode())
            refused(self, {"agents/%s.md" % name: body}, why)
            refused(self, {"commands/%s.md" % name: COMMAND.replace(b"ship", name.encode())}, why)
            refused(self, {"skills/%s/SKILL.md" % name: SKILL.replace(b"sample", name.encode())},
                    why)

    def test_the_front_matter_name_must_match_the_path(self):
        refused(self, {"agents/other.md": AGENT}, "name")

    def test_a_skill_and_a_command_may_not_share_a_name(self):
        both = {"skills/ship/SKILL.md": SKILL.replace(b"sample", b"ship"),
                "commands/ship.md": COMMAND}
        refused(self, both, "ship")


class FrontMatter(unittest.TestCase):
    def agent(self, head):
        return {"agents/reviewer.md": b"---\n" + head + b"---\nbody\n"}

    base = b"name: reviewer\ndescription: d\ntools: read\n"

    def test_ok(self):
        self.assertEqual(len(neutral.read_items(self.agent(self.base))), 1)

    def test_duplicate_key_is_refused(self):
        refused(self, self.agent(self.base + b"description: again\n"), "twice")

    def test_unknown_key_is_refused(self):
        refused(self, self.agent(self.base + b"allow: shell\n"), "allow")

    def test_missing_required_key_is_refused(self):
        refused(self, self.agent(b"name: reviewer\ndescription: d\n"), "tools")
        refused(self, self.agent(b"name: reviewer\ntools: read\n"), "description")

    def test_agent_only_and_command_only_keys_are_refused_elsewhere(self):
        refused(self, {"skills/sample/SKILL.md": SKILL.replace(b"---\nDo", b"tools: read\n---\nDo")},
                "tools")
        refused(self, {"commands/ship.md": COMMAND.replace(b"args: [target]\n", b"model: x\n")},
                "model")

    def test_tools_must_come_from_the_set(self):
        refused(self, self.agent(self.base.replace(b"read", b"read, delete")), "delete")
        refused(self, self.agent(self.base.replace(b"read", b"Read")), "Read")
        refused(self, self.agent(self.base.replace(b"read", b"read, read")), "read")
        refused(self, self.agent(self.base.replace(b"tools: read", b"tools: ")), "tools")
        refused(self, self.agent(self.base.replace(b"tools: read", b"tools: read,")), "tools")

    def test_needs_must_be_capabilities(self):
        refused(self, self.agent(self.base + b"needs: teleport\n"), "teleport")

    def test_a_multi_line_or_folded_value_is_refused(self):
        refused(self, self.agent(self.base + b"  continued: x\n"), "line")
        refused(self, self.agent(b"name: reviewer\ndescription: >\n  folded\ntools: read\n"),
                "description")
        refused(self, self.agent(b"name: reviewer\ndescription: |\ntools: read\n"), "description")

    def test_values_that_start_a_block_or_have_edge_spaces_are_refused(self):
        for value in (b"|", b">", b">-", b"|+ x", b" lead", b"trail ", b""):
            refused(self, self.agent(b"name: reviewer\ndescription: " + value
                                     + b"\ntools: read\n"), "description")

    def test_lookalike_letters_in_a_value_are_refused(self):
        refused(self, self.agent(b"name: reviewer\ndescription: p\xd0\xb0ss\ntools: read\n"),
                "ASCII")

    def test_a_quoted_value_is_read_literally(self):
        item = neutral.read_items(self.agent(b"name: reviewer\ndescription: \"hi\" # x\ntools: read\n"))[0]
        self.assertEqual(item.description, '"hi" # x')

    def test_control_and_invisible_characters_are_refused(self):
        for value in ("a\tb", "a\x00b", "a\x1bb", "a​b", "a‮b", "a b", "a\x7fb"):
            refused(self, self.agent(b"name: reviewer\ndescription: " + value.encode()
                                     + b"\ntools: read\n"))

    def test_crlf_and_bare_carriage_returns_are_refused(self):
        refused(self, {"agents/reviewer.md": AGENT.replace(b"\n", b"\r\n")}, "carriage")
        refused(self, {"agents/reviewer.md": AGENT.replace(b"sonnet", b"son\rnet")}, "carriage")

    def test_the_fence_is_exact(self):
        refused(self, {"agents/reviewer.md": b"name: reviewer\n"}, "---")
        refused(self, {"agents/reviewer.md": b"---\nname: reviewer\ndescription: d\ntools: read\n"},
                "closing")
        refused(self, {"agents/reviewer.md": b"\n" + AGENT}, "---")
        refused(self, {"agents/reviewer.md": AGENT.replace(b"---\nYou", b"--- \nYou")}, "closing")

    def test_a_body_may_contain_a_fence_line(self):
        data = AGENT + b"---\nmore\n"
        self.assertTrue(neutral.read_items({"agents/reviewer.md": data})[0].body.endswith("more\n"))

    def test_invalid_utf8_is_refused(self):
        refused(self, {"agents/reviewer.md": AGENT + b"\xff"}, "UTF-8")

    def test_model_must_be_a_plain_token(self):
        for model in (b"a b", b"X", b"../x", b"a" * 65):
            refused(self, self.agent(self.base + b"model: " + model + b"\n"), "model")

    def test_description_has_a_length_limit(self):
        refused(self, self.agent(b"name: reviewer\ndescription: "
                                 + b"x" * (neutral.MAX_DESCRIPTION_CHARS + 1)
                                 + b"\ntools: read\n"), "description")


class Bounds(unittest.TestCase):
    def test_item_count(self):
        files = {"commands/c%03d.md" % n: COMMAND.replace(b"ship", b"c%03d" % n)
                 for n in range(neutral.MAX_ITEMS + 1)}
        refused(self, files, "items")

    def test_item_size(self):
        refused(self, {"agents/reviewer.md": AGENT + b"x" * neutral.MAX_ITEM_BYTES}, "too large")

    def test_bundled_file_count_and_total_size(self):
        files = tree(**{"skills/sample/f%03d" % n: b"x" for n in range(neutral.MAX_BUNDLED + 1)})
        refused(self, files, "bundled")
        refused(self, tree(**{"skills/sample/big": b"x" * (neutral.MAX_FILE_BYTES + 1)}), "too large")
        big = b"x" * neutral.MAX_FILE_BYTES
        refused(self, {"skills/s%d/SKILL.md" % n: SKILL.replace(b"sample", b"s%d" % n)
                       for n in range(9)} | {"skills/s%d/big" % n: big for n in range(9)}, "total")


class Rules(unittest.TestCase):
    def test_valid_rules(self):
        rules = neutral.read_rules([
            {"action": "deny", "tool": "shell", "pattern": "wb install"},
            {"action": "ask", "tool": "write", "pattern": "docs/**"}])
        self.assertEqual([(r.action, r.tool, r.pattern) for r in rules],
                         [("deny", "shell", "wb install"), ("ask", "write", "docs/**")])

    def test_allow_is_rejected(self):
        with self.assertRaises(neutral.NeutralError) as caught:
            neutral.read_rules([{"action": "allow", "tool": "shell", "pattern": "ls"}])
        self.assertIn("allow", str(caught.exception))

    def test_bad_rules_are_rejected(self):
        for data in ("x", {"action": "deny"}, [1], [{"action": "deny", "tool": "shell"}],
                     [{"action": "deny", "tool": "shell", "pattern": "x", "extra": 1}],
                     [{"action": "DENY", "tool": "shell", "pattern": "x"}],
                     [{"action": "deny", "tool": "network", "pattern": "x"}],
                     [{"action": "deny", "tool": "shell", "pattern": ""}],
                     [{"action": "deny", "tool": "shell", "pattern": "a\nb"}],
                     [{"action": "deny", "tool": "shell", "pattern": "x" * 300}],
                     [{"action": "deny", "tool": "shell", "pattern": "wb install)"}],
                     [{"action": "deny", "tool": "shell", "pattern": "a) , Bash(*"}],
                     [{"action": "deny", "tool": "shell", "pattern": "wb install:*"}],
                     [{"action": "deny", "tool": "write", "pattern": "../../x"}],
                     [{"action": "deny", "tool": "write", "pattern": "a/../x"}],
                     [{"action": "deny", "tool": "shell", "pattern": "w\u0430b"}],
                     [{"action": "deny", "tool": "shell", "pattern": " lead"}],
                     [{"action": "deny", "tool": "shell", "pattern": 5}],
                     [{"action": "deny", "tool": "shell", "pattern": "x"}] * 2,
                     [{"action": "deny", "tool": "shell", "pattern": "x%d" % n}
                      for n in range(neutral.MAX_RULES + 1)]):
            with self.assertRaises(neutral.NeutralError, msg=repr(data)[:60]):
                neutral.read_rules(data)


if __name__ == "__main__":
    unittest.main()


class ConfinedAgents(unittest.TestCase):
    """The ``writes`` and ``run`` fields of an agent, and every way they are refused."""

    base = b"name: reviewer\ndescription: d\ntools: read, search, edit, shell\n"
    example = b"writes: scratch\nrun: python3 {scratch}/check.py, python3 {scratch}/check.py --fast\n"

    def agent(self, head):
        return {"agents/reviewer.md": b"---\n" + head + b"---\nbody\n"}

    def item(self, extra=b"", base=None):
        return neutral.read_items(self.agent((base or self.base) + extra))[0]

    def test_the_example_is_read_back_field_by_field(self):
        item = self.item(self.example)
        self.assertEqual(item.writes, ("scratch",))
        self.assertEqual(item.run, ("python3 {scratch}/check.py", "python3 {scratch}/check.py --fast"))
        self.assertEqual(item.tools, ("edit", "read", "search", "shell"))

    def test_an_agent_without_the_fields_is_not_confined(self):
        item = self.item()
        self.assertEqual((item.writes, item.run), ((), ()))

    def test_either_field_alone_is_read(self):
        self.assertEqual(self.item(b"writes: scratch\n").run, ())
        self.assertEqual(self.item(b"run: ls -l\n").writes, ())

    def test_only_an_agent_takes_them(self):
        refused(self, {"skills/sample/SKILL.md": SKILL.replace(b"---\nDo", b"writes: scratch\n---\nDo")},
                "writes")
        refused(self, {"commands/ship.md": COMMAND.replace(b"args: [target]\n", b"run: ls\n")}, "run")

    def test_a_repeated_field_is_refused(self):
        refused(self, self.agent(self.base + b"writes: scratch\nwrites: scratch\n"), "twice")
        refused(self, self.agent(self.base + b"run: ls\nrun: ls\n"), "twice")

    def test_writes_takes_only_scratch(self):
        for value in (b"home", b"Scratch", b"scratch, home", b"scratch, scratch", b"scratch,", b"/tmp"):
            refused(self, self.agent(self.base + b"writes: " + value + b"\n"), "writes")

    def test_a_field_without_its_tool_is_refused(self):
        no_edit = b"name: reviewer\ndescription: d\ntools: read, shell\n"
        no_shell = b"name: reviewer\ndescription: d\ntools: read, edit\n"
        refused(self, self.agent(no_edit + b"writes: scratch\n"), "edit")
        refused(self, self.agent(no_shell + b"run: ls\n"), "shell")

    def test_the_agents_tool_beside_either_field_is_refused(self):
        both = b"name: reviewer\ndescription: d\ntools: read, edit, shell, agents\n"
        refused(self, self.agent(both + b"writes: scratch\n"), "agents")
        refused(self, self.agent(both + b"run: ls\n"), "agents")
        self.assertEqual(neutral.read_items(self.agent(both))[0].run, ())  # unconfined is unchanged

    def test_the_web_tool_is_allowed(self):
        web = b"name: reviewer\ndescription: d\ntools: read, edit, web\n"
        self.assertEqual(self.item(b"writes: scratch\n", base=web).writes, ("scratch",))

    def test_run_limits_at_the_bound_and_one_past(self):
        four = ", ".join("ls %d" % n for n in range(4)).encode()
        self.assertEqual(len(self.item(b"run: " + four + b"\n").run), 4)
        five = ", ".join("ls %d" % n for n in range(5)).encode()
        refused(self, self.agent(self.base + b"run: " + five + b"\n"), "at most 4")
        exact = b"a" * 200
        self.assertEqual(self.item(b"run: " + exact + b"\n").run, (exact.decode(),))
        refused(self, self.agent(self.base + b"run: " + exact + b"a\n"), "200")
        # 3 patterns of 190 and a short one is 4 patterns and over 600 characters in the line.
        long = ", ".join(("a" * 190, "b" * 190, "c" * 190, "d" * 40)).encode()
        self.assertGreater(len(long), 600)
        refused(self, self.agent(self.base + b"run: " + long + b"\n"), "600")
        fits = ", ".join(("a" * 195, "b" * 195, "c" * 195, "d" * 5)).encode()
        self.assertLessEqual(len(fits), 600)
        self.assertEqual(len(self.item(b"run: " + fits + b"\n").run), 4)

    def test_an_empty_or_repeated_pattern_is_refused(self):
        for value in (b"ls, ", b"ls,,ls -l", b",ls", b"ls,", b"ls, ls", b"ls ,ls"):
            refused(self, self.agent(self.base + b"run: " + value + b"\n"), "run")

    def test_a_pattern_outside_the_grammar_is_refused(self):
        for bad in (b"ls  -l", b"ls \"x\"", b"ls 'x'", b"ls;id", b"ls&&id", b"ls|id", b"ls$HOME",
                    b"ls `id`", b"ls (x)", b"ls >x", b"ls <x", b"ls\\x", b"ls *", b"ls ?", b"ls [a]",
                    b"ls {x}", b"ls ~", b"ls #x", b"ls !x", b"ls ^x", "ls café".encode(),
                    b"ls\tx", b"{scratch}", b"{scratch}/", b"{scratch}/a/b.py", b"{scratch}/..",
                    b"{scratch}/.hidden", b"{scratch}/-x", b"{scratch}x.py", b"x{scratch}/a.py",
                    b"{scratch}/a{scratch}/b", b"{Scratch}/a.py", b"{tmp}/a.py", b"$scratch/a.py",
                    b"python3 {scratch}/a b.py ;"):
            refused(self, self.agent(self.base + b"run: " + bad + b"\n"), "run")

    def test_a_comma_splits_patterns_so_it_cannot_sit_in_one(self):
        self.assertEqual(self.item(b"run: ls a,ls b\n").run, ("ls a", "ls b"))

    def test_accepted_tokens(self):
        for good in (b"python3 {scratch}/check.py", b"python3 -m unittest", b"git status --short",
                     b"make -C . test=1", b"tool a@b:c%d+e", b"{scratch}/run_1-b.sh --fast",
                     b"python3 {scratch}/a.b.c"):
            self.assertEqual(self.item(b"run: " + good + b"\n").run, (good.decode(),))

    def test_a_line_that_is_not_one_line_of_text_is_refused_as_before(self):
        refused(self, self.agent(self.base + b"run: |\n"), "run")
        refused(self, self.agent(self.base + b"run: ls \n"), "run")
