"""Turn neutral harness items into the exact files a harness receives.

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

An override replaces the translation of one item, by kind and name, with files the module author
wrote in the harness's own format. Apart from an agent, which must still name a tools allowlist
(``_unrestricted``), they are not inspected: the owner approves them with the module, and every
override is reported.
"""

import collections
import hashlib
import json

from . import declarations, layout, neutral, safefs

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
    lines = data.decode("utf-8", "replace").split("\n")
    if not lines or lines[0] != "---":
        return "the agent override has no front matter, so it names no tools; not installed"
    prefix = spec["fields"]["tools"] + ":"
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith(prefix) and line[len(prefix):].strip(" \"'"):
            return None
    return "the agent override names no tools, which would give it every tool; not installed"


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
