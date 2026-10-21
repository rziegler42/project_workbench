"""Check the ``layout`` of a harness module's declaration.

The layout is data that the installer applies; nothing in it is executed. ``problems`` returns
every reason a layout is refused, so a bad one is reported whole and before it can be approved.
The declaration loader only checks that the keys are known; the values are checked here, when the
module is verified (``modulefiles.verify_module``).

Keys, all optional (an absent key means ``none`` or empty):

``root``
    ``"none"``, or ``{"file": "CLAUDE.md", "import": "AGENTS.md"}``: a one-segment file name that
    holds an ``@<import>`` line, and the one-segment file it imports.
``kinds``
    For each of ``skill``, ``agent`` and ``command``: ``{"path": ..., "fields": {...}}``. A
    ``path`` is ``<dir>/{name}.md``, or ``<dir>/{name}/SKILL.md`` for a skill, whose bundled files
    then go below ``<dir>/{name}/``. ``fields`` maps a neutral front-matter field to the harness
    field, and must map ``name`` and ``description``. An agent may add ``tools``, which maps a
    neutral tool to a list of the harness tool names that grant it. A neutral field or tool the
    layout does not map cannot be expressed by this harness, and the translation fails closed.
``local_settings``
    ``"none"``, or ``{"path", "format": "json", "actions", "rules", "absolute"}``: the per-clone
    file, the dotted JSON key that holds the ``deny`` and the ``ask`` list, a rule template for
    each tool class (``Name({pattern})`` or, for ``read`` and ``write``, ``Name({path})``), and
    the prefix that spells an absolute path (``//`` or ``~/``).
``hooks``
    ``"none"``, or ``{"settings_key": "<key>"}``. No hook is built yet.
``exclude``
    The literal paths written to ``.git/info/exclude`` (a trailing ``/`` marks a directory). No
    glob, no space, nothing under ``.workbench`` and not the guarded store.
``notes``
    A short list of printable post-install notes.

Every path the layout writes (the root file, each kind's directory and the settings file) must be
covered by an ``exclude`` entry, compared by exact spelling because git compares exactly on most
systems. A ``dir/`` entry covers what is below ``dir`` and a kind directory equal to it, never a
file of that name; an entry that covers no written path is refused, so the layout cannot hide
unrelated files. The renderer must write each entry anchored (``/<entry>``), since git matches a
slash-free entry at any depth. The paths may not overlap, and no kind may share a directory with
another. Paths go through ``safefs``.

Left to the translation: an agent whose layout does not map ``tools`` and its tool table is valid
here, and is then never installed, because it cannot be restricted.
"""

import re
import unicodedata

from . import safefs

KINDS = ("skill", "agent", "command")
KIND_FIELDS = {"skill": ("name", "description"),
               "command": ("name", "description", "args"),
               "agent": ("name", "description", "tools", "model")}
TOOLS = ("read", "search", "edit", "shell", "web", "agents")
RULE_TOOLS = ("shell", "read", "write", "web")
ABSOLUTE_PREFIXES = ("//", "~/")

MAX_EXCLUDE = 64
MAX_NOTES = 10
MAX_NOTE_CHARS = 300

_FIELD = re.compile(r"^[a-z][a-z-]{0,30}\Z")
_TOOL = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}\Z")
_DOTTED = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,31}(\.[A-Za-z][A-Za-z0-9]{0,31})+\Z")
_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,31}\Z")
_TEMPLATE = re.compile(r"^([A-Za-z][A-Za-z0-9]{0,31})\((\{pattern\}|\{path\})\)\Z")
_NO_EXCLUDE_CHARS = set("*?[]!# \\")
# Claude accepts a path rule under these names and never consults it (checked on 2.1.305).
INERT_TEMPLATE_NAMES = ("Write", "NotebookEdit", "Glob", "MultiEdit")
REQUIRED_RULE_TOOLS = ("shell", "write")


def _fold(parts):
    return tuple(unicodedata.normalize("NFC", part).casefold() for part in parts)


def _covers(entry, entry_dir, path, path_is_dir):
    """True when an exclude entry (exact spelling) hides the written `path`."""
    if entry_dir:
        return _prefix(entry, path) and (len(entry) < len(path) or path_is_dir)
    return entry == path and not path_is_dir


def _prefix(small, big):
    return big[:len(small)] == small


