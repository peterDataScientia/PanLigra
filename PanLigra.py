"""PanLigra command-line entry point.

The historical PanViz.py entry point is intentionally preserved for
backward compatibility with existing workflows and scripts.
"""

from PanViz import main, parse_args


if __name__ == "__main__":
    main(parse_args())
