# Instagram Organizer

An enterprise-style Python application that downloads Instagram posts, analyzes
image-based educational carousel content with Gemini, and organizes the results
into a durable, restart-safe local library.

This project is the fully refactored version of the original one-file scraper.
It now uses a layered architecture, typed models, explicit recovery semantics,
portable session handling, structured AI output, and a tested CLI.

## What the project does

Given a target Instagram account, the application can:

- fetch posts from the account through Instaloader
- download the post media into a stable workspace
- analyze image posts and mixed carousel posts with Gemini
- generate a normalized title for the whole post
- detect duplicates by normalized title
- route output into organized, duplicate, or manual-review folders
- unpack Instaloader metadata into readable JSON
- write sidecar files such as notes, hashtags, AI analysis, and engagement
- maintain durable tracker files so completed posts are skipped on future runs
- persist run-state so interrupted work can be retried cleanly on the next run
- rebuild summary indexes without contacting Instagram or Gemini

## Main capabilities

### AI-assisted post understanding

For image and mixed-media posts, the Gemini adapter requests structured JSON and
captures:

- per-image analysis
- OCR summary
- dominant signal classification
- combined post analysis
- final title

The final title is used for routing and folder naming. The detailed AI payload is
also stored on disk for later inspection and reuse.

### Recovery and idempotency

The application intentionally separates completed work from in-progress work:

- `progress.jsonl` and `duplicates_progress.jsonl` track successfully completed posts
- `run_state.json` tracks the last interrupted post and the step where it stopped

On restart, the application:

- skips already completed shortcodes in O(1) time using sets
- retries the previously interrupted shortcode first when appropriate
- cleans partial output folders before retrying
- can reuse the existing workspace for the interrupted shortcode when safe

### Organized filesystem output

The project writes runtime output under the configured `BASE_DIR`, but keeps it
separated from source files by using a dedicated `results/` tree by default.

Typical runtime folders and files include:

- `results/library/Organized_Posts/`
- `results/library/Needs_Manual_Naming/`
- `results/library/Duplicates/`
- `results/workspaces/`
- `results/state/progress.jsonl`
- `results/state/duplicates_progress.jsonl`
- `results/state/run_state.json`
- `results/state/master_index.txt`
- `results/state/master_index.json`
- `results/state/master_duplicates_index.txt`
- `results/state/master_duplicates_index.json`
- `results/state/.ig_session`
- `results/logs/app.log`
- `results/logs/error.log`

Each processed post folder can contain:

- downloaded media files
- `metadata/` with unpacked Instaloader JSON
- `notes.txt`
- `hashtags.txt`
- `engagement.txt`
- `ai_analysis.txt`
- `ai_analysis.json`

## Architecture

The codebase follows a layered architecture so side effects stay at the edges
and policy logic stays testable.

```text
src/instagram_organizer/
  cli/              # Argument parsing and command dispatch
  config/           # Typed settings, logging, validation
  domain/           # Pure models, enums, protocols, policies
  application/      # Use-case orchestration and recovery behavior
  infrastructure/   # Gemini, Instaloader, filesystem, persistence adapters
  utils/            # Shared utility helpers
```

More detail is available in:

- `docs/architecture.md`
- `docs/operations.md`
- `docs/recovery.md`
- `docs/testing.md`

## Requirements

- Python 3.11 or newer
- A Gemini API key
- Optional Instagram login session for more reliable access to rate-sensitive flows, managed directly by the project CLI

## Installation

Create a virtual environment, then install the package in editable mode.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## Configuration

Copy `.env.example` to `.env`, then update the values you actually need.
The CLI automatically loads `./.env` from the current working directory when it exists. Use `--env-file` to point to a different dotenv file.

```bash
cp .env.example .env
```

### Required runtime settings

These are required for the `run` command:

- `GEMINI_API_KEY`
- `TARGET_ACCOUNT`

### Common optional settings

These are the current settings directly consumed by the final application build:

- `GEMINI_MODEL` - defaults to `gemini-1.5-flash`
- `BASE_DIR` - project root used to resolve runtime paths, defaults to `.`
- `RESULTS_DIR` - runtime output root relative to `BASE_DIR`, defaults to `results`
- `IG_USERNAME` - Instagram username for loading a saved session
- `IG_SESSION_FILE` - session file path relative to `RESULTS_DIR`, defaults to `state/.ig_session`
- `MAX_AI_IMAGES` - maximum number of images considered per post, defaults to `10`
- `GEMINI_INLINE_MAX_BYTES` - safe inline-request byte ceiling, defaults to `18000000`
- `GEMINI_USE_FILES_API` - when `true`, oversized payloads switch to the Gemini Files API
- `GEMINI_USE_BATCH_FALLBACK` - when `true`, oversized payloads can fall back to ordered batch analysis plus final synthesis if the Files API path fails
- `LOG_LEVEL` - logging level, defaults to `INFO`
- `APP_LOG_FILE` - log path relative to `RESULTS_DIR`, defaults to `logs/app.log`
- `ERROR_LOG_FILE` - log path relative to `RESULTS_DIR`, defaults to `logs/error.log`

### Session setup

If you want to reuse an Instagram login session, set `IG_USERNAME` and then use the built-in CLI login command. The project stores a portable session snapshot at the configured `IG_SESSION_FILE` path.

