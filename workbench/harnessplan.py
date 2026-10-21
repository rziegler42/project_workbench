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
the owner-run commands of ``rules``.

An override replaces the translation of one item, by kind and name, with files the module author
wrote in the harness's own format. Apart from an agent, which must still name a tools allowlist
(``_unrestricted``), they are not inspected: the owner approves them with the module, and every
override is reported.
"""

import collections
import hashlib
import json
import re

from . import declarations, floor, layout, neutral, safefs
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
Result = collections.namedtuple("Result", "files reports")


class PlanError(ValueError):
    """The input cannot be translated at all; nothing is planned."""


def quote(value):
    """Return ``value`` as a double-quoted string that YAML and JSON read back unchanged."""
    return json.dumps(value)


def _item_id(kind, name):
    return "%s/%s" % (kind, name)


def translate(items, harness_layout, overrides, excludes, provides=declarations.HARNESS_CAPABILITIES):
    """Plan the files for ``items``.

    ``overrides`` maps ``(kind, name)`` to ``{relative path: bytes}``: for a skill the files below
    its directory (``SKILL.md`` is required), for an agent or a command the one ``<name>.md``.
    ``excludes`` maps ``(kind, name)`` to the reason it is not installed. ``provides`` is the
    set of capabilities the harness module declares. Raises ``PlanError``.
    """
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
        if key in overrides:
            made = _override(item, spec, overrides[key])
            problem = _unrestricted(spec, made[0][1]) if item.kind == "agent" else None
            if problem:
                reports.append(Report("skipped", ident, problem))
                continue
            reports.append(Report("overridden", ident,
                                  "replaced by the module's own files for this harness"))
        else:
            made = _render(item, spec, reports)
            if made is None:
                continue
        files.extend(Planned(path, data, FILE_MODE, hashlib.sha256(data).hexdigest(), ident)
                     for path, data in made)
    _no_collision(files)
    files.sort()
    reports.sort()
    return Result(tuple(files), tuple(reports))


def _unavailable(item, kinds, provides):
    if CAPABILITY[item.kind] not in provides:
        return "this harness does not provide %s" % CAPABILITY[item.kind]
    if item.kind not in kinds:
        return "this harness has no %s" % item.kind
    lacking = [need for need in item.needs if need not in provides]
    if lacking:
        return "needs %s, which this harness does not provide" % ", ".join(lacking)
    return None


def _directory(kind, spec, name):
    tail = "/{name}/SKILL.md" if kind == "skill" else "/{name}.md"
    return spec["path"][:-len(tail)]


def _item_path(item, spec):
    return spec["path"].replace("{name}", item.name)


def _render(item, spec, reports):
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
    head = "---\n" + "".join(line + "\n" for line in lines) + "---\n"
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


def render_permissions(rules, harness_layout, store_root, home):
    """Return the bytes of the local settings file for ``rules`` plus what is always rendered.

    Always rendered: a deny for writes to the guarded store at ``store_root``, a deny for every
    owner-run command in each spelling, and the ask rules of every hard stop of the floor. ``rules``
    are the module's own ``neutral.Rule`` tuples. Nothing here can produce an ``allow``: the
    layout validator ties the two output keys to ``deny`` and ``ask``, and only those are built.
    ``home`` and ``store_root`` are absolute paths; the output has no clock and no ordering
    that depends on the input.
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
    for pattern in rules_module.owner_run_patterns():
        wanted["deny"].add(render("shell", pattern))
    floor_ids = {stop.id for stop in floor.FLOOR}
    for stop_id in sorted(floor_ids):
        for action, tool, pattern in rules_module.FLOOR_RULES[stop_id]:
            wanted[action].add(render(tool, pattern))
    for rule in rules:
        wanted[rule.action].add(render(rule.tool, rule.pattern))
    wanted["ask"] -= wanted["deny"]
    document = {}
    for action in ("deny", "ask"):
        node = document
        *parents, last = settings["actions"][action].split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[last] = sorted(wanted[action])
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
