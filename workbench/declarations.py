"""Parsing and validation of ``package.json`` and ``module.json``.

Declarations are data. They are read through ``safefs`` as bytes, decoded as
UTF-8, parsed by a strict JSON loader and never evaluated. The loader refuses a
duplicate key, a non-object top level, NaN, Infinity, any float, and a
declaration over ``MAX_DECLARATION_BYTES`` or nested deeper than ``MAX_DEPTH``. Unknown fields are refused.

Every refusal is a ``DeclarationError`` that names its scope: the package, or one
module of it, and the field or rule that failed.

Formats (proposals until the specs record them):

name        ``^[a-z][a-z0-9-]*$``, at most 64 characters. ``local``, ``neutral``
            and anything beginning ``manifest`` are reserved.
version     one to four dot-separated non-negative integers, no leading zeros.
contract    an integer from 1 up to ``SUPPORTED_CONTRACT``.
capability  printable ASCII, at most 64 characters, in one of three forms:
            ``name`` (core), ``<package>:name`` (third party) or ``slot:name``.
            A name part is the ``name`` format above; dotted sub-names are not
            defined yet and are refused.
requires    each entry a capability, or ``{"capability": ..., "soft": bool}``.
fills       each entry ``{"slot": "slot:<name>", "source": "<relative path>"}``.
slots       the names of the slots the module owns; the module provides
            ``slot:<name>`` for each, so ``provides`` may not list one.
helpers     tool names to look up on ``PATH``: letters, digits and ``._+-``.
writes,
ships       lists of relative paths, checked by ``safefs.validate_relpath``.
commands    an object of at most ``MAX_COMMANDS`` entries, each a command name in the
            helper-name form mapped to ``{"helper", "runtime", "kit", "arguments"}``
            (``module-boundary.md``, "Declaration schema"). The helper is an item of
            ``ships`` or a file below one.
checks      a list of at most ``MAX_CHECKS`` objects ``{"helper", "kit"}``, both required. The
            helper is an item of ``ships`` or a file below one, and its last path segment, the
            check's pin name, is in the helper-name form (``module-boundary.md``).
approval    process modules only: ``{"command", "argument"}``, the key of one of the module's
            ``commands`` and one of that command's ``arguments``. It names the command the
            installer runs to learn a plan's hashed region (``trust-and-approval.md``).
layout      present exactly for a harness module: an object whose keys come from
            ``LAYOUT_KEYS``. Its values are not checked beyond being JSON data;
            that belongs to the harness specification.

Optional fields (``type``, ``provides``, ``requires``, ``blocks``, ``helpers``,
``slots``, ``fills``, ``writes``, ``ships``, ``commands``, ``checks``, ``approval``) default to ``module`` and empty. The
declaration hash covers the declaration as written, never the defaults.

A ``writes`` path may not name the guarded store and may not enter ``.workbench/``
except under the module's own namespace ``.workbench/<package>/<module>/``. That is
stricter than "another module's namespace": another package's tree is also
another module's namespace.
"""

import collections
import re
import unicodedata

from .wbkit import jsonstrict, safefs

SUPPORTED_CONTRACT = 1
MAX_DECLARATION_BYTES = 1024 * 1024
MAX_NAME_CHARS = 64
MAX_DESCRIPTION_CHARS = 200
MAX_DEPTH = jsonstrict.MAX_DEPTH

TYPES = ("harness", "process", "module")
HARNESS_CAPABILITIES = ("instructions", "skills", "agents", "commands", "hooks", "permissions")
LAYOUT_KEYS = ("root", "kinds", "local_settings", "hooks", "exclude", "tolerated", "notes")

PACKAGE_FIELDS = ("name", "version", "contract", "modules")
MODULE_FIELDS = ("name", "version", "type", "description", "provides", "requires", "blocks",
                 "helpers", "slots", "fills", "writes", "ships", "commands", "checks", "approval", "layout")

_NAME = re.compile(r"^[a-z][a-z0-9-]*\Z")
_VERSION = re.compile(r"^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){0,3}\Z")
NAME_RE = _NAME
_HELPER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*\Z")
_ARGUMENT = re.compile(r"^[a-z][a-z0-9-]*\Z")

MAX_COMMANDS = 16
MAX_CHECKS = 16
MAX_ARGUMENTS = 16
MAX_ARGUMENT_CHARS = 32
MAX_KIT = 999999
RUNTIMES = ("python", "exec")

Package = collections.namedtuple("Package", "name version contract modules declaration")
Module = collections.namedtuple(
    "Module", "name version type description provides requires blocks helpers slots fills "
              "writes ships commands checks layout declaration approval", defaults=(None,))
