import json
import os
import tempfile
import unittest

from workbench import verify

HARNESS = {"type": "harness", "layout": {}}


def decl(name, **fields):
    out = {"name": name, "version": "1.0.0", "description": "test module"}
    out.update(fields)
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.realpath(self.tmp.name)

    def package(self, name, modules, dirname=None):
        """Write a package of {module name: declaration fields} and return its path."""
        path = os.path.join(self.root, dirname or name)
        os.makedirs(path)
        self.write(path, "package.json", {"name": name, "version": "1.0.0", "contract": 1,
                                          "modules": sorted(modules)})
        for module, fields in modules.items():
            os.makedirs(os.path.join(path, module))
            self.write(path, module + "/module.json", decl(module, **fields))
        return path

    def write(self, path, rel, value):
        with open(os.path.join(path, rel), "w") as handle:
            json.dump(value, handle)

    def run_set(self, paths, select, **kwargs):
        kwargs.setdefault("which", lambda name: "/bin/" + name)
        if isinstance(paths, str):
            paths = [paths]
        kwargs.setdefault("first_party", paths)
        return verify.verify_packages(paths, select, **kwargs)

    def rules(self, result):
        return [problem.rule for problem in result.problems]

    def accepted(self, result):
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        return result


class PerModuleTest(Base):
    def test_valid_package_without_selection_returns_hashes(self):
        path = self.package("p", {"a": {}, "b": {}})
        result = self.accepted(verify.verify_package(path))
        self.assertEqual([m.name for m in result.modules], ["a", "b"])
        for module in result.modules:
            self.assertEqual(len(module.declaration_hash), 64)
            self.assertEqual(len(module.tree_hash), 64)
            self.assertEqual(module.version, "1.0.0")
        self.assertEqual(result.order, ())

    def test_one_failing_module_refuses_the_package(self):
        path = self.package("p", {"a": {}, "b": {}, "c": {}})
        with open(os.path.join(path, "b", "stray.txt"), "w") as handle:
            handle.write("x")
        result = verify.verify_package(path)
        self.assertFalse(result.accepted)
        self.assertEqual(self.rules(result), ["unaccounted-file"])
        self.assertEqual(result.problems[0].subject, "b")
        self.assertEqual(result.modules, ())
        self.assertEqual(result.order, ())

    def test_package_level_problem_refuses(self):
        path = self.package("p", {"a": {}})
        self.write(path, "package.json", {"name": "p", "version": "1.0.0", "contract": 2,
                                          "modules": ["a"]})
        result = verify.verify_package(path)
        self.assertFalse(result.accepted)
        self.assertEqual(result.problems[0].scope, "package")
        self.assertEqual(result.modules, ())

    def test_a_declaration_error_in_one_module_refuses_all(self):
        path = self.package("p", {"a": {}, "b": {"type": "robot"}})
        result = verify.verify_package(path)
        self.assertFalse(result.accepted)
        self.assertEqual(result.problems[0].subject, "b")

    def test_unprefixed_provides_needs_first_party(self):
        path = self.package("p", {"a": {"provides": ["plans"]}})
        self.assertFalse(verify.verify_package(path).accepted)
        self.assertTrue(verify.verify_package(path, first_party=True).accepted)

    def test_no_packages_is_an_error(self):
        with self.assertRaises(ValueError):
            verify.verify_packages([])

    def test_duplicate_package_name_is_refused(self):
        one = self.package("p", {"a": {}}, dirname="one")
        two = self.package("p", {"a": {}}, dirname="two")
        result = verify.verify_packages([one, two])
        self.assertFalse(result.accepted)
        self.assertEqual(self.rules(result), ["name"])


class SelectionTest(Base):
    def test_unknown_module_is_refused(self):
        path = self.package("p", {"a": HARNESS})
        result = self.run_set(path, ["nope"])
        self.assertFalse(result.accepted)
        self.assertEqual(self.rules(result), ["select"])
        self.assertEqual(result.problems[0].scope, "selection")

    def test_selection_name_is_shown_escaped(self):
        path = self.package("p", {"a": HARNESS})
        result = self.run_set(path, ["x\x1b[31m"])
        self.assertNotIn("\x1b", str(result.problems[0]))

    def test_ambiguous_name_needs_the_package(self):
        one = self.package("one", {"a": HARNESS})
        two = self.package("two", {"a": {}})
        result = self.run_set([one, two], ["a"])
        self.assertEqual(self.rules(result), ["select"])
        self.assertIn("one/a", str(result.problems[0]))
        self.accepted(self.run_set([one, two], ["one/a", "two/a"]))

    def test_selection_checks_are_skipped_after_a_refusal(self):
        path = self.package("p", {"a": HARNESS, "b": {"type": "robot"}})
        result = self.run_set(path, ["a"])
        self.assertFalse(result.accepted)
        self.assertTrue(any("not made" in w for w in result.warnings))
        self.assertNotIn("harness-count", self.rules(result))

    def test_set_checks_only_cover_the_selection(self):
        path = self.package("p", {"h1": HARNESS, "h2": HARNESS, "m": {}})
        self.accepted(self.run_set(path, ["h1", "m"]))
        self.accepted(verify.verify_package(path))