Example:

```bash
instagram-organizer login
```

The command prompts securely for the Instagram password and saves the session file under the runtime `results/state/` tree by default.

## Quick start

Validate configuration first:

```bash
instagram-organizer validate-config
```

Or with an explicit alternate dotenv file:

```bash
instagram-organizer --env-file .env.prod validate-config
```

Review effective settings with secrets redacted:

```bash
instagram-organizer show-settings
```

Run the main pipeline:

```bash
instagram-organizer run
```

You can also run it as a module:

```bash
python -m instagram_organizer run
```

Or inspect help:

```bash
instagram-organizer --help
python -m instagram_organizer --help
```

## CLI commands

The project ships with a multi-command CLI.

```bash
instagram-organizer run
instagram-organizer login
instagram-organizer session-status
instagram-organizer logout
instagram-organizer validate-config
instagram-organizer show-settings
instagram-organizer show-run-state
instagram-organizer clear-run-state
instagram-organizer rebuild-indexes
```

### `run`

Runs the full download, analysis, routing, persistence, and indexing pipeline.
This command requires runtime-critical settings such as `GEMINI_API_KEY` and
`TARGET_ACCOUNT`.

### `login`

Prompts securely for the Instagram password, authenticates through Instaloader,
and saves a portable session file to the configured `IG_SESSION_FILE` path.

### `session-status`

Shows whether the local Instagram session file exists and prints basic file
metadata such as size and modification time.

### `logout`

Deletes the saved local Instagram session file. This does not affect the
Instagram account itself; it only removes the portable session snapshot used by
the project.

### `validate-config`

Validates the resolved configuration and prints any warnings or errors.

```bash
instagram-organizer validate-config
instagram-organizer validate-config --json
```

### `show-settings`

Prints the effective settings with sensitive values redacted.

### `show-run-state`

Shows the persisted recovery state from a previously interrupted run.

```bash
instagram-organizer show-run-state
instagram-organizer show-run-state --json
```

### `clear-run-state`

Deletes any persisted recovery state. This does not delete tracker files.

### `rebuild-indexes`

Rebuilds summary index files from tracker repositories only. This command does
not contact Instagram or Gemini.

## CLI overrides

Several settings can be overridden at execution time:

```bash
instagram-organizer \
  --env-file .env \
  --base-dir ./output \
  --target-account some_account \
  --gemini-model gemini-1.5-flash \
  --max-ai-images 10 \
  --log-level INFO \
  run
```

Supported CLI override flags:

- `--env-file`
- `--base-dir`
- `--target-account`
- `--gemini-model`
- `--max-ai-images`
- `--log-level`

## How a run works

At a high level, a normal run performs these steps:

1. Load and validate settings
2. Configure logging
3. Load prior trackers and seed duplicate detection
4. Load recovery state and clean partial output if needed
5. Fetch the target Instagram profile
6. Iterate posts, retrying the unfinished shortcode first when applicable
7. Download one post into a stable per-post workspace
8. Classify the media as image, mixed, or video
9. Analyze image or mixed posts with Gemini using the best available transport strategy:
   - inline image parts when the estimated request stays below the safe byte threshold
   - Files API when the combined payload is larger than the inline threshold
   - ordered inline batches plus final synthesis if the Files API path fails
10. Route the result into organized, duplicate, or manual-review output
11. Export media and metadata into the final folder
12. Persist tracker records and rebuild indexes
13. Save the session snapshot at the end of the run

## Output categories

The routing policy sends processed posts into one of three categories:

- `organized` - normal successful organization
- `duplicate` - title normalized to a topic that was already seen
- `manual_review` - the post could not be confidently titled or was treated as manual/video output

## Recovery model

The project is designed to recover cleanly from mid-process interruptions.

### Completed posts

A post is only considered completed after it has been exported and written to a
tracker repository. After that, future runs skip it.

### Interrupted posts

If a run stops mid-post, `run_state.json` records information such as:

- shortcode
- processing step
- workspace path
- partial output path
- feed progress position

On the next run, the application can:

- prioritize the interrupted shortcode first
- reuse the existing workspace if it still exists
- delete partially written output before retrying

## Testing

Run the full test suite:

```bash
pytest
```

Run only unit tests:

```bash
pytest tests/unit -q
```

Run only integration tests:

```bash
pytest tests/integration -q
```

The final package was verified with passing `compileall` and `pytest` runs.

## Development helpers

A `Makefile` is included for common local tasks. Exact targets may evolve, but
it is intended to support common developer workflows such as test runs and local
quality checks.

## Limitations and notes

- The quality of AI-generated titles depends on the quality and clarity of the images
- Pure video posts are not image-analyzed and are routed as `VIDEO_POST`
- Large image sets are handled with a transport strategy that prefers inline analysis, then switches to the Gemini Files API, then falls back to ordered batch analysis plus final synthesis if needed
- Uploaded Gemini Files API assets are deleted after use on a best-effort basis when that API path is taken
- Instagram access behavior depends on the target account, session validity, and external platform constraints
- `validate-config` correctly returns a non-zero exit code when required runtime secrets are missing

## Related documentation

- `docs/architecture.md`
- `docs/operations.md`
- `docs/recovery.md`
- `docs/testing.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`

## License / ownership

GLP-3.0
