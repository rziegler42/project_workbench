"""Turn neutral harness items into the exact files a harness receives, and render its permissions.

``translate`` is a pure function: it reads nothing and writes nothing. Its input is the items of
``neutral.read_items``, a layout that ``layout.problems`` accepts, the hand-written overrides of
``harness/<name>/`` and the exclusions of its manifest. Its output is the files to write, with
their bytes, mode and hash, and a list of reports for the owner.

It fails closed. An agent is only installed with an explicit allowlist the layout can express;
a harness that omits ``tools`` from an agent gives it every tool, so an agent that cannot be
restricted is skipped and never written, and so is one none of whose tools the layout can grant.
Dropping a field, or one tool from an allowlist, only loses convenience and is reported.

Every front-matter value is written as a double-quoted string, so a name such as ``null`` or a
description such as ``a: b`` stays the text the author wrote. A neutral value is printable ASCII
(``neutral``), which a JSON string quotes into the same text as a YAML double-quoted one.

``render_permissions`` (below) builds the local settings file from the neutral rules, the floor and
the owner-run commands of ``rules``, and, when asked, the one hook the installer renders, the edit gate's
(``render_hook``), and a deny for the files that carry another hook, the one a confined agent's own file holds
(``_agent_hook``).

An override replaces the translation of one item, by kind and name, with files the module author
wrote in the harness's own format. Apart from an agent, which must still name a tools allowlist
(``_unrestricted``), they are not inspected: the owner approves them with the module, and every
override is reported. A confined agent takes no override, because the file that carries its hook is the
one an override would replace.
"""

import collections
import hashlib
import json
import re

from . import declarations, floor, layout, neutral
from .wbkit import safefs
from . import rules as rules_module

_PLAIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._,()/=+-]*\Z")
_TOOL_LIST = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(, ?[A-Za-z][A-Za-z0-9_]*)*\Z")
_YAML_WORDS = ("null", "true", "false", "yes", "no", "on", "off", "y", "n", "nan", "inf")
_FRONT_LINE = re.compile(r"^([a-z][a-z-]*): (\S.*)\Z")
FILE_MODE = 0o644
CAPABILITY = {"skill": "skills", "agent": "agents", "command": "commands"}
FIELD_ORDER = {"skill": ("name", "description"),
               "command": ("name", "description", "args"),
               "agent": ("name", "description", "tools", "model")}

Planned = collections.namedtuple("Planned", "path data mode sha256 source")
Report = collections.namedtuple("Report", "level item message")
# `confined` are the paths of the agent files that carry a hook, which the deny of `render_permissions` protects.
Result = collections.namedtuple("Result", "files reports confined")


class PlanError(ValueError):
    """The input cannot be translated at all; nothing is planned."""


def quote(value):
    """Return ``value`` as a double-quoted string that YAML and JSON read back unchanged."""
    return json.dumps(value)


def _item_id(kind, name):
    return "%s/%s" % (kind, name)


