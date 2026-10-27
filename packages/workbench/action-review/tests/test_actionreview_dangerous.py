"""The dangerous cases, end to end (`docs/specs/action-review.md`, "Testing"; the cases are in `dangerous-cases.json`, which
the owner reviews and plan 4 reuses).

Plan `2026-10-26-action-review-engine`, increment J. Each case runs `main` in a scratch project that has the real
`safe-git` installed and pinned, a real Git repository and a fake bridge, so `describe` is the real one run through the
real launcher. A case a fixed check decides is run with a bridge that would approve everything: it is declined and the
bridge is never started. A case only a rubric question decides is run with a bridge that approves (which shows that no
fixed check catches it) and with one that declines (which shows that the text reaches the bridge as data and that the
decline is passed through); whether a real model declines it is plan 4's labelled run and is not claimed here. A text that
looks like a secret is built at run time and is never in a file, a message or an assertion."""

import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

from tests import support_helpers, support_project
from tests.support_project import tool
from workbench import firstparty, launch, store

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "action-review")
CASES = os.path.join(MODULE, "tests", "dangerous-cases.json")
SECTION = ".workbench/workbench/action-review"
GIT = shutil.which("git")
CLEAN = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "GIT_CONFIG_GLOBAL": os.devnull,
         "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
STEPS = ("write", "repeat", "mkdir", "symlink", "git", "rule_text", "rule_field")
HOWS = ("control", "code", "refused", "model")
# What the spec and the plan name; a case file that loses one of these no longer covers it.
CATEGORIES = ("secret-in-diff", "secret-in-subject", "secret-in-trailer", "secret-in-body", "head-mismatch", "program-selecting-setting",
              "reviewer-directed-text", "remove-git-metadata", "truncated-object", "credential-file",
              "path-through-link", "unreviewable-command-line", "rule-does-not-load")


def secrets():
    """The secret-shaped strings a case text may name, built here so that no file holds one."""
    return {"aws": "AKIA" + "A" * 16}


def cases():
    with open(CASES, encoding="utf-8") as handle:
        return json.load(handle)["cases"]


def git(where, *args):
    done = subprocess.run([GIT, *args], cwd=where, env=dict(CLEAN, HOME=tempfile.gettempdir()), capture_output=True,
                          text=True)
    if done.returncode:
        raise AssertionError("git %s failed: %s" % (" ".join(args), done.stderr))
    return done.stdout.strip()


def envelope(verdict, failed, reason):
    reply = json.dumps({"verdict": verdict, "failed_checks": list(failed), "reason": reason})
    return json.dumps({"contract": 1, "ok": True, "vendor": "codex", "model": "m", "reply": reply,
                       "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": None}}) + "\n"


APPROVES = envelope("approve", [], "The request is plain.")


def declines(question):
    return envelope("decline", [question], "The request is not one to approve.")


