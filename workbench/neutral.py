"""Read a module's neutral harness items and a neutral rule list, strictly.

The input is a module tree already read through ``safefs`` (``{relative path: bytes}``,
paths relative to ``harness/neutral/``), so no link or special file can reach this code.
Nothing here touches the filesystem, and nothing is translated: ``harnessplan`` does that.

Layout below ``harness/neutral/``:

* ``skills/<name>/SKILL.md``, with bundled files anywhere below ``skills/<name>/``;
* ``agents/<name>.md``;
* ``commands/<name>.md``.

Any other path is refused, so a file cannot sit where a later step would not look at it.
A skill and a command may not share a name, because Claude serves both as ``/<name>``.

Front matter is a fence line ``---``, single-line ``key: value`` lines and a closing ``---``.
A value is read literally: no quoting, no continuation lines, no block indicator. It is
printable ASCII text with no edge space, so a lookalike letter cannot pass. The translation step quotes it for the harness.

Rules are restrictive only: ``ask`` or ``deny`` for a tool class and a pattern. An ``allow``
is refused. The pattern grammar is applied by the layout that renders it.
"""

import collections
import hashlib

from . import declarations
from .wbkit import safefs

KINDS = {"skills": "skill", "agents": "agent", "commands": "command"}
TOOLS = ("read", "search", "edit", "shell", "web", "agents")
NEEDS = declarations.HARNESS_CAPABILITIES
RULE_ACTIONS = ("ask", "deny")
RULE_TOOLS = ("shell", "read", "write", "web")

