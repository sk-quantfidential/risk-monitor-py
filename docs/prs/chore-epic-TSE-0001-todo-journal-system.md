# chore(epic-TSE-0001): standardize git quality standards and documentation

## Summary

This PR standardizes the git quality standards infrastructure in risk-monitor-py by adding validation scripts, GitHub Actions workflows, and markdown linting configuration. It also archives completed milestones from TODO.md to TODO-HISTORY.md as part of the TODO journal system implementation.

**Key Changes:**

- Added git quality standards scripts (validate-all.sh, pre-push-hook.sh, create-pr.sh)
- Added GitHub Actions workflows for automated PR validation
- Configured markdownlint for consistent documentation formatting
- Archived completed milestones to TODO-HISTORY.md
- Updated TODO.md with Git Quality Standards completion milestone

## What Changed

### Git Quality Standards Scripts

**New Scripts Added:**

- `scripts/validate-all.sh` - Comprehensive validation script checking branch names, PR documentation, markdown linting
- `scripts/pre-push-hook.sh` - Git pre-push hook for enforcing quality standards
- `scripts/create-pr.sh` - Helper script for creating properly formatted PRs
- `scripts/install-git-hooks.sh` - Automated installation of git hooks
- `scripts/README.md` - Documentation for all scripts

**Removed:**

- `scripts/validate_tse_0001_3c.py` - Deprecated validation script

### GitHub Actions Workflows

**New Workflows:**

- `.github/workflows/pr-checks.yml` - Automated PR validation on pull requests
- `.github/workflows/validation.yml` - Repository validation checks

### Markdown Configuration

**Added:**

- `.markdownlintrc.json` - Markdown linting rules
- `.markdownlintignore` - Exclusions for .venv and generated files

### Documentation Updates

**TODO Journal System:**

- Archived completed milestones TSE-0001.1b, TSE-0001.3c, TSE-0001.4.4 to TODO-HISTORY.md
- Updated TODO.md to reference TODO-HISTORY.md
- Added Git Quality Standards completion milestone to TODO.md

**PR Documentation:**

- Fixed markdown linting errors across all PR documentation
- Standardized "What Changed" section naming

### Repository Context

This is part of epic TSE-0001 Foundation work to establish consistent git workflows, validation standards, and documentation practices across all repositories in the trading ecosystem. The risk-monitor-py service follows the same patterns as other services in the ecosystem.

## Testing

### Validation Tests

- [x] Run `bash scripts/validate-all.sh` - passes all checks
- [x] Verify PR documentation exists for current branch
- [x] Confirm markdown linting passes
- [x] Verify TODO.md exists and is valid
- [x] Test pre-push hook logic (dry run)
- [x] Verify GitHub Actions workflows are properly configured

### Cross-Repository Verification

- [x] Verified checksums match across all repositories
- [x] Confirmed script standardization successful
- [x] Tested validation in multiple repositories
- [x] Verified TODO-HISTORY.md archival pattern

### Functional Tests

- [x] All 52 existing tests still passing
- [x] Service starts and responds to health checks
- [x] No regressions in service functionality

## Related Issues

- Epic TSE-0001: Foundation - Git Quality Standards
- Standardizing validation scripts across 9+ repositories
- TODO journal system implementation (TODO.md + TODO-HISTORY.md pattern)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
