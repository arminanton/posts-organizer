"""Module execution entrypoint for ``python -m instagram_organizer``."""

from __future__ import annotations

from instagram_organizer.cli.main import main


if __name__ == '__main__':
    raise SystemExit(main())
