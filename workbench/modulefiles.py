"""Check a module's files against its declaration, then hash it.

The module is read once, by ``hashing.hash_tree`` through the race-safe reader in
``safefs``; nothing else touches the module's files. ``module.json`` is read in the
same pass and must still equal the declaration that was parsed, so the hashes
returned always describe the declaration that was checked.

A file is accounted for when it is ``module.json``, lies under ``harness/``,
``templates/``, ``files/``, ``tests/`` or ``tools/`` (exact case), is a ``fills`` source,
or is an item in ``ships`` (a file, or any file below a directory). Every other file
refuses the module. Empty directories hold no files and are ignored. ``tests/`` and
``tools/`` are the maintainer directories: hashed and approved with the module, never
installed, so ``ships`` and ``fills`` may not name them (``is_maintainer``).

Harness layout. A module with a ``harness/`` directory supplies harness items and
must hold ``harness/neutral/`` or at least one ``harness/<name>/`` directory.
A file directly under ``harness/`` is refused. ``manifest.json`` in a
``harness/<name>/`` may hold ``{"exclude": [{"item": "<kind>/<name>", "reason": "..."}]}``.

Item naming (ASSUMED, to be fixed by ``claude-harness``): an item is
``<kind>/<name>``, found at ``harness/neutral/<kind>/<name>`` or
``harness/<harness>/<kind>/<name>``. ``<name>`` is the second path segment, with a
trailing ``.md`` removed when that segment is a single file, so ``skills/x.md`` and
``skills/x/SKILL.md`` are both the item ``skills/x``. ``<kind>`` and ``<name>`` use
the ordinary name format. Two paths that give one item are an error. Only these
file-level checks are made here.
"""

import collections

from . import declarations, hashing, layout
from .wbkit import safefs

MAINTAINER_DIRS = ("tests", "tools")
RESERVED_DIRS = ("harness", "templates", "files") + MAINTAINER_DIRS
MANIFEST = "manifest.json"
MAX_REASON_CHARS = 200

ModuleResult = collections.namedtuple(
    "ModuleResult", "problems warnings declaration_hash tree_hash executable")


def is_maintainer(rel):
    """True for a maintainer directory itself, or a path at or below one, at the module root."""
    return rel.split("/")[0] in MAINTAINER_DIRS


def _keep(rel):
    if rel == "module.json":
        return True
    parts = rel.split("/")
    return len(parts) == 3 and parts[0] == "harness" and parts[2] == MANIFEST


def verify_module(package_path, package_name, module):
    """Verify one parsed ``Module`` in `package_path`; return a ``ModuleResult``.

    Hashes are returned only when there is no problem.
    """
    problems = []
    warnings = []

    def bad(rule, message):
        problems.append(declarations.DeclarationError("module", module.name, rule, message,
                                                      package_name))

    module_path = package_path.rstrip("/") + "/" + module.name
    try:
        info = hashing.hash_tree(module_path, "module", keep=_keep)
    except safefs.SafeFsError as exc:
        bad("files", str(exc))
        return ModuleResult(problems, warnings, None, None, ())

    try:
        reread = declarations.parse_json(info.contents.get("module.json", b""))
    except ValueError as exc:
        reread = None
    if reread != module.declaration:
        bad("module.json", "changed after it was parsed")
        return ModuleResult(problems, warnings, None, None, ())

    files = set(info.files)
    dirs = set(info.dirs)
    _accounted(module, files, bad)
    _declared_paths(module, files, dirs, bad)
    if module.type == "harness":
        for message in layout.problems(module.layout):
            bad("layout", message)
    _harness_layout(module, files, dirs, info.contents, bad, warnings)

    if problems:
        return ModuleResult(problems, warnings, None, None, ())
    return ModuleResult(problems, warnings, hashing.declaration_hash(module.declaration),
                        info.hash,
                        tuple(rel for rel in info.executable if not is_maintainer(rel)))


def _accounted(module, files, bad):
    ships = set(module.ships)
    sources = set(source for _, source in module.fills)
    for rel in sorted(files):
        parts = rel.split("/")
        if (rel == "module.json" or (len(parts) > 1 and parts[0] in RESERVED_DIRS)
                or rel in sources):
            continue
        if any("/".join(parts[:n]) in ships for n in range(1, len(parts) + 1)):
            continue
        bad("unaccounted-file", "%s is not module.json, under harness/, templates/, files/, "
                                "tests/ or tools/, or named by fills or ships" % rel)


