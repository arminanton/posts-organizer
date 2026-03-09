# Changelog

This changelog summarizes the major milestones and refinements applied across
all structured refactor steps, polish passes, and packaging improvements for
this project.

## Step 1 - Project skeleton and baseline

- Created the initial enterprise-style package layout under `src/`, `tests/`,
  and `docs/`
- Added `pyproject.toml`, `README.md`, `.env.example`, and initial developer
  scaffolding
- Introduced typed module stubs for domain, application, infrastructure, CLI,
  config, and utility layers
- Added the first unit/integration test scaffolding so the architecture could be
  validated early

## Step 2 - Domain layer extraction

- Implemented validated domain value objects and serialization helpers
- Added richer enums for routing, processing state, and classification
- Introduced a domain exception hierarchy
- Added protocol-style contracts to improve testability and dependency
  inversion
- Extracted pure domain services for title normalization, hashtag extraction,
  duplicate/routing policy, and recovery advice
- Updated repositories and tests to use domain models directly

## Step 3 - Infrastructure layer extraction

- Added the Gemini adapter with structured-output support and defensive JSON
  parsing
- Added atomic write utilities for durable file generation
- Added durable JSONL tracker and run-state repositories
- Implemented workspace management, output routing, and metadata scanning
  helpers
- Added a portable Instagram session manager and a thin Instaloader wrapper with
  injection points for tests
- Expanded infrastructure-focused unit and integration coverage

## Step 4 - Application runtime wiring

- Replaced stub orchestration with real application wiring
- Implemented the end-to-end `PostProcessor` use case for a single post
- Added recovery coordination to clean partial output and retry an unfinished
  shortcode before continuing normal processing
- Extracted index generation into its own service
- Moved post export logic into a dedicated infrastructure module
- Wired repositories, adapters, and services through a concrete CLI runtime
- Added tests for post processing, exporter behavior, recovery ordering, and
  runtime flow

## Step 5 - Operational CLI and configuration

- Added a real `argparse`-based CLI with operational subcommands
- Added settings loading from optional `.env` files plus CLI overrides
- Added redacted settings display for safe troubleshooting
- Added configuration validation with warnings and errors
- Added maintenance commands for run-state inspection/clearing and index
  rebuilding
- Expanded tests for parser behavior, maintenance workflows, validation, and
  command dispatch

## Step 6 - Documentation and test hardening

- Added `docs/architecture.md`, `docs/testing.md`, `docs/operations.md`, and
  `docs/recovery.md`
- Added shared pytest fixtures in `tests/conftest.py`
- Expanded CLI and maintenance coverage with additional unit/integration tests
- Added `CONTRIBUTING.md`, `CHANGELOG.md`, and a `Makefile` for developer
  workflows
- Improved archive cleanliness by excluding transient build/test artifacts

## Step 6.1 - Final polish pass

- Refreshed the packaged `build_summary.json`
- Added `python -m instagram_organizer` support via `__main__.py`
- Ensured `python -m instagram_organizer.cli.main` executes correctly
- Relaxed settings bootstrapping for maintenance/diagnostic commands so they can
  still run when runtime secrets are missing
- Added additional verification coverage, increasing the total passing test
  count to 57

## Documentation refresh

- Rewrote `README.md` to match the final layered architecture and current CLI
  behavior
- Documented the end-to-end execution flow, output structure, and developer
  workflow more clearly
- Aligned the README with the final project layout rather than earlier
  monolithic-script assumptions

## Repository hygiene pass

- Moved runtime-generated artifacts under `results/` to separate source from
  execution output
- Routed exported post folders to `results/library/`
- Routed trackers, indexes, run-state, and session storage to `results/state/`
- Routed logs to `results/logs/`
- Routed stable per-post workspaces to `results/workspaces/`
- Added a proper `.gitignore` so a first-time clone contains only required
  source files, configuration samples, and documentation
- Updated `README.md`, `docs/operations.md`, and `.env.example` to reflect the
  new runtime layout

## Packaging refresh

- Refreshed `CHANGELOG.md` to capture the full step-by-step evolution of the
  project instead of only the Step 6 summary
- Removed stray `.pytest_cache` content from the packaged archive during the
  changelog refresh