class CaseFile(unittest.TestCase):
    """The shape of the set, which the owner reviews: what each case is, what declines it and what is not claimed."""

    @classmethod
    def setUpClass(cls):
        cls.helper = support_helpers.load("action-review")
        cls.cases = cases()
        cls.rules = {}
        for name in ("safe-git-commit.json", "safe-git-remove.json"):
            with open(os.path.join(MODULE, "rules", name), encoding="utf-8") as handle:
                rule = cls.helper.build_rule(name, json.load(handle))
            cls.rules[rule.action] = rule

    def action(self, case):
        return case["command"].split()[3]

    def test_each_case_has_an_id_a_known_kind_and_a_title(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertIn(case["how"], HOWS)
                self.assertTrue(case["title"].strip())
                self.assertIn("wb run safe-git ", case["command"])
                self.assertEqual({"id", "category", "how", "title", "setup", "command", "expect"}
                                 | ({"declined_by"} if case["how"] in ("code", "model") else set())
                                 | ({"plan4"} if case["how"] == "model" else set()), set(case) - {"note"})

    def test_every_setup_step_is_one_the_runner_knows(self):
        for case in self.cases:
            for step in case["setup"]:
                with self.subTest(case=case["id"]):
                    self.assertEqual(1, len(step))
                    self.assertIn(next(iter(step)), STEPS)

    def test_the_set_names_every_category_the_spec_and_the_plan_name(self):
        self.assertEqual(set(CATEGORIES), {case["category"] for case in self.cases} - {"control"})
        self.assertIn("control", {case["category"] for case in self.cases})

    def test_a_removal_of_git_metadata_is_tried_in_each_spelling(self):
        spellings = [case["command"].rsplit("-- ", 1)[1] for case in self.cases
                     if case["category"] == "remove-git-metadata"]
        for wanted in (".git", ".git/", "./.git", ".GIT", ".git/config", "sub/../.git", "sub/.git"):
            self.assertIn(wanted, spellings)

    def test_what_declines_a_case_is_a_check_or_a_question_of_the_rule_that_the_command_names(self):
        for case in self.cases:
            if case["how"] not in ("code", "model"):
                continue
            with self.subTest(case=case["id"]):
                rule = self.rules[self.action(case)]
                named, failed = case["declined_by"], case["expect"]["failed_checks"]
                self.assertIn(named, rule.checks if case["how"] == "code" else rule.questions)
                self.assertIn(named, failed)
                self.assertTrue(set(failed) <= set(rule.checks if case["how"] == "code" else rule.questions))
                self.assertEqual(len(failed), len(set(failed)))
                self.assertEqual(case["how"] == "model", case["expect"]["bridge_asked"])
                if case["how"] == "model":
                    self.assertEqual([named], failed)

    def test_a_case_only_the_model_decides_is_listed_for_plan_4_and_never_claimed_as_covered(self):
        modelled = [case for case in self.cases if case["how"] == "model"]
        self.assertTrue(modelled)
        for case in modelled:
            self.assertIs(True, case["plan4"])
            self.assertEqual("no_reviewer_directed_text", case["declined_by"])
        self.assertEqual([], [case["id"] for case in self.cases if case["how"] != "model" and "plan4" in case])

    def test_a_refused_case_expects_no_describe_and_no_bridge(self):
        for case in self.cases:
            if case["how"] == "refused":
                with self.subTest(case=case["id"]):
                    expect = dict(case["expect"])
                    self.assertTrue(expect.pop("refusal_contains"))
                    self.assertEqual({"exit": 1, "describe_run": False, "bridge_asked": False}, expect)

    def test_the_file_is_ascii_and_holds_no_secret_shaped_text(self):
        with open(CASES, "rb") as handle:
            data = handle.read()
        data.decode("ascii")
        self.assertIsNone(self.helper.secret_kind(data.decode("ascii")))
        self.assertIsNone(self.helper.diff_secret_kind("+++ b/x\n@@ -0,0 +1 @@\n+" + data.decode("ascii")))


@unittest.skipUnless(GIT, "git was not found")
class EndToEnd(support_project.Project):
    """One case at a time in a fresh scratch project: the real `safe-git`, a real repository and a fake bridge."""

    SCRIPT = ("#!/bin/sh\necho ran >> '%(log)s'\ncat > '%(stdin)s'\ncat '%(answer)s'\n")

    def setUp(self):
        support_project.Project.setUp(self)
        self.helper = support_helpers.load("action-review")
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        base = os.path.realpath(holder.name)
        self.log, self.stdin, self.answer = (os.path.join(base, name) for name in ("ran.log", "stdin", "answer.json"))
        self.write_answer(APPROVES)
        with open(os.path.join(PACKAGE, "safe-git", "module.json"), encoding="utf-8") as handle:
            declared = json.load(handle)
        with open(os.path.join(PACKAGE, "safe-git", "helper", "safe-git"), "rb") as handle:
            real = handle.read()
        bridge, bridge_files = tool(commands={"bridge": {"helper": support_project.HELPER_PATH, "arguments": ["ask"]}},
                                    helper=(self.SCRIPT % {"log": self.log, "stdin": self.stdin,
                                                           "answer": self.answer}).encode())
        bridge["provides"] = ["p:model-bridge"]
        # The unprefixed capability `commit` is the first-party package's; the scratch package does not need it.
        safe_git = {key: value for key, value in declared.items()
                    if key not in ("name", "version", "description", "provides")}
        self.MODULES = {"h": (support_project.HARNESS, {}), "safe-git": (safe_git, {"helper/safe-git": real}),
                        "bridge": (bridge, bridge_files)}
        self.store_root = os.path.join(self.home, ".config", "project-workbench")
        self.guarded = store.Store(self.store_root)
        self.guarded.ensure()
        self.ready()
        self.pin("bridge", self.installed("bridge"))
        self.pin("safe-git", self.installed("safe-git", "helper/safe-git"), kit=1)
        launch.install_wrapper(self.guarded, firstparty.default_distribution())
        for patch in (unittest.mock.patch.dict(os.environ, {"HOME": self.home, "PATH": os.pathsep.join(
                [os.path.join(self.store_root, "bin"), os.environ.get("PATH", "")])}),
                      unittest.mock.patch.object(self.helper, "CAPABILITY", "p:model-bridge")):
            patch.start()
            self.addCleanup(patch.stop)
        self.install_module_files()
        self.make_repository()

    def install_module_files(self):
        self.put(".workbench/review.json", '{"format": 1, "bridge": "bridge", "model": "m1", "effort": "low"}')
        for name in ("rubric/rubric.md", "reply-schema.json", "rules/safe-git-commit.json",
                     "rules/safe-git-remove.json"):
            with open(os.path.join(MODULE, *name.split("/")), "rb") as handle:
                self.put(SECTION + "/" + name, handle.read())

    def make_repository(self):
        shutil.rmtree(os.path.join(self.real, ".git"))
        git(self.real, "init", "-q")
        self.put("README.txt", "readme\n")
        git(self.real, "add", "README.txt")
        git(self.real, "commit", "-q", "-m", "first")
        self.head = git(self.real, "rev-parse", "HEAD")

    def put(self, rel, data):
        path = os.path.join(self.real, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode("utf-8"))

    def write_answer(self, text):
        with open(self.answer, "w", encoding="ascii") as handle:
            handle.write(text)

    def setup_step(self, step):
        (name, value), = step.items()
        built = secrets()

        def text(raw):
            return raw.format(**built) if "{aws}" in raw else raw
        if name == "write":
            self.put(value[0], text(value[1]))
        elif name == "repeat":
            self.put(value[0], value[1] * value[2])
        elif name == "mkdir":
            os.makedirs(os.path.join(self.real, *value.split("/")), exist_ok=True)
        elif name == "symlink":
            os.symlink(value[1], os.path.join(self.real, value[0]))
        elif name == "git":
            git(self.real, *value)
        elif name == "rule_text":
            self.put(SECTION + "/rules/" + value[0], value[1])
        elif name == "rule_field":
            path = os.path.join(self.real, *(SECTION + "/rules/" + value[0]).split("/"))
            with open(path, encoding="utf-8") as handle:
                body = json.load(handle)
            body[value[1]] = value[2]
            self.put(SECTION + "/rules/" + value[0], json.dumps(body))
        else:
            raise AssertionError("unknown step %s" % name)

    def run_case(self, case):
        for step in case["setup"]:
            self.setup_step(step)
        text = case["command"].replace("{head}", self.head).replace("{wrong_head}", "b" * 40)
        text = text.replace("{aws}", secrets()["aws"])
        describes = []
        real_describe = self.helper.describe

        def counted(*args, **kwargs):
            describes.append(args[1].file)
            return real_describe(*args, **kwargs)
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(self.helper, "describe", counted):
            code = self.helper.main(["review", text], io.BytesIO(), out, err, self.real)
        return code, out.getvalue(), err.getvalue(), describes

    def asked(self):
        return os.path.exists(self.log)

    def check(self, case, code, out, err, describes):
        expect = case["expect"]
        self.assertEqual(expect["exit"], code, err)
        self.assertEqual(expect["bridge_asked"], self.asked(), err)
        if expect["exit"] == 0:
            self.assertEqual("", err)
            verdict = json.loads(out)
            self.assertEqual(expect["verdict"], verdict["verdict"])
            self.assertEqual(expect["failed_checks"], verdict["failed_checks"])
            self.assertTrue(describes)
        else:
            self.assertEqual("", out)
            last = err.rstrip("\n").split("\n")[-1]
            self.assertTrue(last.startswith("refused: "), err)
            self.assertIn(expect["refusal_contains"], last)
            self.assertEqual(expect["describe_run"], bool(describes))


def snapshot(top):
    found = {}
    for base, dirs, files in os.walk(top):
        for name in dirs + files:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, top)
            if os.path.islink(full):
                found[rel] = "link:" + os.readlink(full)
            elif os.path.isfile(full):
                with open(full, "rb") as handle:
                    found[rel] = handle.read()
            else:
                found[rel] = "dir"
    return found


