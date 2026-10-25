"""What ``wb adopt`` finds at the paths an install would write.

An install creates every file exclusively, so a path that exists is a conflict. An adoption goes
into a directory that already has content and decides each planned path by what is there
(``docs/specs/installer-interface.md``, "``adopt``"):

* it does not exist: created, as an install does;
* a seeded file that is a regular file: kept, and recorded at the hash of the bytes there;
* a real directory the plan needs: reused;
* anything else (a module-owned path, a directory where a file is planned, a file where a directory
  is, a link at any component, a file that is not regular, one with more than one hard link or one
  that is too large): a conflict, and every conflict is listed.

Nothing is ever written here. The target is read through the held descriptor one component at a
time without following a link, and a file is hashed with no filters. The caller never prints a
file's content.
"""

from . import installplan, projectfs
from .wbkit import safefs

# The most existing content one adoption reads, in all. One file is also bounded by ``safefs``.
MAX_TOTAL_BYTES = 256 * 1024 * 1024

_KIND_WORDS = {"dir": "a directory", "file": "a file", "symlink": "a link",
               "other": "not a regular file"}


class Conflicts(installplan.PlanError):
    """The adoption cannot be planned. `lines` has one entry for each conflict."""

    def __init__(self, lines):
        installplan.PlanError.__init__(self, "; ".join(lines))
        self.lines = list(lines)


def _prefixes(path):
    parts = path.split("/")
    return ["/".join(parts[:n]) for n in range(1, len(parts))]


def inspect(held, selection, snapshots, base):
    """Look at every path the install plan would write and return an ``installplan.Adopted``.

    Raises ``Conflicts``. Reads the target and nothing else."""
    files, _ = installplan.assemble(selection, snapshots, base)
    writer = projectfs.Writer(held)
    listings = {}
    conflicts = []
    kept = {}
    reused = set()
    absent = set()
    bad = set()
    total = [0]

    def kind_of(rel):
        parent, _, name = rel.rpartition("/")
        if parent not in listings:
            listings[parent] = writer.list_dir(parent, lenient=True)
        found = listings[parent]
        if found is None:
            return None
        return dict(found).get(name)

    def conflict(rel, why):
        bad.add(rel)
        conflicts.append("%s: %s" % (rel, why))

    dirs = sorted({prefix for path in files.order for prefix in _prefixes(path)}
                  - {".workbench", ".workbench/local"}, key=lambda rel: (rel.count("/"), rel))
    # `.workbench` is never there in an adoptable target; if it is, say so rather than plan around it.
    try:
        if kind_of(".workbench") is not None:
            conflict(".workbench", "it exists, and adopt needs a directory with no .workbench")
    except safefs.SafeFsError as exc:
        conflict(".workbench", str(exc))

    def parent_state(rel):
        parent = rel.rpartition("/")[0]
        if not parent:
            return "reuse"
        if parent in bad:
            return "bad"
        return "absent" if parent in absent else "reuse"

    for rel in dirs:
        state = parent_state(rel)
        if state == "bad":
            bad.add(rel)
            continue
        if state == "absent":
            absent.add(rel)
            continue
        try:
            kind = kind_of(rel)
        except safefs.SafeFsError as exc:
            conflict(rel, str(exc))
            continue
        if kind is None:
            absent.add(rel)
        elif kind == "dir":
            reused.add(rel)
        else:
            conflict(rel, "%s where the plan needs a directory" % _KIND_WORDS.get(kind, kind))

    for rel in files.order:
        state = parent_state(rel)
        if state != "reuse":
            continue
        try:
            kind = kind_of(rel)
        except safefs.SafeFsError as exc:
            conflict(rel, str(exc))
            continue
        if kind is None:
            continue
        if kind != "file":
            conflict(rel, "%s where the plan needs a file" % _KIND_WORDS.get(kind, kind))
        elif files.items[rel]["class"] != "seeded":
            conflict(rel, "it exists, and a path a module owns is never adopted")
        else:
            try:
                state_of = writer.read_file(rel)
            except safefs.SafeFsError as exc:
                conflict(rel, str(exc))
                continue
            if state_of is None:
                conflict(rel, "it changed while it was read")
                continue
            total[0] += len(state_of.data)
            if total[0] > MAX_TOTAL_BYTES:
                conflict(rel, "the existing files to keep are over %d bytes in all"
                         % MAX_TOTAL_BYTES)
                continue
            kept[rel] = (state_of.hash, len(state_of.data))
    if conflicts:
        raise Conflicts(conflicts)
    return installplan.Adopted(kept, frozenset(reused))
