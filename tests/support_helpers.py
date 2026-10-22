"""A check helper, named by its file, found under ``packages/`` and loaded by its path for tests.

A helper is one file that imports the kit as ``wbkit``; the launcher's runner makes that name
importable, and ``load`` does the same for a test by pointing it at the workbench's own kit."""

import glob
import importlib.machinery
import importlib.util
import os
import sys

from tests import support_install
from workbench import wbkit


def find(name):
    """The one helper file called `name` under a module's `helper/` directory in `packages/`."""
    found = glob.glob(os.path.join(support_install.ROOT, "packages", "*", "*", "helper", name))
    if len(found) != 1:
        raise LookupError("expected one helper called %s under packages/, found %d" % (name, len(found)))
    return found[0]


def load(name):
    sys.modules.setdefault("wbkit", wbkit)
    for each in ("display", "safefs", "gitindex", "jsonstrict"):
        sys.modules.setdefault("wbkit." + each, getattr(wbkit, each))
    loader = importlib.machinery.SourceFileLoader("helper_" + name, find(name))
    spec = importlib.util.spec_from_loader("helper_" + name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module
