import copy
import json
import os
import shutil
import tempfile
import unittest

from workbench import declarations as d
from workbench import hashing

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample-package")


def dump(obj):
    return json.dumps(obj).encode("utf-8")


def read_json(*parts):
    with open(os.path.join(FIXTURE, *parts), "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


PACKAGE = read_json("package.json")
NOTES = read_json("sample-notes", "module.json")
HARNESS = read_json("sample-harness", "module.json")


def module(**changes):
    decl = copy.deepcopy(NOTES)
    for key, value in changes.items():
        if value is DELETE:
            decl.pop(key, None)
        else:
            decl[key] = value
    return decl


DELETE = object()


class ParseJsonTest(unittest.TestCase):
    def refused(self, data):
        with self.assertRaises(ValueError):
            d.parse_json(data)

    def test_accepts_an_object(self):
        self.assertEqual(d.parse_json(b'{"a": 1}'), {"a": 1})

    def test_duplicate_key(self):
        self.refused(b'{"a": 1, "a": 2}')

    def test_nested_duplicate_key(self):
        self.refused(b'{"a": {"b": 1, "b": 2}}')

    def test_not_an_object(self):
        for data in (b"[]", b'"x"', b"1", b"null"):
            self.refused(data)

    def test_invalid_utf8(self):
        self.refused(b'{"a": "\xff"}')

    def test_byte_order_mark(self):
        self.refused(b'\xef\xbb\xbf{"a": 1}')

    def test_nan_infinity_and_floats(self):
        for data in (b'{"a": NaN}', b'{"a": Infinity}', b'{"a": 1.5}', b'{"a": 1e3}'):
            self.refused(data)

    def test_trailing_garbage(self):
        self.refused(b'{"a": 1} x')

    def test_too_large(self):
        self.refused(b'{"a": "' + b"x" * d.MAX_DECLARATION_BYTES + b'"}')

    def test_deep_nesting(self):
        self.refused(b'{"a":' + b"[" * 100000 + b"]" * 100000 + b"}")

    def test_nothing_is_evaluated(self):
        # A string that looks like code stays a string.
        self.assertEqual(d.parse_json(b'{"a": "__import__(\'os\')"}'), {"a": "__import__('os')"})


class HostileValueTest(unittest.TestCase):
    def test_lone_surrogates_are_refused_by_the_loader(self):
        for data in (b'{"a": "\\ud800"}', b'{"\\udc00": 1}', b'{"a": ["x", {"b": "\\ud800"}]}'):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    d.parse_json(data)

    def test_a_surrogate_in_a_layout_value_is_a_refusal(self):
        decl = copy.deepcopy(HARNESS)
        decl["layout"] = {"notes": "\ud800"}
        raw = json.dumps(decl).encode("ascii")
        with self.assertRaises(d.DeclarationError):
            d.parse_module(raw, "sample", "sample-harness")

    def test_unhashable_list_entries_are_refusals_not_crashes(self):
        for field in ("provides", "requires", "blocks", "helpers", "slots", "fills", "ships",
                      "writes"):
            for bad in ([1], {}, None):
                with self.subTest(field=field, bad=bad):
                    decl = module(**{field: [bad]})
                    with self.assertRaises(d.DeclarationError):
                        d.parse_module(dump(decl), "sample", "sample-notes")

    def test_a_long_version_is_a_refusal_not_a_crash(self):
        huge = "1" * 5000
        with self.assertRaises(d.DeclarationError):
            d.parse_module(dump(module(version=huge)), "sample", "sample-notes")
        package = dict(PACKAGE, version=huge)
        with self.assertRaises(d.DeclarationError):
            d.parse_package(dump(package))

    def test_an_unknown_key_is_escaped_and_short_in_the_message(self):
        for key in ("\x1b]0;pwned\x07", "k" * 100000):
            with self.subTest(key=key[:10]):
                decl = module(**{key: 1})
                with self.assertRaises(d.DeclarationError) as ctx:
                    d.parse_module(dump(decl), "sample", "sample-notes")
                text = str(ctx.exception)
                self.assertNotIn("\x1b", text)
                self.assertNotIn("\x07", text)
                self.assertLess(len(text), 400)
                package = dict(PACKAGE, **{key: 1})
                with self.assertRaises(d.DeclarationError) as ctx:
                    d.parse_package(dump(package))
                self.assertNotIn("\x1b", str(ctx.exception))
                self.assertLess(len(str(ctx.exception)), 400)


class PackageTest(unittest.TestCase):
    def refused(self, changes, rule):
        decl = copy.deepcopy(PACKAGE)
        for key, value in changes.items():
            if value is DELETE:
                decl.pop(key, None)
            else:
                decl[key] = value
        with self.assertRaises(d.DeclarationError) as ctx:
            d.parse_package(dump(decl))
        self.assertEqual(ctx.exception.scope, "package")
        self.assertEqual(ctx.exception.rule, rule)
        self.assertIn("package", str(ctx.exception))
        return ctx.exception

    def test_valid(self):
        package = d.parse_package(dump(PACKAGE))
        self.assertEqual((package.name, package.version, package.contract),
                         ("sample", (1, 0, 0), 1))
        self.assertEqual(package.modules, ("sample-harness", "sample-notes"))

    def test_unsupported_contract(self):
        err = self.refused({"contract": 2}, "contract")
        self.assertIn("newer", str(err))
        self.assertIn("'sample'", str(err))

    def test_bad_contract_values(self):
        for value in (0, -1, True, "1", None):
            self.refused({"contract": value}, "contract")

    def test_malformed_names(self):
        for value in ("Sample", "1abc", "a b", "a_b", "", "x" * 65, 5, None, "-a"):
            self.refused({"name": value}, "name")

    def test_reserved_names(self):
        for value in ("local", "neutral", "manifest", "manifest-x"):
            self.refused({"name": value}, "reserved-name")

    def test_reserved_and_malformed_module_names(self):
        self.refused({"modules": ["local"]}, "reserved-name")
        self.refused({"modules": ["Bad"]}, "modules")
        self.refused({"modules": ["a", "a"]}, "modules")
        self.refused({"modules": "a"}, "modules")

    def test_versions(self):
        for value in ("1.2.3", "0", "10.0.0.1"):
            d.parse_package(dump(dict(PACKAGE, version=value)))
        for value in ("", "01.0", "1.2.3.4.5", "1..2", "v1", 1, "1.0-beta", "1.-1"):
            self.refused({"version": value}, "version")

    def test_unknown_and_missing_fields(self):
        self.refused({"extra": 1}, "extra")
        for field in d.PACKAGE_FIELDS:
            self.refused({field: DELETE}, field)

    def test_malformed_document(self):
        for data in (b"{", b"[]", b'{"name": "a", "name": "b"}'):
            with self.assertRaises(d.DeclarationError) as ctx:
                d.parse_package(data)
            self.assertEqual(ctx.exception.rule, "package.json")


class ModuleTest(unittest.TestCase):
    def parse(self, decl, **kw):
        return d.parse_module(dump(decl), kw.pop("package", "sample"),
                              kw.pop("expected", decl.get("name", "sample-notes")), **kw)

    def refused(self, rule, first_party=False, **changes):
        decl = module(**changes)
        with self.assertRaises(d.DeclarationError) as ctx:
            self.parse(decl, expected="sample-notes", first_party=first_party)
        err = ctx.exception
        self.assertEqual(err.scope, "module")
        self.assertEqual(err.rule, rule)
        self.assertIn("module 'sample-notes' (package 'sample')", str(err))
        return err

    def test_valid_fixture_modules(self):
        notes = self.parse(NOTES)
        self.assertEqual(notes.type, "module")
        self.assertEqual(notes.requires, (("sample:harness", True),))
        self.assertEqual(notes.writes, ("docs/notes.md",))
        harness = self.parse(HARNESS)
        self.assertEqual(harness.type, "harness")
        self.assertEqual(harness.layout["root"], "none")

    def test_minimal_module(self):
        minimal = {"name": "m", "version": "0.1", "description": "d"}
        got = self.parse(minimal)
        self.assertEqual((got.provides, got.requires, got.blocks, got.type),
                         ((), (), (), "module"))

    def test_declared_name_must_equal_entry(self):
        err = self.refused("name", name="other-name")
        self.assertIn("differs", str(err))

    def test_unknown_and_missing_fields(self):
        self.refused("extra", extra=1)
        for field in ("name", "version", "description"):
            self.refused(field, **{field: DELETE})

    def test_types(self):
        for value in ("harness-x", "Module", None, 3):
            self.refused("type", type=value)
        self.parse(module(type="process"))

    def test_reserved_module_name(self):
        decl = module(name="manifest-a")
        with self.assertRaises(d.DeclarationError) as ctx:
            d.parse_module(dump(decl), "sample", "manifest-a")
        self.assertEqual(ctx.exception.rule, "reserved-name")

    def test_a_trailing_newline_is_not_part_of_a_name(self):
        self.refused("slots", slots=["a\n"])
        self.refused("helpers", helpers=["git\n"])
        self.refused("version", version="1.0\n")
        self.refused("requires", requires=["a\n"])

    def test_description(self):
        for value in ("", "two\nlines", 5, "x" * 201, "tab\there"):
            self.refused("description", description=value)

    def test_capability_formats(self):
        for bad in ("has space", "UPPER", "a:b:c", ":x", "x:", "x" * 65, "é", "perm.deny", 7, ""):
            self.refused("requires", requires=[bad])
            self.refused("blocks", blocks=[bad])

    def test_duplicates(self):
        self.refused("requires", requires=["a", {"capability": "a", "soft": True}])
        self.refused("blocks", blocks=["a", "a"])
        self.refused("provides", provides=["sample:a", "sample:a"])
        self.refused("slots", slots=["a", "a"])
        self.refused("helpers", helpers=["git", "git"])

    def test_requires_shapes(self):
        self.refused("requires", requires=[{"capability": "a", "soft": "yes"}])
        self.refused("requires", requires=[{"soft": True}])
        self.refused("requires", requires=[{"capability": "a", "extra": 1}])
        self.refused("requires", requires="a")
        self.parse(module(requires=["a", {"capability": "b"}]))

    def test_unprefixed_provides_needs_first_party(self):
        self.refused("provides", provides=["plans"])
        self.parse(module(provides=["plans"]), first_party=True)

    def test_third_party_prefix_must_match_package(self):
        self.refused("provides", provides=["other:thing"])
        self.parse(module(provides=["sample:thing"]))

    def test_harness_capability_only_from_a_harness_module(self):
        for cap in d.HARNESS_CAPABILITIES:
            self.refused("provides", first_party=True, provides=[cap])
        decl = copy.deepcopy(HARNESS)
        decl["provides"] = list(d.HARNESS_CAPABILITIES)
        self.parse(decl, first_party=True)

    def test_slots_are_declared_in_slots(self):
        self.refused("provides", provides=["slot:x"])
        self.refused("slots", slots=["Bad"])
        self.refused("slots", slots=["slot:x"])

    def test_fills(self):
        self.parse(module(fills=[{"slot": "slot:notes", "source": "templates/a.md"}]))
        self.refused("fills", fills=[{"slot": "notes", "source": "a.md"}])
        self.refused("fills", fills=[{"slot": "slot:x"}])
        self.refused("fills", fills=[{"slot": "slot:x", "source": "../a"}])
        self.refused("fills", fills=[{"slot": "slot:x", "source": "a", "extra": 1}])
        self.refused("fills", fills=["slot:x"])
        self.refused("fills", fills=[{"slot": "slot:x", "source": "a"},
                                     {"slot": "slot:x", "source": "b"}])

    def test_helpers(self):
        for bad in ("a b", "/bin/sh", "", "-x", "a;b", 3):
            self.refused("helpers", helpers=[bad])

    def test_layout_rules(self):
        decl = copy.deepcopy(HARNESS)
        del decl["layout"]
        with self.assertRaises(d.DeclarationError) as ctx:
            self.parse(decl)
        self.assertEqual(ctx.exception.rule, "layout")
        decl["layout"] = []
        with self.assertRaises(d.DeclarationError):
            self.parse(decl)
        decl["layout"] = {"bogus": 1}
        with self.assertRaises(d.DeclarationError):
            self.parse(decl)
        self.refused("layout", layout={})

    def test_ships_paths(self):
        for bad in ("/abs", "a/../b", "a\\b", "C:x", ".git/hooks/x", "a//b"):
            self.refused("ships", ships=[bad])

    def command(self, **fields):
        entry = {"helper": "scripts/check.sh"}
        entry.update(fields)
        return {"run-it": entry}

    def test_a_module_without_commands_has_none(self):
        self.assertEqual((), self.parse(module()).commands)

    def test_a_command_takes_its_defaults(self):
        got = self.parse(module(commands=self.command())).commands
        self.assertEqual(1, len(got))
        self.assertEqual(("run-it", "scripts/check.sh", "exec", None, ()),
                         (got[0].name, got[0].helper, got[0].runtime, got[0].kit, got[0].arguments))

    def test_a_full_command_is_read(self):
        got = self.parse(module(ships=["scripts"], commands={
            "a": {"helper": "scripts/run", "runtime": "python", "kit": 2, "arguments": ["check", "x-1"]},
            "b": {"helper": "scripts/other", "runtime": "exec"}})).commands
        self.assertEqual(["a", "b"], [c.name for c in got])
        self.assertEqual(("python", 2, ("check", "x-1")), (got[0].runtime, got[0].kit, got[0].arguments))
        self.assertEqual(("exec", None, ()), (got[1].runtime, got[1].kit, got[1].arguments))

    def test_a_command_helper_may_be_a_file_below_a_shipped_directory(self):
        self.parse(module(ships=["scripts"], commands={"a": {"helper": "scripts/deep/run"}}))

    def test_commands_refusals(self):
        many = {"c%d" % n: {"helper": "scripts/check.sh"} for n in range(17)}
        cases = {
            "not an object": [],
            "too many": many,
            "key starts with a dot": {".a": {"helper": "scripts/check.sh"}},
            "key has a space": {"a b": {"helper": "scripts/check.sh"}},
            "key too long": {"a" * 65: {"helper": "scripts/check.sh"}},
            "empty key": {"": {"helper": "scripts/check.sh"}},
            "value not an object": {"a": "scripts/check.sh"},
            "no helper": {"a": {}},
            "unknown field": {"a": {"helper": "scripts/check.sh", "extra": 1}},
            "helper not shipped": {"a": {"helper": "elsewhere/run"}},
            "helper not a string": {"a": {"helper": 3}},
            "helper path refused": {"a": {"helper": "../scripts/check.sh"}},
            "helper is the shipped directory's sibling": {"a": {"helper": "scripts2/run"}},
            "runtime unknown": {"a": {"helper": "scripts/check.sh", "runtime": "perl"}},
            "runtime not a string": {"a": {"helper": "scripts/check.sh", "runtime": 1}},
            "python without a kit": {"a": {"helper": "scripts/check.sh", "runtime": "python"}},
            "kit with exec": {"a": {"helper": "scripts/check.sh", "kit": 1}},
            "kit zero": {"a": {"helper": "scripts/check.sh", "runtime": "python", "kit": 0}},
            "kit above the pin limit": {"a": {"helper": "scripts/check.sh", "runtime": "python",
                                              "kit": 1000000}},
            "kit a string": {"a": {"helper": "scripts/check.sh", "runtime": "python", "kit": "1"}},
            "kit true": {"a": {"helper": "scripts/check.sh", "runtime": "python", "kit": True}},
            "arguments not a list": {"a": {"helper": "scripts/check.sh", "arguments": "check"}},
            "argument not a string": {"a": {"helper": "scripts/check.sh", "arguments": [1]}},
            "argument has an uppercase letter": {"a": {"helper": "scripts/check.sh", "arguments": ["Check"]}},
            "argument starts with a dash": {"a": {"helper": "scripts/check.sh", "arguments": ["-x"]}},
            "argument empty": {"a": {"helper": "scripts/check.sh", "arguments": [""]}},
            "argument too long": {"a": {"helper": "scripts/check.sh", "arguments": ["a" * 33]}},
            "argument repeated": {"a": {"helper": "scripts/check.sh", "arguments": ["x", "x"]}},
            "too many arguments": {"a": {"helper": "scripts/check.sh",
                                         "arguments": ["a%d" % n for n in range(17)]}},
            "kit true with exec": {"a": {"helper": "scripts/check.sh", "kit": True}},
            "kit null with exec": {"a": {"helper": "scripts/check.sh", "kit": None}},
            "kit zero with exec": {"a": {"helper": "scripts/check.sh", "kit": 0}},
            "argument with a newline": {"a": {"helper": "scripts/check.sh", "arguments": ["a\n"]}},
            "argument with a NUL": {"a": {"helper": "scripts/check.sh", "arguments": ["a\x00"]}},
            "argument with a lookalike letter": {"a": {"helper": "scripts/check.sh",
                                                       "arguments": ["\u0430bc"]}},
            "key with a lookalike letter": {"\u0430bc": {"helper": "scripts/check.sh"}},
            "key with a newline": {"a\n": {"helper": "scripts/check.sh"}},
            "helper an integer": {"a": {"helper": 7}},
            "helper a bool": {"a": {"helper": True}},
            "helper in another case than ships": {"a": {"helper": "scripts/CHECK.sh"}},
            "one helper twice": {"a": {"helper": "scripts/check.sh"}, "b": {"helper": "scripts/check.sh"}},
        }
        for label, commands in cases.items():
            with self.subTest(label):
                self.refused("commands", ships=["scripts"] if label == "helper is the shipped directory's sibling"
                             else ["scripts/check.sh"], commands=commands)

    def test_two_commands_may_not_name_helpers_that_differ_only_in_case(self):
        self.refused("commands", ships=["scripts/Run", "scripts/run"],
                     commands={"a": {"helper": "scripts/Run"}, "b": {"helper": "scripts/run"}})

    def check_entry(self, **fields):
        entry = {"helper": "scripts/check.sh", "kit": 1}
        entry.update(fields)
        return [entry]

    def test_a_module_without_checks_has_none(self):
        self.assertEqual((), self.parse(module()).checks)

    def test_a_check_is_read(self):
        got = self.parse(module(ships=["scripts"], checks=[
            {"helper": "scripts/alpha", "kit": 1},
            {"helper": "scripts/deep/beta", "kit": 2}])).checks
        self.assertEqual([("scripts/alpha", 1), ("scripts/deep/beta", 2)],
                         [(c.helper, c.kit) for c in got])
        self.assertEqual(["alpha", "beta"], [c.pin_name for c in got])

    def test_checks_refusals(self):
        many = [{"helper": "scripts/c%d" % n, "kit": 1} for n in range(17)]
        cases = {
            "not a list": {"helper": "scripts/check.sh", "kit": 1},
            "too many": many,
            "entry not an object": ["scripts/check.sh"],
            "no helper": [{"kit": 1}],
            "no kit": [{"helper": "scripts/check.sh"}],
            "unknown field": self.check_entry(runtime="python"),
            "arguments are not allowed": self.check_entry(arguments=[]),
            "helper not shipped": self.check_entry(helper="elsewhere/run"),
            "helper not a string": self.check_entry(helper=3),
            "helper path refused": self.check_entry(helper="../scripts/check.sh"),
            "helper in another case than ships": self.check_entry(helper="scripts/CHECK.sh"),
            "kit zero": self.check_entry(kit=0),
            "kit above the pin limit": self.check_entry(kit=1000000),
            "kit a string": self.check_entry(kit="1"),
            "kit true": self.check_entry(kit=True),
            "kit null": self.check_entry(kit=None),
            "one helper twice": self.check_entry() + self.check_entry(),
            "pin name too long": self.check_entry(helper="scripts/" + "a" * 65),
            "pin name starts with a dot": self.check_entry(helper="scripts/.hidden"),
            "pin name has a space": self.check_entry(helper="scripts/a b"),
            "pin name with a lookalike letter": self.check_entry(helper="scripts/\u0430bc"),
        }
        for label, checks in cases.items():
            with self.subTest(label):
                self.refused("checks", ships=["scripts/check.sh"] if label in (
                    "helper not shipped", "helper in another case than ships") else ["scripts"],
                    checks=checks)

    def test_two_checks_may_not_share_a_pin_name(self):
        self.refused("checks", ships=["a/run", "b/run"], checks=[
            {"helper": "a/run", "kit": 1}, {"helper": "b/run", "kit": 1}])
        self.refused("checks", ships=["a/Run", "b/run"], checks=[
            {"helper": "a/Run", "kit": 1}, {"helper": "b/run", "kit": 1}])

    def test_a_helper_may_not_be_a_command_and_a_check(self):
        self.refused("checks", ships=["scripts/check.sh"], commands=self.command(),
                     checks=self.check_entry())
        self.refused("checks", ships=["scripts/Check.sh", "scripts/check.sh"],
                     commands={"a": {"helper": "scripts/Check.sh"}}, checks=self.check_entry())

    def test_a_check_pin_name_may_not_be_a_command_name_of_the_module(self):
        self.refused("checks", ships=["scripts/check.sh", "tools/go"],
                     commands={"check.sh": {"helper": "tools/go"}}, checks=self.check_entry())
        self.refused("checks", ships=["scripts/check.sh", "tools/go"],
                     commands={"CHECK.sh": {"helper": "tools/go"}}, checks=self.check_entry())

    def process(self, **changes):
        """A process module with one command whose arguments are `region` and `check`."""
        fields = dict(type="process", ships=["scripts/check.sh"],
                      commands={"run-it": {"helper": "scripts/check.sh", "arguments": ["region", "check"]}})
        fields.update(changes)
        return fields

    def test_a_module_without_an_approval_has_none(self):
        self.assertIsNone(self.parse(module()).approval)
        self.assertIsNone(self.parse(module(**self.process())).approval)

    def test_a_process_module_may_declare_the_approval_command(self):
        got = self.parse(module(**self.process(approval={"command": "run-it", "argument": "region"})))
        self.assertEqual({"command": "run-it", "argument": "region"}, got.approval)
        self.assertEqual(("run-it", "region"), (got.approval["command"], got.approval["argument"]))

    def test_approval_refusals(self):
        cases = {
            "not an object": [],
            "a string": "run-it",
            "null": None,
            "empty": {},
            "no argument": {"command": "run-it"},
            "no command": {"argument": "region"},
            "an unknown key": {"command": "run-it", "argument": "region", "plan": "x"},
            "command not a string": {"command": 1, "argument": "region"},
            "argument not a string": {"command": "run-it", "argument": 1},
            "a command the module does not declare": {"command": "other", "argument": "region"},
            "a command differing in case": {"command": "Run-It", "argument": "region"},
            "an argument the command does not list": {"command": "run-it", "argument": "evil"},
            "an empty argument": {"command": "run-it", "argument": ""},
            "an argument differing in case": {"command": "run-it", "argument": "Region"},
        }
        for label, approval in cases.items():
            with self.subTest(label):
                self.refused("approval", **self.process(approval=approval))

    def test_approval_needs_a_command_that_lists_the_argument(self):
        self.refused("approval", **self.process(
            commands={"run-it": {"helper": "scripts/check.sh"}},
            approval={"command": "run-it", "argument": "region"}))

    def test_approval_is_refused_on_any_other_module_type(self):
        approval = {"command": "run-it", "argument": "region"}
        self.refused("approval", **self.process(type="module", approval=approval))
        self.refused("approval", **dict(self.process(approval=approval), type=DELETE))
        decl = copy.deepcopy(HARNESS)
        decl["approval"] = approval
        with self.assertRaises(d.DeclarationError) as ctx:
            self.parse(decl)
        self.assertEqual("approval", ctx.exception.rule)

    def test_the_approval_is_part_of_the_declaration_hash_as_written(self):
        plain = module(**self.process())
        declared = module(**self.process(approval={"command": "run-it", "argument": "region"}))
        self.assertNotEqual(hashing.declaration_hash(plain), hashing.declaration_hash(declared))

    def declared(self, **changes):
        """A process module whose approval lists `region` and `active`, with the new fields."""
        fields = self.process(
            commands={"run-it": {"helper": "scripts/check.sh", "arguments": ["region", "active", "check"]}},
            approval={"command": "run-it", "argument": "region", "active": "active"},
            checkpoints=["approve-plan", "push-shared-branch"],
            caps=[{"name": "review-rounds", "default": 3, "ceiling": 5}])
        fields.update(changes)
        return fields

    def test_checkpoints_caps_and_the_active_argument_verify(self):
        got = self.parse(module(**self.declared()))
        self.assertEqual(("approve-plan", "push-shared-branch"), got.checkpoints)
        self.assertEqual((d.Cap("review-rounds", 3, 5),), got.caps)
        self.assertEqual({"command": "run-it", "argument": "region", "active": "active"}, got.approval)

    def test_a_module_without_them_has_none(self):
        got = self.parse(module(**self.process()))
        self.assertEqual(((), ()), (got.checkpoints, got.caps))
        got = self.parse(module(**self.process(approval={"command": "run-it", "argument": "region"})))
        self.assertNotIn("active", got.approval)

    def test_the_active_argument_refusals(self):
        base = {"command": "run-it", "argument": "region"}
        cases = {
            "an argument the command does not list": dict(base, active="evil"),
            "the same as the region argument": dict(base, active="region"),
            "not a string": dict(base, active=1),
            "null": dict(base, active=None),
            "empty": dict(base, active=""),
            "differing in case": dict(base, active="Active"),
        }
        for label, approval in cases.items():
            with self.subTest(label):
                self.refused("approval", **self.declared(approval=approval))

    def test_checkpoint_refusals(self):
        cases = {
            "not a list": "approve-plan",
            "an object": {"approve-plan": "stop"},
            "null": None,
            "an entry that is not a string": [1],
            "a repeated name": ["a", "a"],
            "an upper-case name": ["Approve"],
            "a name with a space": ["approve plan"],
            "a name starting with a digit": ["1a"],
            "an empty name": [""],
            "a 65-character name": ["a" * 65],
            "more than 16 names": ["c%d" % n for n in range(17)],
        }
        for label, checkpoints in cases.items():
            with self.subTest(label):
                self.refused("checkpoints", **self.declared(checkpoints=checkpoints))
        self.parse(module(**self.declared(checkpoints=["a" * 64])))
        self.parse(module(**self.declared(checkpoints=["c%d" % n for n in range(16)])))
        self.parse(module(**self.declared(checkpoints=[])))

    def test_cap_refusals(self):
        def cap(**changes):
            return [dict({"name": "review-rounds", "default": 3, "ceiling": 5}, **changes)]
        cases = {
            "not a list": {"name": "review-rounds", "default": 3, "ceiling": 5},
            "an entry that is not an object": ["review-rounds"],
            "no ceiling": [{"name": "a", "default": 1}],
            "no default": [{"name": "a", "ceiling": 1}],
            "no name": [{"default": 1, "ceiling": 1}],
            "an unknown key": cap(extra=1),
            "a repeated name": cap() + cap(),
            "a malformed name": cap(name="Review Rounds"),
            "a default of zero": cap(default=0),
            "a negative default": cap(default=-1),
            "a default above the ceiling": cap(default=6),
            "a ceiling of zero": cap(default=0, ceiling=0),
            "a ceiling over 100": cap(default=3, ceiling=101),
            "a boolean default": cap(default=True),
            "a string default": cap(default="3"),
            "a boolean ceiling": cap(default=1, ceiling=True),
            "a null ceiling": cap(ceiling=None),
            "more than 16 caps": [{"name": "c%d" % n, "default": 1, "ceiling": 1} for n in range(17)],
        }
        for label, caps in cases.items():
            with self.subTest(label):
                self.refused("caps", **self.declared(caps=caps))
        with self.assertRaises(d.DeclarationError):
            self.parse(module(**self.declared(caps=cap(default=3.0))))
        self.parse(module(**self.declared(caps=cap(default=100, ceiling=100))))
        self.parse(module(**self.declared(caps=cap(default=1, ceiling=1))))

    def test_the_new_fields_are_refused_on_any_other_module_type(self):
        for field, value in (("checkpoints", ["approve-plan"]),
                             ("caps", [{"name": "a", "default": 1, "ceiling": 1}])):
            with self.subTest(field):
                self.refused(field, **{field: value})
                other = "caps" if field == "checkpoints" else "checkpoints"
                self.refused(field, **self.declared(type="module", approval=DELETE, **{field: value, other: DELETE}))
                decl = copy.deepcopy(HARNESS)
                decl[field] = value
                with self.assertRaises(d.DeclarationError) as ctx:
                    self.parse(decl)
                self.assertEqual(field, ctx.exception.rule)

    def test_the_new_fields_are_part_of_the_declaration_hash(self):
        base = hashing.declaration_hash(module(**self.declared()))
        for label, changes in (
                ("a checkpoint", dict(checkpoints=["approve-plan"])),
                ("a cap default", dict(caps=[{"name": "review-rounds", "default": 2, "ceiling": 5}])),
                ("a cap ceiling", dict(caps=[{"name": "review-rounds", "default": 3, "ceiling": 4}])),
                ("the active argument", dict(approval={"command": "run-it", "argument": "region"}))):
            with self.subTest(label):
                self.assertNotEqual(base, hashing.declaration_hash(module(**self.declared(**changes))))

    def provider(self, **changes):
        """A first-party module that provides `peer-review` with one command whose arguments name `convergence`."""
        fields = dict(provides=["peer-review"], ships=["scripts/check.sh"],
                      commands={"review": {"helper": "scripts/check.sh", "arguments": ["status", "convergence"]}},
                      convergence={"command": "review", "argument": "convergence"})
        fields.update(changes)
        return fields

    def test_a_provider_may_declare_the_convergence_argument(self):
        got = self.parse(module(**self.provider()), first_party=True)
        self.assertEqual({"command": "review", "argument": "convergence"}, got.convergence)

    def test_a_module_without_convergence_has_none(self):
        self.assertIsNone(self.parse(module()).convergence)
        self.assertIsNone(self.parse(module(**self.provider(convergence=DELETE)), first_party=True).convergence)
        self.assertIsNone(self.parse(module(**self.process())).convergence)

    def test_convergence_refusals(self):
        cases = {
            "not an object": [],
            "a string": "review",
            "null": None,
            "empty": {},
            "no argument": {"command": "review"},
            "no command": {"argument": "convergence"},
            "an unknown key": {"command": "review", "argument": "convergence", "plan": "x"},
            "command not a string": {"command": 1, "argument": "convergence"},
            "argument not a string": {"command": "review", "argument": 1},
            "a command the module does not declare": {"command": "other", "argument": "convergence"},
            "a command differing in case": {"command": "Review", "argument": "convergence"},
            "an argument the command does not list": {"command": "review", "argument": "evil"},
            "an empty argument": {"command": "review", "argument": ""},
            "an argument differing in case": {"command": "review", "argument": "Convergence"},
        }
        for label, convergence in cases.items():
            with self.subTest(label):
                self.refused("convergence", first_party=True, **self.provider(convergence=convergence))

    def test_convergence_is_refused_on_a_module_that_does_not_provide_peer_review(self):
        convergence = {"command": "review", "argument": "convergence"}
        self.refused("convergence", **self.provider(provides=["sample:notes"]))
        self.refused("convergence", **self.provider(provides=DELETE))
        self.refused("convergence", **self.provider(provides=["sample:peer-review"]))
        self.refused("convergence", **self.process(
            commands={"review": {"helper": "scripts/check.sh", "arguments": ["status", "convergence"]}},
            convergence=convergence))
        decl = copy.deepcopy(HARNESS)
        decl["convergence"] = convergence
        with self.assertRaises(d.DeclarationError) as ctx:
            self.parse(decl)
        self.assertEqual("convergence", ctx.exception.rule)

    def test_convergence_is_part_of_the_declaration_hash(self):
        plain = hashing.declaration_hash(module(**self.provider(convergence=DELETE)))
        declared = hashing.declaration_hash(module(**self.provider()))
        self.assertNotEqual(plain, declared)

    def test_writes_path_rules(self):
        bad = ["/etc/passwd", "../x", "a/../../x", "a\\b", "C:/x", ".git/config", ".GIT/config",
               ".git./config", "GIT~1/config", "a/.git/x", "link/../x", ".config/project-workbench/s",
               ".Config/Project-Workbench/x", ".workbench", ".workbench/sample",
               ".workbench/sample/other-module/x", ".workbench/other-package/sample-notes/x",
               ".workbench/sample/sample-notes", ".WORKBENCH/sample/other/x", "", "a\x00b"]
        for rel in bad:
            with self.subTest(rel=rel):
                self.refused("writes", writes=[rel])

    def test_writes_inside_own_namespace_is_allowed(self):
        self.parse(module(writes=[".workbench/sample/sample-notes/state.json", "docs/a.md"]))

    def test_writes_collisions(self):
        self.refused("writes", writes=["Docs/a.md", "docs/A.md"])
        self.refused("writes", writes=["docs", "docs/a.md"])
        self.refused("writes", writes=["a.md", "a.md"])


class LoadPackageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(os.path.realpath(self.tmp.name), "pkg")
        shutil.copytree(FIXTURE, self.path)

    def write(self, rel, text):
        full = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)

    def load(self, **kw):
        return d.load_package(self.path, **kw)

    def only_problem(self, loaded):
        self.assertEqual(len(loaded.problems), 1, [str(p) for p in loaded.problems])
        return loaded.problems[0]

    def test_valid_package(self):
        loaded = self.load()
        self.assertEqual(loaded.problems, [])
        self.assertEqual([m.name for m in loaded.modules], ["sample-harness", "sample-notes"])
        self.assertEqual(loaded.package.name, "sample")

    def test_package_level_refusal_names_the_package(self):
        self.write("package.json", json.dumps(dict(PACKAGE, contract=2)))
        loaded = self.load()
        self.assertIsNone(loaded.package)
        err = self.only_problem(loaded)
        self.assertEqual((err.scope, err.subject, err.rule), ("package", "sample", "contract"))

    def test_missing_package_json(self):
        os.remove(os.path.join(self.path, "package.json"))
        err = self.only_problem(self.load())
        self.assertEqual(err.scope, "package")
        self.assertEqual(err.rule, "package.json")

    def test_module_level_refusal_names_the_module(self):
        self.write("sample-notes/module.json", json.dumps(module(type="bogus")))
        loaded = self.load()
        err = self.only_problem(loaded)
        self.assertEqual((err.scope, err.subject, err.rule), ("module", "sample-notes", "type"))
        self.assertEqual([m.name for m in loaded.modules], ["sample-harness"])

    def test_list_entry_directory_and_declared_name_disagree(self):
        self.write("sample-notes/module.json", json.dumps(module(name="renamed")))
        err = self.only_problem(self.load())
        self.assertEqual((err.scope, err.subject, err.rule), ("module", "sample-notes", "name"))

    def test_listed_module_without_directory(self):
        shutil.rmtree(os.path.join(self.path, "sample-notes"))
        err = self.only_problem(self.load())
        self.assertEqual((err.subject, err.rule), ("sample-notes", "directory"))

    def test_listed_module_without_module_json(self):
        os.remove(os.path.join(self.path, "sample-notes", "module.json"))
        err = self.only_problem(self.load())
        self.assertEqual((err.scope, err.subject, err.rule), ("module", "sample-notes", "module.json"))

    def test_extra_module_directory(self):
        self.write("stray/module.json", json.dumps(module(name="stray")))
        err = self.only_problem(self.load())
        self.assertEqual((err.scope, err.rule), ("package", "modules"))
        self.assertIn("stray", str(err))

    def test_other_directories_are_not_modules(self):
        self.write("docs/readme.md", "hello")
        self.assertEqual(self.load().problems, [])

    def test_listed_module_that_is_a_symlink(self):
        shutil.move(os.path.join(self.path, "sample-notes"), os.path.join(self.path, "real"))
        os.symlink("real", os.path.join(self.path, "sample-notes"))
        problems = self.load().problems
        self.assertTrue(any(p.subject == "sample-notes" for p in problems))

    def test_module_json_that_is_a_symlink(self):
        target = os.path.join(self.path, "sample-notes", "module.json")
        shutil.move(target, os.path.join(self.path, "elsewhere.json"))
        os.symlink("../elsewhere.json", target)
        err = self.only_problem(self.load())
        self.assertEqual(err.subject, "sample-notes")

    def test_package_root_symlink_is_refused(self):
        link = self.path + "-link"
        os.symlink(self.path, link)
        loaded = d.load_package(link)
        self.assertIsNone(loaded.package)
        self.assertEqual(loaded.problems[0].scope, "package")

    def test_oversized_declaration(self):
        self.write("sample-notes/module.json", "{" + " " * (d.MAX_DECLARATION_BYTES + 1) + "}")
        err = self.only_problem(self.load())
        self.assertEqual(err.subject, "sample-notes")

    def test_the_load_writes_nothing(self):
        def listing():
            out = []
            for base, dirs, files in os.walk(self.path):
                out += [os.path.join(base, n) for n in dirs + files]
            return sorted(out)
        before = listing()
        self.load()
        self.assertEqual(listing(), before)

    def test_first_party_flag_reaches_modules(self):
        self.write("sample-notes/module.json", json.dumps(module(provides=["plans"])))
        self.assertEqual(len(self.load().problems), 1)
        self.assertEqual(self.load(first_party=True).problems, [])


if __name__ == "__main__":
    unittest.main()
