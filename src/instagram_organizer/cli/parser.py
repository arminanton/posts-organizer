"""Argument parser construction for the CLI.

The parser layer is intentionally separate from dispatch logic so tests can
validate argument behavior without instantiating the runtime.
"""

from __future__ import annotations

import argparse
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence


def create_parser() -> ArgumentParser:
    """Create the top-level argument parser.

    Returns:
        Configured parser for the console application.
    """

    parser = argparse.ArgumentParser(prog='instagram-organizer')
    parser.add_argument('--env-file', help='Optional path to a dotenv file.', default=None)
    parser.add_argument('--base-dir', help='Override BASE_DIR.', default=None)
    parser.add_argument('--target-account', help='Override TARGET_ACCOUNT.', default=None)
    parser.add_argument('--gemini-model', help='Override GEMINI_MODEL.', default=None)
    parser.add_argument('--max-ai-images', help='Override MAX_AI_IMAGES.', default=None)
    parser.add_argument('--log-level', help='Override LOG_LEVEL.', default=None)

    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('run', help='Run the Instagram organizer pipeline.')

    validate = subparsers.add_parser('validate-config', help='Validate resolved configuration.')
    validate.add_argument('--json', action='store_true', help='Print validation report as JSON.')

    subparsers.add_parser('show-settings', help='Show resolved settings with secrets redacted.')

    show_state = subparsers.add_parser('show-run-state', help='Show saved recovery state.')
    show_state.add_argument('--json', action='store_true', help='Print the saved state as JSON.')

    subparsers.add_parser('clear-run-state', help='Delete any saved recovery state.')
    subparsers.add_parser('rebuild-indexes', help='Rebuild indexes from tracker files.')
    return parser


def parse_args(argv: Sequence[str] | None = None) -> Namespace:
    """Parse command-line arguments.

    When no subcommand is provided, the parser defaults to ``run``.
    """

    parser = create_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not getattr(args, 'command', None):
        args.command = 'run'
    return args


def cli_overrides_from_args(args: Namespace) -> dict[str, str]:
    """Build environment-style overrides from parsed CLI arguments."""

    overrides: dict[str, str] = {}
    mapping = {
        'BASE_DIR': getattr(args, 'base_dir', None),
        'TARGET_ACCOUNT': getattr(args, 'target_account', None),
        'GEMINI_MODEL': getattr(args, 'gemini_model', None),
        'MAX_AI_IMAGES': getattr(args, 'max_ai_images', None),
        'LOG_LEVEL': getattr(args, 'log_level', None),
    }
    for key, value in mapping.items():
        if value is not None:
            overrides[key] = str(value)
    return overrides
