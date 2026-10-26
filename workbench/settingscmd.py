"""``settings``: print the checkpoint and cap values that apply to this project.

The installer reads the project's one process module's verified declaration (``approvalcmd.installed_modules``,
the same reading ``approve-plan`` uses), the owner's personal settings from the guarded store, and prints what
``settings.effective`` makes of the two (``docs/specs/installer-interface.md``, "``settings`` and ``gate``")::

    checkpoint <name>: stop|delegate     one per declared checkpoint, in declaration order
    cap <name>: <n>                      one per declared cap, in declaration order
    level <key>: <level>                 one per declared checkpoint, in declaration order
    settings: <text>                     one per problem in the owner's settings

Nothing is started, written or approved here; the owner's settings are data. Exit 0 printed, 1 refused (a
``refused:`` line on standard error and nothing on standard output), 2 usage.
"""

import os

from . import approvalcmd, settings
from .wbkit import display

USAGE = "usage: wb settings\n"


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def run(guarded, tokens, out, err, *, cwd=None):
    if tokens:
        err.write(USAGE)
        return 2
    try:
        start = cwd if cwd is not None else os.getcwd()
    except OSError as exc:
        return _refuse(err, "the working directory cannot be read: %s" % (exc.strerror or "unknown error"))
    try:
        _, _, found = approvalcmd.installed_modules(start)
    except approvalcmd.ApprovalError as exc:
        return _refuse(err, str(exc))
    process = [item for item in found if item.module.type == "process"]
    if not process:
        return _refuse(err, "no installed module is a process module; there is nothing to set")
    if len(process) > 1:
        return _refuse(err, "more than one installed module is a process module: %s"
                       % ", ".join(sorted("%s/%s" % (item.package, item.module.name) for item in process)))
    module = process[0].module
    loaded = settings.load(guarded)
    effective = settings.effective(loaded, module.checkpoints, module.caps)
    for name in module.checkpoints:
        out.write("checkpoint %s: %s\n" % (name, effective.checkpoints[name]))
    for cap in module.caps:
        out.write("cap %s: %d\n" % (cap.name, effective.caps[cap.name]))
    for name in module.checkpoints:
        out.write("level %s: %s\n" % (name, effective.levels[name]))
    for text in list(loaded.problems) + list(effective.notes):
        out.write("settings: %s\n" % display.clean(text))
    return 0