def translate(items, harness_layout, overrides, excludes, provides=declarations.HARNESS_CAPABILITIES,
              harness_name=None):
    """Plan the files for ``items``.

    ``overrides`` maps ``(kind, name)`` to ``{relative path: bytes}``: for a skill the files below
    its directory (``SKILL.md`` is required), for an agent or a command the one ``<name>.md``.
    ``excludes`` maps ``(kind, name)`` to the reason it is not installed. ``provides`` is the
    set of capabilities the harness module declares. A hook has no neutral form, so an item that
    needs hooks is skipped even when the harness provides the installer's own hook. A confined agent
    (``writes`` or ``run``) is rendered with the hook that runs the agent gate, which names
    `harness_name`; without a name the command can take, it is skipped. Raises ``PlanError``.
    """
    provides = tuple(name for name in provides if name != "hooks")
    found = layout.problems(harness_layout)
    if found:
        raise PlanError("the layout is refused: " + "; ".join(found))
    items = list(items)
    for key, reason in excludes.items():
        if not isinstance(reason, str):
            raise PlanError("%s: the reason for an exclusion must be text" % _item_id(*key))
    known = {(item.kind, item.name): item for item in items}
    if len(known) != len(items):
        raise PlanError("two items have the same kind and name")
    for key in sorted(excludes):
        if key not in known:
            raise PlanError("%s: excluded, but the module has no such neutral item"
                            % _item_id(*key))
    for key in sorted(overrides):
        if key not in known:
            raise PlanError("%s: has an override, but the module has no such neutral item"
                            % _item_id(*key))
        if key in excludes:
            raise PlanError("%s is both overridden and excluded" % _item_id(*key))
    kinds = harness_layout.get("kinds", {})
    files = []
    reports = []
    confined = []
    for key in sorted(known):
        item = known[key]
        ident = _item_id(*key)
        if key in excludes:
            reports.append(Report("excluded", ident, excludes[key]))
            continue
        reason = _unavailable(item, kinds, provides)
        if reason:
            reports.append(Report("skipped", ident, reason))
            continue
        spec = kinds[item.kind]
        hook = None
        if _confined(item):
            reason = _confinable(item, harness_name, key in overrides)
            if reason:
                reports.append(Report("skipped", ident, reason))
                continue
            hook = _agent_hook(spec, harness_name, item.name)
        if key in overrides:
            made = _override(item, spec, overrides[key])
            problem = _unrestricted(spec, made[0][1]) if item.kind == "agent" else None
            if problem:
                reports.append(Report("skipped", ident, problem))
                continue
            reports.append(Report("overridden", ident,
                                  "replaced by the module's own files for this harness"))
        else:
            made = _render(item, spec, reports, hook)
            if made is None:
                continue
        if hook:
            confined.append(made[0][0])
        files.extend(Planned(path, data, FILE_MODE, hashlib.sha256(data).hexdigest(), ident)
                     for path, data in made)
    _no_collision(files)
    files.sort()
    reports.sort()
    return Result(tuple(files), tuple(reports), tuple(sorted(confined)))


def render_root(harness_layout):
    """The root file of the layout as a ``Planned``, or None when it has none.

    It holds the one import line of the layout and nothing else: guidance generated into a root
    file waits for a module that supplies it.
    """
    found = layout.problems(harness_layout)
    if found:
        raise PlanError("the layout is refused: " + "; ".join(found))
    root = harness_layout.get("root", "none")
    if root == "none":
        return None
    data = ("@%s\n" % root["import"]).encode("utf-8")
    return Planned(root["file"], data, FILE_MODE, hashlib.sha256(data).hexdigest(), "root")


def _unavailable(item, kinds, provides):
    if CAPABILITY[item.kind] not in provides:
        return "this harness does not provide %s" % CAPABILITY[item.kind]
    if item.kind not in kinds:
        return "this harness has no %s" % item.kind
    if item.kind == "agent" and (item.writes or item.run):
        # Fail closed, as for an agent whose tools cannot be restricted: a limit nothing enforces is no limit.
        if "hook" not in kinds["agent"] or "scratch" not in kinds["agent"]:
            return ("it declares limits on what it writes and runs, and this harness has no per-agent hook "
                    "and scratch directory to enforce them, so it is not installed")
        if "permissions" not in provides:
            return ("it declares limits on what it writes and runs, and this harness provides no permissions, "
                    "so the file that carries the hook that enforces them could not be protected from an edit, "
                    "so it is not installed")
    lacking = [need for need in item.needs if need not in provides]
    if lacking:
        return "needs %s, which this harness does not provide" % ", ".join(lacking)
    return None


def _confined(item):
    return item.kind == "agent" and bool(item.writes or item.run)


def _confinable(item, harness_name, overridden):
    """Why a confined agent cannot be given its hook, or None. Both names go into a command, so each must be one
    the gate command takes (``_HARNESS_NAME``); and the file that carries the hook is not the module's to replace."""
    if not (isinstance(harness_name, str) and _HARNESS_NAME.match(harness_name)):
        return ("it declares limits on what it writes and runs, and the harness name %r is not one the agent gate "
                "command takes, so it is not installed" % (harness_name,))
    if not _HARNESS_NAME.match(item.name):
        return ("it declares limits on what it writes and runs, and the agent name %r is not one the agent gate "
                "command takes, so it is not installed" % item.name)
    if overridden:
        return ("it declares limits on what it writes and runs, and the module also gives its own file for this "
                "harness, which would replace the file that carries the hook that enforces them, so it is not "
                "installed")
    return None


