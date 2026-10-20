import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
import unittest.mock

import support
from workbench import fetch, safefs, store

REAL_GIT = shutil.which("git")
SHA = "a" * 40


def run_git(cwd, *args, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    done = subprocess.run(
        [REAL_GIT, "-c", "user.name=Test", "-c", "user.email=test@example.test",
         "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"] + list(args),
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and done.returncode != 0:
        raise AssertionError("git %s failed: %s" % (args, done.stderr.decode()))
    return done.stdout.decode().strip()


def listing_line(mode=b"100644", kind=b"blob", oid=None, size=b"3", path=b"a.txt"):
    return b"%s %s %s %8s\t%s\0" % (mode, kind, oid or (b"1" * 40), size, path)


class Base(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        # Fetch's own scratch directory goes here, so a leftover is visible.
        self.scratch = os.path.join(self.base, "scratch")
        os.makedirs(self.scratch)
        patcher = unittest.mock.patch.object(tempfile, "tempdir", self.scratch)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.store = store.Store(os.path.join(self.base, "store"))
        self.store.ensure()
        self.cache = os.path.join(self.store.root, "cache")
        self.source = os.path.join(self.base, "source")
        os.makedirs(self.source)
        run_git(self.source, "init", "-q", "--template=")

    def write(self, rel, data=b"x", mode=None):
        path = os.path.join(self.source, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode())
        if mode is not None:
            os.chmod(path, mode)

    def commit(self, message="c"):
        run_git(self.source, "add", "-A")
        run_git(self.source, "commit", "-q", "-m", message, "--allow-empty")
        return run_git(self.source, "rev-parse", "HEAD")

    def package(self):
        self.write("package.json", '{"name": "p"}\n')
        self.write("bin/run.sh", "#!/bin/sh\n", 0o755)
        self.write("docs/notes.md", "notes\n")
        self.write("café notes.txt", "unicode\n")
        return self.commit()

    def nothing_left(self):
        self.assertEqual(os.listdir(self.cache), [])
        self.assertEqual(os.listdir(self.scratch), [])


class DownloadTest(Base):
    def test_a_package_is_downloaded_as_data_into_a_fresh_cache_directory(self):
        commit = self.package()
        got = fetch.fetch(self.store, self.source, "main", now="2026-10-20T08:00:00Z")
        self.assertEqual((got.commit, got.ref, got.files), (commit, "main", 4))
        self.assertEqual(os.listdir(self.cache), [got.id])
        self.assertEqual(got.path, os.path.join(self.cache, got.id, "package"))
        with open(os.path.join(got.path, "docs", "notes.md"), "rb") as handle:
            self.assertEqual(handle.read(), b"notes\n")
        with open(os.path.join(got.path, "café notes.txt"), "rb") as handle:
            self.assertEqual(handle.read(), b"unicode\n")
        self.assertTrue(os.stat(os.path.join(got.path, "bin", "run.sh")).st_mode & stat.S_IXUSR)
        self.assertFalse(os.stat(os.path.join(got.path, "docs", "notes.md")).st_mode & stat.S_IXUSR)
        self.assertEqual(os.listdir(self.scratch), [])

    def test_no_repository_and_no_git_metadata_is_left_in_the_cache(self):
        self.package()
        got = fetch.fetch(self.store, self.source, "main")
        for base, dirs, files in os.walk(self.cache):
            for name in dirs + files:
                self.assertFalse(name == ".git" or name.endswith(".pack") or name == "objects", name)
        self.assertEqual(sorted(os.listdir(os.path.join(self.cache, got.id))),
                         ["fetch.json", "package"])

    def test_fetch_json_records_where_the_package_came_from_outside_the_package(self):
        commit = self.package()
        got = fetch.fetch(self.store, self.source, "main", now="2026-10-20T08:00:00Z")
        with open(os.path.join(self.cache, got.id, "fetch.json")) as handle:
            meta = json.load(handle)
        self.assertEqual(meta["commit"], commit)
        self.assertEqual((meta["ref"], meta["files"], meta["time"]), ("main", 4, "2026-10-20T08:00:00Z"))
        self.assertTrue(meta["source"].startswith("file:///"))
        self.assertFalse(os.path.exists(os.path.join(got.path, "fetch.json")))

    def test_the_cache_directories_are_private(self):
        self.package()
        got = fetch.fetch(self.store, self.source, "main")
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.cache, got.id)).st_mode) & 0o077, 0)

    def test_a_branch_a_tag_a_commit_and_the_default_head_all_work(self):
        commit = self.package()
        run_git(self.source, "tag", "v1.0.0")
        for ref in ("main", "v1.0.0", commit, "HEAD"):
            with self.subTest(ref=ref):
                self.assertEqual(fetch.fetch(self.store, self.source, ref).commit, commit)
        self.assertEqual(fetch.fetch(self.store, self.source).commit, commit)

    def test_a_ref_that_moves_gives_the_new_commit_but_the_pinned_one_stays_reachable(self):
        first = self.package()
        one = fetch.fetch(self.store, self.source, "main")
        self.write("docs/notes.md", "changed\n")
        second = self.commit("second")
        self.assertNotEqual(first, second)
        moved = fetch.fetch(self.store, self.source, "main")
        pinned = fetch.fetch(self.store, self.source, first)
        self.assertEqual((one.commit, moved.commit, pinned.commit), (first, second, first))
        with open(os.path.join(moved.path, "docs", "notes.md")) as handle:
            self.assertEqual(handle.read(), "changed\n")
        with open(os.path.join(pinned.path, "docs", "notes.md")) as handle:
            self.assertEqual(handle.read(), "notes\n")
        with open(os.path.join(one.path, "docs", "notes.md")) as handle:
            self.assertEqual(handle.read(), "notes\n")

    def test_every_fetch_makes_a_new_directory(self):
        self.package()
        ids = {fetch.fetch(self.store, self.source, "main").id for _ in range(3)}
        self.assertEqual(len(ids), 3)
        self.assertEqual(sorted(os.listdir(self.cache)), sorted(ids))

    def test_a_hook_and_a_filter_that_a_checkout_would_run_are_not_run(self):
        markers = {name: os.path.join(self.base, name) for name in ("smudge-ran", "hook-ran", "script-ran")}
        self.write("run.sh", "#!/bin/sh\ntouch %s\n" % markers["script-ran"], 0o755)
        self.write("data.txt", "payload\n")
        self.write(".gitattributes", "* filter=evil\n")
        self.commit()
        # A user's own configuration that WOULD run code on a checkout: a smudge filter and a
        # post-checkout hook. The control below shows this setup is live.
        home = os.path.join(self.base, "home")
        hooks = os.path.join(home, "hooks")
        os.makedirs(hooks)
        hook = os.path.join(hooks, "post-checkout")
        with open(hook, "w") as handle:
            handle.write("#!/bin/sh\ntouch %s\n" % markers["hook-ran"])
        os.chmod(hook, 0o755)
        smudge = os.path.join(home, "smudge.sh")
        with open(smudge, "w") as handle:
            handle.write("#!/bin/sh\ntouch %s\ncat\n" % markers["smudge-ran"])
        os.chmod(smudge, 0o755)
        with open(os.path.join(home, ".gitconfig"), "w") as handle:
            handle.write('[filter "evil"]\n\tsmudge = %s\n\trequired = false\n'
                         '[core]\n\thooksPath = %s\n' % (smudge, hooks))
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        clean_env["HOME"] = home
        clone = subprocess.run([REAL_GIT, "clone", "-q", self.source, os.path.join(self.base, "control")],
                               env=clean_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(clone.returncode, 0, clone.stderr)
        self.assertTrue(os.path.exists(markers["smudge-ran"]), "the control did not fire the filter")
        self.assertTrue(os.path.exists(markers["hook-ran"]), "the control did not fire the hook")
        for path in markers.values():
            if os.path.exists(path):
                os.unlink(path)

        cwd = os.path.join(self.base, "cwd")
        os.makedirs(cwd)
        before = os.getcwd()
        os.chdir(cwd)
        self.addCleanup(os.chdir, before)
        with unittest.mock.patch.dict(os.environ, {"HOME": home, "XDG_CONFIG_HOME": home}):
            fetch.fetch(self.store, self.source, "main")
        for name, path in markers.items():
            self.assertFalse(os.path.exists(path), name)
        self.assertEqual(os.listdir(cwd), [])


class RefusalTest(Base):
    def test_a_symbolic_link_refuses_the_whole_download(self):
        self.package()
        os.symlink("/etc/passwd", os.path.join(self.source, "link"))
        self.commit()
        with self.assertRaisesRegex(fetch.FetchError, "symbolic link"):
            fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_a_submodule_refuses_the_whole_download(self):
        self.package()
        run_git(self.source, "update-index", "--add", "--cacheinfo", "160000,%s,sub" % SHA)
        run_git(self.source, "commit", "-q", "-m", "submodule")
        with self.assertRaisesRegex(fetch.FetchError, "submodule"):
            fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_a_path_with_a_newline_in_it_refuses_the_download(self):
        self.package()
        self.write("bad\nname", "x")
        self.commit()
        with self.assertRaisesRegex(fetch.FetchError, "unsafe path"):
            fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_an_oversize_file_refuses_the_download(self):
        self.package()
        self.write("big.bin", b"x" * 200)
        self.commit()
        with unittest.mock.patch.object(fetch, "MAX_FILE_BYTES", 100):
            with self.assertRaisesRegex(fetch.FetchError, "over the limit"):
                fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_too_many_files_refuses_the_download(self):
        for n in range(6):
            self.write("f%d" % n)
        self.commit()
        with unittest.mock.patch.object(fetch, "MAX_FILES", 5):
            with self.assertRaisesRegex(fetch.FetchError, "more than 5 files"):
                fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_too_many_bytes_in_total_refuses_the_download(self):
        for n in range(5):
            self.write("f%d" % n, b"x" * 40)
        self.commit()
        with unittest.mock.patch.object(fetch, "MAX_TOTAL_BYTES", 100), \
                unittest.mock.patch.object(fetch, "_file_limit", lambda: 10 ** 8):
            with self.assertRaisesRegex(fetch.FetchError, "total more than"):
                fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_names_that_collide_ignoring_case_refuse_the_download(self):
        run_git(self.source, "config", "core.ignorecase", "false")
        for name in ("Readme", "README"):
            oid = subprocess.run([REAL_GIT, "hash-object", "-w", "--stdin"], cwd=self.source,
                                 input=b"x", stdout=subprocess.PIPE, check=True).stdout.decode().strip()
            run_git(self.source, "update-index", "--add", "--cacheinfo", "100644,%s,%s" % (oid, name))
        run_git(self.source, "commit", "-q", "-m", "case")
        with self.assertRaisesRegex(fetch.FetchError, "unsafe paths"):
            fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_an_empty_repository_refuses_the_download(self):
        self.commit()
        with self.assertRaisesRegex(fetch.FetchError, "no files"):
            fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_a_ref_that_does_not_exist_leaves_nothing(self):
        self.package()
        with self.assertRaisesRegex(fetch.FetchError, "git fetch failed"):
            fetch.fetch(self.store, self.source, "no-such-branch")
        self.nothing_left()

    def test_a_source_that_is_not_a_repository_leaves_nothing(self):
        empty = os.path.join(self.base, "plain")
        os.makedirs(empty)
        with self.assertRaisesRegex(fetch.FetchError, "git fetch failed"):
            fetch.fetch(self.store, empty, "main")
        self.nothing_left()

    def test_a_failure_while_writing_leaves_no_staging_directory(self):
        self.package()
        with unittest.mock.patch.object(safefs, "write_tree",
                                        side_effect=safefs.SafeFsError("simulated")):
            with self.assertRaisesRegex(fetch.FetchError, "cannot write the package"):
                fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_a_failure_part_way_through_writing_removes_what_was_written(self):
        self.package()
        real = safefs.write_tree

        def partial(root, tree, executable=()):
            first = sorted(tree)[0]
            real(root, {first: tree[first]})
            raise safefs.SafeFsError("simulated failure after one file")

        with unittest.mock.patch.object(safefs, "write_tree", partial):
            with self.assertRaises(fetch.FetchError):
                fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_a_missing_cache_directory_is_refused(self):
        self.package()
        shutil.rmtree(self.cache)
        with self.assertRaises(fetch.FetchError):
            fetch.fetch(self.store, self.source, "main")
        self.assertEqual(os.listdir(self.scratch), [])

    def test_a_cache_directory_that_is_a_symbolic_link_is_not_followed(self):
        self.package()
        outside = os.path.join(self.base, "outside")
        os.makedirs(outside)
        shutil.rmtree(self.cache)
        os.symlink(outside, self.cache)
        with self.assertRaises(fetch.FetchError):
            fetch.fetch(self.store, self.source, "main")
        self.assertEqual(os.listdir(outside), [])
        self.assertEqual(os.listdir(self.scratch), [])

    def test_git_missing_from_the_path_is_reported(self):
        self.package()
        empty = os.path.join(self.base, "emptybin")
        os.makedirs(empty)
        with unittest.mock.patch.dict(os.environ, {"PATH": empty}):
            with self.assertRaisesRegex(fetch.FetchError, "git is not installed"):
                fetch.fetch(self.store, self.source, "main")
        self.nothing_left()


class SourceAndRefTest(unittest.TestCase):
    def test_sources_that_are_not_allowed_are_refused(self):
        bad = ["", None, 5, "--upload-pack=touch /tmp/x", "-x", "ext::sh -c id",
               "ext::sh", "git://example.com/x", "http://example.com/x", "ftp://example.com/x",
               "https://user:secret@example.com/x", "https://user@example.com/x", "https://",
               "ssh://", "git@github.com:org/repo.git", "host:path", "has space", "tab\there",
               "new\nline", "esc\x1b[0m", "x" * 2001, "/no/such/directory/anywhere",
               "relative/missing/dir", "file:///x‮y", "у"]
        for source in bad:
            with self.subTest(source=source):
                with self.assertRaises(fetch.FetchError):
                    fetch.normalize_source(source)

    def test_urls_urllib_cannot_parse_are_a_refusal_not_a_traceback(self):
        for source in ("https://[abc/x", "https://℀.com/x", "ssh://[::1/x",
                       "ssh://-oProxyCommand=id/x", "ssh://hostу/x", "https://[::1]x/y",
                       "ssh://[fe80::1%25eth0/x"):
            with self.subTest(source=source):
                with self.assertRaises(fetch.FetchError):
                    fetch.normalize_source(source)

    def test_a_source_starting_with_a_dash_is_refused_even_if_such_a_directory_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            os.mkdir(os.path.join(directory, "-dir"))
            before = os.getcwd()
            os.chdir(directory)
            self.addCleanup(os.chdir, before)
            for source in ("-dir", "--dir"):
                with self.subTest(source=source):
                    with self.assertRaises(fetch.FetchError):
                        fetch.normalize_source(source)

    def test_allowed_sources_are_returned_or_turned_into_file_urls(self):
        for url in ("https://github.com/a/b.git", "ssh://git@github.com/a/b.git",
                    "file:///tmp/some/repo", "HTTPS://example.com/a"):
            with self.subTest(url=url):
                self.assertEqual(fetch.normalize_source(url), url)
        with tempfile.TemporaryDirectory() as directory:
            got = fetch.normalize_source(directory)
            self.assertTrue(got.startswith("file:///"))
            self.assertEqual(fetch.normalize_source(directory + "/"), got)

    def test_refs_that_could_be_options_or_odd_are_refused(self):
        bad = ["", None, 5, "-x", "--upload-pack=touch x", "a b", "main\n", ":x", "a..b", "a/",
               "x.lock", "a;b", "$(id)", "a`b`", "a\x00b", "x" * 201, "у", "@{u}", "a b c"]
        for ref in bad:
            with self.subTest(ref=ref):
                with self.assertRaises(fetch.FetchError):
                    fetch.check_ref(ref)

    def test_ordinary_refs_are_accepted(self):
        for ref in ("main", "HEAD", "v1.0.0", "feature/new-thing", "a" * 40, "release_2", "x@y"):
            with self.subTest(ref=ref):
                self.assertEqual(fetch.check_ref(ref), ref)


class ListingTest(unittest.TestCase):
    def parse(self, *lines, **limits):
        return fetch.parse_listing(b"".join(lines), **limits)

    def test_good_entries_are_returned(self):
        got = self.parse(listing_line(path=b"a/b.txt"), listing_line(b"100755", path=b"run.sh"))
        self.assertEqual([(e.path, e.mode) for e in got], [("a/b.txt", b"100644"), ("run.sh", b"100755")])

    def test_entries_that_are_not_regular_files_are_refused(self):
        cases = [(b"120000", b"blob", "symbolic link"), (b"160000", b"commit", "submodule"),
                 (b"040000", b"tree", "regular file"), (b"100664", b"blob", "regular file"),
                 (b"100644", b"commit", "regular file"), (b"100755", b"tree", "regular file")]
        for mode, kind, word in cases:
            with self.subTest(mode=mode, kind=kind):
                with self.assertRaisesRegex(fetch.FetchError, word):
                    self.parse(listing_line(), listing_line(mode, kind, size=b"-", path=b"x"))

    def test_unsafe_paths_are_refused(self):
        bad = [b".git/config", b"a/.git/hooks/pre-commit", b".GIT/x", b"git~1/x", b"../x",
               b"a/../b", b"/abs", b"a\\b", b"a:b", b"a//b", b"a/./b", b"bad\nname", b"esc\x1b[0m",
               b"x" * 600, b"trail/", b".git"]
        for path in bad:
            with self.subTest(path=path):
                with self.assertRaises(fetch.FetchError):
                    self.parse(listing_line(path=path))

    def test_a_path_that_is_not_utf8_is_refused(self):
        with self.assertRaisesRegex(fetch.FetchError, "UTF-8"):
            self.parse(listing_line(path=b"caf\xe9"))

    def test_collisions_are_refused(self):
        for paths in ([b"README", b"readme"], [b"a", b"a/b"], [b"\xc3\xa9", b"e\xcc\x81"]):
            with self.subTest(paths=paths):
                with self.assertRaises(fetch.FetchError):
                    self.parse(*[listing_line(path=p) for p in paths])

    def test_limits_are_enforced(self):
        with self.assertRaisesRegex(fetch.FetchError, "more than 2 files"):
            self.parse(*[listing_line(path=b"f%d" % n) for n in range(3)], max_files=2)
        with self.assertRaisesRegex(fetch.FetchError, "over the limit"):
            self.parse(listing_line(size=b"101"), max_file_bytes=100)
        with self.assertRaisesRegex(fetch.FetchError, "total more than"):
            self.parse(listing_line(size=b"60", path=b"a"), listing_line(size=b"60", path=b"b"),
                       max_total_bytes=100)
        self.parse(listing_line(size=b"100"), max_file_bytes=100, max_total_bytes=100)

    def test_the_default_limits_are_the_ones_the_plan_states(self):
        self.assertEqual((fetch.MAX_FILES, fetch.MAX_FILE_BYTES, fetch.MAX_TOTAL_BYTES),
                         (2048, 16 * 1024 * 1024, 64 * 1024 * 1024))

    def test_malformed_or_empty_listings_are_refused(self):
        for data in (b"", b"\0", b"garbage\0", b"100644 blob xyz 3\ta\0", b"100644 blob " + b"1" * 40 + b"\ta\0",
                     listing_line(oid=b"Z" * 40), listing_line(size=b"-", path=b"a"),
                     listing_line(oid=b"1" * 39)):
            with self.subTest(data=data):
                with self.assertRaises(fetch.FetchError):
                    fetch.parse_listing(data)


class ObjectsTest(unittest.TestCase):
    ENTRIES = [fetch.Entry("a", b"100644", "1" * 40, 3), fetch.Entry("b", b"100755", "2" * 40, 2)]

    def output(self, *parts):
        return b"".join(parts)

    def good(self):
        return self.output(b"%s blob 3\nabc\n" % (b"1" * 40), b"%s blob 2\nxy\n" % (b"2" * 40))

    def test_matching_output_is_split(self):
        self.assertEqual(fetch.read_objects(self.good(), self.ENTRIES), [b"abc", b"xy"])

    def test_content_may_contain_newlines_and_header_lookalikes(self):
        body = b"x\n%s blob 9" % (b"2" * 40)
        entries = [fetch.Entry("a", b"100644", "1" * 40, len(body))]
        out = b"%s blob %d\n%s\n" % (b"1" * 40, len(body), body)
        self.assertEqual(fetch.read_objects(out, entries), [body])

    def test_every_mismatch_is_refused(self):
        h1, h2 = b"1" * 40, b"2" * 40
        bad = [b"", b"%s blob 3\nabc\n" % h1,
               b"%s blob 3\nabc\n%s blob 3\nxy\n" % (h1, h2),
               b"%s blob 4\nabcd\n%s blob 2\nxy\n" % (h1, h2),
               b"%s tree 3\nabc\n%s blob 2\nxy\n" % (h1, h2),
               b"%s blob 3\nabc\n%s blob 2\nxy\n" % (h2, h1),
               b"%s blob 3\nabc\n%s blob 2\nxy" % (h1, h2),
               b"%s blob 3\nabc\n%s blob 2\nxy\nextra" % (h1, h2),
               b"%s blob x\nabc\n%s blob 2\nxy\n" % (h1, h2),
               b"%s blob 3 \nabc\n%s blob 2\nxy\n" % (h1, h2),
               b"%s blob 3\nabcX%s blob 2\nxy\n" % (h1, h2),
               b"missing newline header"]
        for output in bad:
            with self.subTest(output=output[:40]):
                with self.assertRaises(fetch.FetchError):
                    fetch.read_objects(output, self.ENTRIES)


def crafted_commit(source, tree_bytes):
    """Make a commit on main whose tree is exactly `tree_bytes`, bypassing git's own checks."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

    def run(args, data=None):
        done = subprocess.run([REAL_GIT, "-c", "user.name=T", "-c", "user.email=t@example.test"] + args,
                              cwd=source, env=env, input=data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if done.returncode != 0:
            raise AssertionError(done.stderr.decode())
        return done.stdout.decode().strip()

    tree = run(["hash-object", "-t", "tree", "--literally", "-w", "--stdin"], tree_bytes)
    commit = run(["commit-tree", "-m", "crafted", tree])
    run(["update-ref", "refs/heads/main", commit])
    return commit


def entry(mode, name, oid_hex):
    return mode + b" " + name + b"\0" + bytes.fromhex(oid_hex)


class CraftedRepositoryTest(Base):
    def blob(self):
        done = subprocess.run([REAL_GIT, "hash-object", "-w", "--stdin"], cwd=self.source,
                              input=b"payload", stdout=subprocess.PIPE, check=True)
        return done.stdout.decode().strip()

    def subtree(self, entries):
        done = subprocess.run([REAL_GIT, "hash-object", "-t", "tree", "--literally", "-w", "--stdin"],
                              cwd=self.source, input=b"".join(entries), stdout=subprocess.PIPE, check=True)
        return done.stdout.decode().strip()

    def test_paths_naming_git_or_dotdot_are_refused_with_nothing_left(self):
        blob = self.blob()
        git_dir = self.subtree([entry(b"100644", b"config", blob)])
        nested = self.subtree([entry(b"40000", b".git", git_dir)])
        cases = {
            ".git directory": [entry(b"40000", b".git", git_dir)],
            "nested .git directory": [entry(b"40000", b"a", nested)],
            ".git file": [entry(b"100644", b".git", blob)],
            "dotdot name": [entry(b"100644", b"..", blob)],
            "dot name": [entry(b"100644", b".", blob)],
            "git~1": [entry(b"40000", b"GIT~1", git_dir)],
            "case variant": [entry(b"40000", b".GIT", git_dir)],
        }
        for name, entries in cases.items():
            with self.subTest(case=name):
                crafted_commit(self.source, b"".join(entries))
                with self.assertRaises(fetch.FetchError):
                    fetch.fetch(self.store, self.source, "main")
                self.nothing_left()

    def test_a_tree_that_shares_subtrees_cannot_blow_up_memory(self):
        blob = self.blob()
        width = 60
        names = ["d%02d" % n for n in range(width)]
        level2 = self.subtree([entry(b"100644", n.encode(), blob) for n in names])
        level1 = self.subtree([entry(b"40000", n.encode(), level2) for n in names])
        crafted_commit(self.source, b"".join(entry(b"40000", n.encode(), level1) for n in names))
        # width ** 3 = 216000 files, from a handful of objects. The listing is stopped early.
        with self.assertRaisesRegex(fetch.FetchError, "more output than the limits allow"):
            fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_a_listing_just_under_the_cap_is_still_counted(self):
        blob = self.blob()
        crafted_commit(self.source, b"".join(
            entry(b"100644", ("f%03d" % n).encode(), blob) for n in range(50)))
        with unittest.mock.patch.object(fetch, "MAX_FILES", 20):
            with self.assertRaisesRegex(fetch.FetchError, "more than 20 files|more output"):
                fetch.fetch(self.store, self.source, "main")
        self.nothing_left()


class ProcessTest(Base):
    def wrapper(self, body):
        directory = os.path.join(self.base, "wrapper")
        os.makedirs(directory, exist_ok=True)
        script = os.path.join(directory, "git")
        with open(script, "w") as handle:
            handle.write('#!/bin/sh\n%s\nexec "%s" "$@"\n' % (body, REAL_GIT))
        os.chmod(script, 0o755)
        return directory

    def alive(self, pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    def test_a_timeout_kills_what_git_started_not_only_git(self):
        self.package()
        pidfile = os.path.join(self.base, "child.pid")
        directory = self.wrapper('case "$*" in *" fetch "*) sleep 60 & echo $! > "%s"; wait;; esac' % pidfile)
        started = time.monotonic()
        with unittest.mock.patch.dict(os.environ, {"PATH": directory + os.pathsep + os.environ["PATH"]}):
            with unittest.mock.patch.object(fetch, "FETCH_TIMEOUT", 2):
                with self.assertRaisesRegex(fetch.FetchError, "timed out"):
                    fetch.fetch(self.store, self.source, "main")
        # Without a group kill, git's shell would wait for its 60 second child.
        self.assertLess(time.monotonic() - started, 20)
        with open(pidfile) as handle:
            pid = int(handle.read())
        deadline = time.time() + 5
        while self.alive(pid) and time.time() < deadline:
            time.sleep(0.1)
        if self.alive(pid):
            os.kill(pid, 9)
            self.fail("a process git started was still running after the timeout")
        self.nothing_left()

    def test_output_over_the_limit_stops_git_and_what_it_started(self):
        self.package()
        pidfile = os.path.join(self.base, "flood.pid")
        directory = self.wrapper('case "$*" in *" ls-tree "*) sleep 60 & echo $! > "%s"; '
                                 'yes | head -c 200000000; wait;; esac' % pidfile)
        started = time.monotonic()
        with unittest.mock.patch.dict(os.environ, {"PATH": directory + os.pathsep + os.environ["PATH"]}):
            with self.assertRaisesRegex(fetch.FetchError, "more output than the limits allow"):
                fetch.fetch(self.store, self.source, "main")
        self.assertLess(time.monotonic() - started, 20)
        with open(pidfile) as handle:
            pid = int(handle.read())
        deadline = time.time() + 5
        while self.alive(pid) and time.time() < deadline:
            time.sleep(0.1)
        if self.alive(pid):
            os.kill(pid, 9)
            self.fail("a process git started was still running after the output limit")
        self.nothing_left()

    def test_a_download_larger_than_the_file_limit_is_stopped(self):
        self.write("big.bin", os.urandom(3 * 1024 * 1024))
        self.write("package.json", "{}")
        self.commit()
        with unittest.mock.patch.object(fetch, "_file_limit", lambda: 1024 * 1024):
            with self.assertRaisesRegex(fetch.FetchError, "git .* failed"):
                fetch.fetch(self.store, self.source, "main")
        self.nothing_left()

    def test_the_default_file_limit_is_four_times_the_total_limit(self):
        self.assertEqual(fetch._file_limit(), 4 * fetch.MAX_TOTAL_BYTES)


class GitInvocationTest(Base):
    def make_wrapper(self, body_before_exec=""):
        directory = os.path.join(self.base, "wrapper")
        os.makedirs(directory, exist_ok=True)
        self.log = os.path.join(self.base, "git.log")
        script = os.path.join(directory, "git")
        with open(script, "w") as handle:
            handle.write('#!/bin/sh\n{ echo "ARGS: $*"; env | grep "^GIT_" | sort; echo END; } >> "%s"\n'
                         '%s\nexec "%s" "$@"\n' % (self.log, body_before_exec, REAL_GIT))
        os.chmod(script, 0o755)
        return directory

    def calls(self):
        with open(self.log) as handle:
            blocks = handle.read().split("END\n")
        return [block for block in blocks if block.strip()]

    def test_only_the_expected_git_commands_run_with_a_clean_environment(self):
        self.package()
        directory = self.make_wrapper()
        hostile = {"GIT_DIR": "/nonexistent/dir", "GIT_WORK_TREE": "/nonexistent/tree",
                   "GIT_INDEX_FILE": "/nonexistent/index", "GIT_EXTERNAL_DIFF": "/nonexistent/diff",
                   "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath",
                   "GIT_CONFIG_VALUE_0": "/nonexistent/hooks", "GIT_ASKPASS": "/nonexistent/ask",
                   "GIT_SSH": "/nonexistent/ssh", "GIT_EXEC_PATH": "/nonexistent/exec",
                   "PATH": directory + os.pathsep + os.environ["PATH"]}
        with unittest.mock.patch.dict(os.environ, hostile):
            fetch.fetch(self.store, self.source, "main")
        self.assertFalse(os.path.exists("/nonexistent"))
        calls = self.calls()
        subcommands = set()
        for block in calls:
            args = block.splitlines()[0][len("ARGS: "):].split()
            index = 0
            while index < len(args) and args[index] == "-c":
                index += 2
            subcommands.add(args[index])
        self.assertEqual(subcommands, {"init", "fetch", "rev-parse", "ls-tree", "cat-file"})
        allowed = {"GIT_TERMINAL_PROMPT", "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL",
                   "GIT_ALLOW_PROTOCOL", "GIT_SSH_COMMAND", "GIT_LFS_SKIP_SMUDGE"}
        for block in calls:
            names = {line.split("=")[0] for line in block.splitlines()[1:] if line.startswith("GIT_")}
            self.assertEqual(names, allowed, block)
            self.assertNotIn("/nonexistent", block)
            ssh = [line for line in block.splitlines() if line.startswith("GIT_SSH_COMMAND=")]
            self.assertEqual(len(ssh), 1)
            for option in ("BatchMode=yes", "ForwardAgent=no", "ClearAllForwardings=yes"):
                self.assertIn(option, ssh[0])

    def test_the_fetch_is_inert_by_its_arguments(self):
        self.package()
        directory = self.make_wrapper()
        with unittest.mock.patch.dict(os.environ, {"PATH": directory + os.pathsep + os.environ["PATH"]}):
            fetch.fetch(self.store, self.source, "main")
        fetch_call = next(block for block in self.calls() if " fetch " in block.splitlines()[0])
        line = fetch_call.splitlines()[0]
        for expected in ("core.hooksPath=", "transfer.fsckObjects=true", "--no-tags",
                         "--no-recurse-submodules", "--depth 1", " -- file:///", "main"):
            self.assertIn(expected, line)
        init_call = next(block for block in self.calls() if " init " in block.splitlines()[0])
        self.assertIn("--template=", init_call.splitlines()[0])
        for block in self.calls():
            words = block.splitlines()[0].split()
            for banned in ("clone", "checkout", "merge", "pull", "submodule", "worktree", "archive"):
                self.assertNotIn(banned, words)

    def test_the_environment_and_global_config_cannot_redirect_the_fetch(self):
        self.package()
        decoy = os.path.join(self.base, "decoy")
        os.makedirs(decoy)
        run_git(decoy, "init", "-q", "--template=")
        with open(os.path.join(decoy, "docs"), "w") as handle:
            handle.write("decoy")
        run_git(decoy, "add", "-A")
        run_git(decoy, "commit", "-q", "-m", "decoy")
        home = os.path.join(self.base, "home")
        os.makedirs(home)
        url = "file://" + self.source
        with open(os.path.join(home, ".gitconfig"), "w") as handle:
            handle.write('[url "file://%s"]\n\tinsteadOf = %s\n[core]\n\thooksPath = /nonexistent\n'
                         % (decoy, url))
        with unittest.mock.patch.dict(os.environ, {"HOME": home, "XDG_CONFIG_HOME": home}):
            got = fetch.fetch(self.store, self.source, "main")
        self.assertTrue(os.path.exists(os.path.join(got.path, "package.json")))
        self.assertTrue(os.path.isfile(os.path.join(got.path, "docs", "notes.md")))

    def test_a_git_that_hangs_times_out_and_leaves_nothing(self):
        self.package()
        directory = self.make_wrapper('case "$*" in *" fetch "*) sleep 20;; esac')
        with unittest.mock.patch.dict(os.environ, {"PATH": directory + os.pathsep + os.environ["PATH"]}):
            with unittest.mock.patch.object(fetch, "FETCH_TIMEOUT", 1):
                with self.assertRaisesRegex(fetch.FetchError, "timed out"):
                    fetch.fetch(self.store, self.source, "main")
        self.nothing_left()


if __name__ == "__main__":
    unittest.main()
