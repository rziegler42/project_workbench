"""Shared test support for the harness tests: a neutral tree, the items read from it, and a synthetic layout with made-up names.

A module's own tests may import this (a `tests/support*` file) and no other test module."""

from workbench import neutral

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
