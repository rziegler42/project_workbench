"""Shared test support for the harness tests: a neutral tree, the items read from it, and a synthetic layout with made-up names.

A module's own tests may import this (a `tests/support*` file) and no other test module."""

import json
import os
import shutil

from workbench import firstparty, neutral

SKILL = b"---\nname: sample\ndescription: A sample skill\n---\nDo the thing.\n"
AGENT = (b"---\nname: reviewer\ndescription: Reviews changes\ntools: read, search\n"
         b"model: sonnet\n---\nYou review.\n")
COMMAND = b"---\nname: ship\ndescription: Ship it\nargs: [target]\n---\nShip $ARGUMENTS\n"


def tree(**extra):
    files = {"skills/sample/SKILL.md": SKILL, "agents/reviewer.md": AGENT,
             "commands/ship.md": COMMAND}
    files.update(extra)
    return files


def items(**extra):
    return neutral.read_items(tree(**extra))


SYNTHETIC = {
    "root": {"file": "FIXTURE.md", "import": "AGENTS.md"},
    "kinds": {
        "skill": {"path": ".fixture/skills/{name}/SKILL.md",
                  "fields": {"name": "name", "description": "description"}},
        "agent": {"path": ".fixture/agents/{name}.md",
                  "fields": {"name": "name", "description": "description", "tools": "tools",
                             "model": "model"},
                  "tools": {"read": ["Read"], "search": ["Grep", "Glob"],
                            "edit": ["Edit", "Write"], "shell": ["Bash"]}},
        "command": {"path": ".fixture/commands/{name}.md",
                    "fields": {"name": "name", "description": "description",
                               "args": "argument-hint"}},
    },
    "local_settings": {
        "path": ".fixture/settings.local.json", "format": "json",
        "actions": {"deny": "permissions.deny", "ask": "permissions.ask"},
        "rules": {"shell": "Bash({pattern})", "read": "Read({path})", "write": "Edit({path})"},
        "absolute": "//"},
    "hooks": "none",
    "exclude": ["FIXTURE.md", ".fixture/"],
    "notes": ["Restart the session to load the new settings."],
}

PACKAGE = "synthetic"
MODULE = "fixture"
HARNESS = PACKAGE + "/" + MODULE
PROVIDES = ["instructions", "skills", "agents", "commands", "permissions"]


def renamed(layout, name="second"):
    """The layout with its paths moved from `fixture` to `name`, for a second synthetic harness."""
    return json.loads(json.dumps(layout).replace("FIXTURE.md", name.upper() + ".md")
                      .replace(".fixture", "." + name))


def write_package(distribution, layout=None, package=PACKAGE, module=MODULE):
    """The synthetic harness package, `<distribution>/packages/synthetic`, with one harness module named
    `fixture`; `package` and `module` name another. It provides the five capabilities its layout
    renders. Returns the package path."""
    path = os.path.join(distribution, firstparty.PACKAGES, package)
    os.makedirs(os.path.join(path, module))
    with open(os.path.join(path, "package.json"), "w") as handle:
        json.dump({"name": package, "version": "0.1.0", "contract": 1, "modules": [module]}, handle)
    with open(os.path.join(path, module, "module.json"), "w") as handle:
        json.dump({"name": module, "version": "0.1.0", "type": "harness",
                   "description": "A synthetic harness for the installer's tests.",
                   "provides": PROVIDES, "layout": layout or SYNTHETIC}, handle)
    return path


def distribution(directory, layout=None):
    """A distribution at `directory` whose one first-party package is the synthetic harness, with its
    shipped approvals written by the release mechanism. A harness has to be first-party to provide the
    unprefixed capabilities, so the tests attach it from here and pass this path as the distribution."""
    # `workbench/` holds the shipped approvals the release mechanism writes below.
    os.makedirs(os.path.join(directory, "workbench"))
    # `install` reads the base from its distribution. The base is the installer's own content, not a
    # module's, so the tests copy the real one instead of making up a second.
    shutil.copytree(os.path.join(firstparty.default_distribution(), "base"),
                    os.path.join(directory, "base"))
    write_package(directory, layout)
    firstparty.release_approvals(directory)
    return directory