class TypeCountTest(Base):
    def test_two_harness_modules_are_refused(self):
        path = self.package("p", {"h1": HARNESS, "h2": HARNESS})
        result = self.run_set(path, ["h1", "h2"])
        self.assertEqual(self.rules(result), ["harness-count"])
        self.assertIn("p/h1", str(result.problems[0]))
        self.assertIn("p/h2", str(result.problems[0]))

    def test_two_process_modules_are_refused(self):
        path = self.package("p", {"h": HARNESS, "x": {"type": "process"},
                                  "y": {"type": "process"}})
        result = self.run_set(path, ["h", "x", "y"])
        self.assertEqual(self.rules(result), ["process-count"])

    def test_harness_is_required_by_default(self):
        path = self.package("p", {"m": {}})
        result = self.run_set(path, ["m"])
        self.assertEqual(self.rules(result), ["harness-count"])
        self.accepted(self.run_set(path, ["m"], harness_required=False))

    def test_a_process_module_is_optional(self):
        path = self.package("p", {"h": HARNESS})
        self.accepted(self.run_set(path, ["h"]))


class RequirementTest(Base):
    def test_hard_requirement_met(self):
        path = self.package("p", {"h": HARNESS, "a": {"requires": ["p:x"]},
                                  "b": {"provides": ["p:x"]}})
        self.accepted(self.run_set(path, ["h", "a", "b"]))

    def test_hard_requirement_unmet_names_the_capability_and_candidates(self):
        path = self.package("p", {"h": HARNESS, "a": {"requires": ["p:x"]},
                                  "b": {"provides": ["p:x"]}})
        result = self.run_set(path, ["h", "a"])
        self.assertEqual(self.rules(result), ["requires"])
        self.assertEqual(result.problems[0].scope, "module")
        self.assertEqual(result.problems[0].subject, "a")
        self.assertIn("p:x", str(result.problems[0]))
        self.assertIn("p/b", str(result.problems[0]))

    def test_hard_requirement_with_no_candidate_says_to_add_a_package(self):
        path = self.package("p", {"h": HARNESS, "a": {"requires": ["p:x"]}})
        result = self.run_set(path, ["h", "a"])
        self.assertIn("add a package", str(result.problems[0]))

    def test_soft_requirement_unmet_warns(self):
        path = self.package("p", {"h": HARNESS,
                                  "a": {"requires": [{"capability": "p:x", "soft": True}]}})
        result = self.accepted(self.run_set(path, ["h", "a"]))
        self.assertTrue(any("p:x" in w for w in result.warnings))

    def test_a_harness_capability_requirement_is_always_soft(self):
        path = self.package("p", {"h": HARNESS, "a": {"requires": ["hooks"]}})
        result = self.accepted(self.run_set(path, ["h", "a"]))
        self.assertTrue(any("hooks" in w and "skipped" in w for w in result.warnings))

    def test_a_harness_capability_requirement_is_met_by_the_harness(self):
        path = self.package("p", {"h": dict(HARNESS, provides=["hooks"]),
                                  "a": {"requires": ["hooks"]}})
        result = self.accepted(self.run_set(path, ["h", "a"]))
        self.assertEqual(result.warnings, [])

    def test_a_slot_requirement_is_always_soft(self):
        path = self.package("p", {"h": HARNESS, "a": {"requires": ["slot:x"]}})
        result = self.accepted(self.run_set(path, ["h", "a"]))
        self.assertTrue(any("slot:x" in w for w in result.warnings))

    def test_a_slot_fill_is_soft_and_met_by_the_owner(self):
        path = self.package("p", {"h": HARNESS, "owner": {"slots": ["x"]},
                                  "filler": {"fills": [{"slot": "slot:x", "source": "x.md"}]}})
        with open(os.path.join(path, "filler", "x.md"), "w") as handle:
            handle.write("x")
        result = self.accepted(self.run_set(path, ["h", "owner", "filler"]))
        self.assertEqual(result.warnings, [])
        self.assertLess(result.order.index(("p", "owner")), result.order.index(("p", "filler")))

    def test_a_slot_fill_without_an_owner_warns(self):
        path = self.package("p", {"h": HARNESS,
                                  "filler": {"fills": [{"slot": "slot:x", "source": "x.md"}]}})
        with open(os.path.join(path, "filler", "x.md"), "w") as handle:
            handle.write("x")
        result = self.accepted(self.run_set(path, ["h", "filler"]))
        self.assertTrue(any("slot:x" in w for w in result.warnings))

    def test_a_module_does_not_satisfy_its_own_requirement(self):
        path = self.package("p", {"h": HARNESS,
                                  "a": {"provides": ["p:x"], "requires": ["p:x"]}})
        result = self.run_set(path, ["h", "a"])
        self.assertEqual(self.rules(result), ["requires"])

    def test_cross_package_requirement_met_and_unmet(self):
        one = self.package("one", {"h": HARNESS, "a": {"requires": ["two:x"]}})
        two = self.package("two", {"b": {"provides": ["two:x"]}})
        self.accepted(self.run_set([one, two], ["one/h", "one/a", "two/b"]))
        result = self.run_set([one, two], ["one/h", "one/a"])
        self.assertEqual(self.rules(result), ["requires"])
        self.assertIn("two/b", str(result.problems[0]))


