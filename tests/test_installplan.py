import hashlib
import json
import os
import tempfile
import unittest
import unittest.mock

from workbench import base, installplan, manifest, snapshot, target, verify
from workbench.installplan import PlanError

HARNESS = {"type": "harness", "layout": {}}
SEED = "11111111-2222-4333-8444-555555555555"


def decl(name, **fields):
    out = {"name": name, "version": "1.0.0", "description": "test module"}
    out.update(fields)
    return out


class PlanTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = os.path.realpath(holder.name)
        self.store = os.path.join(self.root, "store")
        os.mkdir(self.store)
        self.base = base.load_base()

    def package(self, name, modules):
        """modules: {module name: (declaration fields, {relative path: bytes})}."""
        self.count = getattr(self, "count", 0) + 1
        path = os.path.join(self.root, "set%d" % self.count, "pkg-" + name)
        os.makedirs(path)
        with open(os.path.join(path, "package.json"), "w") as handle:
            json.dump({"name": name, "version": "1.0.0", "contract": 1,
                       "modules": sorted(modules)}, handle)
        for module, (fields, files) in modules.items():
            os.makedirs(os.path.join(path, module))
            with open(os.path.join(path, module, "module.json"), "w") as handle:
                json.dump(decl(module, **fields), handle)
            for rel, data in files.items():
                full = os.path.join(path, module, *rel.split("/"))
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "wb") as handle:
                    handle.write(data)
        return path

    def select(self, paths, names, source="https://user:pw@example.test/p?token=1#frag"):
        if isinstance(paths, str):
            paths = [paths]
        result = verify.verify_packages(paths, names, first_party=paths,
                                        which=lambda name: "/bin/" + name)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        by_key = {(v.package, v.name): v for v in result.modules}
        modules = tuple(by_key[key] for key in result.order)
        snaps = {}
        roots = {os.path.basename(p)[len("pkg-"):]: p for p in paths}
        for v in modules:
            snaps[(v.package, v.name)] = snapshot.take(
                os.path.join(roots[v.package], v.name), v)
        packages = tuple(installplan.PackageSource(i.name, source, "main", "a" * 40, i.tree_hash)
                         for i in result.packages)
        return installplan.Selection(modules, packages), snaps

    def plan(self, modules, names, state="missing", **kwargs):
        path = self.package("p", modules)
        selection, snaps = self.select(path, names)
        return self.build(selection, snaps, state=state, **kwargs)

    def build(self, selection, snaps, state="missing", seed=SEED, version="0.1.0"):
        place = os.path.join(self.root, "proj")
        if state != "missing":
            os.makedirs(place, exist_ok=True)
            if state == "git":
                os.mkdir(os.path.join(place, ".git"))
        held = target.open_target(place, self.store, home=self.root + "/nohome")
        self.addCleanup(held.close)
        return installplan.build(held, selection, snaps, self.base, seed, version)

    def paths(self, plan, kind=None):
        return [a.path for a in plan.actions if kind is None or a.kind == kind]

    def action(self, plan, path):
        return [a for a in plan.actions if a.path == path][0]

    NOTES = ({"writes": ["docs/notes.md"], "ships": ["scripts/run.sh"]}, {"files/docs/notes.md": b"# Notes\n",
                                              "scripts/run.sh": b"#!/bin/sh\n"})

    def test_plan_order_and_markers(self):
        plan = self.plan({"h": (HARNESS, {}), "notes": self.NOTES}, ["h", "notes"])
        kinds = [a.kind for a in plan.actions]
        self.assertEqual(["make-target", "create-file", "git-init"], kinds[:3])
        self.assertEqual(installplan.MARKER_PATH, plan.actions[1].path)
        self.assertEqual("create-file", plan.actions[1].kind)
        self.assertEqual("create-dir", kinds[3])
        self.assertEqual(".workbench/manifest.json", plan.actions[-1].path)
        self.assertEqual(".workbench/.gitignore", plan.actions[-2].path)
        self.assertNotIn(".workbench", self.paths(plan, "create-dir"))
        self.assertNotIn(".workbench/local", self.paths(plan, "create-dir"))
        for state, expect in (("empty", ["create-file", "git-init"]),
                              ("git", ["create-file", "create-dir"])):
            other = self.plan({"h": (HARNESS, {})}, ["h"], state=state)
            self.assertEqual(expect, [a.kind for a in other.actions[:2]], state)
            self.assertNotIn("make-target", [a.kind for a in other.actions])
            self.assertEqual(state != "git", other.git_init)
            if state == "git":
                self.assertNotIn("git-init", [a.kind for a in other.actions])
            os.rmdir(os.path.join(self.root, "proj", ".git")) if state == "git" else None
            os.rmdir(os.path.join(self.root, "proj"))

    def test_files_classes_and_modes(self):
        plan = self.plan({"h": (HARNESS, {}), "notes": self.NOTES}, ["h", "notes"])
        self.assertEqual("seeded", self.action(plan, "AGENTS.md").owner_class)
        self.assertEqual("module-owned", self.action(plan, ".workbench/.gitignore").owner_class)
        self.assertEqual(manifest.BASE_IGNORE, self.action(plan, ".workbench/.gitignore").data)
        self.assertEqual("seeded", self.action(plan, "docs/notes.md").owner_class)
        copy = self.action(plan, ".workbench/p/notes/files/docs/notes.md")
        self.assertEqual("module-owned", copy.owner_class)
        self.assertEqual(b"# Notes\n", copy.data)
        # A harness module writes nothing, and the manifest never names it.
        self.assertFalse([p for p in self.paths(plan) if p.startswith(".workbench/p/h")])
        document = plan.manifest
        self.assertEqual(["notes"], [m["name"] for m in document["packages"][0]["modules"]])
        self.assertNotIn(b"harness", self.action(plan, ".workbench/manifest.json").data.lower())
        self.assertEqual(plan.manifest, manifest.parse(
            self.action(plan, ".workbench/manifest.json").data))

    def test_executable_mode_follows_the_module_tree(self):
        files = {"scripts/run.sh": b"#!/bin/sh\n"}
        path = self.package("p", {"h": (HARNESS, {}), "x": ({"ships": ["scripts/run.sh"]}, files)})
        os.chmod(os.path.join(path, "x", "scripts", "run.sh"), 0o755)
        selection, snaps = self.select(path, ["h", "x"])
        plan = self.build(selection, snaps)
        self.assertEqual("x", self.action(plan, ".workbench/p/x/scripts/run.sh").mode)
        self.assertEqual("-", self.action(plan, ".workbench/p/x/module.json").mode)

    def test_filled_slot_keeps_marker_and_orders_blocks(self):
        fill = lambda text: ({"fills": [{"slot": "slot:policy", "source": "policy.md"}]},
                             {"policy.md": text})
        plan = self.plan({"h": (HARNESS, {}), "a": fill(b"Rule A\n"), "b": fill(b"Rule B")},
                         ["h", "a", "b"])
        text = self.action(plan, "AGENTS.md").data.decode()
        one = "<!-- BEGIN p/a slot:policy -->\nRule A\n<!-- END p/a slot:policy -->\n"
        two = "<!-- BEGIN p/b slot:policy -->\nRule B\n<!-- END p/b slot:policy -->\n"
        self.assertIn(one + two + "<!-- @slot: policy -->", text)
        self.assertEqual(1, text.count("<!-- @slot: policy -->"))
        self.assertIn("with blocks: p/a slot:policy, p/b slot:policy",
                      self.action(plan, "AGENTS.md").detail)
        entries = [e for e in plan.manifest["files"] if e["path"] == "AGENTS.md"]
        self.assertEqual(["seeded", "slot block", "slot block"], [e["class"] for e in entries])
        self.assertEqual(hashlib.sha256(self.base.files["AGENTS.md"]).hexdigest(),
                         entries[0]["hash"])
        self.assertEqual(hashlib.sha256(one.encode()).hexdigest(), entries[1]["hash"])
        self.assertEqual(("policy", "p/a"), (entries[1]["slot"], entries[1]["block"]))
        # The baseline is the hash of the bytes actually written.
        baselines = json.loads(plan.store_writes[0][1])
        self.assertEqual(self.action(plan, "AGENTS.md").hash, baselines["baselines"]["AGENTS.md"])

    def test_fill_into_a_slot_marker_of_a_written_markdown_file(self):
        owner = ({"slots": ["extra"], "writes": ["docs/extra.md"]},
                 {"files/docs/extra.md": b"# Extra\n\n<!-- @slot: extra -->\n"})
        filler = ({"fills": [{"slot": "slot:extra", "source": "x.md"}]}, {"x.md": b"added\n"})
        plan = self.plan({"h": (HARNESS, {}), "owner": owner, "filler": filler},
                         ["h", "owner", "filler"])
        text = self.action(plan, "docs/extra.md").data.decode()
        self.assertEqual("# Extra\n\n<!-- BEGIN p/filler slot:extra -->\nadded\n"
                         "<!-- END p/filler slot:extra -->\n<!-- @slot: extra -->\n", text)
        # The module's own namespace copy is untouched.
        self.assertEqual(b"# Extra\n\n<!-- @slot: extra -->\n",
                         self.action(plan, ".workbench/p/owner/files/docs/extra.md").data)

    def refused(self, modules, names, needle):
        with self.assertRaises(PlanError) as caught:
            self.plan(modules, names)
        self.assertIn(needle, str(caught.exception))

    def test_two_modules_writing_one_path_refused(self):
        one = ({"writes": ["docs/x.md"]}, {"files/docs/x.md": b"1"})
        two = ({"writes": ["docs/x.md"]}, {"files/docs/x.md": b"2"})
        self.refused({"h": (HARNESS, {}), "a": one, "b": two}, ["h", "a", "b"], "docs/x.md")

    def test_module_path_colliding_with_base_refused(self):
        bad = ({"writes": ["AGENTS.md"]}, {"files/AGENTS.md": b"mine"})
        self.refused({"h": (HARNESS, {}), "a": bad}, ["h", "a"], "the base writes")

    def test_case_colliding_paths_refused(self):
        one = ({"writes": ["docs/x.md"]}, {"files/docs/x.md": b"1"})
        two = ({"writes": ["docs/X.md"]}, {"files/docs/X.md": b"2"})
        self.refused({"h": (HARNESS, {}), "a": one, "b": two}, ["h", "a", "b"], "collide")

    def test_harness_with_writes_or_fills_refused(self):
        writes = (dict(HARNESS, writes=["docs/h.md"]), {"files/docs/h.md": b"x"})
        self.refused({"h": writes}, ["h"], "harness module")
        fills = (dict(HARNESS, fills=[{"slot": "slot:policy", "source": "p.md"}]),
                 {"p.md": b"x"})
        self.refused({"h": fills}, ["h"], "harness module")

    def test_fill_with_no_or_two_marker_files_refused(self):
        fill = ({"fills": [{"slot": "slot:nowhere", "source": "x.md"}]}, {"x.md": b"x"})
        self.refused({"h": (HARNESS, {}), "a": fill}, ["h", "a"], "no marker")
        two = ({"slots": ["dup"], "writes": ["docs/a.md", "docs/b.md"]},
               {"files/docs/a.md": b"<!-- @slot: dup -->\n",
                "files/docs/b.md": b"<!-- @slot: dup -->\n"})
        filler = ({"fills": [{"slot": "slot:dup", "source": "x.md"}]}, {"x.md": b"x"})
        self.refused({"h": (HARNESS, {}), "o": two, "f": filler}, ["h", "o", "f"], "more than one")

    def test_fill_source_containing_marker_refused(self):
        for text in (b"a\n<!-- @slot: policy -->\n", b"<!-- BEGIN p/x slot:policy -->\n",
                     b"<!-- END p/x slot:policy -->\n"):
            fill = ({"fills": [{"slot": "slot:policy", "source": "x.md"}]}, {"x.md": text})
            self.refused({"h": (HARNESS, {}), "a": fill}, ["h", "a"], "marker line")

    def test_an_existing_project_cannot_be_planned(self):
        class Existing:
            state = "existing"
        with self.assertRaises(PlanError):
            installplan.build(Existing(), None, None, self.base, SEED, "0.1.0")

    def test_same_inputs_same_digest(self):
        path = self.package("p", {"h": (HARNESS, {}), "notes": self.NOTES})
        selection, snaps = self.select(path, ["h", "notes"])
        first = self.build(selection, snaps)
        again = self.build(selection, snaps)
        self.assertEqual(first.digest, again.digest)
        self.assertEqual(64, len(first.digest))
        self.assertEqual(first.actions, again.actions)

    def test_digest_changes_with_any_byte_path_mode_class_or_store_write(self):
        path = self.package("p", {"h": (HARNESS, {}), "notes": self.NOTES})
        selection, snaps = self.select(path, ["h", "notes"])
        plan = self.build(selection, snaps)
        fields = self.fields(plan)
        original = installplan.digest_of(fields)
        self.assertEqual(plan.digest, original)

        def changed(edit):
            copy = json.loads(json.dumps(fields))
            edit(copy)
            return installplan.digest_of(copy)

        edits = [
            lambda f: f["actions"][4].update(hash="0" * 64),
            lambda f: f["actions"][4].update(path=f["actions"][4]["path"] + "x"),
            lambda f: f["actions"][4].update(mode="x"),
            lambda f: f["actions"][4].update(**{"class": "seeded" if f["actions"][4]["class"] != "seeded" else "module-owned"}),
            lambda f: f["actions"][4].update(size=f["actions"][4]["size"] + 1),
            lambda f: f["actions"].pop(),
            lambda f: f["store_writes"][0].update(hash="0" * 64),
            lambda f: f["store_writes"].pop(),
            lambda f: f["target"].update(inode=f["target"]["inode"] + 1),
            lambda f: f.update(workbench="9.9"),
            lambda f: f.update(seed="other"),
            lambda f: f.update(git_init=not f["git_init"]),
            lambda f: f["modules"][0].update(tree="0" * 64),
            lambda f: f.update(command="upgrade"),
        ]
        for edit in edits:
            self.assertNotEqual(original, changed(edit))
        # Different content or seed from the real builder also changes it.
        self.assertNotEqual(plan.digest, self.build(selection, snaps, seed="22222222").digest)
        self.assertNotEqual(plan.digest, self.build(selection, snaps, version="0.2.0").digest)

    def fields(self, plan):
        def sha(data):
            return hashlib.sha256(data).hexdigest()
        return {
            "command": "install",
            "target": {"device": plan.target_identity[0], "inode": plan.target_identity[1],
                       "state": plan.state},
            "workbench": "0.1.0", "base": self.base.tree_hash,
            "modules": list(plan.modules),
            "packages": [dict(p, source=installplan.public_source(p["source"]))
                         for p in [{"commit": s["commit"], "name": s["name"], "ref": s["ref"],
                                    "source": s["source"], "tree": s["tree"]}
                                   for s in plan.manifest["packages"]]],
            "seed": plan.seed, "project_id": plan.project_id, "git_init": plan.git_init,
            "actions": [{"kind": a.kind, "path": a.path, "class": a.owner_class, "mode": a.mode,
                         "size": a.size, "hash": a.hash, "detail": a.detail}
                        for a in plan.actions],
            "store_writes": [{"path": p, "hash": sha(d)} for p, d in plan.store_writes],
            "pins": [],
        }

    def test_digest_encoding_is_injective(self):
        base_fields = {"actions": [{"kind": "create", "path": "a b"}]}
        other = {"actions": [{"kind": "b create", "path": "a"}]}
        self.assertNotEqual(installplan.digest_of(base_fields), installplan.digest_of(other))
        joined = {"actions": ["a b create"]}
        split = {"actions": ["a", "b create"]}
        self.assertNotEqual(installplan.digest_of(joined), installplan.digest_of(split))

    def test_store_writes_and_project_id(self):
        plan = self.plan({"h": (HARNESS, {})}, ["h"])
        self.assertEqual(manifest.project_id(SEED), plan.project_id)
        names = [p for p, _ in plan.store_writes]
        self.assertEqual(["projects/%s/baselines" % plan.project_id,
                          "projects/%s/seen" % plan.project_id], names)
        seen = json.loads(plan.store_writes[1][1])
        self.assertEqual({"format": 1, "kind": "path",
                          "value": os.path.join(self.root, "proj")}, seen)
        baselines = json.loads(plan.store_writes[0][1])["baselines"]
        self.assertNotIn(installplan.MARKER_PATH, baselines)
        self.assertIn(".workbench/manifest.json", baselines)

    def test_render_shows_target_first_and_counts_before_detail(self):
        plan = self.plan({"h": (HARNESS, {}), "notes": self.NOTES}, ["h", "notes"])
        text = installplan.render(plan, os.path.join(self.root, "proj"))
        lines = text.split("\n")
        self.assertEqual("target: " + os.path.join(self.root, "proj"), lines[0])
        self.assertLess(text.index("summary:"), text.index("actions:"))
        self.assertIn("high risk: harness module p/h", text)
        self.assertNotIn("digest:", text)
        self.assertIn("digest: " + plan.digest, installplan.render(plan, "x", show_digest=True))
        for a in plan.actions:
            self.assertIn(a.path, text)
        self.assertIn("harness: none planned", text)
        self.assertIn(self.action(plan, "AGENTS.md").hash, text)

    def test_render_escapes_lookalike_and_control_characters(self):
        plan = self.plan({"h": (HARNESS, {}), "notes": self.NOTES}, ["h", "notes"])
        text = installplan.render(plan, "/tmp/prоj\x1b[31m\\n")
        self.assertIn("pr\\u043ej\\x1b[31m\\\\n", text)
        text.encode("ascii")
        self.assertNotIn("\x1b", text)

    def test_render_strips_url_credentials_and_query(self):
        plan = self.plan({"h": (HARNESS, {}), "notes": self.NOTES}, ["h", "notes"])
        text = installplan.render(plan, "/x")
        self.assertIn("https://example.test/p", text)
        for secret in ("user", "pw", "token", "frag"):
            self.assertNotIn(secret, text)
        self.assertNotIn("pw", plan.manifest["packages"][0]["source"])

    def test_public_source(self):
        self.assertEqual("https://h.test/a/b", installplan.public_source("https://u:p@h.test/a/b?q=1#f"))
        self.assertEqual("/local/dir", installplan.public_source("/local/dir"))

    def test_the_skeleton_is_bound_by_the_digest_and_shown(self):
        plan = self.plan({"h": (HARNESS, {})}, ["h"])
        (action,) = [a for a in plan.actions if a.kind == "git-init"]
        self.assertEqual(installplan.GIT_DETAIL, action.detail)
        self.assertEqual(installplan._skeleton_hash(), action.hash)
        self.assertIn("git: creates an empty repository", installplan.render(plan, "/t"))
        self.assertNotIn("git init", installplan.render(plan, "/t"))
        with unittest.mock.patch.object(installplan, "GIT_SKELETON",
                                        installplan.GIT_SKELETON[:-1] + (("config", b"x"),)):
            other = self.plan({"h": (HARNESS, {})}, ["h"])
        self.assertNotEqual(plan.digest, other.digest)


class PublicSourceTest(unittest.TestCase):
    def test_credentials_query_and_fragment_are_removed_whatever_they_hold(self):
        for source, expected in (
                ("https://user:pw@example.test/p.git?token=1#frag", "https://example.test/p.git"),
                ("ssh://u:p#w@host/repo", "ssh://host/repo"),
                ("ssh://u:p?w@host:22/repo?x=a@b", "ssh://host:22/repo"),
                ("file:///srv/p.git", "file:///srv/p.git"),
                ("https://host?x=1", "https://host"),
                ("/plain/path", "/plain/path")):
            with self.subTest(source=source):
                shown = installplan.public_source(source)
                self.assertEqual(expected, shown)
                for secret in ("pw", "u:p", "token"):
                    self.assertNotIn(secret, shown)


if __name__ == "__main__":
    unittest.main()