Command = collections.namedtuple("Command", "name helper runtime kit arguments")


class Check(collections.namedtuple("Check", "helper kit")):
    """A check helper and the kit API number it needs. It is pinned under the last segment of its path."""

    @property
    def pin_name(self):
        return self.helper.rsplit("/", 1)[-1]


Loaded = collections.namedtuple("Loaded", "package modules problems")


class DeclarationError(Exception):
    """A declaration is refused. `scope` is "package" or "module"."""

    def __init__(self, scope, subject, rule, message, package=None):
        self.scope = scope
        self.subject = subject
        self.rule = rule
        self.message = message
        self.package = package
        super().__init__(str(self))

    def __str__(self):
        if self.scope == "module" and self.package:
            who = "module '%s' (package '%s')" % (self.subject, self.package)
        else:
            who = "%s '%s'" % (self.scope, self.subject)
        return "%s: %s: %s" % (who, self.rule, self.message)


# --- strict loader -------------------------------------------------------------


def parse_json(data):
    """Parse declaration bytes into a JSON object; raise ValueError with a reason."""
    return jsonstrict.parse_object(data, MAX_DECLARATION_BYTES)


# --- value checks -------------------------------------------------------------------


class _Checker:
    def __init__(self, scope, subject, package=None):
        self.scope = scope
        self.subject = subject
        self.package = package

    def fail(self, rule, message):
        raise DeclarationError(self.scope, self.subject, rule, message, self.package)

    def name(self, value, field, what="name"):
        if (not isinstance(value, str) or len(value) > MAX_NAME_CHARS
                or not _NAME.match(value)):
            self.fail(field, "%s %r must be lowercase kebab-case, starting with a letter, "
                             "at most %d characters" % (what, value, MAX_NAME_CHARS))
        if value in ("local", "neutral") or value.startswith("manifest"):
            self.fail("reserved-name", "%r is a reserved name" % value)
        return value

    def version(self, value, field="version"):
        if (not isinstance(value, str) or len(value) > MAX_NAME_CHARS
                or not _VERSION.match(value)):
            self.fail(field, "%r is not one to four dot-separated integers without leading zeros"
                      % (value,))
        return tuple(int(part) for part in value.split("."))

    def string_list(self, value, field):
        if not isinstance(value, list):
            self.fail(field, "must be a list")
        return value

    def unique(self, items, field):
        seen = set()
        for item in items:
            if not isinstance(item, str):
                self.fail(field, "each entry must be a string")
            if item in seen:
                self.fail(field, "%r is listed twice" % (item,))
            seen.add(item)

    def capability(self, value, field):
        """Return (prefix, name) for a valid capability; prefix is None for a core name."""
        if (not isinstance(value, str) or not value or len(value) > MAX_NAME_CHARS
                or not all(33 <= ord(c) <= 126 for c in value)):
            self.fail(field, "capability %r must be printable ASCII without spaces, "
                             "at most %d characters" % (value, MAX_NAME_CHARS))
        prefix, sep, rest = value.partition(":")
        if not sep:
            prefix, rest = None, value
        if (prefix is not None and not _NAME.match(prefix)) or not _NAME.match(rest):
            self.fail(field, "capability %r must be 'name', '<package>:name' or 'slot:name'"
                      % value)
        return prefix, rest

    def path(self, value, field):
        try:
            return safefs.validate_relpath(value)
        except safefs.SafeFsError as exc:
            self.fail(field, "path %r refused: %s" % (value, exc))

    def exact_keys(self, value, field, required, optional=()):
        if not isinstance(value, dict):
            self.fail(field, "each entry must be an object")
        for key in value:
            if key not in required and key not in optional:
                self.fail(field, "unknown key %r" % key)
        for key in required:
            if key not in value:
                self.fail(field, "missing key %r" % key)


def fold_name(name):
    """A pin name as it is compared: the same fold as a path segment, so case and Unicode variants meet."""
    return _fold(name)


def _shown(text):
    """Text from a declaration, escaped and shortened for a message."""
    text = repr(text)[1:-1]
    return text if len(text) <= 64 else text[:61] + "..."


def _fold(segment):
    return unicodedata.normalize("NFC", segment).rstrip(" .").casefold()


# --- package ---------------------------------------------------------------------------


