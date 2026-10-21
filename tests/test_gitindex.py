import hashlib
import os
import random
import shutil
import struct
import subprocess
import tempfile
import time
import unittest
import unittest.mock

from workbench import gitindex


def run_git(place, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.test",
                           "-c", "commit.gpgsign=false"] + list(args), cwd=place, env=env,
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return done


class Index(unittest.TestCase):
    FILES = ["a.txt", "docs/b.md", "docs/deep/c.md", "docs/deep/d.md", "é/ünï.md", "z"]

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.place = os.path.join(self.root, "p")
        os.mkdir(self.place)

    def repo(self, *init, version=None, split=False, intent=None):
        self.assertEqual(0, run_git(self.place, "init", "-q", "--template=", *init).returncode)
        for rel in self.FILES:
            full = os.path.join(self.place, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as handle:
                handle.write(rel.encode())
        os.symlink("a.txt", os.path.join(self.place, "link"))
        self.assertEqual(0, run_git(self.place, "add", "-A").returncode)
        if intent:
            with open(os.path.join(self.place, intent), "wb") as handle:
                handle.write(b"x")
            self.assertEqual(0, run_git(self.place, "add", "-N", intent).returncode)
        if version:
            done = run_git(self.place, "update-index", "--index-version", str(version))
            self.assertEqual(0, done.returncode, done.stderr)
        if split:
            done = run_git(self.place, "update-index", "--split-index")
            self.assertEqual(0, done.returncode, done.stderr)
        with open(os.path.join(self.place, ".git", "index"), "rb") as handle:
            return handle.read()

    def expected(self, extra=()):
        files = set(self.FILES) | {"link"} | set(extra)
        dirs = {"docs", "docs/deep", "é"}
        return files, dirs

    def test_every_index_version_is_read(self):
        for version in (2, 3, 4):
            with self.subTest(version=version):
                shutil.rmtree(self.place)
                os.mkdir(self.place)
                data = self.repo(version=version, intent="intent.txt" if version == 3 else None)
                self.assertEqual(version, struct.unpack_from(">I", data, 4)[0])
                tracked = gitindex.parse(data)
                files, dirs = self.expected(["intent.txt"] if version == 3 else ())
                self.assertEqual(files, set(tracked.files))
                self.assertEqual(dirs, set(tracked.dirs))
                self.assertEqual({"link"}, set(tracked.links))

    def test_an_index_after_a_commit_has_extensions_that_are_skipped(self):
        self.repo()
        self.assertEqual(0, run_git(self.place, "commit", "-q", "-m", "x").returncode)
        with open(os.path.join(self.place, ".git", "index"), "rb") as handle:
            data = handle.read()
        self.assertIn(b"TREE", data)
        self.assertEqual(set(self.expected()[0]), set(gitindex.parse(data).files))

    def test_a_sha256_repository_is_read(self):
        done = run_git(self.place, "init", "-q", "--object-format=sha256", "--template=")
        if done.returncode:
            self.skipTest("this git has no sha256 repositories")
        shutil.rmtree(self.place)
        os.mkdir(self.place)
        data = self.repo("--object-format=sha256")
        self.assertEqual(hashlib.sha256(data[:-32]).digest(), data[-32:])
        self.assertEqual(set(self.expected()[0]), set(gitindex.parse(data).files))

    def test_a_split_index_is_refused(self):
        data = self.repo(split=True)
        self.assertIn(b"link", data)
        with self.assertRaises(gitindex.GitIndexError) as caught:
            gitindex.parse(data)
        # Either refusal path may fire, depending on how git laid out the index.
        self.assertIn("split", str(caught.exception))

    def test_a_submodule_entry_is_a_tracked_directory(self):
        self.repo()
        done = run_git(self.place, "update-index", "--add", "--cacheinfo",
                       "160000,%s,mod" % ("1" * 40))
        self.assertEqual(0, done.returncode, done.stderr)
        with open(os.path.join(self.place, ".git", "index"), "rb") as handle:
            tracked = gitindex.parse(handle.read())
        self.assertIn("mod", tracked.files)
        self.assertIn("mod", tracked.dirs)

    def test_no_index_tracks_nothing(self):
        class Absent:
            def git_bytes(self, rel, limit):
                return None

        self.assertEqual((frozenset(), frozenset(), frozenset()), tuple(gitindex.read(Absent())))

    def test_a_damaged_index_raises_only_the_documented_error(self):
        data = self.repo()
        self.assertEqual(0, run_git(self.place, "commit", "-q", "-m", "x").returncode)
        with open(os.path.join(self.place, ".git", "index"), "rb") as handle:
            data = handle.read()
        for cut in range(0, len(data)):
            with self.subTest(cut=cut):
                try:
                    gitindex.parse(data[:cut])
                except gitindex.GitIndexError:
                    pass
        generator = random.Random(7)
        for version in (2, 4):
            body = bytearray(self.repo_bytes(version))
            for _ in range(600):
                mutated = bytearray(body[:-20])
                for _ in range(generator.randint(1, 4)):
                    mutated[generator.randrange(len(mutated))] = generator.randrange(256)
                signed = bytes(mutated) + hashlib.sha1(bytes(mutated)).digest()
                try:
                    tracked = gitindex.parse(signed)
                except gitindex.GitIndexError:
                    continue
                self.assertLessEqual(len(tracked.files), len(mutated))

    def repo_bytes(self, version):
        shutil.rmtree(self.place)
        os.mkdir(self.place)
        return self.repo(version=version)

    def test_the_counts_and_lengths_are_checked_against_the_bytes(self):
        header = b"DIRC" + struct.pack(">II", 2, 1)
        for body in (b"", b"\0" * 62, b"\0" * 61):
            data = header + body
            data += hashlib.sha1(data).digest()
            with self.assertRaises(gitindex.GitIndexError):
                gitindex.parse(data)
        huge = b"DIRC" + struct.pack(">II", 2, gitindex.MAX_ENTRIES + 1)
        huge += hashlib.sha1(huge).digest()
        with self.assertRaises(gitindex.GitIndexError):
            gitindex.parse(huge)
        for version in (1, 5):
            data = b"DIRC" + struct.pack(">II", version, 0)
            data += hashlib.sha1(data).digest()
            with self.assertRaises(gitindex.GitIndexError):
                gitindex.parse(data)
        with self.assertRaises(gitindex.GitIndexError):
            gitindex.parse(b"")

    def entry(self, path):
        entry = b"\0" * 24 + struct.pack(">I", 0o100644) + b"\0" * 12 + b"\0" * 20
        entry += struct.pack(">H", min(len(path), 0xFFF)) + path
        return entry + b"\0" * (-(len(entry) + 1) % 8 + 1)

    def signed(self, body, version=2, count=1):
        data = b"DIRC" + struct.pack(">II", version, count) + body
        return data + hashlib.sha1(data).digest()

    def test_the_padding_of_the_last_entry_may_not_run_past_the_end(self):
        whole = self.entry(b"ab")
        self.assertEqual({"ab"}, set(gitindex.parse(self.signed(whole)).files))
        with self.assertRaises(gitindex.GitIndexError):
            gitindex.parse(self.signed(whole[:65]))

    def test_a_required_extension_is_refused_and_an_optional_one_is_skipped(self):
        whole = self.entry(b"ab")
        optional = b"TREE" + struct.pack(">I", 3) + b"abc"
        self.assertEqual({"ab"}, set(gitindex.parse(self.signed(whole + optional)).files))
        for name in (b"link", b"sdir"):
            with self.subTest(name=name), self.assertRaises(gitindex.GitIndexError) as caught:
                gitindex.parse(self.signed(whole + name + struct.pack(">I", 0)))
            self.assertIn("split or sparse", str(caught.exception))

    def test_an_extension_may_not_run_past_the_end_or_be_cut_short(self):
        whole = self.entry(b"ab")
        for tail in (b"TREE" + struct.pack(">I", 1000) + b"abc", b"TREE" + b"\0\0"):
            with self.subTest(tail=tail), self.assertRaises(gitindex.GitIndexError):
                gitindex.parse(self.signed(whole + tail))

    def test_a_long_path_or_many_long_paths_are_refused_quickly(self):
        start = time.monotonic()
        with self.assertRaises(gitindex.GitIndexError):
            gitindex.parse(self.signed(self.entry(b"a/" * 50000)))
        self.assertEqual({"a" * gitindex.MAX_PATH},
                         set(gitindex.parse(self.signed(self.entry(b"a" * gitindex.MAX_PATH))).files))
        # Version 4 with nothing stripped: each path is the last one plus a byte.
        body = b""
        for _ in range(5000):
            entry = b"\0" * 24 + struct.pack(">I", 0o100644) + b"\0" * 12 + b"\0" * 20
            body += entry + struct.pack(">H", 1) + b"\0" + b"a" + b"\0"
        with self.assertRaises(gitindex.GitIndexError):
            gitindex.parse(self.signed(body, version=4, count=5000))
        with unittest.mock.patch.object(gitindex, "MAX_PATH_BYTES", 100):
            with self.assertRaises(gitindex.GitIndexError):
                gitindex.parse(self.signed(self.entry(b"abcdef") * 40, count=40))
        self.assertLess(time.monotonic() - start, 5)

    def test_the_number_of_entries_is_bounded(self):
        data = self.repo()
        self.assertEqual(7, len(gitindex.parse(data).files))
        with unittest.mock.patch.object(gitindex, "MAX_ENTRIES", 6):
            with self.assertRaises(gitindex.GitIndexError) as caught:
                gitindex.parse(data)
        self.assertIn("more than the 6", str(caught.exception))

    def test_an_entry_without_a_path_is_refused(self):
        entry = b"\0" * 24 + struct.pack(">I", 0o100644) + b"\0" * 12 + b"\0" * 20 + b"\0\0"
        entry += b"\0" * (-len(entry) % 8 or 8)
        data = b"DIRC" + struct.pack(">II", 2, 1) + entry
        data += hashlib.sha1(data).digest()
        with self.assertRaises(gitindex.GitIndexError):
            gitindex.parse(data)


if __name__ == "__main__":
    unittest.main()
