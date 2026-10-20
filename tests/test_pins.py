import io
import json
import os
import sys
import tempfile
import unittest

import support
from workbench import approve, cli, pins, store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = "a" * 64
OTHER = "b" * 64
SHA = "c" * 64
PROMPT = b"Anything else cancels and records nothing.\r\n> "
HELPER = "#!/bin/sh\necho helper ran\n"


class Base(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.home = os.path.join(self.base, "home")
        os.makedirs(self.home)
        self.store = store.Store(os.path.join(self.home, ".config", "project-workbench"))
        self.store.ensure()
        self.root = os.path.join(self.base, "project")
        os.makedirs(os.path.join(self.root, "tools"))
        self.helper = os.path.join(self.root, "tools", "helper.sh")
        with open(self.helper, "w") as handle:
            handle.write(HELPER)

    def pins_path(self, project=PROJECT):
        return os.path.join(self.store.root, "projects", project, "pins")


class PinFileTest(Base):
    def test_a_pin_round_trips(self):
        pins.set_pin(self.store, PROJECT, "commit", "tools/helper.sh", SHA, "owner",
                     "2026-10-20T08:00:00Z")
        got = pins.lookup(self.store, PROJECT, "commit")
        self.assertEqual(got, pins.Pin("commit", "tools/helper.sh", SHA, "owner", "2026-10-20T08:00:00Z"))

    def test_the_file_is_fixed_text(self):
        pins.set_pin(self.store, PROJECT, "commit", "tools/helper.sh", SHA, "owner",
                     "2026-10-20T08:00:00Z")
        with open(self.pins_path()) as handle:
            self.assertEqual(handle.read(), (
                '{\n  "format": 1,\n  "pins": {\n    "commit": {\n      "path": "tools/helper.sh",\n'
                '      "pinned_by": "owner",\n      "sha256": "%s",\n'
                '      "time": "2026-10-20T08:00:00Z"\n    }\n  }\n}\n' % SHA))

    def test_pins_for_other_helpers_and_projects_are_kept_and_separate(self):
        pins.set_pin(self.store, PROJECT, "one", "a/one.sh", SHA, "owner")
        pins.set_pin(self.store, PROJECT, "two", "a/two.sh", "d" * 64, "owner")
        pins.set_pin(self.store, OTHER, "one", "b/one.sh", "e" * 64, "owner")
        self.assertEqual(sorted(pins.load(self.store, PROJECT)), ["one", "two"])
        self.assertEqual(pins.lookup(self.store, OTHER, "one").path, "b/one.sh")
        self.assertEqual(pins.lookup(self.store, PROJECT, "one").path, "a/one.sh")

    def test_pinning_again_replaces_that_pin_only(self):
        pins.set_pin(self.store, PROJECT, "one", "a/one.sh", SHA, "owner")
        pins.set_pin(self.store, PROJECT, "two", "a/two.sh", SHA, "owner")
        pins.set_pin(self.store, PROJECT, "one", "a/new.sh", "d" * 64, "owner")
        self.assertEqual(pins.lookup(self.store, PROJECT, "one").sha256, "d" * 64)
        self.assertEqual(pins.lookup(self.store, PROJECT, "two").sha256, SHA)

    def test_no_file_means_no_pins(self):
        self.assertEqual(pins.load(self.store, PROJECT), {})
        with self.assertRaisesRegex(pins.PinError, "no pin named"):
            pins.lookup(self.store, PROJECT, "commit")

    def test_a_missing_name_in_an_existing_file_is_no_pin(self):
        pins.set_pin(self.store, PROJECT, "one", "a/one.sh", SHA, "owner")
        with self.assertRaisesRegex(pins.PinError, "no pin named"):
            pins.lookup(self.store, PROJECT, "two")

    def put(self, data, project=PROJECT):
        path = self.pins_path(project)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else json.dumps(data).encode())

    def good(self, **entry):
        item = {"path": "a/one.sh", "pinned_by": "owner", "sha256": SHA, "time": "2026-10-20T08:00:00Z"}
        item.update(entry)
        return {"format": 1, "pins": {"one": item}}

    def test_every_malformed_file_fails_closed(self):
        bad = [b"", b"{", b"[]", b"null", b"\xff", b'{"format": 1, "format": 1, "pins": {}}',
               {"format": 2, "pins": {}}, {"format": True, "pins": {}}, {"format": 1},
               {"format": 1, "pins": []}, {"format": 1, "pins": {}, "extra": 1},
               self.good(path="/abs"), self.good(path="../x"), self.good(path=".git/config"),
               self.good(path="a\\b"), self.good(path=""), self.good(path=5),
               self.good(sha256="C" * 64), self.good(sha256="c" * 63), self.good(sha256=5),
               self.good(pinned_by=""), self.good(pinned_by="x" * 65), self.good(pinned_by="a\nb"),
               self.good(time="yesterday"), self.good(time=5), self.good(extra=1),
               {"format": 1, "pins": {"bad name": self.good()["pins"]["one"]}},
               {"format": 1, "pins": {"": self.good()["pins"]["one"]}},
               {"format": 1, "pins": {"one": {"path": "a"}}},
               {"format": 1, "pins": {"one": "text"}}, b" " * (2 * 1024 * 1024)]
        for data in bad:
            with self.subTest(data=str(data)[:60]):
                self.put(data)
                with self.assertRaises(pins.PinError):
                    pins.load(self.store, PROJECT)
                with self.assertRaises(pins.PinError):
                    pins.lookup(self.store, PROJECT, "one")

    def test_a_damaged_file_is_not_replaced_by_a_new_pin(self):
        self.put(b"{ broken")
        with self.assertRaises(pins.PinError):
            pins.set_pin(self.store, PROJECT, "one", "a/one.sh", SHA, "owner")
        with open(self.pins_path(), "rb") as handle:
            self.assertEqual(handle.read(), b"{ broken")

    def test_a_symbolic_link_or_directory_in_place_of_the_file_fails_closed(self):
        os.makedirs(os.path.dirname(self.pins_path()))
        target = os.path.join(self.base, "elsewhere.json")
        with open(target, "wb") as handle:
            handle.write(json.dumps(self.good()).encode())
        os.symlink(target, self.pins_path())
        with self.assertRaisesRegex(pins.PinError, "not a regular file"):
            pins.load(self.store, PROJECT)
        os.unlink(self.pins_path())
        os.mkdir(self.pins_path())
        with self.assertRaises(pins.PinError):
            pins.load(self.store, PROJECT)

    def test_a_symbolic_link_in_place_of_the_project_directory_is_not_followed(self):
        outside = os.path.join(self.base, "outside")
        os.makedirs(outside)
        with open(os.path.join(outside, "pins"), "wb") as handle:
            handle.write(json.dumps(self.good()).encode())
        os.symlink(outside, os.path.join(self.store.root, "projects", PROJECT))
        with self.assertRaises(pins.PinError):
            pins.load(self.store, PROJECT)
        with self.assertRaises(pins.PinError):
            pins.set_pin(self.store, PROJECT, "two", "a/two.sh", SHA, "owner")
        self.assertEqual(os.listdir(outside), ["pins"])

    def test_bad_ids_and_names_are_refused(self):
        for project in ("", "A" * 64, "a" * 63, "a" * 65, "../x", None, 5, "a" * 64 + "\n"):
            with self.subTest(project=project):
                with self.assertRaises(pins.PinError):
                    pins.load(self.store, project)
        for name in ("", "a b", "-x", ".x", "a/b", "x" * 65, None, 5, "a\n"):
            with self.subTest(name=name):
                with self.assertRaises(pins.PinError):
                    pins.set_pin(self.store, PROJECT, name, "a/one.sh", SHA, "owner")
        self.assertEqual(os.listdir(os.path.join(self.store.root, "projects")), [])

    def test_unsafe_paths_cannot_be_written_into_a_pin(self):
        for path in ("/abs", "../x", ".git/x", "a//b", "a\\b", ""):
            with self.subTest(path=path):
                with self.assertRaises(pins.PinError):
                    pins.set_pin(self.store, PROJECT, "one", path, SHA, "owner")
        self.assertFalse(os.path.exists(self.pins_path()))

    def test_a_bad_hash_cannot_be_written_into_a_pin(self):
        for digest in ("", "C" * 64, "c" * 63, None):
            with self.subTest(digest=digest):
                with self.assertRaises(pins.PinError):
                    pins.set_pin(self.store, PROJECT, "one", "a/one.sh", digest, "owner")


