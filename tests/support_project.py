"""A project with a module that offers commands, installed the way `install` writes it.

The module is synthetic: it knows nothing of any real module. A test that needs a different
declaration passes it to `tool`."""

import unittest.mock

from tests import test_attach
from workbench import approve, pins

HARNESS = test_attach.HARNESS
HELPER_PATH = "helper/tool"
HELPER = b"#!/bin/sh\necho ran \"$@\"\n"
COMMANDS = {"tool": {"helper": HELPER_PATH, "arguments": ["check", "report"]}}


def tool(commands=None, helper=HELPER):
    """A module that ships one helper and declares `commands` (the default: one command, `tool`)."""
    fields = {"ships": [HELPER_PATH],
              "commands": dict(COMMANDS if commands is None else commands)}
    return fields, {HELPER_PATH: helper}


class Project(test_attach.Base):
    """`self.ready()` installs a harness module and the `tool` module into `self.place`."""

    MODULES = {"h": (HARNESS, {}), "tool": tool()}

    def setUp(self):
        test_attach.Base.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)

    def installed(self, module="tool", rel=HELPER_PATH):
        return ".workbench/p/%s/%s" % (module, rel)

    def unpin(self, *names):
        """Remove the pins the installer made, as if the owner had never confirmed them: the named
        ones, or every pin when none is named."""
        held = pins.load(self.guarded, self.project_id)
        for name in names or list(held):
            del held[name]
        self.guarded.write("projects/%s/pins" % self.project_id, pins.serialize(held))

    def pin(self, name="tool", path=None, data=None, kit=None):
        """Pin a helper as `wb pin` would: by default the installed helper of the `tool` module."""
        path = path or self.installed()
        data = self.read(path) if data is None else data
        pins.set_pin(self.guarded, self.project_id, name, path, pins.hash_bytes(data), "owner", kit=kit)
