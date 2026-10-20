import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

from tests import support
from tests.test_preview import HARNESS, NOTES, decl
from workbench import (approvals, approve, cli, fetch, install, manifest, preview, projectfs,
                       sources, store, verify)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = "11111111-2222-4333-8444-555555555555"
DIGEST = re.compile(r"digest: ([0-9a-f]{64})")
MARKER = os.path.join(".workbench", "local", "incomplete")


class Typist(io.StringIO):
    """A standard input that answers from what the command has printed so far."""

    def __init__(self, out, reply):
        io.StringIO.__init__(self)
        self.out, self.reply, self.reads = out, reply, 0

    def readline(self, limit=-1):
        self.reads += 1
        return self.reply(self.out.getvalue()) + "\n"


def correct(text):
    return DIGEST.findall(text)[-1][:12]


class InstallBase(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = os.path.realpath(holder.name)
        self.store_root = os.path.join(self.root, "store")
        self.guarded = store.Store(self.store_root)
        self.guarded.ensure()
        self.count = 0
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)

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

    def approve(self, path):
        result = verify.verify_package(path, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        for item in result.modules:
            approvals.record_module(self.guarded, "%s/%s" % (item.package, item.name),
                                    item.declaration_hash, item.tree_hash, "tester",
                                    "2026-10-20T00:00:00Z")

    def good(self):
        path = self.package()
        os.chmod(os.path.join(path, "notes", "scripts", "run.sh"), 0o755)
        self.approve(path)
        return path

    def place(self, name="proj", state="missing"):
        place = os.path.join(self.root, name)
        if state == "empty":
            os.mkdir(place)
        elif state == "git":
            os.makedirs(os.path.join(place, ".git"))
        return place

    def run_install(self, place, path, reply=correct, seed=None, extra=(), select=("h", "notes")):
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(path, None)] + list(extra), list(select))
        code = install.run(self.guarded, command, Typist(out, reply), out, err, seed=seed)
        return code, out.getvalue(), err.getvalue()

    def tree(self, top):
        found = {}
        for base, dirs, files in os.walk(top):
            for name in dirs + files:
                full = os.path.join(base, name)
                info = os.lstat(full)
                found[os.path.relpath(full, top)] = (info.st_mode, info.st_size, info.st_mtime_ns)
        return found

    def read(self, *parts):
        with open(os.path.join(*parts), "rb") as handle:
            return handle.read()


