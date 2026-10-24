"""Check the ``layout`` of a harness module's declaration.

The layout is data that the installer applies; nothing in it is executed. ``problems`` returns
every reason a layout is refused, so a bad one is reported whole and before it can be approved.
The declaration loader only checks that the keys are known; the values are checked here, when the
module is verified (``modulefiles.verify_module``).

Keys, all optional (an absent key means ``none`` or empty):

``root``
    ``"none"``, or ``{"file": "HARNESS.md", "import": "AGENTS.md"}``: a one-segment file name that
    holds an ``@<import>`` line, and the one-segment file it imports.
``kinds``
    For each of ``skill``, ``agent`` and ``command``: ``{"path": ..., "fields": {...}}``. A
    ``path`` is ``<dir>/{name}.md``, or ``<dir>/{name}/SKILL.md`` for a skill, whose bundled files
    then go below ``<dir>/{name}/``. ``fields`` maps a neutral front-matter field to the harness
    field, and must map ``name`` and ``description``. An agent may add ``tools``, which maps a
    neutral tool to a list of the harness tool names that grant it. A neutral field or tool the
    layout does not map cannot be expressed by this harness, and the translation fails closed.
    An agent may also carry ``hook`` and ``scratch``, together, which describe a per-agent hook and the
    session's scratch directory (``_confinement``). An agent that declares ``writes`` or ``run`` is
    installed only where both are present.
``local_settings``
    ``"none"``, or ``{"path", "format": "json", "actions", "rules", "absolute"}``: the per-clone
    file, the dotted JSON key that holds the ``deny`` and the ``ask`` list, a rule template for
    each tool class (``Name({pattern})`` or, for ``read`` and ``write``, ``Name({path})``), and
    the prefix that spells an absolute path (``//`` or ``~/``).
``hooks``
    ``"none"``, or ``{"settings_key": "<key>"}`` with, optionally, ``"targets"``: for each file-editing tool the
    harness's hook can be given, the fields of that tool's input that name a file it writes
    (``{"<Tool>": ["<field>", ...]}``). The edit gate reads the table (``gate_hook.py``) and reads no tool name
    of its own. With ``"event"`` (a word), ``"timeout"`` (seconds, 1 to 600) and ``"block_code"`` (the exit code
    the harness takes as a block, 1 to 255), all three or none, and ``targets``, the layout describes the one hook
    the installer renders, the edit gate (``harnessplan.render_hook``); its matcher is the tools of ``targets``.
``exclude``
    The literal paths written to ``.git/info/exclude`` (a trailing ``/`` marks a directory). No
    glob, no space, nothing under ``.workbench`` and not the guarded store.
``tolerated``
    A short list of literal paths, each inside a top-level directory the layout writes into, that the
    harness itself or the owner may keep there; ``wb check`` does not warn about them. The directory is
    spelled as the layout spells it. A path the layout writes, one that contains such a path and one inside
    a file the layout writes are refused; one below a kind directory is allowed.
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

from .wbkit import safefs

KINDS = ("skill", "agent", "command")
KIND_FIELDS = {"skill": ("name", "description"),
               "command": ("name", "description", "args"),
               "agent": ("name", "description", "tools", "model")}
TOOLS = ("read", "search", "edit", "shell", "web", "agents")
RULE_TOOLS = ("shell", "read", "write", "web")
ABSOLUTE_PREFIXES = ("//", "~/")

MAX_EXCLUDE = 64
MAX_TOLERATED = 16
MAX_NOTES = 10
MAX_NOTE_CHARS = 300

_FIELD = re.compile(r"^[a-z][a-z-]{0,30}\Z")
_TOOL = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}\Z")
_DOTTED = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,31}(\.[A-Za-z][A-Za-z0-9]{0,31})+\Z")
_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,31}\Z")
_TEMPLATE = re.compile(r"^([A-Za-z][A-Za-z0-9]{0,31})\((\{pattern\}|\{path\})\)\Z")
_NO_EXCLUDE_CHARS = set("*?[]!# \\")
# A harness accepts a path rule under these names and never consults it (checked on the first
# harness, at version 2.1.305).
INERT_TEMPLATE_NAMES = ("Write", "NotebookEdit", "Glob", "MultiEdit")
REQUIRED_RULE_TOOLS = ("shell", "write")
# The one rule name each tool class may use, so a deny cannot be written under a name that does
# not stop its tool (a store-write deny as `Read(...)`). Checked on the first harness, at
# version 2.1.305; another harness adds its own names here when its formats are verified.
RULE_NAMES = {"shell": ("Bash",), "read": ("Read",), "write": ("Edit",), "web": ("WebFetch",)}
SETTINGS_KEYS = ("permissions",)
AGENT_TOOLS_FIELD = "tools"
MAX_SCRATCH_CHARS = 200
SCRATCH_PLACEHOLDERS = ("uid", "cwd_key", "session_id")
_SCRATCH_PART = re.compile(r"(?:[A-Za-z0-9._-]|\{(?:uid|cwd_key|session_id)\})+\Z")
# The harness tool names that may grant each neutral tool, so a "read" agent cannot be given Bash.
TOOL_NAMES = {"read": ("Read",), "search": ("Grep", "Glob"),
              "edit": ("Edit", "Write", "NotebookEdit", "MultiEdit"), "shell": ("Bash",),
              "web": ("WebFetch", "WebSearch"), "agents": ("Task", "Agent")}


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
        # Windows ignores trailing dots and spaces, so `.workbench.` is `.workbench` there.
        reserved = tuple(part.rstrip(" .") for part in folded)
        if reserved[0] == ".workbench":
            self.add(where, "%r is inside .workbench/" % value)
            return None
        if reserved[:2] == (".config", "project-workbench"):
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
        if out.keys(hooks, "layout.hooks", ("settings_key", "targets") + HOOK_RENDER, ("settings_key",)):
            if not (isinstance(hooks["settings_key"], str) and _WORD.match(hooks["settings_key"])):
                out.add("layout.hooks", "settings_key must be a plain word")
            if "targets" in hooks:
                _hook_targets(hooks["targets"], out)
            _hook_render(hooks, out)
    hook_key = hooks["settings_key"] if isinstance(hooks, dict) \
        and isinstance(hooks.get("settings_key"), str) else None
    actions = settings.get("actions") if isinstance(settings, dict) else None
    if hook_key and isinstance(actions, dict) and any(
            isinstance(v, str) and v.split(".")[0].casefold() == hook_key.casefold()
            for v in actions.values()):
        out.add("layout.hooks", "settings_key is the same top-level key as the permission lists")
    excluded = _exclude(layout.get("exclude", []), out)
    _notes(layout.get("notes", []), out)
    _overlaps(written, out)
    _tolerated(layout.get("tolerated", []), written, out)
    for where, _, raw, is_dir in written:
        if not any(_covers(entry, entry_dir, raw, is_dir) for entry, entry_dir in excluded):
            out.add(where, "is written but no exclude entry covers it, so it could be committed")
    for entry, entry_dir in excluded:
        if not any(_covers(entry, entry_dir, raw, is_dir) or _prefix(raw, entry)
                   for _, _, raw, is_dir in written):
            out.add("layout.exclude", "%r covers no path this layout writes" %
                    ("/".join(entry) + ("/" if entry_dir else "")))
    return out.messages


HOOK_RENDER = ("event", "timeout", "block_code")
MAX_HOOK_TIMEOUT = 600
MAX_HOOK_TOOLS = 16
MAX_HOOK_FIELDS = 4
_HOOK_TOOL = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,39}\Z")
_HOOK_FIELD = re.compile(r"[a-z][a-z_]{0,39}\Z")


def _hook_targets(targets, out):
    where = "layout.hooks.targets"
    if not isinstance(targets, dict) or not targets:
        out.add(where, "must be an object with at least one tool")
        return
    if len(targets) > MAX_HOOK_TOOLS:
        out.add(where, "at most %d tools" % MAX_HOOK_TOOLS)
    for tool, fields in targets.items():
        if not _HOOK_TOOL.match(tool):
            out.add(where, "%r is not a plain tool name" % tool)
        if not isinstance(fields, list) or not 1 <= len(fields) <= MAX_HOOK_FIELDS \
                or not all(isinstance(f, str) and _HOOK_FIELD.match(f) for f in fields) \
                or len(set(fields)) != len(fields):
            out.add(where, "%r must map to one to %d different lowercase field names" % (tool, MAX_HOOK_FIELDS))


def _hook_render(hooks, out):
    """The three values the renderer writes into a hook: its event, its time limit in seconds and the exit
    code the harness takes as a block. They come together or not at all."""
    where = "layout.hooks"
    given = [key for key in HOOK_RENDER if key in hooks]
    if not given:
        return
    if len(given) != len(HOOK_RENDER):
        out.add(where, "event, timeout and block_code are given together")
        return
    if not (isinstance(hooks["event"], str) and _WORD.match(hooks["event"])):
        out.add(where, "event must be a plain word")
    for key, high in (("timeout", MAX_HOOK_TIMEOUT), ("block_code", 255)):
        value = hooks[key]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= high:
            out.add(where, "%s must be a whole number from 1 to %d" % (key, high))


ROOT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\.md")


def _root(root, out):
    if not out.keys(root, "layout.root", ("file", "import"), ("file", "import")):
        return []
    folded = out.path(root["file"], "layout.root.file", one_segment=True)
    out.path(root["import"], "layout.root.import", one_segment=True)
    for key in ("file", "import"):
        if isinstance(root[key], str) and not ROOT_NAME.fullmatch(root[key]):
            out.add("layout.root.%s" % key, "must be a plain Markdown file name (letters, digits, - and _, "
                    "ending .md), because the file is a line the tool reads, not a script")
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
        allowed = ("path", "fields") + (("tools", "hook", "scratch") if kind == "agent" else ())
        if not out.keys(kinds[kind], where, allowed, ("path", "fields")):
            continue
        entry = kinds[kind]
        directory = _kind_path(kind, entry["path"], where, out)
        if directory:
            written.append((where + ".path", directory[0], directory[1], True))
        _fields(kind, entry["fields"], where + ".fields", out)
        if "tools" in entry:
            _tools(entry["tools"], where + ".tools", out)
        if "hook" in entry or "scratch" in entry:
            _confinement(entry, where, out)
    return written


def _confinement(entry, where, out):
    """The agent's per-agent ``hook`` (the front-matter key that holds hooks, the event, the timeout in
    seconds and the exit code that blocks) and the ``scratch`` directory template. They come together,
    and the hook needs a tool table that grants ``edit`` and ``shell`` to match."""
    if "hook" not in entry or "scratch" not in entry:
        out.add(where, "hook and scratch are given together")
        return
    hook = entry["hook"]
    if out.keys(hook, where + ".hook", ("key", "event", "timeout", "block_code"),
                ("key", "event", "timeout", "block_code")):
        for key in ("key", "event"):
            if not (isinstance(hook[key], str) and _WORD.match(hook[key])):
                out.add(where + ".hook", "%s must be a plain word" % key)
        mapped = entry["fields"].values() if isinstance(entry.get("fields"), dict) else ()
        if hook["key"] == AGENT_TOOLS_FIELD or hook["key"] in mapped:
            out.add(where + ".hook", "key is a field the layout already maps")
        for key, high in (("timeout", MAX_HOOK_TIMEOUT), ("block_code", 255)):
            value = hook[key]
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= high:
                out.add(where + ".hook", "%s must be a whole number from 1 to %d" % (key, high))
    tools = entry.get("tools")
    if not isinstance(tools, dict) or "edit" not in tools or "shell" not in tools:
        out.add(where + ".hook", "needs a tools table that grants edit and shell, to know what to match")
    _scratch(entry["scratch"], where + ".scratch", out)


def _scratch(template, where, out):
    """An absolute path whose first segment is literal, with ``{session_id}`` once and ``{uid}`` and
    ``{cwd_key}`` at most once; every other character is a letter, digit, ``.``, ``_`` or ``-``."""
    if not isinstance(template, str) or not template.startswith("/") or len(template) > MAX_SCRATCH_CHARS:
        out.add(where, "must be an absolute path of at most %d characters" % MAX_SCRATCH_CHARS)
        return
    parts = template[1:].split("/")
    if len(parts) < 2 or any(part in ("", ".", "..") or not _SCRATCH_PART.match(part) for part in parts) \
            or "{" in parts[0]:
        out.add(where, "must be at least two plain segments (letters, digits, . _ - and the placeholders "
                       "{uid}, {cwd_key}, {session_id}), the first of them literal")
        return
    for name in SCRATCH_PLACEHOLDERS:
        count = template.count("{%s}" % name)
        if count > 1 or (name == "session_id" and count != 1):
            out.add(where, "{%s} must appear %s" % (name, "exactly once" if name == "session_id"
                                                    else "at most once"))


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
    if fields.get("tools", AGENT_TOOLS_FIELD) != AGENT_TOOLS_FIELD:
        out.add(where, "'tools' must map to the harness field %r" % AGENT_TOOLS_FIELD)
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
        elif key in TOOL_NAMES and any(n not in TOOL_NAMES[key] for n in names):
            out.add(where, "%r may only grant %s" % (key, ", ".join(TOOL_NAMES[key])))


def _settings(settings, out):
    where = "layout.local_settings"
    keys = ("path", "format", "actions", "rules", "absolute")
    if not out.keys(settings, where, keys, keys):
        return []
    folded = out.path(settings["path"], where + ".path")
    if folded and not _settings_path(settings["path"]):
        out.add(where + ".path", "must be <.directory>/<name>.json, directly inside a "
                                 "dot-directory other than .git and .workbench")
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
            if len(deny) != 2 or len(ask) != 2 or deny[0] != ask[0]:
                out.add(where + ".actions", "deny and ask must be <key>.deny and <key>.ask "
                                            "with the same <key>")
            if deny[0] not in SETTINGS_KEYS:
                out.add(where + ".actions", "the key must be one of %s" % ", ".join(SETTINGS_KEYS))
            if any(part.casefold() == "allow" for part in deny + ask):
                out.add(where + ".actions", "no key may be named allow")
    rules = settings["rules"]
    if out.keys(rules, where + ".rules", RULE_TOOLS, REQUIRED_RULE_TOOLS):
        for tool, template in rules.items():
            match = _TEMPLATE.match(template) if isinstance(template, str) else None
            wanted = "{path}" if tool in ("read", "write") else "{pattern}"
            if not match or match.group(2) != wanted:
                out.add(where + ".rules", "%s must be Name(%s)" % (tool, wanted))
            elif match.group(1) not in RULE_NAMES[tool] and match.group(1) not in INERT_TEMPLATE_NAMES:
                out.add(where + ".rules", "%s must use the rule name %s, not %s"
                        % (tool, " or ".join(RULE_NAMES[tool]), match.group(1)))
            elif match.group(1) in INERT_TEMPLATE_NAMES:
                out.add(where + ".rules", "%s uses %s, a rule name the harness accepts and never "
                                          "consults" % (tool, match.group(1)))
    if isinstance(rules, dict):
        names = [t.split("(")[0] for t in rules.values() if isinstance(t, str)]
        if len(set(names)) != len(names):
            out.add(where + ".rules", "two tool classes use the same rule name, so a deny meant "
                                      "for one would apply to the other")
        if any(name.casefold() == "allow" for name in names):
            out.add(where + ".rules", "a rule name may not be allow")
    if settings["absolute"] not in ABSOLUTE_PREFIXES:
        out.add(where + ".absolute", "must be one of %s" % ", ".join(ABSOLUTE_PREFIXES))
    return [(where + ".path", folded, tuple(settings["path"].split("/")), False)] if folded else []


def _settings_path(path):
    """True for exactly two segments: a dot-directory, then a `.json` name. (`out.path` has already
    refused `.`, .git, .workbench and the guarded store, so only the shape is checked here.)"""
    parts = path.split("/")
    if len(parts) != 2:
        return False
    directory, name = parts
    return (directory.startswith(".") and name.endswith(".json")
            and name[:-len(".json")].strip() != "")


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


def _tolerated(entries, written, out):
    where = "layout.tolerated"
    # A top-level name is spelled once: two spellings alias on a case-insensitive filesystem.
    spelled = {}
    for _, folded, raw, is_dir in written:
        if is_dir or len(raw) > 1:
            if spelled.setdefault(folded[0], raw[0]) != raw[0]:
                out.add("layout", "%r and %r name one directory, spelled two ways" %
                        (spelled[folded[0]], raw[0]))
    if not isinstance(entries, list) or len(entries) > MAX_TOLERATED:
        out.add(where, "must be a list of at most %d paths" % MAX_TOLERATED)
        return
    seen = set()
    for entry in entries:
        folded = out.path(entry, where)
        if folded is None:
            continue
        if folded in seen:
            out.add(where, "%r is listed twice" % entry)
        seen.add(folded)
        if any(folded == other for _, other, _, _ in written):
            out.add(where, "%r is written by this layout, so it is not tolerated" % entry)
        elif any(len(folded) < len(other) and _prefix(folded, other) for _, other, _, _ in written):
            out.add(where, "%r contains a path this layout writes" % entry)
        elif any(not is_dir and _prefix(other, folded) for _, other, _, is_dir in written):
            out.add(where, "%r is inside a file this layout writes" % entry)
        elif len(folded) < 2 or folded[0] not in spelled:
            out.add(where, "%r is not inside a directory this layout writes into" % entry)
        elif entry.split("/")[0] != spelled[folded[0]]:
            out.add(where, "%r is not spelled as the layout spells its directory, %r" %
                    (entry, spelled[folded[0]]))


def facts(layout):
    """What `wb check` needs from a layout that `problems` accepted, as a dict of tuples.

    ``roots``: the top-level names the harness occupies (the root file, the first segment of each kind
    directory and of the settings file). ``directories``: those that are directories. ``generated``: each
    kind's directory, which holds files the installer generates. ``tolerated``: the declared paths.
    ``hook_targets``: the pairs ``(tool, fields)`` of the hook's ``targets`` table, or empty.
    ``agent_gate``: ``(edit tool names, shell tool names, scratch template)`` of a layout that describes a per-agent
    hook, or empty.
    """
    roots, directories, generated = [], [], []
    root = layout.get("root", "none")
    if isinstance(root, dict):
        roots.append(root["file"])
    paths = []
    for kind in KINDS:
        entry = layout.get("kinds", {}).get(kind)
        if entry:
            tail = "/{name}/SKILL.md" if kind == "skill" else "/{name}.md"
            generated.append(entry["path"][:-len(tail)])
            paths.append(generated[-1])
    settings = layout.get("local_settings", "none")
    if isinstance(settings, dict):
        paths.append(settings["path"])
    for path in paths:
        first, _, rest = path.partition("/")
        roots.append(first)
        if rest or path in generated:
            directories.append(first)
    unique = lambda items: tuple(dict.fromkeys(items))
    hooks = layout.get("hooks", "none")
    targets = hooks.get("targets", {}) if isinstance(hooks, dict) else {}
    agent = layout.get("kinds", {}).get("agent", {})
    confining = "hook" in agent and "scratch" in agent
    return {"roots": unique(roots), "directories": unique(directories),
            "generated": unique(generated), "tolerated": tuple(layout.get("tolerated", [])),
            "hook_targets": tuple((tool, tuple(fields)) for tool, fields in targets.items()),
            "agent_gate": (tuple(agent["tools"]["edit"]), tuple(agent["tools"]["shell"]), agent["scratch"])
            if confining else ()}


def _overlaps(written, out):
    for index, (where, folded, _, _) in enumerate(written):
        for other_where, other, _, _ in written[index + 1:]:
            if _prefix(folded, other) or _prefix(other, folded):
                out.add(where, "overlaps %s" % other_where)
