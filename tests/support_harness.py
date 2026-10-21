"""Shared test support for the harness tests: a neutral tree, the items read from it, and Claude's layout.

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


CLAUDE = {
    "root": {"file": "CLAUDE.md", "import": "AGENTS.md"},
    "kinds": {
        "skill": {"path": ".claude/skills/{name}/SKILL.md",
                  "fields": {"name": "name", "description": "description"}},
        "agent": {"path": ".claude/agents/{name}.md",
                  "fields": {"name": "name", "description": "description", "tools": "tools",
                             "model": "model"},
                  "tools": {"read": ["Read"], "search": ["Grep", "Glob"],
                            "edit": ["Edit", "Write"], "shell": ["Bash"]}},
        "command": {"path": ".claude/commands/{name}.md",
                    "fields": {"name": "name", "description": "description",
                               "args": "argument-hint"}},
    },
    "local_settings": {
        "path": ".claude/settings.local.json", "format": "json",
        "actions": {"deny": "permissions.deny", "ask": "permissions.ask"},
        "rules": {"shell": "Bash({pattern})", "read": "Read({path})", "write": "Edit({path})"},
        "absolute": "//"},
    "hooks": "none",
    "exclude": ["CLAUDE.md", ".claude/"],
    "notes": ["Restart the session to load the new settings."],
}
