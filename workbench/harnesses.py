"""The harnesses this workbench knows, with the facts ``wb check`` needs about each.

A harness is known when it is a module of type ``harness`` in a package that ``firstparty.is_first_party``
accepts in the workbench's distribution, whose layout verifies. The distribution is the trust root for the
layout, as it is for the shipped approvals. The facts are derived from that layout (``layout.facts``) and
from nothing else: no harness name or path is written here.

A name that two first-party packages both declare is refused as a name, not resolved by picking one. A
package that is not first-party, or does not load, or a layout that does not verify, contributes nothing.
"""

import collections
import os

from . import declarations, firstparty, layout

Known = collections.namedtuple("Known", "found refused")


def load(distribution=None):
    """``Known``: ``found`` maps each harness name to its ``layout.facts``; ``refused`` is the names that
    more than one first-party package declares."""
    distribution = distribution or firstparty.default_distribution()
    packages = os.path.join(distribution, firstparty.PACKAGES)
    try:
        names = sorted(os.listdir(packages)) if os.path.isdir(packages) else []
    except OSError:
        return Known({}, ())
    seen, refused = {}, set()
    for name in names:
        path = os.path.join(packages, name)
        if not firstparty.is_first_party(path, distribution):
            continue
        loaded = declarations.load_package(path, first_party=True)
        # The layout is read after the package was hashed, so it is hashed again: a package that changed
        # in between contributes nothing.
        if loaded.problems or not firstparty.is_first_party(path, distribution):
            continue
        for module in loaded.modules:
            if module.type != "harness" or layout.problems(module.layout):
                continue
            if module.name in seen:
                refused.add(module.name)
            seen.setdefault(module.name, layout.facts(module.layout))
    found = {name: facts for name, facts in seen.items() if name not in refused}
    return Known(found, tuple(sorted(refused)))


def known(distribution=None):
    """The facts of each known harness, by name."""
    return load(distribution).found
