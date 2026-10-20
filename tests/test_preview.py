import hashlib
import io
import json
import os
import tempfile
import unittest
import unittest.mock

from tests import support
from workbench import approvals, cli, fetch, sources, store, verify

HARNESS = {"type": "harness", "layout": {}}
NOTES = ({"writes": ["docs/notes.md"], "ships": ["scripts/run.sh"]},
         {"files/docs/notes.md": b"# Notes\n", "scripts/run.sh": b"#!/bin/sh\n"})


def decl(name, **fields):
    out = {"name": name, "version": "1.0.0", "description": "test module"}
    out.update(fields)
    return out


class PreviewTest(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = os.path.realpath(holder.name)
        self.store_root = os.path.join(self.root, "store")
        self.guarded = store.Store(self.store_root)
        self.guarded.ensure()
        self.count = 0
        patch = unittest.mock.patch.object(fetch, "fetch",
                                           side_effect=AssertionError("preview fetched"))
        patch.start()
        self.addCleanup(patch.stop)

    def package(self, name="p", modules=None):
        modules = modules or {"h": (HARNESS, {}), "notes": NOTES}
        self.count += 1
        path = os.path.join(self.root, "set%d" % self.count, name)
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

    def approve(self, path, only=None):
        result = verify.verify_package(path, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        for item in result.modules:
            if only is None or item.name in only:
                approvals.record_module(self.guarded, "%s/%s" % (item.package, item.name),
                                        item.declaration_hash, item.tree_hash, "tester",
                                        "2026-10-20T00:00:00Z")

    def run_preview(self, *args, target=None):
        out, err = io.StringIO(), io.StringIO()
        argv = ["preview", "install"] + ([target] if target else []) + list(args)
        code = cli.main(argv, out, err, store_root=self.store_root)
        return code, out.getvalue(), err.getvalue()

    def good(self, path=None):
        path = path or self.package()
        self.approve(path)
        return path

    def warm(self, path):
        """Run any command once, so the store's own first-run seeding is not counted."""
        cli.main(["verify", path], io.StringIO(), io.StringIO(), store_root=self.store_root)

    def tree(self, top):
        found = {}
        for base, dirs, files in os.walk(top):
            for name in dirs + files:
                full = os.path.join(base, name)
                info = os.lstat(full)
                found[os.path.relpath(full, top)] = (info.st_mode, info.st_size,
                                                     info.st_mtime_ns)
        return found

    def test_preview_prints_plan_and_writes_nothing(self):
        path = self.good()
        place = os.path.join(self.root, "proj")
        os.mkdir(place)
        os.mkdir(os.path.join(place, ".git"))
        with open(os.path.join(place, ".git", "index"), "wb") as handle:
            handle.write(b"index")
        self.warm(path)
        before = (self.tree(place), self.tree(self.store_root))
        code, out, err = self.run_preview("--package", path, "--select", "h", "notes",
                                          target=place)
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.startswith("target: " + place + "\n"))
        self.assertTrue(out.endswith("preview only: nothing was written\n"))
        self.assertIn("create-file docs/notes.md [seeded]", out)
        self.assertNotIn("digest:", out)
        self.assertEqual(before, (self.tree(place), self.tree(self.store_root)))
        with open(os.path.join(place, ".git", "index"), "rb") as handle:
            self.assertEqual(b"index", handle.read())

    def test_preview_of_a_missing_target_creates_nothing(self):
        path = self.good()
        place = os.path.join(self.root, "later")
        code, out, err = self.run_preview("--package", path, "--select", "h", "notes",
                                          target=place)
        self.assertEqual(0, code, err)
        self.assertIn("state: new-missing", out)
        self.assertFalse(os.path.exists(place))

    def test_preview_never_contacts_the_network(self):
        path = self.good()
        self.run_preview("--package", path, "--select", "h", "notes",
                         target=os.path.join(self.root, "x"))
        code, _, err = self.run_preview("--package", "https://example.test/p.git", "--select", "h",
                                        target=os.path.join(self.root, "x"))
        self.assertEqual(1, code)
        self.assertIn("has not been downloaded", err)
        fetch.fetch.assert_not_called()

    def test_preview_refuses_uncached_url_and_names_it(self):
        code, out, err = self.run_preview(
            "--package", "https://user:secret@example.test/p.git?token=1", "--ref", "v1",
            "--select", "h", target=os.path.join(self.root, "x"))
        self.assertEqual((1, ""), (code, out))
        self.assertTrue(err.startswith("refused: "))
        self.assertIn("https://example.test/p.git", err)
        self.assertIn("v1", err)
        for secret in ("secret", "token"):
            self.assertNotIn(secret, err)
        self.assertFalse(os.path.exists(os.path.join(self.store_root, "cache", "anything")))

    def cache_copy(self, path, source, ref="HEAD", commit="a" * 40, ident="0123456789abcdef0123"):
        import shutil
        dest = os.path.join(self.store_root, "cache", ident)
        os.makedirs(dest)
        shutil.copytree(path, os.path.join(dest, "package"))
        with open(os.path.join(dest, "fetch.json"), "w") as handle:
            json.dump({"bytes": 1, "commit": commit, "files": 1, "ref": ref, "source": source,
                       "time": "2026-10-20T00:00:00Z"}, handle)
        return os.path.join(dest, "package")

    def test_preview_uses_an_approved_cached_download(self):
        original = self.package()
        cached = self.cache_copy(original, "https://example.test/p.git", "v1")
        self.approve(cached)
        code, out, err = self.run_preview("--package", "https://example.test/p.git", "--ref", "v1",
                                          "--select", "h", "notes",
                                          target=os.path.join(self.root, "x"))
        self.assertEqual((0, ""), (code, err))
        self.assertIn("package p from https://example.test/p.git", out)

    def test_preview_accepts_local_directory_that_is_approved(self):
        path = self.good()
        code, out, err = self.run_preview("--package", path, "--select", "h", "notes",
                                          target=os.path.join(self.root, "x"))
        self.assertEqual((0, ""), (code, err))
        self.assertIn("package p from local:p", out)
        self.assertNotIn(self.root, out.split("target:", 1)[1].split("\n", 1)[1])

    def test_preview_refuses_unapproved_module(self):
        path = self.package()
        self.approve(path, only={"h"})
        code, out, err = self.run_preview("--package", path, "--select", "h", "notes",
                                          target=os.path.join(self.root, "x"))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("refused: p/notes is not approved on this machine", err)

    def test_preview_refuses_a_swapped_module_after_approval(self):
        path = self.good()
        with open(os.path.join(path, "notes", "files", "docs", "notes.md"), "ab") as handle:
            handle.write(b"changed")
        code, out, err = self.run_preview("--package", path, "--select", "h", "notes",
                                          target=os.path.join(self.root, "x"))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("not approved", err)

    def test_preview_refuses_selection_without_harness(self):
        path = self.good()
        code, out, err = self.run_preview("--package", path, "--select", "notes",
                                          target=os.path.join(self.root, "x"))
        self.assertEqual((1, ""), (code, out))
        self.assertIn("no harness module is selected", err)

    def test_preview_target_rules_refuse_and_write_nothing(self):
        path = self.good()
        os.mkdir(os.path.join(self.root, "full"))
        with open(os.path.join(self.root, "full", "f"), "w") as handle:
            handle.write("x")
        real = os.path.join(self.root, "real")
        os.mkdir(real)
        os.symlink(real, os.path.join(self.root, "link"))
        args = ("--package", path, "--select", "h", "notes")
        self.warm(path)
        for place in (os.path.join(self.root, "full"), os.path.join(self.root, "link"),
                      self.store_root, os.path.join(self.store_root, "cache"),
                      self.root, os.path.join(self.root, "no", "parent")):
            before = (self.tree(self.root), self.tree(self.store_root))
            code, out, err = self.run_preview(*args, target=place)
            self.assertEqual((1, ""), (code, out), place)
            self.assertTrue(err.startswith("refused: "), err)
            self.assertEqual(before, (self.tree(self.root), self.tree(self.store_root)), place)
        fetch.fetch.assert_not_called()

    def test_an_existing_project_is_refused(self):
        path = self.good()
        place = os.path.join(self.root, "proj")
        os.makedirs(os.path.join(place, ".git"))
        os.makedirs(os.path.join(place, ".workbench"))
        with open(os.path.join(place, ".workbench", "manifest.json"), "w") as handle:
            handle.write("{}")
        code, out, err = self.run_preview("--package", path, "--select", "h", "notes",
                                          target=place)
        self.assertEqual(1, code)
        self.assertIn("existing project", err)

    def test_usage_errors_exit_2_without_touching_store(self):
        bare = os.path.join(self.root, "untouched")
        cases = [
            ["preview"], ["preview", "add"], ["preview", "install"],
            ["preview", "install", "--select", "h"],
            ["preview", "install", "--package", "p"],
            ["preview", "install", "--ref", "v1", "--package", "p", "--select", "h"],
            ["preview", "install", "--package", "p", "--ref", "a", "--ref", "b", "--select", "h"],
            ["preview", "install", "--package", "", "--select", "h"],
            ["preview", "install", "--package", "p", "--select"],
            ["preview", "install", "--package", "p", "--select", "h", "--bogus"],
            ["preview", "install", "a", "b", "--package", "p", "--select", "h"],
            ["preview", "install", "a", "--dir", "b", "--package", "p", "--select", "h"],
            ["preview", "install", "--dir", "", "--package", "p", "--select", "h"],
        ]
        for argv in cases:
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(2, cli.main(argv, out, err, store_root=bare), argv)
            self.assertIn("usage:", err.getvalue())
            self.assertFalse(os.path.exists(bare), argv)

    def test_ref_binds_to_preceding_package(self):
        parsed = sources.parse_install(["--package", "a", "--ref", "r1", "--package", "b",
                                        "--package", "c", "--ref", "r3", "--select", "x", "y"])
        self.assertEqual([("a", "r1"), ("b", None), ("c", "r3")], parsed.packages)
        self.assertEqual(["x", "y"], parsed.select)
        self.assertEqual([("a", "r1")], sources.parse_packages(
            ["--package", "a", "--ref", "r1", "--select", "m"]))
        again = sources.parse_install(["dir", "--package", "a", "--select", "m"])
        self.assertEqual("dir", again.positional)

    def test_same_directory_by_two_spellings_is_accepted(self):
        path = self.good()
        place = os.path.join(self.root, "same")
        os.mkdir(place)
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "install", place, "--dir", place + "/.", "--package", path,
                         "--select", "h", "notes"], out, err, store_root=self.store_root)
        self.assertEqual(0, code, err.getvalue())

    def test_a_directory_without_package_json_is_named_as_such(self):
        empty = os.path.join(self.root, "emptydir")
        os.mkdir(empty)
        code, _, err = self.run_preview("--package", empty, "--select", "h",
                                        target=os.path.join(self.root, "x"))
        self.assertEqual(1, code)
        self.assertIn("directory without a package.json", err)
        self.assertNotIn("has not been downloaded", err)

    def test_a_local_ref_and_a_link_are_refused(self):
        path = self.good()
        place = os.path.join(self.root, "x")
        code, _, err = self.run_preview("--package", path, "--ref", "main", "--select", "h",
                                        "notes", target=place)
        self.assertEqual(1, code)
        self.assertIn("cannot apply", err)
        link = os.path.join(self.root, "pkglink")
        os.symlink(path, link)
        code, _, err = self.run_preview("--package", link, "--select", "h", "notes", target=place)
        self.assertEqual(1, code)
        self.assertIn("symbolic link", err)


if __name__ == "__main__":
    unittest.main()
