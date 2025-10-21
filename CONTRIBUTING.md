# Contributing to Risk Monitor

## Development Environment

### Prerequisites
- **Python**: 3.13+
- **uv**: Fast Python package manager
- **Docker**: For integration testing

### Setup
```bash
# Create virtual environment
uv venv

# Activate environment
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Workflow

### 1. Branch Creation
**Branch Naming Convention**: `type/epic-XXX-9999-milestone-description`

Examples:
- `feature/epic-TSE-0001-foundation-add-grpc-health-check`
- `fix/epic-TSE-0002-trading-fix-risk-calculation`
- `chore/epic-TSE-0001-foundation-update-dependencies`

### 2. Development
**Before committing**:
1. Run tests: `pytest tests/ -v`
2. Run linting: `ruff check src/ tests/`
3. Run type checking: `mypy src/`
4. Update TODO.md if working on milestone tasks

### 3. Commit Messages
Follow conventional commits with epic tracking:

```
type(epic-XXX/milestone): description

Detailed explanation if needed

Milestone: Milestone Name
Behavior: What this enables
```

## Code Standards

### Clean Architecture Rules
1. **Domain Layer**: NO external dependencies (pure Python)
2. **Application Layer**: Depends on domain only
3. **Infrastructure Layer**: Implements ports from domain

### Testing Requirements
- Minimum 30% test coverage
- Unit tests for domain logic
- Integration tests for external dependencies
- Use pytest fixtures for test data

### Python-Specific Standards
- Type hints for all functions
- Pydantic models for data validation
- Async/await for I/O operations
- Follow PEP 8 style guide

## Pull Requests

Before creating PR:
1. ✅ All tests passing (pytest)
2. ✅ Linting clean (ruff)
3. ✅ Type checking passing (mypy)
4. ✅ PR documentation created in `docs/prs/`
5. ✅ TODO.md updated
6. ✅ No markdown linting errors

See git_workflow_checklist skill for full PR requirements.

## Questions?

Check project documentation:
- Architecture: `.claude/.claude_architecture.md`
- Python Standards: `.claude/.claude_python.md`
- Testing: `.claude/.claude_testing_python.md`
