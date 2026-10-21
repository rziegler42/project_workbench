"""The kit: what the installer and a module's helper share for reading untrusted content safely.

It belongs to the workbench, not to any module. It imports only the standard library and itself, names
no module, document kind or harness, and carries an integer API version that a helper declares and the
runner checks (``docs/specs/module-boundary.md``, "The kit").
"""

# Raised when a change to the kit can break a helper that was released against the old one.
API = 1
