"""Strict JSON for a document a helper does not trust: an object with no repeated key, no fraction,
exponent or constant such as ``NaN``, valid Unicode throughout, bounded in size and in depth.

The installer reads declarations with this; a helper that reads a project's JSON uses the same rules.
"""

import json

MAX_DEPTH = 32


def _no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError("duplicate key")  # the key is the file's text, so it is not repeated
        seen[key] = value
    return seen


def _refuse_constant(text):
    raise ValueError("%s is not allowed" % text)


def _refuse_float(text):
    raise ValueError("numbers with a fraction or exponent are not allowed: %s" % text[:40])


def parse_object(data, limit):
    """Parse `data` (bytes of at most `limit`) into a JSON object; raise ValueError with a reason."""
    if len(data) > limit:
        raise ValueError("larger than %d bytes" % limit)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("not valid UTF-8")
    try:
        value = json.loads(text, object_pairs_hook=_no_duplicates,
                           parse_constant=_refuse_constant, parse_float=_refuse_float)
    except RecursionError:
        raise ValueError("nested too deeply")
    except json.JSONDecodeError as exc:
        raise ValueError("not valid JSON (%s)" % exc.msg)
    if not isinstance(value, dict):
        raise ValueError("the top level must be an object")
    _check_depth(value)
    return value


def _check_text(item):
    # A lone surrogate is valid JSON but cannot be encoded, hashed or printed.
    if isinstance(item, str):
        try:
            item.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("a string is not valid Unicode (lone surrogate)")


def _check_depth(value):
    # Iterative, so a hostile document cannot exhaust the stack here.
    stack = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if isinstance(item, (dict, list)):
            if depth > MAX_DEPTH:
                raise ValueError("nested deeper than %d levels" % MAX_DEPTH)
            if isinstance(item, dict):
                for key in item:
                    _check_text(key)
                children = item.values()
            else:
                children = item
            stack.extend((child, depth + 1) for child in children)
        else:
            _check_text(item)
