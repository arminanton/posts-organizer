# Recovery Semantics

Recovery is intentionally split into two concepts:

- Completed work is discovered from tracker repositories
- In-progress work is described by run-state

## Completed posts

A post is considered completed only after it has been exported and persisted to a
tracker. On restart, completed shortcodes are skipped in O(1) time via a set.

## In-progress post

When a run stops mid-post, run-state records the shortcode and stage. The
application can inspect that state, retry the unfinished shortcode first, and
clean any partial output folder before retrying.

## Why this split matters

Trackers provide durable idempotency. Run-state provides operator visibility and
unfinished-work prioritization.
