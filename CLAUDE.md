# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

[TODO: Add project description and purpose]

## Development Commands

### Setup
```bash
[TODO: Add setup/installation commands]
```

### Build
```bash
[TODO: Add build commands]
```

### Testing
```bash
# Run all tests
[TODO: Add test command]

# Run a single test
[TODO: Add single test command]
```

### Linting
```bash
[TODO: Add linting commands]
```

## Architecture

[TODO: Describe high-level architecture, key design patterns, and how major components interact]

## Key Conventions

[TODO: Add important coding conventions, naming patterns, or architectural decisions specific to this codebase]
### Git version control

- Always use the conventional commits convention for git commits
- Do not mention co-authorship by Claude or tool use in commit messages
- Analyze commits and suggest semantic version updates (e.g., 1.0.1 → 1.0.2 for patches, 1.1.3 → 1.2.0 for features, 2.0.0 → 3.0.0 for breaking changes)
- When a version update is appropriate:
  - Update version numbers in all relevant files (package.json, pyproject.toml, __version__, etc.)
  - Create a git tag with the version number after committing
- Ensure the README is updated before committing when:
  - User-facing changes occur (new features, API changes, usage modifications)
  - Architecture or structure changes meaningfully (e.g., switching from NGINX to Apache)
