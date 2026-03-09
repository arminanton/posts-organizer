# Operations Guide

## Common commands

```bash
instagram-organizer validate-config
instagram-organizer show-settings
instagram-organizer show-run-state
instagram-organizer clear-run-state
instagram-organizer rebuild-indexes
instagram-organizer run
```

## Recommended operator flow

1. Validate configuration
2. Review redacted settings output
3. Inspect run state if the prior run stopped unexpectedly
4. Rebuild indexes if tracker files were restored manually
5. Start a new run

## Safety notes

- Trackers are append-oriented and rewritten into de-duplicated canonical form
- Run-state exists to recover unfinished work, not to replace trackers
- Rebuilding indexes does not contact Instagram or Gemini


## Runtime output layout

By default, the application writes all generated runtime artifacts beneath
`results/` so the repository root stays clean:

- `results/library/` for exported post folders
- `results/state/` for trackers, indexes, run-state, and session files
- `results/logs/` for application logs
- `results/workspaces/` for stable per-post workspaces during execution
