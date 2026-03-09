# Architecture Overview

The project follows a layered architecture:

- `domain/`: pure business concepts, policies, and contracts
- `application/`: orchestration of use cases and recovery flow
- `infrastructure/`: adapters for Gemini, Instaloader, persistence, and filesystem
- `cli/`: command-line parsing and dispatch
- `config/`: settings, logging, and validation

## Design goals

- Keep side effects at the edges
- Prefer explicit dependencies over hidden globals
- Make recovery deterministic and testable
- Allow adapters to be swapped without changing core policy code
- Keep modules small enough to read and review quickly

## Dependency direction

The dependency direction is intentionally inward:

- CLI depends on application/config
- application depends on domain and infrastructure contracts
- infrastructure depends on domain models and protocols
- domain depends on nothing outside the standard library

This helps preserve testability and avoids circular imports.