class _Collect:
    def __init__(self):
        self.messages = []

    def add(self, where, message):
        self.messages.append("%s: %s" % (where, message))

    def path(self, value, where, one_segment=False):
        """Return the folded segments of a safe path that is not reserved, or None."""
        if not isinstance(value, str):
            self.add(where, "must be a string")
            return None
        try:
            parts = safefs.validate_relpath(value)
        except safefs.SafeFsError as exc:
            self.add(where, str(exc))
            return None
        folded = _fold(parts)
        if folded[0] == ".workbench":
            self.add(where, "%r is inside .workbench/" % value)
            return None
        if folded[:2] == (".config", "project-workbench"):
            self.add(where, "%r is the guarded store" % value)
            return None
        if one_segment and len(parts) != 1:
            self.add(where, "%r must be a single file name" % value)
            return None
        return folded

    def keys(self, value, where, allowed, required=()):
        if not isinstance(value, dict):
            self.add(where, "must be an object")
            return False
        for key in value:
            if key not in allowed:
                self.add(where, "unknown key %r (expected one of %s)" % (key, ", ".join(allowed)))
        missing = [key for key in required if key not in value]
        for key in missing:
            self.add(where, "missing key %r" % key)
        return not missing and all(key in allowed for key in value)


def problems(layout):
    """Return a list of messages, empty when `layout` is acceptable."""
    out = _Collect()
    if not isinstance(layout, dict):
        return ["layout: must be an object"]
    written = []
    root = layout.get("root", "none")
    if root != "none":
        written += _root(root, out)
    kinds = layout.get("kinds", {})
    written += _kinds(kinds, out)
    settings = layout.get("local_settings", "none")
    if settings != "none":
        written += _settings(settings, out)
    hooks = layout.get("hooks", "none")
    if hooks != "none":
        if out.keys(hooks, "layout.hooks", ("settings_key",), ("settings_key",)) \
                and not (isinstance(hooks["settings_key"], str)
                         and _WORD.match(hooks["settings_key"])):
            out.add("layout.hooks", "settings_key must be a plain word")
    hook_key = hooks["settings_key"] if isinstance(hooks, dict) \
        and isinstance(hooks.get("settings_key"), str) else None
    actions = settings.get("actions") if isinstance(settings, dict) else None
    if hook_key and isinstance(actions, dict) and any(
            isinstance(v, str) and v.split(".")[0] == hook_key for v in actions.values()):
        out.add("layout.hooks", "settings_key is the same top-level key as the permission lists")
    excluded = _exclude(layout.get("exclude", []), out)
    _notes(layout.get("notes", []), out)
    _overlaps(written, out)
    for where, _, raw, is_dir in written:
        if not any(_covers(entry, entry_dir, raw, is_dir) for entry, entry_dir in excluded):
            out.add(where, "is written but no exclude entry covers it, so it could be committed")
    for entry, entry_dir in excluded:
        if not any(_covers(entry, entry_dir, raw, is_dir) or _prefix(raw, entry)
                   for _, _, raw, is_dir in written):
            out.add("layout.exclude", "%r covers no path this layout writes" %
                    ("/".join(entry) + ("/" if entry_dir else "")))
    return out.messages


def _root(root, out):
    if not out.keys(root, "layout.root", ("file", "import"), ("file", "import")):
        return []
    folded = out.path(root["file"], "layout.root.file", one_segment=True)
    out.path(root["import"], "layout.root.import", one_segment=True)
    if root["file"] == root["import"]:
        out.add("layout.root", "the file may not import itself")
    return [("layout.root.file", folded, tuple(root["file"].split("/")), False)] if folded else []


def _kinds(kinds, out):
    if not out.keys(kinds, "layout.kinds", KINDS):
        return []
    written = []
    for kind in KINDS:
        if kind not in kinds:
            continue
        where = "layout.kinds.%s" % kind
        allowed = ("path", "fields") + (("tools",) if kind == "agent" else ())
        if not out.keys(kinds[kind], where, allowed, ("path", "fields")):
            continue
        entry = kinds[kind]
        directory = _kind_path(kind, entry["path"], where, out)
        if directory:
            written.append((where + ".path", directory[0], directory[1], True))
        _fields(kind, entry["fields"], where + ".fields", out)
        if "tools" in entry:
            _tools(entry["tools"], where + ".tools", out)
    return written


def _kind_path(kind, path, where, out):
    tail = "/{name}/SKILL.md" if kind == "skill" else "/{name}.md"
    if not isinstance(path, str) or not path.endswith(tail) or "{" in path[:-len(tail)] \
            or "}" in path[:-len(tail)]:
        out.add(where + ".path", "must be <directory>%s" % tail)
        return None
    folded = out.path(path[:-len(tail)], where + ".path")
    if folded == (".config",):
        out.add(where + ".path", "%r would contain the guarded store" % path)
        return None
    return (folded, tuple(path[:-len(tail)].split("/"))) if folded else None


