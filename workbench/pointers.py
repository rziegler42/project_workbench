"""The paths a Markdown document links to, includes or imports.

The tracked-pointer rule (``repository-boundary.md``) forbids a tracked document from depending on
an untracked file by path: a link, an include or an import. A plain mention of a path is allowed,
and source code is not inspected. So this reads only Markdown, ignores fenced and inline code,
and reports only what a reader or an agent would follow:

* an inline link or image, ``[text](target)``;
* a reference definition, ``[id]: target``;
* an HTML ``href`` or ``src``;
* an import, ``@path`` (the form ``CLAUDE.md`` uses), where the path has a ``/`` or an extension.

The text is untrusted. Every pattern is linear, and the number of references taken from one
document is bounded.
"""

import posixpath
import re
import urllib.parse

MAX_REFERENCES = 2000
# Every bracketed form is bounded: an unterminated one would otherwise rescan its line each time.

OUTSIDE = "outside"

# The lookahead after the run of fence characters keeps the pattern from retrying shorter runs, which
# would make a long line of backticks quadratic.
_FENCE = re.compile(r"^[ ]{0,3}(`{3,}(?!`)|~{3,}(?!~))[^\n]*\n.*?(?:^[ ]{0,3}\1[`~]*[ \t]*$|\Z)",
                    re.S | re.M)
_CODE = re.compile(r"`[^`\n]*`")
_INLINE = re.compile(r"\]\(\s*(?:<([^>\n]{0,256})>|([^\s()]*))")
_DEFINITION = re.compile(r"^[ ]{0,3}\[[^\]\n]{1,2048}\]:[ \t]*(?:<([^>\n]{0,256})>|(\S+))", re.M)
_ATTRIBUTE = re.compile(r"""\b(?:href|src)\s*=\s*(?:"([^"\n]{0,2048})"|'([^'\n]{0,2048})')""", re.I)
_IMPORT = re.compile(r"(?<![\w@/.:-])@([A-Za-z_~./][\w./~+-]*)")
_SCHEME = re.compile(r"\A[A-Za-z][A-Za-z0-9+.-]*:")
_EXTENSION = re.compile(r"\.[A-Za-z]")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def references(text):
    """``[(raw target, is_import)]`` for `text`, in order of appearance, at most
    ``MAX_REFERENCES`` of them. Code is ignored."""
    text = _CODE.sub(" ", _FENCE.sub("\n", text))
    found = []
    for pattern in (_INLINE, _DEFINITION, _ATTRIBUTE):
        for match in pattern.finditer(text):
            target = next((group for group in match.groups() if group), None)
            if target is not None:
                found.append((match.start(), target, False))
    for match in _IMPORT.finditer(text):
        token = match.group(1).rstrip(".,;:")
        if token and ("/" in token or _EXTENSION.search(token)):
            found.append((match.start(), token, True))
    found.sort(key=lambda item: item[0])
    return [(target, is_import) for _, target, is_import in found[:MAX_REFERENCES]]


def target_of(document, raw, is_import):
    """The project-relative path a reference means, ``OUTSIDE`` when it leaves the project, or
    None when it is not a path (a URL, an anchor, an empty target).

    `document` is the project-relative path of the document holding the reference. A link that
    starts with ``/`` is relative to the project, as a forge reads it; an import that starts with
    ``/`` or ``~`` names a file of the machine."""
    text = raw.strip()
    if not text or text.startswith(("#", "//")) or _SCHEME.match(text):
        return None
    text = text.split("#", 1)[0].split("?", 1)[0]
    text = urllib.parse.unquote(text)
    if not text or _CONTROL.search(text) or "\\" in text:
        return None
    if is_import and text.startswith(("/", "~")):
        return OUTSIDE
    if text.startswith("/"):
        base, text = "", text.lstrip("/")
    else:
        base = posixpath.dirname(document)
    joined = posixpath.normpath(posixpath.join(base, text))
    if joined == ".":
        return None
    if joined == ".." or joined.startswith("../"):
        return OUTSIDE
    return joined
