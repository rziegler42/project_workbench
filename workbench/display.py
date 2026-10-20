"""Text shown to a person. Anything read from disk or from a package goes through here."""

import unicodedata

# Characters that print as nothing or as a blank but are not caught by ``isprintable``.
_BLANK_FILLERS = "ᅟᅠㅤﾠ͏᠎"
_HIDDEN_CATEGORIES = ("Cf", "Mn", "Me", "Zs", "Zl", "Zp", "Cc", "Cs", "Co", "Cn")


def _visible(char):
    if char == " ":
        return True
    if not char.isprintable() or char in _BLANK_FILLERS:
        return False
    return unicodedata.category(char) not in _HIDDEN_CATEGORIES


def _escape(char):
    if not char.isprintable():
        return repr(char)[1:-1]
    code = ord(char)
    return "\\u%04x" % code if code <= 0xFFFF else "\\U%08x" % code


def clean(text):
    """Escape control and invisible characters so nothing read from disk can steer the
    terminal or hide in the text.

    A newline, an escape sequence, a bidirectional override, a zero-width or combining
    character, a non-breaking space and other characters that print as nothing become visible
    escapes such as ``\\n``, ``\\x1b`` or ``\\u200b``. Ordinary letters, digits and
    punctuation, including non-ASCII ones, are kept.
    """
    return "".join(c if _visible(c) else _escape(c) for c in str(text))


def ascii_text(text):
    """Like `clean`, and every non-ASCII character is shown as an escape.

    Used where a lookalike letter would mislead, such as a path the owner is asked to
    approve: ``bin/r\\u0443n`` cannot pass for ``bin/run``.
    """
    return "".join(c if " " <= c <= "~" else _escape(c) for c in str(text))
