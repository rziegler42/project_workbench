"""Fixtures for tests of a project that has the groundwork module: a manifest that records it and
files written under the project root. Used by the refcheck tests until refcheck moves into the module."""

import os
import shutil

from tests.test_projectfs import Fixture
from workbench import manifest

HASH = "a" * 64

SPEC = "# Power\n\nStatus: Current. Approved on 2026-10-21.\n\n## Scope\n\nText.\n"
DECISION = "# Use SPI flash\n\nStatus: Accepted\nDate: 2026-01-15\n\n## Context\n\nText.\n"
ROADMAP = ("# Roadmap: first-release\n\nStatus: Active\nUpdated: 2026-10-21\n\n## Purpose\n\nx\n\n"
           "## Candidates\n\n### pick-a-board: Pick a board\n\nx\n\n### write-driver — Write\n")


def installed_document(module="groundwork", package="workbench"):
    return {
        "base": HASH, "files": [],
        "packages": [{"commit": "", "modules": [{"declaration": HASH, "name": module,
                                                  "tree": HASH, "version": "0.1.0"}],
                      "name": package, "ref": "", "source": "https://example.test/p",
                      "tree": HASH}],
        "seed": "11111111-2222-4333-8444-555555555555", "version": 1, "workbench": "0.1.0",
    }


class Base(Fixture):
    def put(self, rel, data):
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data.encode("utf-8") if isinstance(data, str) else data)

    def fresh(self, rel, data):
        """Only this document under docs/, so one subtest never sees another's file."""
        shutil.rmtree(os.path.join(self.root, "docs"), ignore_errors=True)
        self.put(rel, data)

    def install(self, **changes):
        self.put(".workbench/manifest.json", manifest.serialize(installed_document(**changes)))
