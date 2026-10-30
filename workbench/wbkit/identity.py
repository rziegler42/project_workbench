"""The git identity an approval records, as ``Name <email>``: what the installer and a module's helper share.

It imports the standard library only and knows no module. Adding to it does not raise ``wbkit.API``. The installer's
``workbench/identity.py`` re-exports these names.

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

What this does not guard against, found by the security review of 2026-10-29 and left as it is:

* A person who can write in the account's home can write the global file, so the symbolic-link refusal is not a boundary against
  them. It does not see a link at ``~/.config`` or at the home itself, and it cannot close a swap between the check and git's
  read. An actor with the account's own rights can always set the identity; the identity is a label and grants nothing.
* The second and third fixed git locations are not checked for owner or write permission. ``/opt/homebrew/bin`` is writable by
  the account on Apple silicon and is reached only when ``/usr/bin/git`` and ``/usr/local/bin/git`` are absent; requiring root
  ownership would refuse Homebrew's git altogether.
* Which characters count as unassigned (the ``Cn`` category) depends on the Unicode data of the Python that runs this, so the
  allowed set can differ a little between machines. It was read on Python 3.15.0 and Unicode 17.
* The name grammar is the decision's with its clarification note. It still lets through a name that prints as a second identity
  (lookalike brackets, a lookalike letter) and a run of combining marks. Records compare by the lowercased ASCII email, never by
  the name.

Output is read in pieces and the child is killed when it passes ``MAX_OUTPUT`` bytes of output or ``MAX_ERROR`` of messages, or
at the timeout. Only Unix is supported (``pwd``, the fixed paths). ``home`` of ``read`` is for tests; a caller in the installer
never gives it.

A missing, empty or ungrammatical value refuses and says how to set it. There is no fallback to a word such as ``owner``.
The grammar is the decision's: the name is 1 to 100 characters after NFC normalization with no control, format,
surrogate, private-use or unassigned character, no line or paragraph separator and neither ``<`` nor ``>``; the email is
3 to 100 printable ASCII characters from ``!`` to ``~`` other than ``<`` and ``>``, with exactly one ``@`` and something
on each side; the stored text is at most 210 characters. The clarification note of 2026-10-29 adds two rules for the name:
it holds a letter, number, punctuation mark or symbol that shows (not one of the fillers in ``_PRINTS_AS_NOTHING``), and it
neither begins nor ends with a blank (a ``Zs`` character). Records compare by the lowercased email, ``Identity.key``, and never by the name.
"""

import collections
import os
import pwd
import selectors
import subprocess
import time
import unicodedata

GIT_LOCATIONS = ("/usr/bin/git", "/usr/local/bin/git", "/opt/homebrew/bin/git")
FIXED_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
TIMEOUT = 10
MAX_OUTPUT = 4096
MAX_ERROR = 1024
MAX_NAME = 100
MIN_EMAIL, MAX_EMAIL = 3, 100
MAX_TEXT = 210

Identity = collections.namedtuple("Identity", "name email text key")

_REFUSED_CATEGORIES = ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp")
# Characters that are letters or symbols by category and print as nothing, or combine with nothing (clarification note of
# 2026-10-29 to decision 4): the Hangul fillers, the Braille blank, the Khmer inherent vowels and the grapheme joiner.
_PRINTS_AS_NOTHING = "ᅟᅠㅤﾠ⠀឴឵͏"
_SET_NAME ='set it with: git config --global user.name "Your Name"'
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
    if unicodedata.category(name[0]) == "Zs" or unicodedata.category(name[-1]) == "Zs":
        raise IdentityError("the git name %r begins or ends with a blank; %s" % (_shown(name), _SET_NAME))
    if not any(unicodedata.category(c)[0] in "LNPS" and c not in _PRINTS_AS_NOTHING for c in name):
        raise IdentityError("the git name %r has no letter, number, punctuation mark or symbol that shows; %s"
                            % (_shown(name), _SET_NAME))
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


def parse(text):
    """The ``Identity`` whose stored text is `text` (``Name <email>``), or ``IdentityError``. The text must be exactly what
    ``check`` would store, so a record cannot hold a form that a person could not have configured."""
    if not isinstance(text, str) or not text.endswith(">") or " <" not in text:
        raise IdentityError("the approver %r is not a name and an email in the form Name <email>" % _shown(text))
    name, _, rest = text.rpartition(" <")
    found = check(name, rest[:-1])
    if found.text != text:
        raise IdentityError("the approver %r is not in the form that is stored" % _shown(text))
    return found


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


class _Excess(Exception):
    """A run wrote more than it may; the child has been stopped."""


def _run(git, home, key):
    """``(exit code, standard output, standard error)`` of one run, or an ``IdentityError``. Output is read in pieces and
    the child is killed as soon as it passes its bound or the deadline, so a program that never stops costs neither time nor
    memory beyond the bound."""
    env = {"HOME": home, "PATH": FIXED_PATH, "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"}
    try:
        child = subprocess.Popen([git, "config", "--global", "--get", key], cwd=home, env=env, shell=False,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise IdentityError("git could not be run to read %s (%s)" % (key, exc.__class__.__name__))
    seen = {"out": bytearray(), "err": bytearray()}
    limits = {"out": MAX_OUTPUT, "err": MAX_ERROR}
    deadline = time.monotonic() + TIMEOUT
    chooser = selectors.DefaultSelector()
    try:
        chooser.register(child.stdout, selectors.EVENT_READ, "out")
        chooser.register(child.stderr, selectors.EVENT_READ, "err")
        while chooser.get_map():
            left = deadline - time.monotonic()
            if left <= 0:
                raise subprocess.TimeoutExpired(git, TIMEOUT)
            for item, _ in chooser.select(left):
                chunk = os.read(item.fd, 65536)
                if not chunk:
                    chooser.unregister(item.fileobj)
                    continue
                seen[item.data] += chunk
                if len(seen[item.data]) > limits[item.data]:
                    raise _Excess(item.data)
        code = child.wait(timeout=max(deadline - time.monotonic(), 0.1))
    except subprocess.TimeoutExpired:
        raise IdentityError("git did not finish reading %s within %s seconds" % (key, TIMEOUT))
    except _Excess as exc:
        raise IdentityError("git wrote more than %d bytes %s while reading %s; the value of %s is longer than allowed"
                            % (limits[exc.args[0]], "of output" if exc.args[0] == "out" else "of messages", key, key))
    finally:
        if child.poll() is None:
            child.kill()
        chooser.close()
        child.stdout.close()
        child.stderr.close()
        child.wait()
    return code, bytes(seen["out"]), bytes(seen["err"])


def _value(git, home, key, how):
    code, out, err = _run(git, home, key)
    if code == 1 and not out and not err:
        raise IdentityError("the global git configuration has no %s; %s" % (key, how))
    if code != 0:
        said = _shown(err.decode("utf-8", "replace").strip().splitlines()[0]) if err.strip() else ""
        raise IdentityError("git could not read %s from the global configuration (exit %d)%s; is the file readable?"
                            % (key, code, ": " + said if said else ""))
    try:
        text = out.decode("utf-8")
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
