"""The installer's own test fixtures that a module's tests build on, named in one place.

A module's tests may import only `tests.support*` (see `test_module_test_imports`). These names are the
installer's project, upgrade and install fixtures; a module test reaches them here and not through the
installer's test files."""

from tests import test_attach, test_groundwork_fixture, test_install, test_upgrade

HARNESS = test_attach.HARNESS
Base = test_attach.Base
Upgrade = test_upgrade.Upgrade
ROOT = test_install.ROOT
SEED = test_install.SEED
Typist = test_install.Typist
correct = test_install.correct
InstallBase = test_install.InstallBase
groundwork = test_groundwork_fixture.groundwork
GROUNDWORK_AREAS = test_groundwork_fixture.AREAS
