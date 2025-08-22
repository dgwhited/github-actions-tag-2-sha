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

## ⚠️ Important: Updating Workflow Files Requires PAT

**To update `.github/workflows/*.yml` files, you MUST use a Personal Access Token** due to GitHub security restrictions. The default `GITHUB_TOKEN` cannot modify workflow files.

### Quick Start for Workflow Updates

#### 1. Create Personal Access Token
1. Go to https://github.com/settings/tokens/new
2. Give it a name: "GitHub Actions Updater"
3. Select scope: ✅ **`repo`** (includes workflow permissions)
4. Click **Generate token** and copy it

#### 2. Add Token to Repository
1. Go to your repository **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `WORKFLOW_TOKEN`
4. Value: Paste your PAT
5. Click **Add secret**

#### 3. Use in Your Workflow
```yaml
name: Weekly GitHub Actions Update
on:
  schedule:
    - cron: '0 10 * * 1'  # Every Monday at 10 AM

jobs:
  update:
    uses: dgwhited/github-actions-tag-2-sha/.github/workflows/update-actions.yml@main
    with:
      files: '.github/workflows/*.yml'
    secrets:
      token: ${{ secrets.WORKFLOW_TOKEN }}  # Required for workflow files!
```

✅ **Ready to go!** Your workflows will now be updated automatically every week.

## 🔧 Setup Requirements

### Repository Configuration (Required)
Before using this action, you must enable PR creation in your repository:

1. Go to **Settings → Actions → General → Workflow permissions**
2. Check: ✅ **"Allow GitHub Actions to create and approve pull requests"**

**For Organization Repositories**: Organization admins may need to enable this setting at the organization level first.

### Token Options

#### Option 1: Personal Access Token (For Workflow Files)
**Required for updating `.github/workflows/*.yml` files:**
- ✅ Create PAT with `repo` scope (includes workflow permissions)
- ✅ Add as repository secret: `WORKFLOW_TOKEN` 
- ✅ Can trigger other workflows when PRs are created

**Setup:** See "Quick Start for Workflow Updates" section above

#### Option 2: Default GITHUB_TOKEN (Limited Use)
**Only works for non-workflow files (action.yml, docker-compose.yml, etc.):**
- ✅ No additional setup required
- ✅ No secrets to manage  
- ✅ Works out of the box

**Major Limitations:**
- ❌ **Cannot update `.github/workflows/*.yml` files** (will fail)
- ⚠️ Pull requests created won't trigger other workflows

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
          token: ${{ secrets.WORKFLOW_TOKEN }}  # Required for workflow files!
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          title: 'Update GitHub Actions to latest releases'
          body: 'Automated update of GitHub Actions dependencies'
          branch: 'update-actions'
          token: ${{ secrets.WORKFLOW_TOKEN }}
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
    secrets:
      token: ${{ secrets.WORKFLOW_TOKEN }}  # Required for workflow files!
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
    secrets:
      token: ${{ secrets.ORG_WORKFLOW_TOKEN }}  # Required: PAT with workflow permissions
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

## 🚨 Troubleshooting

### Workflow Permission Error (Most Common)
**Error**: `refusing to allow a GitHub App to create or update workflow '.github/workflows/xxx.yml' without workflows permission`

**Cause**: You're trying to update workflow files with the default `GITHUB_TOKEN`, which lacks workflow permissions.

**Solution**: Use a Personal Access Token (see "Quick Start for Workflow Updates" above)

### Permission Denied Error (403)
If you get an error like `Permission to <repo>.git denied to github-actions[bot]`, follow these steps:

#### 1. Check Repository Settings (Most Common Fix)
1. Go to **Settings → Actions → General → Workflow permissions**
2. Select **"Read and write permissions"**
3. Check ✅ **"Allow GitHub Actions to create and approve pull requests"**
4. Click **Save**

#### 2. Organization Settings (If Repository Setting is Grayed Out)
For organization repositories, admins must enable these settings:
1. Go to **Organization Settings → Actions → General**
2. Enable **"Allow GitHub Actions to create and approve pull requests"**
3. Then return to repository settings and enable the same option

#### 3. Repository Created After February 2, 2023
If your repository was created after February 2, 2023, the default GITHUB_TOKEN permissions are read-only. The workflow includes the necessary permissions, but repository settings must be enabled as described above.

#### 4. Still Getting Errors?
If you continue getting permission errors after enabling repository settings:

**Use a Personal Access Token:**
1. Create a PAT with `repo` scope
2. Add as repository secret: `GITHUB_TOKEN_PAT`
3. Use in workflow:
   ```yaml
   secrets:
     token: ${{ secrets.GITHUB_TOKEN_PAT }}
   ```

### No Changes Detected
If the action runs but reports "No changes detected":
- Your GitHub Actions are already at their latest releases
- Run with `dry-run: true` to see what would be updated
- Check if the action patterns match your workflow file paths

### Actions Not Found
If you get "No release found for repo" warnings:
- The action repository might not have releases (only tags)
- Some actions use different release strategies
- The action might be deprecated or moved

## Features

- Converts GitHub Actions tag references to commit SHA references
- Updates all actions (tags and SHAs) to their latest releases with `--update-to-latest`
- Adds comments with original tag versions for reference
- Handles version references like 'v4' by using the latest matching tag
- Can convert 'main' branch references to the latest release
- Supports git branch creation, commits, and pushing
- Handles both lightweight and annotated tags
- Skips updates when actions are already at their latest versions 