class InstallTest(InstallBase):
    def test_install_into_missing_empty_and_lone_git_target(self):
        path = self.good()
        for state in ("missing", "empty", "git"):
            with self.subTest(state=state):
                place = self.place("proj-" + state, state)
                code, out, err = self.run_install(place, path)
                self.assertEqual(0, code, (out, err))
                self.assertTrue(os.path.isfile(os.path.join(place, ".workbench", "manifest.json")))
                self.assertFalse(os.path.exists(os.path.join(place, MARKER)))
                self.assertTrue(os.path.isdir(os.path.join(place, ".git")))
                self.assertIn("nothing was committed", out)
                self.assertIn("harness not attached: attach is not built yet", out)
        self.assertIn("no remote is recorded", err)

    def test_install_writes_expected_tree_modes_classes_and_manifest(self):
        path = self.good()
        place = self.place()
        code, out, err = self.run_install(place, path, seed=SEED)
        self.assertEqual(0, code, (out, err))
        self.assertEqual(b"# Notes\n", self.read(place, "docs", "notes.md"))
        script = os.path.join(place, ".workbench", "p", "notes", "scripts", "run.sh")
        self.assertEqual(0o755, os.stat(script).st_mode & 0o777)
        self.assertEqual(0o644, os.stat(os.path.join(place, "docs", "notes.md")).st_mode & 0o777)
        self.assertEqual(manifest.BASE_IGNORE, self.read(place, ".workbench", ".gitignore"))
        self.assertTrue(os.path.isfile(os.path.join(place, "AGENTS.md")))
        document = manifest.parse(self.read(place, ".workbench", "manifest.json"))
        classes = {item["path"]: item["class"] for item in document["files"]}
        self.assertEqual("seeded", classes["docs/notes.md"])
        self.assertEqual("module-owned", classes[".workbench/p/notes/scripts/run.sh"])
        self.assertEqual(SEED, document["seed"])
        # Every file the manifest lists exists, and nothing else is in the tree.
        on_disk = set()
        for base, dirs, files in os.walk(place):
            dirs[:] = [d for d in dirs if d != ".git"]
            on_disk.update(os.path.relpath(os.path.join(base, f), place) for f in files)
        listed = {item["path"] for item in document["files"]} | {".workbench/manifest.json"}
        self.assertEqual(listed, on_disk)

    def test_install_creates_an_empty_git_only_when_no_git_and_runs_no_program(self):
        path = self.good()
        with unittest.mock.patch.object(subprocess, "Popen",
                                        side_effect=AssertionError("ran a program")):
            code, _, err = self.run_install(self.place("a"), path)
            self.assertEqual(0, code, err)
            self.assertEqual("ref: refs/heads/main\n",
                             self.read(self.root, "a", ".git", "HEAD").decode())
            lone = self.place("b", "git")
            with open(os.path.join(lone, ".git", "HEAD"), "w") as handle:
                handle.write("ref: refs/heads/other\n")
            self.assertEqual(0, self.run_install(lone, path)[0])
            self.assertEqual("ref: refs/heads/other\n",
                             self.read(lone, ".git", "HEAD").decode())
        # Git itself accepts what was written, and sees nothing committed.
        env = fetch.git_environment()
        for name in ("a",):
            top = os.path.join(self.root, name)
            branch = subprocess.run(["git", "-C", top, "symbolic-ref", "--short", "HEAD"],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(("main\n", 0), (branch.stdout, branch.returncode))
            status = subprocess.run(["git", "-C", top, "status", "--porcelain"], env=env,
                                    capture_output=True, text=True)
            self.assertEqual(0, status.returncode, status.stderr)

    def test_install_never_reads_lone_git_config(self):
        path = self.good()
        place = self.place("lone", "git")
        with open(os.path.join(place, ".git", "config"), "w") as handle:
            handle.write("[core]\n\tfsmonitor = touch %s\n" % os.path.join(self.root, "pwned"))
        opened, watching = [], [True]

        def audit(event, args):
            if watching[0] and event == "open":
                opened.append(str(args[0]))

        sys.addaudithook(audit)
        try:
            with unittest.mock.patch.object(subprocess, "Popen",
                                            side_effect=AssertionError("ran a program")):
                code, out, err = self.run_install(place, path)
        finally:
            watching[0] = False
        self.assertEqual(0, code, (out, err))
        self.assertEqual([], [p for p in opened if p.endswith(os.path.join(".git", "config"))])
        self.assertFalse(os.path.exists(os.path.join(self.root, "pwned")))

    def test_marker_exists_before_git_init(self):
        path = self.good()
        place = self.place()
        seen = []
        original = install._git_init

        def check(held, writer):
            seen.append(os.path.isfile(os.path.join(place, MARKER)))
            original(held, writer)

        with unittest.mock.patch.object(install, "_git_init", check):
            code, _, err = self.run_install(place, path)
        self.assertEqual((0, [True]), (code, seen), err)

    def test_failure_in_git_creation_leaves_marker(self):
        path = self.good()
        place = self.place()
        original = projectfs.Writer.create_git

        def failing(writer, skeleton):
            original(writer, skeleton[:3])
            raise OSError("disk full")

        with unittest.mock.patch.object(projectfs.Writer, "create_git", failing):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code)
        self.assertIn("failed: disk full", err)
        self.assertIn("written:\n  ./ (the target directory)", err)
        self.assertIn("  .git/\n", err)
        self.assertIn("  AGENTS.md", err)
        self.assertIn(projectfs.MARKER + " is left in place", err)
        self.assertTrue(os.path.isfile(os.path.join(place, MARKER)))
        self.assertFalse(os.path.exists(os.path.join(place, "AGENTS.md")))
        self.assertNotIn("Traceback", out + err)
        again, _, why = self.run_install(place, path)
        self.assertEqual(1, again)
        self.assertIn("unfinished install", why)

    def test_a_git_link_planted_after_the_marker_writes_nothing_outside(self):
        path = self.good()
        place = self.place()
        victim = os.path.join(self.root, "victim")
        os.mkdir(victim)
        original = install._git_init

        def plant(held, writer):
            os.symlink(victim, os.path.join(place, ".git"))
            original(held, writer)

        with unittest.mock.patch.object(install, "_git_init", plant):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code)
        self.assertIn(".git already exists", err)
        self.assertEqual([], os.listdir(victim))
        self.assertTrue(os.path.isfile(os.path.join(place, MARKER)))

    def test_git_directory_planted_after_the_marker_is_a_conflict_not_reused(self):
        path = self.good()
        place = self.place()
        original = install._git_init

        def plant(held, writer):
            os.mkdir(os.path.join(place, ".git"))
            original(held, writer)

        with unittest.mock.patch.object(install, "_git_init", plant):
            code, _, err = self.run_install(place, path)
        self.assertEqual(3, code)
        self.assertEqual([], os.listdir(os.path.join(place, ".git")))

    def test_created_modes_do_not_follow_a_permissive_umask(self):
        path = self.good()
        place = self.place()
        old = os.umask(0)
        try:
            code, _, err = self.run_install(place, path)
        finally:
            os.umask(old)
        self.assertEqual(0, code, err)
        for base, dirs, files in os.walk(place):
            for name in dirs:
                self.assertEqual(0o755, os.stat(os.path.join(base, name)).st_mode & 0o777, name)
            for name in files:
                mode = os.stat(os.path.join(base, name)).st_mode & 0o777
                self.assertIn(mode, (0o644, 0o755), os.path.join(base, name))
        self.assertEqual(0o755, os.stat(place).st_mode & 0o777)

    def test_refused_target_causes_no_fetch_or_cache_write(self):
        full = self.place("full", "empty")
        with open(os.path.join(full, "f"), "w") as handle:
            handle.write("x")
        os.symlink(full, os.path.join(self.root, "link"))
        before = self.tree(self.store_root)
        with unittest.mock.patch.object(fetch, "fetch",
                                        side_effect=AssertionError("fetched")) as patched:
            for place in (full, os.path.join(self.root, "link"), self.store_root,
                          os.path.join(self.root, "no", "parent")):
                code, out, err = self.run_install(place, "https://example.test/p.git")
                self.assertEqual((1, True), (code, err.startswith("refused: ")), (place, err))
                self.assertNotIn("Downloading", out)
        patched.assert_not_called()
        self.assertEqual(before, self.tree(self.store_root))

    def test_install_commits_nothing(self):
        path = self.good()
        place = self.place()
        self.assertEqual(0, self.run_install(place, path)[0])
        env = fetch.git_environment()
        log = subprocess.run(["git", "-C", place, "rev-parse", "--verify", "HEAD"], env=env,
                             capture_output=True)
        self.assertNotEqual(0, log.returncode)
        staged = subprocess.run(["git", "-C", place, "diff", "--cached", "--name-only"],
                                env=env, capture_output=True)
        self.assertEqual(b"", staged.stdout)

    def test_refuses_without_terminal_before_fetching(self):
        path = self.good()
        place = self.place()
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False):
            with unittest.mock.patch.object(fetch, "fetch",
                                            side_effect=AssertionError("fetched")):
                for package in (path, "https://example.test/p.git"):
                    code, out, err = self.run_install(place, package)
                    self.assertEqual((1, ""), (code, out))
                    self.assertIn("refused: install is owner-run", err)
                    self.assertIn("preview install", err)
        self.assertFalse(os.path.exists(place))

    def test_wrong_digest_cancels_and_writes_nothing(self):
        path = self.good()
        place = self.place("proj", "empty")
        self.warm(path)
        before = (self.tree(place), self.tree(self.store_root))
        answers = [lambda t: "", lambda t: "yes", lambda t: "0" * 12, lambda t: "x" * 500,
                   lambda t: correct(t)[:11], lambda t: correct(t) + "0",
                   lambda t: correct(t)[:11] + ("0" if correct(t)[11] != "0" else "1")]
        for answer in answers:
            code, out, err = self.run_install(place, path, reply=answer)
            self.assertEqual(1, code, err)
            self.assertTrue(out.endswith("cancelled: nothing was written\n"))
            self.assertEqual(before, (self.tree(place), self.tree(self.store_root)))
        self.assertEqual([], os.listdir(os.path.join(self.store_root, "projects")))

    def warm(self, path):
        """Any command once, so the store's own first-run seeding is not counted."""
        cli.main(["verify", path], io.StringIO(), io.StringIO(), store_root=self.store_root)

    def test_typed_ahead_input_is_discarded(self):
        path = self.good()
        order = []
        out, err = io.StringIO(), io.StringIO()

        class Stream(io.StringIO):
            def fileno(self):
                return 99

            def readline(self, limit=-1):
                order.append("read")
                return correct(out.getvalue()) + "\n"

        with unittest.mock.patch.object(install.termios, "tcflush",
                                        lambda fd, what: order.append(("flush", fd, what))):
            command = sources.Command(self.place(), [(path, None)], ["h", "notes"])
            code = install.run(self.guarded, command, Stream(), out, err, seed=SEED)
        self.assertEqual(0, code, err.getvalue())
        self.assertEqual([("flush", 99, install.termios.TCIFLUSH), "read"], order)

    def test_the_answer_is_bounded(self):
        path = self.good()
        limits = []
        out, err = io.StringIO(), io.StringIO()

        class Stream(io.StringIO):
            def readline(self, limit=-1):
                limits.append(limit)
                return "\n"

        command = sources.Command(self.place(), [(path, None)], ["h", "notes"])
        install.run(self.guarded, command, Stream(), out, err, seed=SEED)
        self.assertEqual([install.MAX_ANSWER], limits)

    def test_package_changed_after_preview_refused(self):
        path = self.good()
        place = self.place()

        def change(text):
            with open(os.path.join(path, "notes", "files", "docs", "notes.md"), "ab") as handle:
                handle.write(b"changed")
            return correct(text)

        code, out, err = self.run_install(place, path, reply=change)
        self.assertEqual(1, code)
        self.assertIn("refused: the packages changed while the plan was shown", err)
        self.assertFalse(os.path.exists(place))
        self.assertEqual([], os.listdir(os.path.join(self.store_root, "projects")))

    def test_target_swapped_after_preview_refused(self):
        path = self.good()
        place = self.place("proj", "empty")

        def swap(text):
            os.rename(place, place + ".old")
            os.mkdir(place)
            return correct(text)

        code, out, err = self.run_install(place, path, reply=swap)
        self.assertEqual(1, code)
        self.assertIn("refused: the target changed", err)
        self.assertEqual([], os.listdir(place))
        self.assertEqual([], os.listdir(place + ".old"))

    def test_target_gaining_a_file_after_preview_refused(self):
        path = self.good()
        place = self.place("proj", "empty")

        def add(text):
            with open(os.path.join(place, "late"), "w") as handle:
                handle.write("x")
            return correct(text)

        code, _, err = self.run_install(place, path, reply=add)
        self.assertEqual(1, code)
        self.assertIn("refused: the target changed", err)
        self.assertEqual(["late"], os.listdir(place))

    def test_existing_path_is_a_conflict_nothing_overwritten(self):
        path = self.good()
        place = self.place("proj", "empty")
        original = projectfs.Writer.create_file

        def racing(writer, rel, data, executable=False):
            if rel == "docs/notes.md":
                os.makedirs(os.path.join(place, "docs"), exist_ok=True)
                with open(os.path.join(place, "docs", "notes.md"), "w") as handle:
                    handle.write("mine")
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", racing):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code)
        self.assertEqual(b"mine", self.read(place, "docs", "notes.md"))
        self.assertIn("failed: the path already exists", err)

    def test_failure_after_first_write_exits_3_lists_paths_and_keeps_marker(self):
        path = self.good()
        place = self.place()
        original = projectfs.Writer.create_file
        calls = [0]

        def failing(writer, rel, data, executable=False):
            calls[0] += 1
            if calls[0] == 4:
                raise OSError("disk full")
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", failing):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code)
        self.assertTrue(err.startswith("failed: disk full\nwritten:\n"))
        self.assertIn("  " + projectfs.MARKER + "\n", err)
        self.assertIn("not written:\n", err)
        self.assertIn("  .workbench/manifest.json\n", err)
        self.assertIn("  projects/", err)
        self.assertTrue(os.path.isfile(os.path.join(place, MARKER)))
        self.assertFalse(os.path.exists(os.path.join(place, ".workbench", "manifest.json")))
        self.assertNotIn("Traceback", out + err)

    def test_failure_writing_the_store_entry_is_a_failure_part_way(self):
        path = self.good()
        place = self.place()
        with unittest.mock.patch.object(store.Store, "write", side_effect=OSError("store full")):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code)
        self.assertIn("failed: store full", err)
        self.assertIn("files are written but its guarded store entries are not", err)
        self.assertTrue(os.path.isfile(os.path.join(place, MARKER)))
        self.assertTrue(os.path.isfile(os.path.join(place, ".workbench", "manifest.json")))

    def test_marker_directory_is_not_an_existing_project(self):
        path = self.good()
        place = self.place("proj", "git")
        os.makedirs(os.path.join(place, ".workbench", "local"))
        with open(os.path.join(place, MARKER), "w"):
            pass
        with unittest.mock.patch.object(fetch, "fetch", side_effect=AssertionError("fetched")):
            code, out, err = self.run_install(place, "https://example.test/p.git")
        self.assertEqual(1, code)
        self.assertIn("unfinished install", err)

    def test_interrupt_before_write_exits_130(self):
        path = self.good()
        place = self.place()

        def interrupt(text):
            raise KeyboardInterrupt

        code, out, err = self.run_install(place, path, reply=interrupt)
        self.assertEqual(130, code)
        self.assertIn("cancelled: nothing was written", out)
        self.assertNotIn("Traceback", out + err)
        self.assertFalse(os.path.exists(place))

    def test_interrupt_during_the_write_exits_3(self):
        path = self.good()
        place = self.place()
        original = projectfs.Writer.create_file
        calls = [0]

        def interrupted(writer, rel, data, executable=False):
            calls[0] += 1
            if calls[0] == 3:
                raise KeyboardInterrupt
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", interrupted):
            code, out, err = self.run_install(place, path)
        self.assertEqual(3, code)
        self.assertIn("failed: interrupted", err)
        self.assertTrue(os.path.isfile(os.path.join(place, MARKER)))

    def test_a_closed_output_ends_quietly(self):
        path = self.good()
        out, err = io.StringIO(), io.StringIO()

        class Broken(io.StringIO):
            def write(self, text):
                raise BrokenPipeError

        command = sources.Command(self.place(), [(path, None)], ["h", "notes"])
        code = install.run(self.guarded, command, Typist(out, correct), Broken(), err, seed=SEED)
        self.assertEqual(1, code)
        self.assertEqual("", err.getvalue())

    def test_store_entries_written_and_id_matches_seed(self):
        path = self.good()
        place = self.place()
        self.assertEqual(0, self.run_install(place, path, seed=SEED)[0])
        project = manifest.project_id(SEED)
        seen = json.loads(self.read(self.store_root, "projects", project, "seen"))
        self.assertEqual({"format": 1, "kind": "path", "value": place}, seen)
        baselines = json.loads(self.read(self.store_root, "projects", project, "baselines"))
        self.assertEqual(1, baselines["format"])
        self.assertIn("AGENTS.md", baselines["baselines"])
        self.assertNotIn(projectfs.MARKER, baselines["baselines"])
        for rel, digest in baselines["baselines"].items():
            self.assertEqual(digest, hashlib.sha256(self.read(place, *rel.split("/"))).hexdigest(),
                             rel)

    def test_install_twice_with_one_seed_does_not_overwrite_the_store(self):
        path = self.good()
        self.assertEqual(0, self.run_install(self.place("a"), path, seed=SEED)[0])
        code, _, err = self.run_install(self.place("b"), path, seed=SEED)
        self.assertEqual(3, code)
        self.assertIn("the guarded store already holds projects/", err)

    def test_preview_matches_install_plan(self):
        path = self.good()
        shown, _ = io.StringIO(), io.StringIO()
        place = self.place()
        code = preview.run(self.guarded, sources.Command(place, [(path, None)], ["h", "notes"]),
                           shown, io.StringIO(), seed=SEED)
        self.assertEqual(0, code)
        code, out, err = self.run_install(place, path, seed=SEED)
        self.assertEqual(0, code, err)
        head = out.split("\nTo install, type", 1)[0]
        head = re.sub(r"digest: [0-9a-f]{64}\n", "", head)
        self.assertEqual(shown.getvalue().replace("preview only: nothing was written\n", ""), head)
        # What was written is what the plan listed.
        for line in head.splitlines():
            found = re.match(r"  create-file (\S+) \[\w[\w-]*\] \S+ (\d+) bytes sha256 ([0-9a-f]{64})",
                             line)
            if found and found.group(1) != projectfs.MARKER:
                data = self.read(place, *found.group(1).split("/"))
                self.assertEqual((int(found.group(2)), found.group(3)),
                                 (len(data), hashlib.sha256(data).hexdigest()), line)

    def test_install_end_to_end_from_file_url_source(self):
        import shutil
        path = self.good()
        env = dict(fetch.git_environment(), GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        repo = os.path.join(self.root, "origin")
        shutil.copytree(path, repo)
        for step in (["init", "--quiet", "--initial-branch=main"], ["add", "-A"],
                     ["commit", "--quiet", "-m", "package"]):
            subprocess.run(["git", "-C", repo] + step, env=env, check=True, capture_output=True)
        url = "file://" + repo
        place = self.place()
        code, out, err = self.run_install(place, url)
        self.assertEqual(0, code, (out, err))
        self.assertIn("Downloading file://" + repo, out)
        document = manifest.parse(self.read(place, ".workbench", "manifest.json"))
        (package,) = document["packages"]
        self.assertEqual(url, package["source"])
        self.assertRegex(package["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(1, len(os.listdir(os.path.join(self.store_root, "cache"))))
        self.assertEqual(b"# Notes\n", self.read(place, "docs", "notes.md"))


class InstallTerminalTest(InstallBase):
    """The command run in a child process whose terminals are real pseudo-terminals."""

    def setUp(self):
        InstallBase.setUp(self)
        self.home = self.root
        self.store_root = os.path.join(self.home, ".config", "project-workbench")
        self.guarded = store.Store(self.store_root)
        self.guarded.ensure()
        self.path = self.good()
        self.project = os.path.join(self.home, "proj")

    def drive(self, answer, **kwargs):
        env = dict(os.environ, HOME=self.home, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1",
                   PATH=support.clean_path())
        argv = [sys.executable, "-B", "-m", "workbench", "install", self.project,
                "--package", self.path, "--select", "h", "notes"]
        return support.drive_pty(self, argv, env, self.home, answer, b"> ", **kwargs)

    def test_the_digest_typed_in_a_terminal_installs(self):
        code, output, error = self.drive(correct)
        self.assertEqual((0, ""), (code, error), output)
        self.assertIn("nothing was committed", output)
        self.assertTrue(os.path.isfile(os.path.join(self.project, ".workbench", "manifest.json")))
        self.assertFalse(os.path.exists(os.path.join(self.project, MARKER)))
        self.assertEqual(1, len(os.listdir(os.path.join(self.store_root, "projects"))))

    def test_any_other_text_in_a_terminal_writes_nothing(self):
        code, output, error = self.drive("no")
        self.assertEqual(1, code, error)
        self.assertIn("cancelled: nothing was written", output)
        self.assertFalse(os.path.exists(self.project))

    def test_without_terminals_it_refuses(self):
        code, output, error = self.drive("x", stdin="pipe", stdout="pipe")
        self.assertEqual(1, code)
        self.assertIn("refused: install is owner-run", error)
        self.assertFalse(os.path.exists(self.project))

    def test_a_second_install_into_the_same_target_is_refused(self):
        self.assertEqual(0, self.drive(correct)[0])
        code, _, error = self.drive(correct)
        self.assertEqual(1, code)
        self.assertIn("refused", error)


if __name__ == "__main__":
    unittest.main()