MAX_ITEMS = 200
MAX_NAME_CHARS = 64
MAX_DESCRIPTION_CHARS = 300
MAX_ARGS_CHARS = 100
MAX_MODEL_CHARS = 64
MAX_ITEM_BYTES = 256 * 1024
MAX_FILE_BYTES = 1024 * 1024
MAX_BUNDLED = 100
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_RULES = 200
MAX_PATTERN_CHARS = 200
# A rule pattern is words, paths and the globs ``*`` and ``**``. No bracket, quote, colon or
# backslash can reach a harness's own rule syntax. The layout that renders a pattern checks it
# again against its target syntax; this only keeps the neutral form small.
PATTERN_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _./*~@=+-"

FIELDS = {
    "skill": (("name", "description"), ("needs",)),
    "command": (("name", "description"), ("args", "needs")),
    "agent": (("name", "description", "tools"), ("model", "needs")),
}

Bundled = collections.namedtuple("Bundled", "rel data sha256")
Item = collections.namedtuple(
    "Item", "kind name description args tools needs model body files")
Rule = collections.namedtuple("Rule", "action tool pattern")


class NeutralError(ValueError):
    """A neutral item or rule is refused; the message names the path or rule."""


def _name_ok(name):
    return len(name) <= MAX_NAME_CHARS and declarations.NAME_RE.match(name) is not None


def read_items(files):
    """Return the items of a neutral tree, sorted by kind then name, or raise ``NeutralError``."""
    if not isinstance(files, dict):
        raise NeutralError("the neutral tree is not a mapping of paths to bytes")
    try:
        safefs.check_tree_paths(files)
    except safefs.SafeFsError as exc:
        raise NeutralError(str(exc))
    total = 0
    sources = {}
    bundled = collections.defaultdict(list)
    for rel in sorted(files):
        data = files[rel]
        if not isinstance(data, bytes):
            raise NeutralError("%s: content is not bytes" % rel)
        total += len(data)
        parts = rel.split("/")
        kind = KINDS.get(parts[0])
        if kind is None:
            raise NeutralError("%s: not under skills/, agents/ or commands/" % rel)
        if kind == "skill":
            if len(parts) < 3 or not _name_ok(parts[1]):
                raise NeutralError("%s: a skill is skills/<name>/SKILL.md with a valid name" % rel)
            if parts[2:] == ["SKILL.md"]:
                sources[(kind, parts[1])] = rel
            else:
                if len(data) > MAX_FILE_BYTES:
                    raise NeutralError("%s: too large (over %d bytes)" % (rel, MAX_FILE_BYTES))
                bundled[parts[1]].append((rel, "/".join(parts[2:]), data))
            continue
        if len(parts) != 2 or not parts[1].endswith(".md") or not _name_ok(parts[1][:-3]):
            raise NeutralError("%s: expected %s/<name>.md with a valid name" % (rel, parts[0]))
        sources[(kind, parts[1][:-3])] = rel
    if total > MAX_TOTAL_BYTES:
        raise NeutralError("the neutral tree is too large: total over %d bytes" % MAX_TOTAL_BYTES)
    if len(sources) > MAX_ITEMS:
        raise NeutralError("too many items (%d, limit %d)" % (len(sources), MAX_ITEMS))
    for name in sorted(bundled):
        if ("skill", name) not in sources:
            raise NeutralError("skills/%s has no SKILL.md" % name)
        if len(bundled[name]) > MAX_BUNDLED:
            raise NeutralError("skills/%s: too many bundled files (limit %d)" % (name, MAX_BUNDLED))
    names = {}
    for kind, name in sorted(sources):
        other = names.setdefault(name, kind)
        if other != kind and {other, kind} == {"skill", "command"}:
            raise NeutralError("%s is both a skill and a command; both would be /%s"
                               % (name, name))
    items = []
    for (kind, name), rel in sorted(sources.items()):
        items.append(_item(kind, name, rel, files[rel],
                           sorted(bundled.get(name, ())) if kind == "skill" else []))
    return items


def _item(kind, name, rel, data, extra):
    if len(data) > MAX_ITEM_BYTES:
        raise NeutralError("%s: too large (over %d bytes)" % (rel, MAX_ITEM_BYTES))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise NeutralError("%s: not valid UTF-8" % rel)
    if "\r" in text:
        raise NeutralError("%s: contains a carriage return; use plain newlines" % rel)
    head, body = _split(text, rel)
    values = _front_matter(head, rel)
    required, optional = FIELDS[kind]
    for key in values:
        if key not in required + optional:
            raise NeutralError("%s: %s does not take the field %r" % (rel, kind, key))
    for key in required:
        if key not in values:
            raise NeutralError("%s: missing the field %r" % (rel, key))
    if values["name"] != name:
        raise NeutralError("%s: the field 'name' (%s) must equal the path name (%s)"
                           % (rel, values["name"], name))
    description = values["description"]
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise NeutralError("%s: description is over %d characters" % (rel, MAX_DESCRIPTION_CHARS))
    args = values.get("args", "")
    if len(args) > MAX_ARGS_CHARS:
        raise NeutralError("%s: args is over %d characters" % (rel, MAX_ARGS_CHARS))
    model = values.get("model", "")
    if model and (len(model) > MAX_MODEL_CHARS or not _model_ok(model)):
        raise NeutralError("%s: model must be lowercase letters, digits, '.', '-' and '_'" % rel)
    tools = _choice(values, "tools", TOOLS, rel) if kind == "agent" else ()
    needs = _choice(values, "needs", NEEDS, rel, required=False)
    files = tuple(Bundled(sub, content, hashlib.sha256(content).hexdigest())
                  for _, sub, content in extra)
    return Item(kind, name, description, args, tools, needs, model, body, files)


def _model_ok(model):
    return (model[0].isalnum() and model[0].isascii() and model == model.lower()
            and all(c.isascii() and (c.isalnum() or c in "._-") for c in model))


def _split(text, rel):
    lines = text.split("\n")
    if lines[0] != "---":
        raise NeutralError("%s: must start with a line of exactly ---" % rel)
    for index in range(1, len(lines)):
        if lines[index] == "---":
            return lines[1:index], "\n".join(lines[index + 1:])
    raise NeutralError("%s: no closing --- line" % rel)


def _front_matter(head, rel):
    values = {}
    for number, line in enumerate(head, 2):
        key, sep, value = line.partition(": ")
        if not sep and line.endswith(":"):
            key, sep, value = line[:-1], ":", ""
        if (not sep or not key or not key.isascii() or not key.replace("-", "").isalnum()
                or key != key.lower()):
            raise NeutralError("%s: line %d is not 'key: value'" % (rel, number))
        if key in values:
            raise NeutralError("%s: the field %r is given twice" % (rel, key))
        if (not value or value != value.strip() or not value.isascii()
                or not value.isprintable() or value[0] in "|>"):
            raise NeutralError("%s: the field %r must be one line of printable ASCII text "
                               "with no edge space or block indicator" % (rel, key))
        values[key] = value
    return values


def _choice(values, key, allowed, rel, required=True):
    if key not in values:
        return ()
    chosen = tuple(part.strip() for part in values[key].split(","))
    for word in chosen:
        if word not in allowed:
            raise NeutralError("%s: %s lists %r; allowed: %s"
                               % (rel, key, word or "(empty)", ", ".join(allowed)))
    for word in chosen:
        if chosen.count(word) > 1:
            raise NeutralError("%s: %s lists %r twice" % (rel, key, word))
    return tuple(sorted(chosen))


def read_rules(data):
    """Return ``Rule`` tuples for a parsed rule list; an ``allow`` or any odd entry is refused."""
    if not isinstance(data, list):
        raise NeutralError("the rule list must be a list")
    if len(data) > MAX_RULES:
        raise NeutralError("too many rules (%d, limit %d)" % (len(data), MAX_RULES))
    rules = []
    seen = set()
    for number, entry in enumerate(data, 1):
        where = "rule %d" % number
        if not isinstance(entry, dict) or set(entry) != {"action", "tool", "pattern"}:
            raise NeutralError("%s: needs exactly action, tool and pattern" % where)
        action, tool, pattern = entry["action"], entry["tool"], entry["pattern"]
        if action == "allow":
            raise NeutralError("%s: allow is not a neutral action; the owner's own "
                               "configuration holds allow rules" % where)
        if action not in RULE_ACTIONS:
            raise NeutralError("%s: action must be one of %s" % (where, ", ".join(RULE_ACTIONS)))
        if tool not in RULE_TOOLS:
            raise NeutralError("%s: tool must be one of %s" % (where, ", ".join(RULE_TOOLS)))
        if (not isinstance(pattern, str) or not pattern or len(pattern) > MAX_PATTERN_CHARS
                or pattern != pattern.strip() or not pattern.isascii()
                or any(c not in PATTERN_CHARS for c in pattern)
                or ".." in pattern.split("/")):
            raise NeutralError("%s: the pattern must be 1 to %d characters from %r, with no "
                               "edge space and no '..' segment"
                               % (where, MAX_PATTERN_CHARS, PATTERN_CHARS))
        key = (action, tool, pattern)
        if key in seen:
            raise NeutralError("%s: duplicates an earlier rule" % where)
        seen.add(key)
        rules.append(Rule(action, tool, pattern))
    return rules
