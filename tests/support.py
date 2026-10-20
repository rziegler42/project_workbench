"""Shared test helpers."""

import unittest.mock

from workbench import store


def forbid_real_store(case):
    """Fail the test if code asks for the real store location.

    Tests pass a temporary store root, so nothing should call ``default_root``.
    """
    def refuse():
        raise AssertionError("a test reached the real guarded store location")

    patcher = unittest.mock.patch.object(store, "default_root", refuse)
    patcher.start()
    case.addCleanup(patcher.stop)