class ConflictTest(Base):
    def packages(self):
        return self.package("p", {"h": HARNESS, "blocker": {"blocks": ["p:x"]},
                                  "provider": {"provides": ["p:x"]}})

    def test_conflict_in_either_selection_order(self):
        path = self.packages()
        for select in (["h", "blocker", "provider"], ["h", "provider", "blocker"]):
            with self.subTest(select=select):
                result = self.run_set(path, select)
                self.assertEqual(self.rules(result), ["blocks"])
                text = str(result.problems[0])
                self.assertIn("blocker", text)
                self.assertIn("provider", text)

    def test_no_conflict_when_the_provider_is_not_selected(self):
        self.accepted(self.run_set(self.packages(), ["h", "blocker"]))

    def test_provide_and_block_is_accepted_alone(self):
        path = self.package("p", {"h": HARNESS,
                                  "one": {"provides": ["p:x"], "blocks": ["p:x"]}})
        self.accepted(self.run_set(path, ["h", "one"]))

    def test_provide_and_block_is_refused_with_a_second_provider(self):
        path = self.package("p", {"h": HARNESS,
                                  "one": {"provides": ["p:x"], "blocks": ["p:x"]},
                                  "two": {"provides": ["p:x"]}})
        for select in (["h", "one", "two"], ["h", "two", "one"]):
            with self.subTest(select=select):
                self.assertEqual(self.rules(self.run_set(path, select)), ["blocks"])

    def test_two_provide_and_block_modules_conflict_once(self):
        path = self.package("p", {"h": HARNESS,
                                  "one": {"provides": ["p:x"], "blocks": ["p:x"]},
                                  "two": {"provides": ["p:x"], "blocks": ["p:x"]}})
        self.assertEqual(self.rules(self.run_set(path, ["h", "one", "two"])), ["blocks"])

    def test_blocking_a_slot_conflicts_with_its_owner(self):
        path = self.package("p", {"h": HARNESS, "blocker": {"blocks": ["slot:x"]},
                                  "owner": {"slots": ["x"]}})
        self.assertEqual(self.rules(self.run_set(path, ["h", "blocker", "owner"])), ["blocks"])