def _agent_hook(spec, harness_name, agent_name):
    """The lines of the front matter that hold a confined agent's hook, in the layout's key, event, time limit and
    block code. The matcher is every tool name the layout gives ``edit`` and ``shell``, the same table the agent's
    ``tools`` line is built from, so a tool the agent is granted for either is a tool the hook sees. The command is
    ``wb agent-gate <harness> <agent> || exit <code>``: the ``|| exit`` turns a missing program or any other failure
    into the code the harness takes as a block."""
    hook, table = spec["hook"], spec["tools"]
    matcher = "|".join(sorted(set(table["edit"]) | set(table["shell"])))
    command = "wb agent-gate %s %s || exit %d" % (harness_name, agent_name, hook["block_code"])
    return ["%s:" % hook["key"],
            "  %s:" % hook["event"],
            "    - matcher: %s" % quote(matcher),
            "      hooks:",
            "        - type: command",
            "          command: %s" % quote(command),
            "          timeout: %d" % hook["timeout"]]


def _directory(kind, spec, name):
    tail = "/{name}/SKILL.md" if kind == "skill" else "/{name}.md"
    return spec["path"][:-len(tail)]


def _item_path(item, spec):
    return spec["path"].replace("{name}", item.name)


def _render(item, spec, reports, hook=None):
    ident = _item_id(item.kind, item.name)
    fields = spec["fields"]
    values = {"name": item.name, "description": item.description, "args": item.args,
              "model": item.model}
    lines = []
    dropped = []
    for field in FIELD_ORDER[item.kind]:
        if field == "tools":
            tools = _agent_tools(item, spec, reports)
            if tools is None:
                return None
            lines.append("%s: %s" % (fields["tools"], quote(tools)))
            continue
        if not values[field]:
            continue
        if field not in fields:
            dropped.append(field)
            continue
        lines.append("%s: %s" % (fields[field], quote(values[field])))
    if dropped:
        reports.append(Report("warning", ident, "the harness has no field for %s; dropped"
                              % ", ".join(dropped)))
    head = "---\n" + "".join(line + "\n" for line in lines + (hook or [])) + "---\n"
    made = [(_item_path(item, spec), (head + item.body).encode("utf-8"))]
    base = _directory(item.kind, spec, item.name) + "/" + item.name
    made.extend((base + "/" + bundled.rel, bundled.data) for bundled in item.files)
    return made


def _agent_tools(item, spec, reports):
    ident = _item_id(item.kind, item.name)
    table = spec.get("tools")
    if "tools" not in spec["fields"] or not table:
        reports.append(Report("skipped", ident, "this harness cannot restrict an agent's tools, "
                                                "so the agent cannot be restricted and is not "
                                                "installed"))
        return None
    granted = set()
    missing = []
    for tool in item.tools:
        if tool in table:
            granted.update(table[tool])
        else:
            missing.append(tool)
    if not granted:
        reports.append(Report("skipped", ident, "none of its tools (%s) can be granted by this "
                                                "harness, so it is not installed"
                              % ", ".join(item.tools)))
        return None
    if missing:
        reports.append(Report("warning", ident, "this harness cannot grant %s; the agent gets "
                                                "less than it asked for" % ", ".join(missing)))
    return ", ".join(sorted(granted))


def _override(item, spec, given):
    ident = _item_id(item.kind, item.name)
    if not isinstance(given, dict) or not given:
        raise PlanError("%s: the override has no files" % ident)
    for rel, data in given.items():
        if not isinstance(rel, str) or not isinstance(data, bytes):
            raise PlanError("%s: an override is {path: bytes}" % ident)
    try:
        safefs.check_tree_paths(sorted(given))
    except safefs.SafeFsError as exc:
        raise PlanError("%s: override: %s" % (ident, exc))
    if sum(len(data) for data in given.values()) > neutral.MAX_TOTAL_BYTES \
            or any(len(data) > neutral.MAX_FILE_BYTES for data in given.values()):
        raise PlanError("%s: the override is too large" % ident)
    if len(given) > neutral.MAX_BUNDLED + 1:
        raise PlanError("%s: the override has too many files" % ident)
    if item.kind == "skill":
        if "SKILL.md" not in given:
            raise PlanError("%s: the override has no SKILL.md" % ident)
        base = _directory("skill", spec, item.name) + "/" + item.name
        return [(base + "/" + rel, data) for rel, data in sorted(given.items())]
    if sorted(given) != [item.name + ".md"]:
        raise PlanError("%s: the override must be the one file %s.md" % (ident, item.name))
    return [(_item_path(item, spec), given[item.name + ".md"])]


