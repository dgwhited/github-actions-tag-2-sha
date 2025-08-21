# Tag2SHA

A tool for converting GitHub Actions tags to SHA references.

## Installation

```bash
# Install directly from GitHub repository
pip install git+https://github.com/dgwhited/github-actions-tag-2-sha.git
```

## Usage

```bash
# Basic usage
tag2sha .github/workflows/*.yml

# Preview changes without making them
tag2sha --dry-run .github/workflows/*.yml

# Make changes with git operations
tag2sha --branch="update-actions" --commit-msg="Update actions to use SHA" --push .github/workflows/*.yml

# Convert main/master to latest release
tag2sha --convert-main-to-release .github/workflows/*.yml

# Update all actions to their latest releases
tag2sha --update-to-latest .github/workflows/*.yml

# Update to latest with git operations
tag2sha --update-to-latest --branch="update-actions-latest" --commit-msg="Update all actions to latest releases" --push .github/workflows/*.yml

# Skip git operations
tag2sha --no-git .github/workflows/*.yml
```

## Features

- Converts GitHub Actions tag references to commit SHA references
- Updates all actions (tags and SHAs) to their latest releases with `--update-to-latest`
- Adds comments with original tag versions for reference
- Handles version references like 'v4' by using the latest matching tag
- Can convert 'main' branch references to the latest release
- Supports git branch creation, commits, and pushing
- Handles both lightweight and annotated tags
- Skips updates when actions are already at their latest versions 