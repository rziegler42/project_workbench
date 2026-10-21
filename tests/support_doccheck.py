"""A groundwork check helper (``doccheck`` or ``refcheck``), loaded by its path for tests.

A helper is one file that imports the kit as ``wbkit``; the launcher's runner makes that name
importable, and ``load`` does the same for a test by pointing it at the workbench's own kit."""

import importlib.machinery
import importlib.util
import os
import sys

from tests import support_install
from workbench import wbkit

HELPERS = os.path.join(support_install.ROOT, "packages", "workbench", "groundwork", "helper")
HELPER = os.path.join(HELPERS, "doccheck")


def load(name="doccheck"):
    sys.modules.setdefault("wbkit", wbkit)
    for each in ("display", "safefs", "gitindex", "jsonstrict"):
        sys.modules.setdefault("wbkit." + each, getattr(wbkit, each))
    loader = importlib.machinery.SourceFileLoader("groundwork_" + name, os.path.join(HELPERS, name))
    spec = importlib.util.spec_from_loader("groundwork_" + name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module
