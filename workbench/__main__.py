"""Entry point for ``python3 -m workbench``."""

import sys

from . import cli


def main(argv):
    return cli.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