def _declared_paths(module, files, dirs, bad):
    for slot, source in module.fills:
        if source not in files:
            bad("fills", "source %s for %s does not exist as a file" % (source, slot))
        elif is_maintainer(source):
            bad("fills", "source %s for %s is in a maintainer directory, which is never installed"
                % (source, slot))
    for item in module.ships:
        if is_maintainer(item):
            bad("ships", "%s is in a maintainer directory, which is never installed" % item)
            continue
        if item in files:
            continue
        if item not in dirs:
            bad("ships", "%s does not exist" % item)
        elif not any(rel.startswith(item + "/") for rel in files):
            # An empty directory is not in the tree hash, so an approval would not cover it.
            bad("ships", "%s is an empty directory" % item)
    for rel in module.writes:
        if "files/" + rel not in files:
            bad("writes", "%s has no source file at files/%s" % (rel, rel))


def _item(parts, bad, where):
    """Return the item id for the path segments below a neutral or harness directory."""
    if len(parts) < 2:
        bad("harness-layout", "%s: a harness item must be <kind>/<name>" % where)
        return None
    kind, name = parts[0], parts[1]
    if len(parts) == 2 and name.endswith(".md"):
        name = name[:-3]
    for label, value in (("kind", kind), ("name", name)):
        if not declarations.NAME_RE.match(value):
            bad("harness-layout", "%s: item %s %r is not a valid name" % (where, label, value))
            return None
    return kind + "/" + name


def _harness_layout(module, files, dirs, contents, bad, warnings):
    if "harness" not in dirs:
        return
    top = sorted(set(rel.split("/")[1] for rel in files | dirs
                     if rel.startswith("harness/") and rel.count("/") >= 1))
    for rel in sorted(files):
        if rel.startswith("harness/") and rel.count("/") == 1:
            bad("harness-layout", "%s sits directly under harness/; use harness/neutral/ or "
                                  "harness/<harness>/" % rel)
    subdirs = [name for name in top if "harness/" + name in dirs]
    if not subdirs:
        bad("harness-layout", "harness/ holds neither neutral/ nor a <harness>/ directory")
        return
    for name in subdirs:
        if not declarations.NAME_RE.match(name):
            bad("harness-layout", "harness/%s: %r is not a valid harness name" % (name, name))

    def items_under(base):
        found = {}
        for rel in sorted(files):
            if not rel.startswith(base + "/"):
                continue
            parts = rel[len(base) + 1:].split("/")
            if base != "harness/neutral" and parts == [MANIFEST]:
                continue
            item = _item(parts, bad, rel)
            if item is None:
                continue
            first = "/".join(parts[:2])
            if found.setdefault(item, first) != first:
                bad("harness-layout", "%s: %s and %s are both the item %s"
                    % (base, found[item], first, item))
        return set(found)

    neutral = items_under("harness/neutral") if "neutral" in subdirs else set()
    for name in subdirs:
        if name == "neutral":
            continue
        base = "harness/" + name
        overrides = items_under(base)
        excluded = _exclusions(base, contents, neutral, overrides, bad, warnings)
        for item in sorted(overrides & excluded):
            bad("harness-layout", "%s: %s is both overridden and excluded" % (base, item))


def _exclusions(base, contents, neutral, overrides, bad, warnings):
    data = contents.get(base + "/" + MANIFEST)
    if data is None:
        return set()
    where = base + "/" + MANIFEST
    try:
        manifest = declarations.parse_json(data)
    except ValueError as exc:
        bad("harness-layout", "%s: %s" % (where, exc))
        return set()
    for key in manifest:
        if key != "exclude":
            bad("harness-layout", "%s: unknown field %r" % (where, key))
    entries = manifest.get("exclude", [])
    if not isinstance(entries, list):
        bad("harness-layout", "%s: 'exclude' must be a list" % where)
        return set()
    excluded = set()
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) != {"item", "reason"}
                or not isinstance(entry["item"], str) or not isinstance(entry["reason"], str)
                or not entry["reason"].strip() or len(entry["reason"]) > MAX_REASON_CHARS
                or not entry["reason"].isprintable()):
            bad("harness-layout", "%s: each exclusion needs exactly an 'item' and a non-empty "
                                  "printable 'reason' of at most %d characters"
                    % (where, MAX_REASON_CHARS))
            continue
        item = entry["item"]
        if item not in neutral:
            bad("harness-layout", "%s: excluded item %s does not exist in harness/neutral/"
                % (where, item))
            continue
        if item in excluded:
            bad("harness-layout", "%s: %s is excluded twice" % (where, item))
            continue
        excluded.add(item)
        warnings.append("excludes %s for %s: %s" % (item, base[len("harness/"):], entry["reason"]))
    return excluded
