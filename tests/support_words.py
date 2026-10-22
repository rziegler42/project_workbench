"""The names the installer, the kit and their tests must not know: the first-party modules, the helpers
they ship and the harnesses.

The modules are read from the `module.json` files under `packages/`, so nothing here names one; the
harnesses that have no module yet are listed in `tests/fixtures/boundary-words.json`."""

import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "boundary-words.json")


def declarations():
    for path in sorted(glob.glob(os.path.join(ROOT, "packages", "*", "*", "module.json"))):
        with open(path, encoding="utf-8") as handle:
            yield json.load(handle)


def module_names():
    """The declared module names, and each with its hyphens removed, case-folded."""
    names = set()
    for document in declarations():
        name = document["name"].casefold()
        names.update((name, name.replace("-", "")))
    return sorted(names)


def harness_names():
    """The names of the modules that are harnesses, and the harnesses that have no module yet."""
    with open(FIXTURE, encoding="utf-8") as handle:
        names = set(json.load(handle)["harnesses"])
    names.update(d["name"].casefold() for d in declarations() if d.get("type") == "harness")
    return sorted(names)


def command_names():
    """The names of the commands the modules declare."""
    return sorted({name for document in declarations() for name in document.get("commands", {})})
