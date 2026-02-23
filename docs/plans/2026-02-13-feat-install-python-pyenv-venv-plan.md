---
title: Install Python 3.12 via pyenv with venv
type: feat
date: 2026-02-13
---

# Install Python 3.12 via pyenv with venv

## Overview

Set up Python 3.12 using pyenv and create a project-local venv for the `voice-report` CLI. The project requires `>=3.10` (per `pyproject.toml`) but the system Python is 3.9.6.

## Current State

- **System Python:** 3.9.6 (`/usr/bin/python3`) — too old
- **pyenv:** not installed
- **Homebrew:** 5.0.11 — available
- **venv:** none exists
- **`.gitignore`:** already has `.venv/` and `venv/`

## Steps

### 1. Install pyenv via Homebrew

```bash
brew install pyenv
```

Add pyenv init to shell config (`~/.zshrc` on macOS):

```bash
# Add to ~/.zshrc
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

Reload shell:

```bash
source ~/.zshrc
```

### 2. Install Python 3.12

```bash
pyenv install 3.12
```

### 3. Pin Python version for this project

```bash
cd /Users/gen/Documents/docker/voice-report
pyenv local 3.12
```

This creates a `.python-version` file in the project root. Add it to `.gitignore` (or commit it — team preference).

### 4. Create venv

```bash
python -m venv .venv
```

### 5. Activate venv and install dependencies

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the project in editable mode with dev dependencies (pytest, ruff).

### 6. Verify

```bash
python --version          # Should show 3.12.x
which python              # Should point to .venv/bin/python
voice-report --help       # CLI should work
pytest                    # Tests should run
```

## Acceptance Criteria

- [x] pyenv installed and configured in shell
- [x] Python 3.12.x available via pyenv
- [x] `.python-version` file pins project to 3.12
- [x] `.venv/` created with Python 3.12
- [x] All project dependencies installed (`pip install -e ".[dev]"`)
- [x] `voice-report` CLI command works
- [x] Tests pass with `pytest` (no test files yet — empty tests/ dir)

## Context

- Every project uses venv (user convention)
- `.gitignore` already excludes `.venv/` — no changes needed
- `pyproject.toml` uses hatchling build system with `[project.scripts]` entry point