def _unrestricted(spec, data):
    """Return why an agent override is refused, or None when it names a tools allowlist.

    The harness gives an agent every tool when the field is missing, so an override is held to
    the same rule as a translated agent: the layout must be able to restrict, and the file's
    front matter must carry a non-empty tools line.
    """
    if "tools" not in spec["fields"] or not spec.get("tools"):
        return ("this harness cannot restrict an agent's tools, so the agent cannot be "
                "restricted and its override is not installed")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "the agent override is not UTF-8; not installed"
    if "\r" in text:
        return "the agent override has a carriage return; not installed"
    lines = text.split("\n")
    if lines[0] != "---" or "---" not in lines[1:]:
        return "the agent override has no complete front matter, so it names no tools; not installed"
    key = spec["fields"]["tools"]
    allowed = {name for names in spec["tools"].values() for name in names}
    mapped = set(spec["fields"].values())
    found = []
    seen = set()
    for line in lines[1:lines.index("---", 1)]:
        if not all(" " <= c <= "~" for c in line):
            return ("the agent override's front matter has a character other than printable "
                    "ASCII, which a YAML reader may take as a line break; not installed")
        match = _FRONT_LINE.match(line)
        if not match:
            return ("the agent override has a front-matter line that is not a plain "
                    "'key: value'; not installed")
        name, value = match.groups()
        if name in seen:
            return "the agent override gives %r twice; not installed" % name
        seen.add(name)
        if name not in mapped:
            return ("the agent override sets %r, which this harness's layout does not map; "
                    "not installed" % name)
        value = _scalar(value)
        if value is None:
            return ("the agent override has a value that is not a plain or a double-quoted "
                    "single-line string; not installed")
        if name == key:
            found.append(value)
    if len(found) != 1:
        return "the agent override must name its tools exactly once; not installed"
    if not _TOOL_LIST.match(found[0]) or not all(
            part in allowed for part in re.split(r", ?", found[0])):
        return ("the agent override lists tools this harness's layout does not define, "
                "so it is not installed")
    return None


def _scalar(value):
    """The text of a front-matter value that is one self-contained string, or None.

    Two shapes only: a complete double-quoted string (what ``quote`` writes), or a plain scalar
    of letters, digits and a few marks that YAML reads as text and not as a number, a boolean or
    null. Anything else could be read across lines or as another type.
    """
    if value.startswith('"'):
        try:
            text = json.loads(value)
        except ValueError:
            return None
        return text if isinstance(text, str) and "---" not in text else None
    if not _PLAIN.match(value) or "---" in value or value.casefold() in _YAML_WORDS:
        return None
    for convert in (int, float):
        try:
            convert(value.replace("_", "x"))
            return None
        except ValueError:
            pass
    try:
        int(value, 0)
        return None
    except ValueError:
        return value


def _no_collision(files):
    seen = {}
    for planned in files:
        if planned.path in seen:
            raise PlanError("%s and %s map to the same path %s"
                            % (seen[planned.path], planned.source, planned.path))
        seen[planned.path] = planned.source
    try:
        safefs.check_tree_paths(sorted(seen))
    except safefs.SafeFsError as exc:
        raise PlanError(str(exc))


# --- permission rendering ----------------------------------------------------

_PATH_CHARS = set(neutral.PATTERN_CHARS) - {"*"}


def _absolute(prefix, path, home):
    """Spell the absolute `path` as the layout's `prefix` requires, or raise PlanError."""
    if not path.startswith("/") or any(c not in neutral.PATTERN_CHARS for c in path):
        raise PlanError("cannot write the path %r as a permission rule" % path)
    if prefix == "~/":
        base = home.rstrip("/") + "/"
        if not path.startswith(base):
            raise PlanError("%s is outside the home directory, which this harness cannot "
                            "write as a rule" % path)
        return "~/" + path[len(base):]
    return "//" + path.lstrip("/")


