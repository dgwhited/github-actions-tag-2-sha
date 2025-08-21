# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Build and Installation
```bash
# Install in development mode
pip install -e .

# Install from source
pip install .
```

### Running the Tool
```bash
# Basic usage - convert tags to SHA in workflow files
tag2sha .github/workflows/*.yml

# Dry run - preview changes without making them
tag2sha --dry-run .github/workflows/*.yml

# Create branch, commit, and push changes
tag2sha --branch="update-actions" --commit-msg="Update actions to use SHA" --push .github/workflows/*.yml

# Convert main/master references to latest release
tag2sha --convert-main-to-release .github/workflows/*.yml

# Update all actions to their latest releases
tag2sha --update-to-latest .github/workflows/*.yml

# Update to latest with git workflow
tag2sha --update-to-latest --branch="update-actions-latest" --commit-msg="Update all actions to latest releases" --push .github/workflows/*.yml
```

### Testing
```bash
# Run tests (when tests are added)
pytest
```

## Architecture

This is a command-line tool for converting GitHub Actions tag references to SHA references for improved security. The codebase consists of:

**Main Components:**
- `tag2sha/cli.py`: Core logic including:
  - `parse_args()`: Argument parsing with support for dry-run, git operations, and branch conversion
  - `get_commit_sha()`: Fetches SHA for tags/refs from GitHub API, handles annotated tags
  - `get_latest_release()`: Finds the latest release tag for a repository
  - `get_latest_matching_tag()`: Resolves version patterns (e.g., 'v4' to 'v4.1.2')
  - `process_workflow_file()`: Parses YAML workflow files and replaces action references
  - Git operation helpers for branch creation, commits, and pushing

**Key Features:**
- Converts GitHub Actions tag references (e.g., `actions/checkout@v4`) to SHA references with comments
- Updates ALL actions (tags and SHAs) to their latest releases with `--update-to-latest` flag
- Handles version patterns intelligently (e.g., `v4` resolves to latest `v4.x.x` tag)
- Can convert `main`/`master` branch references to latest release tags
- Supports git workflow integration (branch creation, commits, pushing)
- Uses GitHub API with optional token authentication for rate limiting
- Intelligently skips actions already at their latest releases to avoid unnecessary changes

**Dependencies:**
- `requests`: GitHub API interactions
- `pyyaml`: Workflow file parsing
- `semver`: Semantic version comparison for finding latest tags