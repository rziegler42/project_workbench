"""The one refusal every planning step raises, below ``preview``, ``attach`` and ``harnessstage``
so none of them imports another to name it."""


class Refused(Exception):
    """The command would be refused. ``lines`` are the reasons, already cleaned, each printed as
    ``refused: ...``; `after` is printed below them as it is, indented."""

    def __init__(self, lines, after=()):
        Exception.__init__(self, "; ".join(lines))
        self.lines = [lines] if isinstance(lines, str) else list(lines)
        self.after = list(after)
