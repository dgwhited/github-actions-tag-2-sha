# Tag2SHA

A tool for converting GitHub Actions tags to SHA references.

## Installation

```bash
# Install directly from GitHub repository
pip install git+https://github.com/dgwhited/github-actions-tag-2-sha.git
```

## Usage

### Command Line Interface

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

### GitHub Action Usage

This tool is also available as a GitHub Action for automated dependency updates across your organization.

## 🔧 Setup Requirements

### Repository Configuration (Required)
Before using this action, you must enable PR creation in your repository:

1. Go to **Settings → Actions → General → Workflow permissions**
2. Check: ✅ **"Allow GitHub Actions to create and approve pull requests"**

**For Organization Repositories**: Organization admins may need to enable this setting at the organization level first.

### Token Options

#### Option 1: Default GITHUB_TOKEN (Recommended)
**Pros:**
- ✅ No additional setup required
- ✅ No secrets to manage  
- ✅ Works out of the box
- ✅ Secure by default

**Limitations:**
- ⚠️ Pull requests created won't trigger other workflows (GitHub security feature)
- ⚠️ Won't run `on: pull_request` or `on: push` workflow checks

#### Option 2: Personal Access Token (Advanced)
**When to use:**
- ✅ Need PRs to trigger other workflows
- ✅ Need `on: pull_request` checks to run
- ✅ Integration with external workflow dependencies

**Setup:**
1. Create a Personal Access Token with `repo` scope
2. Add as repository secret (e.g., `GITHUB_TOKEN_PAT`)
3. Reference in workflow: `token: ${{ secrets.GITHUB_TOKEN_PAT }}`

#### 1. Using the Composite Action

```yaml
name: Update Dependencies
on:
  schedule:
    - cron: '0 10 * * 1'  # Every Monday at 10 AM UTC

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Update GitHub Actions
        uses: dgwhited/github-actions-tag-2-sha@v1
        with:
          files: '.github/workflows/*.yml'
          mode: 'update-to-latest'
          # token: ${{ github.token }} # Optional - uses default GITHUB_TOKEN
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          title: 'Update GitHub Actions to latest releases'
          body: 'Automated update of GitHub Actions dependencies'
          branch: 'update-actions'
```

#### 2. Using the Reusable Workflow (Recommended for Organizations)

Create `.github/workflows/update-actions.yml` in any repository:

```yaml
name: Weekly Actions Update
on:
  schedule:
    - cron: '0 10 * * 1'  # Every Monday at 10 AM UTC
  workflow_dispatch:      # Allow manual triggering

jobs:
  update:
    uses: dgwhited/github-actions-tag-2-sha/.github/workflows/update-actions.yml@main
    with:
      mode: 'update-to-latest'
      create-pr: true
      pr-title: '🤖 Weekly GitHub Actions Update'
      pr-labels: 'dependencies, automated-pr'
    # secrets:
    #   token: ${{ secrets.CUSTOM_TOKEN }} # Optional - only needed for advanced use cases
```

#### 3. Organization-Wide Setup

For organization-wide automation:

1. **Create a central workflow repository** or use this repository
2. **Set up repository permissions** in your organization settings
3. **Use the reusable workflow** from multiple repositories
4. **Configure secrets** for broader permissions if needed

**Example organization workflow:**
```yaml
name: Organization Actions Update
on:
  schedule:
    - cron: '0 10 * * 1'
  workflow_dispatch:

jobs:
  update:
    uses: your-org/github-actions-tag-2-sha/.github/workflows/update-actions.yml@main
    with:
      mode: 'update-to-latest'
      create-pr: true
    # secrets:
    #   token: ${{ secrets.ORG_GITHUB_TOKEN }}  # Optional: PAT with org permissions for advanced use cases
```

### Action Inputs

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `files` | Workflow files to process | `.github/workflows/*.yml` | No |
| `mode` | Update mode: `update-to-latest`, `convert-to-sha`, `convert-main-to-release` | `update-to-latest` | No |
| `token` | GitHub token for API access | `github.token` | No |
| `dry-run` | Preview changes without modifying files | `false` | No |
| `create-pr` | Create pull request with changes | `true` | No |
| `pr-title` | Pull request title | `Update GitHub Actions to latest releases` | No |
| `pr-body` | Pull request body | Auto-generated | No |
| `pr-labels` | Pull request labels (comma-separated) | `dependencies, automated-pr, github-actions` | No |

### Important Notes

#### Workflow Trigger Limitations
When using the default `GITHUB_TOKEN`, pull requests created by this action **will not trigger other workflows**. This is a GitHub security feature to prevent recursive workflow runs.

**What this means:**
- ✅ External checks and status checks from third-party services will still run
- ❌ Your repository's `on: pull_request` workflows will NOT run
- ❌ Your repository's `on: push` workflows will NOT run when the PR is merged

**If you need other workflows to trigger**, use a Personal Access Token instead of the default token.

## Features

- Converts GitHub Actions tag references to commit SHA references
- Updates all actions (tags and SHAs) to their latest releases with `--update-to-latest`
- Adds comments with original tag versions for reference
- Handles version references like 'v4' by using the latest matching tag
- Can convert 'main' branch references to the latest release
- Supports git branch creation, commits, and pushing
- Handles both lightweight and annotated tags
- Skips updates when actions are already at their latest versions 