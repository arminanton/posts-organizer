from instagram_organizer.cli.parser import cli_overrides_from_args, parse_args


def test_parse_args_defaults_to_run_command() -> None:
    args = parse_args([])
    assert args.command == 'run'


def test_cli_overrides_are_mapped_from_arguments() -> None:
    args = parse_args([
        '--base-dir', '/tmp/project',
        '--target-account', 'target',
        '--max-ai-images', '5',
        'validate-config',
    ])
    overrides = cli_overrides_from_args(args)
    assert overrides['BASE_DIR'] == '/tmp/project'
    assert overrides['TARGET_ACCOUNT'] == 'target'
    assert overrides['MAX_AI_IMAGES'] == '5'
