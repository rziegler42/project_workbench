"""The names the installer, the kit and their tests must not know: the first-party modules, the helpers
they ship, the commands they declare and the harnesses with their paths.

Everything is read from the `module.json` files under `packages/`, so nothing here names one; the
harnesses that have no module yet are listed in `tests/fixtures/boundary-words.json`."""

import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES = os.path.join(ROOT, "packages")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "boundary-words.json")
SHORTEST = 3


def declarations(packages=PACKAGES):
    for path in sorted(glob.glob(os.path.join(packages, "*", "*", "module.json"))):
        with open(path, encoding="utf-8") as handle:
            yield json.load(handle)


def _last(path):
    return path.rstrip("/").rsplit("/", 1)[-1]


def _tagged(document):
    """The `(kind, word)` pairs one module declaration gives, case-folded."""
    name = document["name"].casefold()
    yield "module", name
    yield "module", name.replace("-", "")
    if document.get("type") == "harness":
        yield "harness", name
    for command in document.get("commands", {}):
        yield "command", command.casefold()
    for path in list(document.get("ships", ())) + [c["helper"] for c in document.get("checks", ())]:
        yield "helper", _last(path).casefold()
    layout = document.get("layout")
    if isinstance(layout, dict):
        paths = [layout.get("root", {}).get("file", ""), layout.get("local_settings", {}).get("path", "")]
        paths += [kind.get("path", "").split("{", 1)[0] for kind in layout.get("kinds", {}).values()]
        paths += list(layout.get("exclude", ())) + list(layout.get("tolerated", ()))
        for path in paths:
            if path:
                yield "layout path", path.casefold().rstrip("/")


def _kind(kind, packages):
    return sorted({word for document in declarations(packages) for each, word in _tagged(document)
                   if each == kind})


def module_names(packages=PACKAGES):
    """The declared module names, and each with its hyphens removed, case-folded."""
    return _kind("module", packages)


def harness_names(packages=PACKAGES, fixture=FIXTURE):
    """The names of the modules that are harnesses, and the harnesses that have no module yet."""
    with open(fixture, encoding="utf-8") as handle:
        listed = [name.casefold() for name in json.load(handle)["harnesses"]]
    return sorted(set(listed) | set(_kind("harness", packages)))


def command_names(packages=PACKAGES):
    """The names of the commands the modules declare."""
    return _kind("command", packages)


def helper_names(packages=PACKAGES):
    """The last segment of each shipped file and each check helper path, which is a helper's pin name."""
    return _kind("helper", packages)


def layout_paths(packages=PACKAGES):
    """The root file, the directory of each kind, the settings path, the exclude entries and the tolerated
    paths of each harness layout, case-folded and without a trailing slash."""
    return _kind("layout path", packages)


def sources(packages=PACKAGES, fixture=FIXTURE):
    """Every word the boundary test looks for, case-folded and without the ones of two characters or
    fewer, mapped to where it came from: its kind and the module (or the list) that gave it."""
    found = {}
    with open(fixture, encoding="utf-8") as handle:
        for name in json.load(handle)["harnesses"]:
            found.setdefault(name.casefold(), "harness listed in %s" % os.path.basename(fixture))
    for document in declarations(packages):
        for kind, word in _tagged(document):
            found.setdefault(word, "%s of the module %s" % (kind, document["name"]))
    return {word: found[word] for word in sorted(found) if len(word) >= SHORTEST}


def words(packages=PACKAGES, fixture=FIXTURE):
    """Every word the boundary test looks for."""
    return sorted(sources(packages, fixture))
