"""The groundwork check helper, loaded by its path for tests.

The helper is one file that imports the kit as ``wbkit``; the launcher's runner makes that name
importable, and ``load`` does the same for a test by pointing it at the workbench's own kit."""

import importlib.machinery
import importlib.util
import os
import sys

from tests import support_install
from workbench import wbkit

HELPER = os.path.join(support_install.ROOT, "packages", "workbench", "groundwork", "helper", "doccheck")


def load():
    sys.modules.setdefault("wbkit", wbkit)
    for name in ("display", "safefs"):
        sys.modules.setdefault("wbkit." + name, getattr(wbkit, name))
    loader = importlib.machinery.SourceFileLoader("groundwork_doccheck", HELPER)
    spec = importlib.util.spec_from_loader("groundwork_doccheck", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module
