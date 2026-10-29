"""PanLigra command-line entry point.

The historical PanLigra.py entry point is intentionally preserved for
backward compatibility with existing workflows and scripts.
"""

from PanLigra_cli import main, parse_args


if __name__ == "__main__":
    main(parse_args())