class OrderTest(Base):
    def test_order_is_harness_process_then_the_rest(self):
        path = self.package("p", {"zeta": {}, "alpha": {}, "proc": {"type": "process"},
                                  "h": HARNESS})
        result = self.accepted(self.run_set(path, ["zeta", "alpha", "proc", "h"]))
        self.assertEqual(result.order, (("p", "h"), ("p", "proc"), ("p", "zeta"), ("p", "alpha")))

    def test_a_module_follows_the_modules_it_requires_in_its_group(self):
        path = self.package("p", {"h": HARNESS, "a": {"requires": ["p:b"]},
                                  "b": {"provides": ["p:b"], "requires": ["p:c"]},
                                  "c": {"provides": ["p:c"]}})
        result = self.accepted(self.run_set(path, ["h", "a", "b", "c"]))
        self.assertEqual(result.order, (("p", "h"), ("p", "c"), ("p", "b"), ("p", "a")))

    def test_a_soft_requirement_also_orders(self):
        path = self.package("p", {"h": HARNESS,
                                  "a": {"requires": [{"capability": "p:b", "soft": True}]},
                                  "b": {"provides": ["p:b"]}})
        result = self.accepted(self.run_set(path, ["h", "a", "b"]))
        self.assertEqual(result.order, (("p", "h"), ("p", "b"), ("p", "a")))

    def test_a_requirement_on_a_later_group_is_allowed(self):
        # A process module needing a capability that an ordinary module provides.
        path = self.package("p", {"h": HARNESS,
                                  "code-work": {"type": "process", "requires": ["p:ground"]},
                                  "groundwork": {"provides": ["p:ground"]}})
        for select in (["h", "code-work", "groundwork"], ["h", "groundwork", "code-work"]):
            with self.subTest(select=select):
                result = self.accepted(self.run_set(path, select))
                self.assertEqual(result.order, (("p", "h"), ("p", "code-work"),
                                                ("p", "groundwork")))

    def test_a_requirement_on_the_harness_orders_nothing_new(self):
        path = self.package("p", {"h": dict(HARNESS, provides=["hooks"]),
                                  "a": {"requires": ["hooks"]}})
        result = self.accepted(self.run_set(path, ["a", "h"]))
        self.assertEqual(result.order, (("p", "h"), ("p", "a")))

    def test_a_cycle_is_refused_and_named(self):
        path = self.package("p", {"h": HARNESS,
                                  "a": {"provides": ["p:a"], "requires": ["p:b"]},
                                  "b": {"provides": ["p:b"], "requires": ["p:c"]},
                                  "c": {"provides": ["p:c"], "requires": ["p:a"]}})
        result = self.run_set(path, ["h", "a", "b", "c"])
        self.assertFalse(result.accepted)
        self.assertEqual(self.rules(result), ["cycle"])
        self.assertIn("p/a -> p/b -> p/c -> p/a", str(result.problems[0]))
        self.assertEqual(result.order, ())

    def test_a_cycle_across_groups_is_refused(self):
        path = self.package("p", {"h": HARNESS,
                                  "proc": {"type": "process", "provides": ["p:proc"],
                                           "requires": ["p:other"]},
                                  "other": {"provides": ["p:other"], "requires": ["p:proc"]}})
        result = self.run_set(path, ["h", "proc", "other"])
        self.assertEqual(self.rules(result), ["cycle"])

    def test_a_cycle_outside_the_selection_is_ignored(self):
        path = self.package("p", {"h": HARNESS,
                                  "a": {"provides": ["p:a"], "requires": ["p:b"]},
                                  "b": {"provides": ["p:b"], "requires": ["p:a"]}})
        self.accepted(self.run_set(path, ["h"]))

    def test_order_does_not_depend_on_the_directory_listing(self):
        path = self.package("p", {"h": HARNESS, "b": {}, "a": {}})
        first = self.accepted(self.run_set(path, ["h", "b", "a"])).order
        second = self.accepted(self.run_set(path, ["h", "b", "a"])).order
        self.assertEqual(first, second)


class HelperTest(Base):
    def test_a_missing_helper_is_only_a_warning(self):
        path = self.package("p", {"h": HARNESS, "a": {"helpers": ["tool-x", "git"]}})
        result = self.accepted(self.run_set(path, ["h", "a"],
                                            which=lambda name: None if name == "tool-x" else "/x"))
        self.assertEqual(len([w for w in result.warnings if "tool-x" in w]), 1)
        self.assertFalse(any("git" in w for w in result.warnings))

    def test_helpers_of_unselected_modules_are_not_looked_up(self):
        path = self.package("p", {"h": HARNESS, "a": {"helpers": ["tool-x"]}})
        looked = []
        self.accepted(self.run_set(path, ["h"], which=lambda name: looked.append(name)))
        self.assertEqual(looked, [])


class AllOrNothingTest(Base):
    def test_a_failing_module_among_valid_ones_refuses_with_no_hashes(self):
        path = self.package("p", {"h": HARNESS, "a": {}, "b": {}, "c": {"ships": ["missing.sh"]}})
        result = self.run_set(path, ["h", "a", "b"])
        self.assertFalse(result.accepted)
        self.assertEqual(result.modules, ())
        self.assertEqual(result.order, ())
        self.assertEqual(self.rules(result), ["ships"])

    def test_a_set_problem_with_valid_modules_refuses_with_no_hashes(self):
        path = self.package("p", {"h": HARNESS, "a": {"requires": ["p:x"]}})
        result = self.run_set(path, ["h", "a"])
        self.assertFalse(result.accepted)
        self.assertEqual(result.modules, ())

    def test_verification_writes_nothing(self):
        path = self.package("p", {"h": HARNESS, "a": {}})

        def listing():
            found = {}
            for base, dirs, files in os.walk(self.root):
                for name in dirs + files:
                    full = os.path.join(base, name)
                    found[full] = os.stat(full).st_mtime_ns
            return found

        before = listing()
        self.run_set(path, ["h", "a"])
        self.assertEqual(listing(), before)


if __name__ == "__main__":
    unittest.main()