def parse_package(data, shown="package"):
    """Validate the bytes of ``package.json``; return a ``Package``."""
    check = _Checker("package", shown)
    try:
        declaration = parse_json(data)
    except ValueError as exc:
        check.fail("package.json", str(exc))
    for key in declaration:
        if key not in PACKAGE_FIELDS:
            check.fail(_shown(key), "unknown field")
    for key in PACKAGE_FIELDS:
        if key not in declaration:
            check.fail(key, "missing field")
    name = check.name(declaration["name"], "name", "package name")
    check = _Checker("package", name)
    version = check.version(declaration["version"])
    contract = declaration["contract"]
    if isinstance(contract, bool) or not isinstance(contract, int) or contract < 1:
        check.fail("contract", "%r is not a positive integer" % (contract,))
    if contract > SUPPORTED_CONTRACT:
        check.fail("contract", "contract %d is newer than the highest supported (%d)"
                   % (contract, SUPPORTED_CONTRACT))
    modules = check.string_list(declaration["modules"], "modules")
    for entry in modules:
        check.name(entry, "modules", "module name")
    check.unique(modules, "modules")
    return Package(name, version, contract, tuple(modules), declaration)


# --- module ------------------------------------------------------------------------------


def _commands(check, value, ships):
    """The ``commands`` field as a tuple of ``Command``, or a refusal naming the field."""
    if not isinstance(value, dict):
        check.fail("commands", "must be an object")
    if len(value) > MAX_COMMANDS:
        check.fail("commands", "at most %d commands, not %d" % (MAX_COMMANDS, len(value)))
    commands = []
    helpers = set()
    for name, entry in value.items():
        if not isinstance(name, str) or len(name) > MAX_NAME_CHARS or not _HELPER.match(name):
            check.fail("commands", "command name %s must be letters, digits and ._+-, starting "
                                   "with a letter or digit, at most %d characters"
                       % (_shown(name), MAX_NAME_CHARS))
        check.exact_keys(entry, "commands", ("helper",), ("runtime", "kit", "arguments"))
        helper = check.path(entry["helper"], "commands")
        helper = "/".join(helper)
        if not any("/".join(helper.split("/")[:n]) in ships
                   for n in range(1, len(helper.split("/")) + 1)):
            check.fail("commands", "command %s: helper %s is not an item of 'ships' or below one"
                       % (name, _shown(helper)))
        folded = "/".join(_fold(part) for part in helper.split("/"))
        if folded in helpers:
            check.fail("commands", "two commands name the helper %s (or one that differs only in "
                                   "letter case)" % _shown(helper))
        helpers.add(folded)
        runtime = entry.get("runtime", "exec")
        if runtime not in RUNTIMES:
            check.fail("commands", "command %s: runtime %s is not one of %s"
                       % (name, _shown(runtime), ", ".join(RUNTIMES)))
        kit = entry.get("kit")
        if runtime == "python":
            if type(kit) is not int or not 1 <= kit <= MAX_KIT:
                check.fail("commands", "command %s: a python command needs 'kit', an integer "
                                       "from 1 to %d" % (name, MAX_KIT))
        elif "kit" in entry:
            check.fail("commands", "command %s: 'kit' goes only with runtime 'python'" % name)
        arguments = entry.get("arguments", [])
        if not isinstance(arguments, list) or len(arguments) > MAX_ARGUMENTS:
            check.fail("commands", "command %s: 'arguments' must be a list of at most %d"
                       % (name, MAX_ARGUMENTS))
        check.unique(arguments, "commands")
        for argument in arguments:
            if len(argument) > MAX_ARGUMENT_CHARS or not _ARGUMENT.match(argument):
                check.fail("commands", "command %s: argument %s must be lowercase letters, digits "
                                       "and dashes, starting with a letter, at most %d characters"
                           % (name, _shown(argument), MAX_ARGUMENT_CHARS))
        commands.append(Command(name, helper, runtime, kit, tuple(arguments)))
    return tuple(commands)