def _path_pattern(prefix, pattern, home):
    """A neutral path pattern: `~/x` is under home, `/x` is absolute, anything else is kept."""
    if pattern.startswith("~") and not pattern.startswith("~/"):
        raise PlanError("%r: only '~/...' names the home directory" % pattern)
    if pattern.startswith("~/"):
        return _absolute(prefix, home.rstrip("/") + "/" + pattern[2:], home)
    if pattern.startswith("/"):
        return _absolute(prefix, pattern, home)
    return pattern


_HARNESS_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
# The file git reads the clone's own ignore lines from, which the edit gate's hook is protected along with.
GIT_EXCLUDE = ".git/info/exclude"


def hook_described(harness_layout):
    """Whether the layout carries the whole description of the one hook the installer renders."""
    hooks = harness_layout.get("hooks", "none")
    return isinstance(hooks, dict) and all(key in hooks for key in ("targets",) + layout.HOOK_RENDER)


def render_hook(harness_layout, harness_name):
    """``(settings key, value)`` of the edit gate's hook for the harness named `harness_name`.

    The event, the tools whose calls it covers, the time limit and the exit code that blocks all come from the
    layout; the command is ``wb gate <harness> || exit <code>``. The ``|| exit`` turns a missing program or any
    other failure of the gate into the code the harness takes as a block. Raises ``PlanError``."""
    found = layout.problems(harness_layout)
    if found:
        raise PlanError("the layout is refused: " + "; ".join(found))
    if not hook_described(harness_layout):
        raise PlanError("this layout does not describe a hook (it needs targets, event, timeout and block_code)")
    if not isinstance(harness_name, str) or not _HARNESS_NAME.match(harness_name):
        raise PlanError("the harness name %r is not one the gate command takes" % (harness_name,))
    hooks = harness_layout["hooks"]
    command = "wb gate %s || exit %d" % (harness_name, hooks["block_code"])
    entry = {"matcher": "|".join(sorted(hooks["targets"])),
             "hooks": [{"type": "command", "command": command, "timeout": hooks["timeout"]}]}
    return hooks["settings_key"], {hooks["event"]: [entry]}


def _spelled(paths, root):
    """The patterns of the files at `paths`, relative to the project: from the directory the harness starts in, from
    any directory below it, and by the absolute path in the project at `root`."""
    return ([spelled + path for path in paths for spelled in ("", "**/")]
            + [root.rstrip("/") + "/" + path for path in paths])


def _protected(settings, root):
    """The patterns of the files the hook is kept in: the settings file and git's exclude file, spelled from the
    directory the harness starts in, from any directory below it, and by their absolute path in the project at
    `root`. A relative pattern is matched from where the session started, so only the absolute one holds when the
    session starts below the root. The agent may not write them; the owner edits them by hand. This is the one rule
    beyond the hook itself, and it is rendered here and nowhere else."""
    return _spelled((settings["path"], GIT_EXCLUDE), root)


def _plain_relative(path):
    """`path` when it names a file below the project in a way a permission rule can spell, or raise PlanError."""
    if not isinstance(path, str) or not path or path.startswith(("/", "~")) \
            or any(part in ("", ".", "..") for part in path.split("/")) or any(c not in _PATH_CHARS for c in path):
        raise PlanError("cannot protect %r: it is not a plain path below the project that a permission rule can "
                        "name" % (path,))
    return path


def _plain_root(root):
    """`root` when it is an absolute path that can be written as a permission rule, or raise PlanError."""
    if not isinstance(root, str) or not root.startswith("/") or root.rstrip("/") == "" \
            or any(part in ("", ".", "..") for part in root.rstrip("/").split("/")[1:]):
        raise PlanError("the project directory %r is not a plain absolute path" % (root,))
    if any(c not in _PATH_CHARS for c in root):
        raise PlanError("cannot write the path %r as a permission rule" % root)
    return root


