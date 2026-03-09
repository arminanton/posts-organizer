"""Console script entrypoint.

The ``main`` function keeps argument parsing, configuration loading, and exit
behavior close to the process boundary while delegating business logic to the
application and infrastructure layers.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from instagram_organizer.cli.commands import dispatch
from instagram_organizer.cli.parser import cli_overrides_from_args, parse_args
from instagram_organizer.config.logging_config import configure_logging
from instagram_organizer.config.settings import AppSettings


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line application.

    Args:
        argv: Optional command-line arguments. When omitted, ``sys.argv`` is used.

    Returns:
        Process exit code. Zero indicates success.
    """

    args = parse_args(argv)
    command = getattr(args, 'command', 'run') or 'run'
    strict = command == 'run'

    try:
        settings = AppSettings.from_sources(
            env_file=args.env_file,
            overrides=cli_overrides_from_args(args),
            strict=strict,
        )
    except ValueError as exc:
        print(f'[!] {exc}', file=sys.stderr)
        return 1

    configure_logging(settings.logging)
    return dispatch(args, settings)


if __name__ == '__main__':
    raise SystemExit(main())