def _checks(check, value, ships, commands):
    """The ``checks`` field as a tuple of ``Check``, or a refusal naming the field."""
    if not isinstance(value, list):
        check.fail("checks", "must be a list")
    if len(value) > MAX_CHECKS:
        check.fail("checks", "at most %d checks, not %d" % (MAX_CHECKS, len(value)))
    taken = {"/".join(_fold(part) for part in c.helper.split("/")): "a command" for c in commands}
    names = {_fold(c.name): "a command name" for c in commands}
    checks = []
    for entry in value:
        check.exact_keys(entry, "checks", ("helper", "kit"), ())
        helper = "/".join(check.path(entry["helper"], "checks"))
        if not any("/".join(helper.split("/")[:n]) in ships
                   for n in range(1, len(helper.split("/")) + 1)):
            check.fail("checks", "helper %s is not an item of 'ships' or below one" % _shown(helper))
        folded = "/".join(_fold(part) for part in helper.split("/"))
        if folded in taken:
            check.fail("checks", "the helper %s is already named by %s of this module (or one that "
                                 "differs only in letter case)" % (_shown(helper), taken[folded]))
        taken[folded] = "another check"
        pin_name = helper.rsplit("/", 1)[-1]
        if len(pin_name) > MAX_NAME_CHARS or not _HELPER.match(pin_name):
            check.fail("checks", "the pin name %s (the last part of helper %s) must be letters, digits "
                                 "and ._+-, starting with a letter or digit, at most %d characters"
                       % (_shown(pin_name), _shown(helper), MAX_NAME_CHARS))
        if _fold(pin_name) in names:
            check.fail("checks", "the pin name %s is already used by %s of this module"
                       % (_shown(pin_name), names[_fold(pin_name)]))
        names[_fold(pin_name)] = "another check"
        kit = entry["kit"]
        if type(kit) is not int or not 1 <= kit <= MAX_KIT:
            check.fail("checks", "'kit' must be an integer from 1 to %d" % MAX_KIT)
        checks.append(Check(helper, kit))
    return tuple(checks)


def _approval(check, value, mtype, commands):
    """The ``approval`` field as ``{"command", "argument"}``, or a refusal naming the field."""
    if mtype != "process":
        check.fail("approval", "only a process module declares an approval command")
    check.exact_keys(value, "approval", ("command", "argument"))
    command, argument = value["command"], value["argument"]
    if not isinstance(command, str) or not isinstance(argument, str):
        check.fail("approval", "'command' and 'argument' must be strings")
    found = {c.name: c for c in commands}.get(command)
    if found is None:
        check.fail("approval", "the command %s is not one of this module's commands" % _shown(command))
    if argument not in found.arguments:
        check.fail("approval", "%s is not an argument of the command %s" % (_shown(argument), _shown(command)))
    return {"command": command, "argument": argument}


def parse_module(data, package_name, expected_name, first_party=False):
    """Validate the bytes of one ``module.json``; return a ``Module``."""
    check = _Checker("module", expected_name, package_name)
    try:
        declaration = parse_json(data)
    except ValueError as exc:
        check.fail("module.json", str(exc))
    for key in declaration:
        if key not in MODULE_FIELDS:
            check.fail(_shown(key), "unknown field")
    for key in ("name", "version", "description"):
        if key not in declaration:
            check.fail(key, "missing field")

    name = check.name(declaration["name"], "name", "module name")
    if name != expected_name:
        check.fail("name", "declared name %r differs from the package list entry and "
                           "directory %r" % (name, expected_name))
    version = check.version(declaration["version"])

    description = declaration["description"]
    if (not isinstance(description, str) or not description.strip()
            or len(description) > MAX_DESCRIPTION_CHARS
            or not description.isprintable()):
        check.fail("description", "must be one printable line of at most %d characters"
                   % MAX_DESCRIPTION_CHARS)

    mtype = declaration.get("type", "module")
    if mtype not in TYPES:
        check.fail("type", "%r is not one of %s" % (mtype, ", ".join(TYPES)))

    provides = check.string_list(declaration.get("provides", []), "provides")
    check.unique(provides, "provides")
    for cap in provides:
        prefix, rest = check.capability(cap, "provides")
        if prefix == "slot":
            check.fail("provides", "%r: declare a slot in 'slots', not in 'provides'" % cap)
        if prefix is None:
            if cap in HARNESS_CAPABILITIES and mtype != "harness":
                check.fail("provides", "harness capability %r may be provided only by a "
                                       "harness module" % cap)
            if not first_party:
                check.fail("provides", "unprefixed capability %r is reserved for the "
                                       "first-party package" % cap)
        elif prefix != package_name:
            check.fail("provides", "capability %r must be prefixed with the package name %r"
                       % (cap, package_name))

    requires = []
    raw_requires = check.string_list(declaration.get("requires", []), "requires")
    for entry in raw_requires:
        soft = False
        if isinstance(entry, dict):
            check.exact_keys(entry, "requires", ("capability",), ("soft",))
            cap = entry["capability"]
            soft = entry.get("soft", False)
            if not isinstance(soft, bool):
                check.fail("requires", "'soft' must be true or false")
        else:
            cap = entry
        check.capability(cap, "requires")
        requires.append((cap, soft))
    check.unique([cap for cap, _ in requires], "requires")

    blocks = check.string_list(declaration.get("blocks", []), "blocks")
    for cap in blocks:
        check.capability(cap, "blocks")
    check.unique(blocks, "blocks")

    helpers = check.string_list(declaration.get("helpers", []), "helpers")
    for helper in helpers:
        if (not isinstance(helper, str) or len(helper) > MAX_NAME_CHARS
                or not _HELPER.match(helper)):
            check.fail("helpers", "%r is not a plain tool name" % (helper,))
    check.unique(helpers, "helpers")

    slots = check.string_list(declaration.get("slots", []), "slots")
    for slot in slots:
        check.name(slot, "slots", "slot name")
    check.unique(slots, "slots")

    fills = []
    for entry in check.string_list(declaration.get("fills", []), "fills"):
        check.exact_keys(entry, "fills", ("slot", "source"))
        prefix, rest = check.capability(entry["slot"], "fills")
        if prefix != "slot":
            check.fail("fills", "%r is not a slot; write 'slot:<name>'" % (entry["slot"],))
        check.path(entry["source"], "fills")
        fills.append((entry["slot"], entry["source"]))
    check.unique([slot for slot, _ in fills], "fills")

    ships = check.string_list(declaration.get("ships", []), "ships")
    for rel in ships:
        check.path(rel, "ships")
    check.unique(ships, "ships")

    writes = check.string_list(declaration.get("writes", []), "writes")
    own = (".workbench", _fold(package_name), _fold(name))
    for rel in writes:
        parts = [_fold(part) for part in check.path(rel, "writes")]
        if parts[:2] == [".config", "project-workbench"]:
            check.fail("writes", "%r names the guarded store" % rel)
        if parts[0] == ".workbench" and (len(parts) <= 3 or tuple(parts[:3]) != own):
            check.fail("writes", "%r enters .workbench/ outside this module's own namespace "
                                 ".workbench/%s/%s/" % (rel, package_name, name))
    try:
        safefs.check_tree_paths(writes)
    except safefs.SafeFsError as exc:
        check.fail("writes", str(exc))

    commands = _commands(check, declaration.get("commands", {}), ships)
    checks = _checks(check, declaration.get("checks", []), ships, commands)
    approval = _approval(check, declaration["approval"], mtype, commands) if "approval" in declaration else None

    layout = declaration.get("layout")
    if mtype == "harness":
        if "layout" not in declaration:
            check.fail("layout", "a harness module must declare a layout")
        if not isinstance(layout, dict):
            check.fail("layout", "must be an object")
        for key in layout:
            if key not in LAYOUT_KEYS:
                check.fail("layout", "unknown key %r (expected one of %s)"
                           % (key, ", ".join(LAYOUT_KEYS)))
    elif "layout" in declaration:
        check.fail("layout", "only a harness module declares a layout")

    return Module(name, version, mtype, description, tuple(provides), tuple(requires),
                  tuple(blocks), tuple(helpers), tuple(slots), tuple(fills), tuple(writes),
                  tuple(ships), commands, checks, layout, declaration, approval)


