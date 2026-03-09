# Contributing

## Local setup

```bash
python -m pip install -e .[dev]
```

## Before opening a change

```bash
pytest
python -m compileall src
```

## Coding guidelines

- Keep modules focused and reasonably small
- Prefer typed public APIs
- Add or update tests with every behavioral change
- Document public functions and tricky recovery logic
- Preserve the layering boundaries described in `docs/architecture.md`
