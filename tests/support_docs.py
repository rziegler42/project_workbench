"""Fixtures for the document helpers' tests: documents to write under a temporary project and the
directory fixture that holds them. Standard library only."""

import os
import shutil
import tempfile
import unittest

SPEC = "# Power\n\nStatus: Current. Approved on 2026-10-21.\n\n## Scope\n\nText.\n"
DECISION = "# Use SPI flash\n\nStatus: Accepted\nDate: 2026-01-15\n\n## Context\n\nText.\n"
ROADMAP = ("# Roadmap: first-release\n\nStatus: Active\nUpdated: 2026-10-21\n\n## Purpose\n\nx\n\n"
           "## Candidates\n\n### pick-a-board: Pick a board\n\nx\n\n### write-driver — Write\n")


class Base(unittest.TestCase):
    """A project directory and a directory outside it."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.root = os.path.join(self.base, "proj")
        os.mkdir(self.root)
        self.outside = os.path.join(self.base, "outside")
        os.mkdir(self.outside)

    def put(self, rel, data):
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data.encode("utf-8") if isinstance(data, str) else data)

    def fresh(self, rel, data):
        """Only this document under docs/, so one subtest never sees another's file."""
        shutil.rmtree(os.path.join(self.root, "docs"), ignore_errors=True)
        self.put(rel, data)