def make(case):
    def test(self):
        for step in case["setup"]:
            self.setup_step(step)
        before = snapshot(self.real)
        case_without_setup = dict(case, setup=[])
        if case["how"] != "model":
            code, out, err, describes = self.run_case(case_without_setup)
            self.check(case, code, out, err, describes)
        else:
            code, out, err, describes = self.run_case(case_without_setup)
            self.assertEqual(("approve", True), (json.loads(out)["verdict"], self.asked()), "a code check decides it")
            os.remove(self.log)
            self.write_answer(declines(case["declined_by"]))
            code, out, err, describes = self.run_case(case_without_setup)
            self.check(case, code, out, err, describes)
            with open(self.stdin, "rb") as handle:
                prompt = handle.read().decode("utf-8")
            body = next(part for part in case["command"].split("--body '")[1:])
            body = body.split("' --")[0]
            self.assertIn(json.dumps(body, ensure_ascii=True)[1:-1], prompt)
            data = prompt.split("FACTS-BEGIN-")[1].split("\n")[1]
            self.assertIn(json.dumps(body, ensure_ascii=True)[1:-1], data)
            self.assertEqual(case["declined_by"], json.loads(out)["failed_checks"][0])
        self.assertEqual(before, snapshot(self.real), "the project changed")
    return test


for _case in cases():
    setattr(EndToEnd, "test_" + _case["id"].replace("-", "_"), make(_case))
del _case


if __name__ == "__main__":
    unittest.main()
