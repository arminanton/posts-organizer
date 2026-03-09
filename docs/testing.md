# Testing Guide

## Test layers

- `tests/unit/`: fast tests for pure logic and thin adapters
- `tests/integration/`: narrow end-to-end flows using temporary directories and test doubles

## Running tests

```bash
pytest
```

Run a subset:

```bash
pytest tests/unit -q
pytest tests/integration -q
```

## Fixture strategy

Common fixtures live in `tests/conftest.py` so new tests can reuse sample
settings, temporary project layouts, and fake post records.

## Principles

- Prefer fakes over broad mocks when behavior matters
- Test observable behavior, not implementation details
- Keep integration tests file-system based and deterministic
