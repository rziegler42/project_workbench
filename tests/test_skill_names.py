"""A skill, an agent or a command name is one path in the harness, so no two first-party packages may ship one name.

The packages are read from the tree, so this file names none of them. The inventory spec states which package owns
each ported skill; a row it marks built must name an item that its owner ships."""

import collections
import os
import re
import types
import unittest

from tests import support_words
from workbench import harnessstage

ROOT = support_words.ROOT
SPEC = os.path.join(ROOT, "docs", "specs", "superpowers-ports.md")
KINDS = {"skills": "skill", "agents": "agent", "commands": "command"}
HEX = re.compile(r"\A[0-9a-f]{64}\Z")


def shipped():
    """`{(package directory, module name): {(kind, item name), ...}}` for every module under `packages/`."""
    found = {}
    packages = support_words.PACKAGES
    for package in sorted(os.listdir(packages)):
        for module in sorted(os.listdir(os.path.join(packages, package))):
            neutral = os.path.join(packages, package, module, "harness", "neutral")
            items = set()
            for folder, kind in KINDS.items():
                where = os.path.join(neutral, folder)
                if not os.path.isdir(where):
                    continue
                for entry in sorted(os.listdir(where)):
                    items.add((kind, entry[:-3] if entry.endswith(".md") else entry))
            if os.path.isfile(os.path.join(packages, package, module, "module.json")):
                found[(package, module)] = items
    return found


def read_spec():
    with open(SPEC, encoding="utf-8") as handle:
        return handle.read()


def rows(text, heading, which=0):
    """The body rows of table number `which` (counting from 0) after the line `heading`, as lists of cells."""
    tables, table = [], []
    for line in text.split("\n")[text.split("\n").index(heading) + 1:]:
        if line.startswith("|"):
            table.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif table:
            tables.append(table[2:])
            table = []
    if table:
        tables.append(table[2:])
    return tables[which]


class NamesAreUnique(unittest.TestCase):
    def test_no_two_packages_ship_the_same_name(self):
        seen = collections.defaultdict(list)
        for who, items in shipped().items():
            for kind, name in items:
                # A skill and a command are both `/name`, so they share one namespace.
                seen[("agent" if kind == "agent" else "slash", name)].append("%s/%s" % who)
        repeated = {key: owners for key, owners in seen.items() if len(owners) > 1}
        self.assertEqual({}, repeated)

    def test_the_tree_is_not_empty(self):
        self.assertGreater(sum(len(items) for items in shipped().values()), 0)

    def test_the_installer_refuses_one_path_from_two_modules(self):
        def module(name):
            return types.SimpleNamespace(package="p", name=name)

        def snap(data):
            return types.SimpleNamespace(files={"harness/neutral/skills/x/SKILL.md": data})

        snaps = {("p", "a"): snap(b"one"), ("p", "b"): snap(b"two")}
        with self.assertRaises(harnessstage.Refused) as caught:
            harnessstage.inputs([module("a"), module("b")], snaps, "any")
        text = " ".join(caught.exception.lines)
        self.assertIn("p/a", text)
        self.assertIn("p/b", text)
        self.assertIn("skills/x/SKILL.md", text)


class TheInventoryMatchesThePackages(unittest.TestCase):
    def setUp(self):
        self.text = read_spec()
        self.table = rows(self.text, "## The inventory")
        self.modules = {module: items for (package, module), items in shipped().items()}

    def test_every_row_has_six_cells(self):
        self.assertGreater(len(self.table), 0)
        for row in self.table:
            self.assertEqual(6, len(row), row)

    def test_a_row_marked_built_names_items_its_owner_ships(self):
        built = [row for row in self.table if row[5] == "built"]
        self.assertGreater(len(built), 0)
        for row in built:
            owner = self.modules.get(row[4].strip("`"))
            self.assertIsNotNone(owner, "no module %r for %r" % (row[4], row[0]))
            names = re.findall(r"`([a-z][a-z0-9-]*)`", row[3])
            self.assertTrue(names, row)
            for name in names:
                self.assertTrue(any(name == item for _, item in owner),
                                "%s does not ship %s (row %s)" % (row[4], name, row[0]))

    def test_a_row_without_an_owner_has_no_item_and_no_status(self):
        for row in self.table:
            if row[4] == "none":
                self.assertEqual(["none", "none"], [row[3], row[5]], row)


class TheProvenanceIsRecorded(unittest.TestCase):
    def setUp(self):
        self.text = read_spec()

    def test_the_source_the_date_and_the_licence_are_given(self):
        self.assertRegex(self.text, r"\| source URL \| `https://[^`\s]+`")
        self.assertRegex(self.text, r"\| retrieved \| \d{4}-\d{2}-\d{2} \|")
        self.assertRegex(self.text, r"\| licence \| MIT")

    def test_every_skill_of_the_inventory_has_one_hash(self):
        inventory = [row[0] for row in rows(self.text, "## The inventory")]
        hashes = rows(self.text, "## Source and provenance", 1)
        self.assertEqual(15, len(inventory))
        self.assertEqual(sorted(inventory), sorted(row[0] for row in hashes))
        for name, value in hashes:
            self.assertRegex(value.strip("`"), HEX, name)
        self.assertEqual(len(hashes), len({value for _, value in hashes}))


if __name__ == "__main__":
    unittest.main()
