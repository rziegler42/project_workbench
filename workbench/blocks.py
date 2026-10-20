"""Slot blocks in a Markdown file: a strict scanner and exact edits, over bytes.

The format is the one ``docs/specs/repository-boundary.md`` fixes and ``installplan`` writes::

    <!-- BEGIN <package>/<module> slot:<name> -->
    ...text...
    <!-- END <package>/<module> slot:<name> -->
    <!-- @slot: <name> -->

A filled slot keeps its marker line after the blocks. A line is a marker when it starts with one
of the three markers; a line that starts like one and is not exactly one is an error, so a
damaged or hostile file is refused and never guessed at. A CRLF at the end of a marker line is
accepted. Blocks this module writes end every line with a plain line feed, as the installer's do.

Nothing here touches a file. Every edit returns new bytes in which all bytes outside the changed
span are the input's bytes, and an edit that cannot be made exactly raises ``BlockError``.
"""

import collections
import re

_NAME = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_BEGIN = re.compile(rb"<!-- BEGIN (" + _NAME.encode() + rb"/" + _NAME.encode() + rb") slot:("
                    + _NAME.encode() + rb") -->")
_END = re.compile(rb"<!-- END (" + _NAME.encode() + rb"/" + _NAME.encode() + rb") slot:("
                  + _NAME.encode() + rb") -->")
_SLOT = re.compile(rb"<!-- @slot: (" + _NAME.encode() + rb") -->")
_ID = re.compile(r"\A" + _NAME + "/" + _NAME + r"\Z")
_SLOT_NAME = re.compile(r"\A" + _NAME + r"\Z")

_PREFIXES = (b"<!-- BEGIN ", b"<!-- END ", b"<!-- @slot:")

PRESENT = "present"    # the block is in the file
GONE = "gone"          # a recorded block whose markers are no longer in the file
OPEN = "open"          # not recorded, and the slot's marker line is in the file
ABSENT = "absent"      # not recorded, and the slot has no marker line in the file


class BlockError(ValueError):
    """The file or the requested edit is not exactly the format; nothing is changed."""


# `start` and `end` are byte offsets; `text` is the whole block, markers included, which is the
# text the manifest hashes; `body` is what lies between the markers.
Block = collections.namedtuple("Block", "id slot start end text body")
Marker = collections.namedtuple("Marker", "slot start end")
Scan = collections.namedtuple("Scan", "blocks markers")


def _lines(data):
    """Yield (start, end, content): `end` is after the line feed; `content` has neither the line
    feed nor a carriage return before it."""
    start = 0
    while start < len(data):
        feed = data.find(b"\n", start)
        end = len(data) if feed < 0 else feed + 1
        yield start, end, data[start:end].rstrip(b"\n").rstrip(b"\r") if feed >= 0 \
            else data[start:end]
        start = end


def _is_marker_line(content):
    return content.startswith(_PREFIXES)


def scan(data):
    """The blocks and the slot marker lines of `data`, in file order."""
    if not isinstance(data, bytes):
        raise BlockError("the file is not bytes")
    blocks, markers = [], []
    seen = set()
    open_ = None            # (id, slot, start, body_start) of the block being read
    for start, end, content in _lines(data):
        if not _is_marker_line(content):
            continue
        begin, finish, slot = _BEGIN.fullmatch(content), _END.fullmatch(content), \
            _SLOT.fullmatch(content)
        if not (begin or finish or slot):
            raise BlockError("a malformed marker at byte %d" % start)
        if begin:
            if open_ is not None:
                raise BlockError("a BEGIN at byte %d inside the block begun at byte %d"
                                 % (start, open_[2]))
            key = (begin.group(1), begin.group(2))
            if key in seen:
                raise BlockError("the block %s slot:%s is present twice"
                                 % (key[0].decode(), key[1].decode()))
            seen.add(key)
            open_ = (key[0], key[1], start, end)
        elif finish:
            if open_ is None:
                raise BlockError("an END at byte %d with no BEGIN" % start)
            if (finish.group(1), finish.group(2)) != open_[:2]:
                raise BlockError("the END at byte %d does not match the BEGIN at byte %d"
                                 % (start, open_[2]))
            blocks.append(Block(open_[0].decode(), open_[1].decode(), open_[2], end,
                                data[open_[2]:end], data[open_[3]:start]))
            open_ = None
        else:
            if open_ is not None:
                raise BlockError("a slot marker at byte %d inside the block begun at byte %d"
                                 % (start, open_[2]))
            markers.append(Marker(slot.group(1).decode(), start, end))
    if open_ is not None:
        raise BlockError("the block begun at byte %d has no END" % open_[2])
    return Scan(blocks, markers)