class PinCommandTest(Base):
    def drive(self, args, answer=None, **kwargs):
        env = dict(os.environ, HOME=self.home, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1",
                   PATH=support.clean_path())
        return support.drive_pty(self, [sys.executable, "-B", "-m", "workbench", "pin"] + list(args),
                                 env, self.base, answer, PROMPT, **kwargs)

    def digest(self):
        with open(self.helper, "rb") as handle:
            return pins.hash_bytes(handle.read())

    def test_the_correct_text_pins_the_helper_relative_to_the_root(self):
        code, output, error = self.drive([PROJECT, "commit", self.helper, "--root", self.root],
                                         answer=self.digest()[:12])
        self.assertEqual((code, error), (0, ""), output)
        pin = pins.lookup(self.store, PROJECT, "commit")
        self.assertEqual((pin.path, pin.sha256), ("tools/helper.sh", self.digest()))
        self.assertEqual(pin.pinned_by, approve.approver_name())
        self.assertIn("pinned commit -> tools/helper.sh", output)

    def test_the_owner_is_shown_the_path_hash_and_start_of_the_file(self):
        _, output, _ = self.drive([PROJECT, "commit", self.helper, "--root", self.root], answer="no")
        for expected in ("path in the project: tools/helper.sh", "sha256: " + self.digest(),
                         "size:   %d bytes" % len(HELPER), "echo helper ran", "Read the file first"):
            self.assertIn(expected, output)

    def test_a_relative_helper_path_works(self):
        code, output, _ = self.drive([PROJECT, "commit", "project/tools/helper.sh", "--root",
                                      "project"], answer=self.digest()[:12])
        self.assertEqual(code, 0, output)
        self.assertEqual(pins.lookup(self.store, PROJECT, "commit").path, "tools/helper.sh")

    def test_any_other_text_cancels_and_records_nothing(self):
        token = self.digest()[:12]
        for answer in ("", "yes", "y", token[:11], token + "0", token.upper(), "0" * 12):
            with self.subTest(answer=answer):
                code, output, _ = self.drive([PROJECT, "commit", self.helper, "--root", self.root],
                                             answer=answer)
                self.assertEqual(code, 1)
                self.assertIn("cancelled: nothing was recorded", output)
                self.assertFalse(os.path.exists(self.pins_path()))

    def test_a_helper_that_changes_while_it_is_shown_is_not_pinned(self):
        def edit():
            with open(self.helper, "a") as handle:
                handle.write("echo edited\n")

        digest = self.digest()
        code, output, error = self.drive([PROJECT, "commit", self.helper, "--root", self.root],
                                         answer=digest[:12], between=edit)
        self.assertEqual(code, 1, output)
        self.assertIn("changed while it was shown", error)
        self.assertFalse(os.path.exists(self.pins_path()))

    def test_pinning_again_says_it_replaces_the_old_pin(self):
        self.assertEqual(self.drive([PROJECT, "commit", self.helper, "--root", self.root],
                                    answer=self.digest()[:12])[0], 0)
        with open(self.helper, "a") as handle:
            handle.write("echo new\n")
        code, output, _ = self.drive([PROJECT, "commit", self.helper, "--root", self.root],
                                     answer=self.digest()[:12])
        self.assertEqual(code, 0, output)
        self.assertIn("this REPLACES the pin tools/helper.sh", output)
        self.assertEqual(pins.lookup(self.store, PROJECT, "commit").sha256, self.digest())

    def test_without_terminals_nothing_is_pinned(self):
        for kwargs in ({"stdin": "pipe"}, {"stdout": "pipe"}, {"stdin": "pipe", "stdout": "pipe"}):
            with self.subTest(kwargs=kwargs):
                code, output, error = self.drive([PROJECT, "commit", self.helper, "--root", self.root],
                                                 answer=self.digest()[:12], **kwargs)
                self.assertEqual(code, 1)
                self.assertIn("owner-run", error)
                self.assertNotIn("sha256:", output)
                self.assertFalse(os.path.exists(self.pins_path()))

    def test_a_helper_outside_the_root_is_refused_before_the_prompt(self):
        outside = os.path.join(self.base, "outside.sh")
        with open(outside, "w") as handle:
            handle.write(HELPER)
        for helper in (outside, os.path.join(self.root, "..", "outside.sh"), self.root + "x/y"):
            with self.subTest(helper=helper):
                code, output, error = self.drive([PROJECT, "commit", helper, "--root", self.root],
                                                 answer="x")
                self.assertEqual(code, 1)
                self.assertIn("not inside the project root", error)
                self.assertNotIn("sha256:", output)
        self.assertFalse(os.path.exists(self.pins_path()))

    def test_symbolic_links_directories_and_missing_files_are_refused(self):
        link = os.path.join(self.root, "tools", "link.sh")
        os.symlink(self.helper, link)
        linked_dir = os.path.join(self.root, "linked")
        os.symlink(os.path.join(self.root, "tools"), linked_dir)
        fifo = os.path.join(self.root, "tools", "fifo")
        os.mkfifo(fifo)
        for helper in (link, os.path.join(linked_dir, "helper.sh"), fifo,
                       os.path.join(self.root, "tools"), os.path.join(self.root, "tools", "none.sh")):
            with self.subTest(helper=helper):
                code, output, error = self.drive([PROJECT, "commit", helper, "--root", self.root],
                                                 answer="x")
                self.assertEqual(code, 1)
                self.assertIn("cannot be read", error)
                self.assertNotIn("sha256:", output)
        self.assertFalse(os.path.exists(self.pins_path()))

    def test_a_root_that_is_a_symbolic_link_is_refused(self):
        link = os.path.join(self.base, "rootlink")
        os.symlink(self.root, link)
        code, _, error = self.drive([PROJECT, "commit", os.path.join(link, "tools", "helper.sh"),
                                     "--root", link], answer="x")
        self.assertEqual(code, 1)
        self.assertIn("refused:", error)
        self.assertFalse(os.path.exists(self.pins_path()))

    def test_bad_ids_and_names_are_refused(self):
        for args in (["short", "commit"], [PROJECT, "bad name"], [PROJECT, ".hidden"]):
            with self.subTest(args=args):
                code, _, error = self.drive(args + [self.helper, "--root", self.root], answer="x")
                self.assertEqual(code, 1)
                self.assertIn("refused:", error)
        self.assertFalse(os.path.exists(self.pins_path()))

    def test_a_path_naming_git_is_refused_before_the_prompt(self):
        os.makedirs(os.path.join(self.root, "sub", ".git"))
        bad = os.path.join(self.root, "sub", ".git", "hook.sh")
        with open(bad, "w") as handle:
            handle.write(HELPER)
        code, output, error = self.drive([PROJECT, "commit", bad, "--root", self.root], answer="x")
        self.assertEqual(code, 1)
        self.assertIn("not allowed", error)
        self.assertNotIn("sha256:", output)
        self.assertFalse(os.path.exists(self.pins_path()))

    def test_usage_errors(self):
        for argv in ([], [PROJECT], [PROJECT, "c"], [PROJECT, "c", self.helper],
                     [PROJECT, "c", self.helper, "--root"], ["", "c", self.helper, "--root", self.root],
                     [PROJECT, "", self.helper, "--root", self.root],
                     [PROJECT, "c", "", "--root", self.root],
                     [PROJECT, "c", self.helper, "--root", ""], [PROJECT, "-x", self.helper,
                                                                 "--root", self.root]):
            with self.subTest(argv=argv):
                out, err = io.StringIO(), io.StringIO()
                self.assertEqual(cli.main(["pin"] + argv, out, err, store_root=self.store.root), 2)


if __name__ == "__main__":
    unittest.main()