def render_permissions(rules, harness_layout, store_root, home, hook_for=None, root=None, protect=(),
                       ask_patterns=(), open_patterns=()):
    """Return the bytes of the local settings file for ``rules`` plus what is always rendered.

    Always rendered: a deny for writes to the guarded store at ``store_root``, a deny for every
    owner-run command in each spelling, and the ask rules of every hard stop of the floor. ``rules``
    are the module's own ``neutral.Rule`` tuples. Nothing here can produce an ``allow``: the
    layout validator ties the two output keys to ``deny`` and ``ask``, and only those are built.
    ``home`` and ``store_root`` are absolute paths; the output has no clock and no ordering
    that depends on the input.

    ``hook_for`` is the name of the harness to render the edit gate's hook for, or None for no hook. A hook
    comes with a deny for the files it is kept in (``_protected``), which names them by their path in the project
    at `root`, an absolute real path; a hook cannot be rendered without it.

    ``protect`` are paths below the project, of files that carry a hook of their own (a confined agent's); each
    gets the same deny in the same three spellings, with or without the edit gate's hook, and needs `root` too.

    ``ask_patterns`` and ``open_patterns`` are shell patterns of owner-run commands whose level is not ``block``
    (``rendering.py``): an open pattern is not denied, and an ask pattern is asked instead, also through the guarded
    store's own ``bin/wb`` (a path-qualified spelling no other pattern names). Nothing here builds an ``allow``.
    """
    found = layout.problems(harness_layout)
    if found:
        raise PlanError("the layout is refused: " + "; ".join(found))
    settings = harness_layout.get("local_settings", "none")
    if settings == "none":
        raise PlanError("this layout has no local settings to render permissions into")
    for rule in rules:
        if not isinstance(rule, neutral.Rule) or rule.action not in neutral.RULE_ACTIONS \
                or rule.tool not in neutral.RULE_TOOLS:
            raise PlanError("not a neutral rule: %r" % (rule,))
        try:
            neutral.read_rules([{"action": rule.action, "tool": rule.tool,
                                 "pattern": rule.pattern}])
        except neutral.NeutralError as exc:
            raise PlanError(str(exc))
    if not (isinstance(home, str) and isinstance(store_root, str) and home.startswith("/")
            and store_root.startswith("/")):
        raise PlanError("the home directory and the guarded store must be absolute paths")
    for base in (home, store_root):
        if (any(c not in _PATH_CHARS for c in base) or base.rstrip("/") == ""
                or any(part in ("", ".", "..") for part in base.rstrip("/").split("/")[1:])):
            raise PlanError("cannot write the path %r as a permission rule" % base)
    templates, prefix = settings["rules"], settings["absolute"]

    def render(tool, pattern):
        if tool not in templates:
            raise PlanError("this layout has no rule template for %s, which a rule needs" % tool)
        slot = "{path}" if tool in ("read", "write") else "{pattern}"
        value = _path_pattern(prefix, pattern, home) if slot == "{path}" else pattern
        return templates[tool].replace(slot, value)

    wanted = {"deny": set(), "ask": set()}
    store = store_root.rstrip("/")
    for pattern in (store, store + "/**"):
        wanted["deny"].add(render("write", pattern))
    opened = set(open_patterns)
    for pattern in rules_module.owner_run_patterns():
        if pattern not in opened:
            wanted["deny"].add(render("shell", pattern))
    for pattern in ask_patterns:
        wanted["ask"].add(render("shell", pattern))
        if pattern.startswith("wb "):
            wanted["ask"].add(render("shell", store + "/bin/wb" + pattern[2:]))
    floor_ids = {stop.id for stop in floor.FLOOR}
    for stop_id in sorted(floor_ids):
        for action, tool, pattern in rules_module.FLOOR_RULES[stop_id]:
            wanted[action].add(render(tool, pattern))
    for rule in rules:
        if rule.action == "deny" and rule.tool == "shell" and rule.pattern in opened:
            continue
        wanted[rule.action].add(render(rule.tool, rule.pattern))
    hook = render_hook(harness_layout, hook_for) if hook_for is not None else None
    if hook:
        if root is None:
            raise PlanError("the project directory is needed to render the edit gate's hook")
        wanted["deny"].update(render("write", pattern) for pattern in _protected(settings, _plain_root(root)))
    if protect:
        if root is None:
            raise PlanError("the project directory is needed to protect the files that carry a hook")
        paths = sorted({_plain_relative(path) for path in protect})
        wanted["deny"].update(render("write", pattern) for pattern in _spelled(paths, _plain_root(root)))
    wanted["ask"] -= wanted["deny"]
    document = {}
    for action in ("deny", "ask"):
        node = document
        *parents, last = settings["actions"][action].split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[last] = sorted(wanted[action])
    if hook:
        document[hook[0]] = hook[1]
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