# --- exact edits -------------------------------------------------------------------------------


def _check_names(block_id, slot):
    if not isinstance(block_id, str) or not _ID.match(block_id):
        raise BlockError("not a block ID: %r" % (block_id,))
    _check_slot(slot)


def _check_slot(slot):
    if not isinstance(slot, str) or not _SLOT_NAME.match(slot):
        raise BlockError("not a slot name: %r" % (slot,))


def _check_text(text):
    if not isinstance(text, bytes):
        raise BlockError("the block text is not bytes")
    for _, _, content in _lines(text):
        if _is_marker_line(content):
            raise BlockError("the block text holds a slot or block marker line")


def _block(block_id, slot, text):
    _check_names(block_id, slot)
    _check_text(text)
    if text and not text.endswith(b"\n"):
        text += b"\n"
    return (b"<!-- BEGIN " + block_id.encode() + b" slot:" + slot.encode() + b" -->\n" + text
            + b"<!-- END " + block_id.encode() + b" slot:" + slot.encode() + b" -->\n")


def marker_line(slot):
    _check_slot(slot)
    return b"<!-- @slot: " + slot.encode() + b" -->\n"


def _one_marker(found, slot):
    mine = [m for m in found.markers if m.slot == slot]
    if len(mine) > 1:
        raise BlockError("the marker of slot %s is in the file %d times" % (slot, len(mine)))
    return mine[0] if mine else None


def _find(found, block_id, slot):
    return next((b for b in found.blocks if b.id == block_id and b.slot == slot), None)


def slot_state(data, slot, block_id, recorded=False):
    """Where a block stands in `data`: `present` when its BEGIN/END are there; otherwise `gone`
    when it is `recorded` as installed, else `open` when the slot's marker line is there (the
    block can be inserted) and `absent` when it is not (the block can be appended)."""
    _check_names(block_id, slot)
    found = scan(data)
    if _find(found, block_id, slot) is not None:
        return PRESENT
    if recorded:
        return GONE
    return OPEN if _one_marker(found, slot) is not None else ABSENT


def insert(data, filler, slot, text):
    """Put a new block for `filler` before the slot's marker line."""
    block = _block(filler, slot, text)
    found = scan(data)
    if _find(found, filler, slot) is not None:
        raise BlockError("%s already fills slot %s" % (filler, slot))
    marker = _one_marker(found, slot)
    if marker is None:
        raise BlockError("the slot %s has no marker line" % slot)
    return data[:marker.start] + block + data[marker.start:]


def replace(data, block_id, slot, text):
    """Replace the whole block `block_id` of `slot` with a block holding `text`."""
    block = _block(block_id, slot, text)
    found = scan(data)
    old = _find(found, block_id, slot)
    if old is None:
        raise BlockError("%s has no block in slot %s" % (block_id, slot))
    return data[:old.start] + block + data[old.end:]


def append(data, filler, slot, text):
    """Add the block and then the slot's marker line at the end of the file. Only for a slot with
    no marker line in the file; a file that does not end in a line feed gets one first."""
    block = _block(filler, slot, text)
    found = scan(data)
    if _find(found, filler, slot) is not None:
        raise BlockError("%s already fills slot %s" % (filler, slot))
    if _one_marker(found, slot) is not None:
        raise BlockError("the slot %s already has a marker line; insert into it" % slot)
    lead = b"\n" if data and not data.endswith(b"\n") else b""
    return data + lead + block + marker_line(slot)