# --- from a directory ------------------------------------------------------------------------


def load_package(path, first_party=False):
    """Read and validate a package directory; return ``Loaded``.

    Problems are collected, not raised. A package-level failure leaves no modules.
    """
    shown = path
    try:
        with safefs.Root(path, "package") as root:
            entries = root.walk()
            kinds = {entry.rel: entry.kind for entry in entries}
            data = _read(root, "package.json", kinds)
            package = parse_package(data, shown)
            problems = []
            modules = []
            for name in package.modules:
                try:
                    modules.append(_load_module(root, kinds, package, name, first_party))
                except DeclarationError as exc:
                    problems.append(exc)
                except safefs.SafeFsError as exc:
                    problems.append(DeclarationError("module", name, "module.json", str(exc),
                                                     package.name))
            listed = set(package.modules)
            for rel, kind in sorted(kinds.items()):
                if "/" in rel or kind != "dir" or rel in listed:
                    continue
                if kinds.get(rel + "/module.json") == "file":
                    problems.append(DeclarationError(
                        "package", package.name, "modules",
                        "directory %r holds a module.json but is not listed in 'modules'" % rel))
            return Loaded(package, modules, problems)
    except DeclarationError as exc:
        return Loaded(None, [], [exc])
    except safefs.SafeFsError as exc:
        return Loaded(None, [], [DeclarationError("package", shown, "package.json", str(exc))])


def _read(root, rel, kinds):
    if kinds.get(rel) != "file":
        raise safefs.SafeFsError("%s is missing or is not a regular file" % rel)
    return root.read_file(rel, limit=MAX_DECLARATION_BYTES)


def _load_module(root, kinds, package, name, first_party):
    if kinds.get(name) != "dir":
        raise DeclarationError("module", name, "directory",
                               "listed in 'modules' but there is no directory of that name",
                               package.name)
    data = _read(root, name + "/module.json", kinds)
    return parse_module(data, package.name, name, first_party)
