"""Entry point for ``python3 -m workbench``."""

import sys

USAGE = "usage: python3 -m workbench <command> [options]\n"


def main(argv):
    sys.stderr.write(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
