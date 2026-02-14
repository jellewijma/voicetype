# VoiceType - Agent Guidelines

This document provides guidelines for AI agents working on the VoiceType project.

## Project Overview

VoiceType is a local AI voice dictation tool for Linux, using faster-whisper for transcription. The codebase is a single Python script (`src/voicetype.py`) with a supporting configuration system.

## Build and Run Commands

### Environment Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the Application

```bash
python src/voicetype.py
# or
chmod +x src/voicetype.py && ./src/voicetype.py
```

### Development Tools Installation (Optional)

```bash
pip install black flake8 isort mypy pytest pytest-cov
```

## Development Commands

### Testing (No existing test suite)

```bash
pytest                           # run all tests
pytest tests/test_module.py      # specific test file
pytest tests/test_module.py::test_function_name  # single test
pytest --cov=src tests/          # with coverage
```

### Linting and Formatting

```bash
black src/ tests/                # format
black --check src/ tests/        # check only
isort src/ tests/                # sort imports
isort --check-only src/ tests/   # check only
flake8 src/ tests/               # lint
mypy src/ --ignore-missing-imports  # type check
```

## Code Style Guidelines

### General Principles

- Follow PEP 8.
- Use type hints for all function arguments and return values.
- Keep functions focused and single‑purpose.
- Avoid global variables; use class attributes or configuration objects.

### Imports

Group imports: standard library, third‑party, local (none). Separate groups with a blank line. Use absolute imports; avoid wildcard imports. Import only what is needed.

### Naming Conventions

- **Classes**: `PascalCase`
- **Functions / methods**: `snake_case`
- **Variables / attributes**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: prefix with `_` (e.g., `_private_method`)

### Type Annotations

- Use Python 3.10+ style type hints.
- Annotate all function parameters and return types.
- Use `Optional[T]` for values that can be `None`.
- Use `Union` or the `|` operator for union types.
- Leverage `dataclass` for configuration and data‑holding classes.

### Error Handling

- Avoid bare `except:` clauses. Catch specific exceptions.
- Log errors appropriately (currently uses `print`; consider `logging` for production).
- Handle recoverable errors gracefully; raise appropriate exceptions for fatal errors.

### String Formatting

- Use f‑strings for most cases.
- For complex formatting, use `str.format()`.
- Avoid `%`‑formatting.

### Documentation

- Provide a module‑level docstring at the top of each file.
- Document public classes and functions with a brief one‑line description.
- Use inline comments sparingly; prefer clear code.
- Update the `README.md` when adding features or changing behavior.

### File and Directory Structure

- Main application: `src/voicetype.py`.
- Configuration: `config/` → `~/.config/voicetype/`.
- Assets: `assets/`.
- Tests (if added): `tests/` mirroring source structure.

## Git Conventions

### Commit Messages
- Use concise, descriptive, imperative mood ("Add feature", "Fix bug", "Update docs").
- Reference issues or pull requests when applicable.
- Keep commits focused; avoid unrelated changes.

### Workflow for Adding Changes
When making changes to the codebase, follow this workflow:

1. **Check current status** before starting:
   ```bash
   git status
   git diff
   ```

2. **Stage changes** for commit:
   ```bash
   # Stage specific files
   git add path/to/file1.py path/to/file2.py
   
   # Stage all modified files
   git add .
   
   # Stage all files (modified, new, deleted)
   git add -A
   ```

3. **Review staged changes** before committing:
   ```bash
   git diff --cached
   git status
   ```

4. **Create commit** with descriptive message:
   ```bash
   git commit -m "Brief summary of changes"
   
   # For multi-line commit messages
   git commit -m "Summary line
   
   Detailed description of changes:
   - Added feature X
   - Fixed bug Y
   - Updated documentation"
   ```

5. **Push to remote repository** (if you have permission):
   ```bash
   git push
   
   # Push to specific branch
   git push origin branch-name
   ```

6. **Verify** the commit was successful:
   ```bash
   git log --oneline -5
   git status
   ```

### Testing Before Committing
Always run tests before committing changes:
```bash
# Run test suite
python run_tests.py

# Run specific tests
python test_initialization.py
python smoke_test.py
```

### Common Git Commands
```bash
# View commit history
git log --oneline -10

# View changes between commits
git diff HEAD~1 HEAD

# Undo local changes (dangerous!)
git checkout -- path/to/file

# Unstage files
git reset HEAD path/to/file

# Create new branch
git checkout -b feature-branch-name

# Merge branches
git merge feature-branch-name
```

## Cursor / Copilot Rules

No project‑specific Cursor (`.cursor/rules/`) or Copilot (`.github/copilot-instructions.md`) rules are currently defined. Agents should follow the guidelines in this document.

## Additional Notes

- Targets **Arch Linux**; uses system packages (python‑pyaudio, portaudio, xdotool, etc.). Ensure compatibility with other distributions if changes are made.
- GPU acceleration relies on CUDA for NVIDIA GPUs. Fallback to CPU mode if CUDA is unavailable.
- Hotkey handling depends on Hyprland socket communication; consider alternative window managers if extending support.
- System tray uses `pystray` and GTK3. Keep UI changes minimal and consistent with existing style.

---

*Last updated: 2026‑02‑14*