def _fields(kind, fields, where, out):
    if not isinstance(fields, dict):
        out.add(where, "must be an object")
        return
    allowed = KIND_FIELDS[kind]
    for key, target in fields.items():
        if key not in allowed:
            out.add(where, "%r is not a neutral %s field (expected one of %s)"
                    % (key, kind, ", ".join(allowed)))
        if not isinstance(target, str) or not _FIELD.match(target):
            out.add(where, "%r must map to a lowercase field name" % key)
    for key in ("name", "description"):
        if key not in fields:
            out.add(where, "must map %r" % key)
    for key, target in fields.items():
        if key != "tools" and target == "tools":
            out.add(where, "%r may not map to the harness field 'tools'" % key)
    targets = [t for t in fields.values() if isinstance(t, str)]
    if len(set(targets)) != len(targets):
        out.add(where, "two neutral fields map to the same harness field")


def _tools(tools, where, out):
    if not isinstance(tools, dict):
        out.add(where, "must be an object")
        return
    for key, names in tools.items():
        if key not in TOOLS:
            out.add(where, "%r is not a neutral tool (expected one of %s)" % (key, ", ".join(TOOLS)))
        if (not isinstance(names, list) or not 1 <= len(names) <= 8
                or not all(isinstance(n, str) and _TOOL.match(n) for n in names)
                or len(set(names)) != len(names)):
            out.add(where, "%r must be a list of 1 to 8 distinct tool names" % key)


def _settings(settings, out):
    where = "layout.local_settings"
    keys = ("path", "format", "actions", "rules", "absolute")
    if not out.keys(settings, where, keys, keys):
        return []
    folded = out.path(settings["path"], where + ".path")
    if settings["format"] != "json":
        out.add(where + ".format", "must be \"json\"")
    actions = settings["actions"]
    if out.keys(actions, where + ".actions", ("deny", "ask"), ("deny", "ask")):
        for action in ("deny", "ask"):
            if not isinstance(actions[action], str) or not _DOTTED.match(actions[action]):
                out.add(where + ".actions", "%s must be a dotted key such as a.b" % action)
        if all(isinstance(actions[a], str) for a in ("deny", "ask")):
            deny, ask = actions["deny"].split("."), actions["ask"].split(".")
            if deny[-1] != "deny" or ask[-1] != "ask":
                out.add(where + ".actions", "the deny key must end in 'deny' and the ask key in "
                                            "'ask', so a deny cannot be written as an allow")
            if _prefix(deny, ask) or _prefix(ask, deny):
                out.add(where + ".actions", "deny and ask must be different, un-nested keys")
    rules = settings["rules"]
    if out.keys(rules, where + ".rules", RULE_TOOLS, REQUIRED_RULE_TOOLS):
        for tool, template in rules.items():
            match = _TEMPLATE.match(template) if isinstance(template, str) else None
            wanted = "{path}" if tool in ("read", "write") else "{pattern}"
            if not match or match.group(2) != wanted:
                out.add(where + ".rules", "%s must be Name(%s)" % (tool, wanted))
            elif match.group(1) in INERT_TEMPLATE_NAMES:
                out.add(where + ".rules", "%s uses %s, a rule name the harness accepts and never "
                                          "consults" % (tool, match.group(1)))
    if settings["absolute"] not in ABSOLUTE_PREFIXES:
        out.add(where + ".absolute", "must be one of %s" % ", ".join(ABSOLUTE_PREFIXES))
    return [(where + ".path", folded, tuple(settings["path"].split("/")), False)] if folded else []


def _exclude(entries, out):
    where = "layout.exclude"
    if not isinstance(entries, list) or len(entries) > MAX_EXCLUDE:
        out.add(where, "must be a list of at most %d paths" % MAX_EXCLUDE)
        return []
    found = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, str):
            out.add(where, "%r is not a string" % (entry,))
            continue
        is_dir = entry.endswith("/")
        folded = out.path(entry[:-1] if is_dir else entry, where)
        if folded is None:
            continue
        if _NO_EXCLUDE_CHARS & set(entry):
            out.add(where, "%r must be a literal path with no glob, space, '#' or '!'" % entry)
            continue
        if folded in seen:
            out.add(where, "%r is listed twice" % entry)
            continue
        seen.add(folded)
        found.append((tuple((entry[:-1] if is_dir else entry).split("/")), is_dir))
    return found


def _notes(notes, out):
    where = "layout.notes"
    if not isinstance(notes, list) or len(notes) > MAX_NOTES:
        out.add(where, "must be a list of at most %d notes" % MAX_NOTES)
        return
    for note in notes:
        if (not isinstance(note, str) or not note.strip() or len(note) > MAX_NOTE_CHARS
                or not note.isprintable()):
            out.add(where, "each note must be printable text of at most %d characters"
                    % MAX_NOTE_CHARS)


def _overlaps(written, out):
    for index, (where, folded, _, _) in enumerate(written):
        for other_where, other, _, _ in written[index + 1:]:
            if _prefix(folded, other) or _prefix(other, folded):
                out.add(where, "overlaps %s" % other_where)
