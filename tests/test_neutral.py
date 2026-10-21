import unittest

from workbench import neutral

SKILL = b"---\nname: sample\ndescription: A sample skill\n---\nDo the thing.\n"
AGENT = (b"---\nname: reviewer\ndescription: Reviews changes\ntools: read, search\n"
         b"model: sonnet\n---\nYou review.\n")
COMMAND = b"---\nname: ship\ndescription: Ship it\nargs: [target]\n---\nShip $ARGUMENTS\n"


def tree(**extra):
    files = {"skills/sample/SKILL.md": SKILL, "agents/reviewer.md": AGENT,
             "commands/ship.md": COMMAND}
    files.update(extra)
    return files


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
