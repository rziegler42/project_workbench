"""The git identity an approval records, as ``Name <email>``.

The reader, the grammar and ``Identity`` live in the kit (``workbench/wbkit/identity.py``), so a module's helper reads the
identity with the same rules and limits as the installer (``2026-10-29-approvals-name-the-approver-by-git-identity``). This
module keeps the installer's names for them and adds nothing.
"""

from .wbkit.identity import Identity, IdentityError, account_home, check, parse, read  # noqa: F401
