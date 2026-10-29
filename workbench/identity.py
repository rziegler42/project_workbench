"""The git identity an approval records, as ``Name <email>``.

``docs/decisions/2026-10-29-approvals-name-the-approver-by-git-identity.md``, decisions 2 and 4. The identity is an
unverified attribution label: git does not check that a person owns an email. It is read from the account's own global
git configuration and from nowhere else:

* two runs, ``git config --global --get user.name`` and ``... user.email``, each an argument list with no shell;
* the working directory is the account's home from the account database, never the project;
* the environment is built from nothing: ``HOME`` set to that directory, a fixed ``PATH``, ``GIT_CONFIG_NOSYSTEM=1`` and
  ``LC_ALL=C``, so no ``GIT_*`` variable of the caller reaches git, and ``--global`` follows no ``include`` directive;
* git is one of a fixed list of files, not whatever the caller's ``PATH`` names first: a run without a terminal happens in
  an agent's environment, and a program placed first on that ``PATH`` must not be able to name the approver;
* a global configuration file that is a symbolic link is refused, and so is one git cannot read.

The output of a run is bounded only after it is read, within the timeout: the program is one of the fixed files and the data
is the account's own configuration, so the residual is memory and not a way to choose the identity. Only Unix is supported
(``pwd``, the fixed paths). ``home`` of ``read`` is for tests; a caller in the installer never gives it.

A missing, empty or ungrammatical value refuses and says how to set it. There is no fallback to a word such as ``owner``.
The grammar is the decision's: the name is 1 to 100 characters after NFC normalization with no control, format,
surrogate, private-use or unassigned character, no line or paragraph separator and neither ``<`` nor ``>``; the email is
3 to 100 printable ASCII characters from ``!`` to ``~`` other than ``<`` and ``>``, with exactly one ``@`` and something
on each side; the stored text is at most 210 characters. A name of nothing but blanks is refused too (my call): it names
nobody. Records compare by the lowercased email, ``Identity.key``, and never by the name.
"""

import collections
import os
import pwd
import subprocess
import unicodedata

GIT_LOCATIONS = ("/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git")
FIXED_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
TIMEOUT = 10
MAX_OUTPUT = 4096
MAX_NAME = 100
MIN_EMAIL, MAX_EMAIL = 3, 100
MAX_TEXT = 210

Identity = collections.namedtuple("Identity", "name email text key")

_REFUSED_CATEGORIES = ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp")
_SET_NAME = 'set it with: git config --global user.name "Your Name"'
_SET_EMAIL = 'set it with: git config --global user.email "you@example.com"'


class IdentityError(Exception):
    """The identity could not be read or is not valid; the text is the caller's to print after ``refused: ``."""


def account_home():
    """The account's home directory from the account database, or ``IdentityError``."""
    try:
        home = pwd.getpwuid(os.getuid()).pw_dir
    except (KeyError, OSError) as exc:
        raise IdentityError("the home directory of this account cannot be found (%s)" % exc.__class__.__name__)
    if not home or not os.path.isabs(home) or not os.path.isdir(home):
        raise IdentityError("the home directory of this account is not usable")
    return home


def _shown(value):
    """`value` for a message: short, with anything unprintable escaped."""
    text = "".join(c if c.isprintable() else repr(c)[1:-1] for c in str(value))
    return text if len(text) <= 40 else text[:37] + "..."


def check(name, email):
    """The ``Identity`` of `name` and `email` under the grammar, or ``IdentityError`` naming the value and the rule."""
    if not isinstance(name, str) or not isinstance(email, str):
        raise IdentityError("the git name and email must be text")
    name = unicodedata.normalize("NFC", name)
    if not 1 <= len(name) <= MAX_NAME:
        raise IdentityError("the git name %r is not 1 to %d characters; %s" % (_shown(name), MAX_NAME, _SET_NAME))
    bad = [c for c in name if unicodedata.category(c) in _REFUSED_CATEGORIES]
    if bad or "<" in name or ">" in name:
        raise IdentityError("the git name %r holds a control, format, surrogate, private-use, unassigned or separator "
                            "character, or < or >; %s" % (_shown(name), _SET_NAME))
    if not name.strip():
        raise IdentityError("the git name is only blanks; %s" % _SET_NAME)
    if not MIN_EMAIL <= len(email) <= MAX_EMAIL:
        raise IdentityError("the git email %r is not %d to %d characters; %s"
                            % (_shown(email), MIN_EMAIL, MAX_EMAIL, _SET_EMAIL))
    if any(not "!" <= c <= "~" or c in "<>" for c in email):
        raise IdentityError("the git email %r holds a character other than printable ASCII from ! to ~ (or a < or >); %s"
                            % (_shown(email), _SET_EMAIL))
    left, at, right = email.partition("@")
    if not at or not left or not right or "@" in right:
        raise IdentityError("the git email %r needs exactly one @ with something on each side; %s"
                            % (_shown(email), _SET_EMAIL))
    text = "%s <%s>" % (name, email)
    if len(text) > MAX_TEXT:
        raise IdentityError("the git identity is longer than %d characters; %s" % (MAX_TEXT, _SET_NAME))
    return Identity(name, email, text, email.lower())


def _git():
    for path in GIT_LOCATIONS:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise IdentityError("git was not found at %s; install it, then set the identity with git config --global"
                        % ", ".join(GIT_LOCATIONS))


def _refuse_links(home):
    for rel in (".gitconfig", os.path.join(".config", "git", "config")):
        path = os.path.join(home, rel)
        if os.path.islink(path):
            raise IdentityError("the global git configuration %s is a symbolic link; the identity is not read through "
                                "one" % rel)


def _value(git, home, key, how):
    env = {"HOME": home, "PATH": FIXED_PATH, "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"}
    try:
        done = subprocess.run([git, "config", "--global", "--get", key], cwd=home, env=env, shell=False,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise IdentityError("git did not finish reading %s within %s seconds" % (key, TIMEOUT))
    except OSError as exc:
        raise IdentityError("git could not be run to read %s (%s)" % (key, exc.__class__.__name__))
    if done.returncode == 1 and not done.stdout:
        raise IdentityError("the global git configuration has no %s; %s" % (key, how))
    if done.returncode != 0:
        raise IdentityError("git could not read %s from the global configuration (exit %d); is the file readable?"
                            % (key, done.returncode))
    if len(done.stdout) > MAX_OUTPUT:
        raise IdentityError("the value of %s is longer than %d bytes" % (key, MAX_OUTPUT))
    try:
        text = done.stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise IdentityError("the value of %s is not valid UTF-8; %s" % (key, how))
    if text.endswith("\n"):
        text = text[:-1]
    if not text:
        raise IdentityError("the global git configuration has an empty %s; %s" % (key, how))
    return text


def read(home=None):
    """The ``Identity`` of the account, read as the module's header says. `home` is for tests; it is the account's home
    from the account database when not given. ``IdentityError`` when it cannot be read or is not valid."""
    home = account_home() if home is None else home
    git = _git()
    _refuse_links(home)
    name = _value(git, home, "user.name", _SET_NAME)
    email = _value(git, home, "user.email", _SET_EMAIL)
    return check(name, email)
