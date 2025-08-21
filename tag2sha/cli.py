#!/usr/bin/env python3
import os
import re
import sys
import requests
import yaml
import argparse
import subprocess
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import semver
import fnmatch

def parse_args():
    parser = argparse.ArgumentParser(description='Convert GitHub Actions tags to SHA references')
    parser.add_argument('files', nargs='+', help='Workflow files to process')
    parser.add_argument('--token', help='GitHub token for API authentication', 
                      default=os.environ.get('GITHUB_TOKEN'))
    parser.add_argument('--dry-run', action='store_true', help='Print changes without modifying files')
    parser.add_argument('--branch', help='Create and switch to this branch for changes', 
                      default=f'tag-to-sha-{datetime.now().strftime("%Y%m%d-%H%M%S")}')
    parser.add_argument('--commit-msg', help='Commit message for changes', 
                      default='Convert GitHub Actions tags to SHA references')
    parser.add_argument('--push', action='store_true', help='Push changes to remote repository')
    parser.add_argument('--remote', help='Remote name to push to', default='origin')
    parser.add_argument('--no-git', action='store_true', help='Skip all git operations')
    parser.add_argument('--convert-main-to-release', action='store_true', 
                      help='Convert main/master branch references to latest release')
    parser.add_argument('--update-to-latest', action='store_true', 
                      help='Update all actions (tags and SHAs) to their latest releases')
    return parser.parse_args()

def get_latest_release(repo: str, token: str = None) -> Optional[str]:
    """Get the latest release tag for a repository."""
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    # Try the releases API first (excludes pre-releases by default)
    releases_url = f'https://api.github.com/repos/{repo}/releases/latest'
    response = requests.get(releases_url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('tag_name')
    
    # If no official "latest" release, fall back to getting all releases/tags
    tags_url = f'https://api.github.com/repos/{repo}/tags'
    response = requests.get(tags_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Could not fetch tags for {repo}", file=sys.stderr)
        print(f"API response: {response.status_code} - {response.text}", file=sys.stderr)
        return None
    
    tags = response.json()
    if not tags:
        return None
    
    # Try to find and sort semantic versions
    versioned_tags = []
    for tag in tags:
        tag_name = tag['name']
        # Skip tags that don't look like versions (no v prefix, no digits)
        if not (tag_name.startswith('v') or any(c.isdigit() for c in tag_name)):
            continue
            
        # Clean tag for semver parsing
        clean_tag = tag_name
        if tag_name.startswith('v'):
            clean_tag = tag_name[1:]
            
        try:
            semver.parse(clean_tag)
            versioned_tags.append((tag_name, clean_tag))
        except ValueError:
            # Skip tags that aren't valid semver
            continue
    
    if versioned_tags:
        # Sort by semantic version
        sorted_tags = sorted(
            versioned_tags,
            key=lambda x: semver.VersionInfo.parse(x[1]),
            reverse=True
        )
        return sorted_tags[0][0]  # Return the highest version tag
        
    # If no semantic versions found, just return the first tag
    return tags[0]['name'] if tags else None

def get_latest_matching_tag(repo: str, version_pattern: str, token: str = None) -> Optional[str]:
    """Get the latest tag that matches the given pattern."""
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    # Fetch all tags for the repository
    tags_url = f'https://api.github.com/repos/{repo}/tags'
    response = requests.get(tags_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Could not fetch tags for {repo}", file=sys.stderr)
        print(f"API response: {response.status_code} - {response.text}", file=sys.stderr)
        return None
    
    tags = response.json()
    if not tags:
        return None
    
    # Create a pattern for matching
    # For example, if version_pattern is 'v4', we want to match 'v4*'
    if version_pattern.startswith('v') and version_pattern[1:].isdigit():
        # It's a simple version like 'v4', match with wildcard
        pattern = f"{version_pattern}*"
    else:
        # Exact match for other patterns
        pattern = version_pattern
    
    # Find all matching tags
    matching_tags = []
    for tag in tags:
        tag_name = tag['name']
        if fnmatch.fnmatch(tag_name, pattern):
            matching_tags.append(tag_name)
    
    if not matching_tags:
        return None
    
    # Sort tags by semantic versioning if possible
    try:
        # Clean tags to valid semver if needed
        clean_tags = []
        for tag in matching_tags:
            # Handle tags like 'v1.2.3'
            tag_version = tag
            if tag.startswith('v'):
                tag_version = tag[1:]
            
            # Try to parse as semver, add if valid
            try:
                semver.parse(tag_version)
                clean_tags.append((tag, tag_version))
            except ValueError:
                # If not valid semver, still keep the original tag
                clean_tags.append((tag, None))
        
        # Sort by semantic version, putting non-semver tags at the end
        sorted_tags = sorted(
            clean_tags,
            key=lambda x: semver.VersionInfo.parse(x[1]) if x[1] is not None else semver.VersionInfo(0, 0, 0),
            reverse=True
        )
        return sorted_tags[0][0]  # Return the original tag name
    except (ValueError, ImportError):
        # Fallback to simple string sorting if semver parsing fails
        matching_tags.sort(reverse=True)
        return matching_tags[0]

def get_commit_sha(repo: str, tag: str, token: str = None, convert_main_to_release: bool = False) -> Tuple[str, str]:
    """
    Get the commit SHA for a given tag/ref in a repository.
    Returns a tuple of (sha, resolved_ref) where resolved_ref is the tag/ref that was actually used.
    """
    resolved_ref = tag
    original_ref = tag  # Store the original reference
    
    # Handle main/master branch conversion if enabled
    if convert_main_to_release and tag.lower() in ['main', 'master']:
        latest_release = get_latest_release(repo, token)
        if latest_release:
            print(f"Converting {repo}@{tag} to latest release: {latest_release}")
            resolved_ref = latest_release
            tag = latest_release
        else:
            print(f"Warning: No releases found for {repo}, keeping {tag} reference")
    
    # Check if this is a version reference (like 'v4') that should get the latest matching tag
    elif tag.startswith('v') and len(tag) > 1 and tag[1:].isdigit():
        # It's a version reference like 'v4', find the latest matching tag
        latest_tag = get_latest_matching_tag(repo, tag, token)
        if latest_tag and latest_tag != tag:
            print(f"Resolving {repo}@{tag} to latest matching tag: {latest_tag}")
            resolved_ref = latest_tag
            tag = latest_tag
    
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    # Try to get the reference
    ref_url = f'https://api.github.com/repos/{repo}/git/refs/tags/{tag}'
    response = requests.get(ref_url, headers=headers)
    
    # If it's not a tag, try as a branch/ref
    if response.status_code != 200:
        ref_url = f'https://api.github.com/repos/{repo}/git/refs/heads/{tag}'
        response = requests.get(ref_url, headers=headers)
    
    if response.status_code == 200:
        ref_data = response.json()
        ref_type = ref_data.get('object', {}).get('type')
        
        if ref_type == 'tag':
            # This is an annotated tag, need to get the commit it points to
            tag_sha = ref_data['object']['sha']
            tag_obj_url = f'https://api.github.com/repos/{repo}/git/tags/{tag_sha}'
            tag_obj_response = requests.get(tag_obj_url, headers=headers)
            if tag_obj_response.status_code == 200:
                return tag_obj_response.json()['object']['sha'], resolved_ref
        else:
            # This is a direct reference to a commit
            return ref_data['object']['sha'], resolved_ref
    
    # If we can't find the ref or something else went wrong
    print(f"Error: Could not find SHA for {repo}@{tag}", file=sys.stderr)
    print(f"API response: {response.status_code} - {response.text}", file=sys.stderr)
    return None, resolved_ref

def process_workflow_file(file_path: str, token: str, dry_run: bool = False, convert_main_to_release: bool = False, update_to_latest: bool = False) -> Tuple[int, int]:
    """
    Process a workflow file, replacing tags with SHAs.
    Returns a tuple of (changes_made, errors).
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Regular expression to match GitHub action references
    # Matches patterns like: uses: owner/repo@tag or uses: owner/repo@sha  # tag
    action_pattern = re.compile(r'(\s+uses:\s+)([^/\s]+/[^@\s]+)@([^#\s]+)(\s*(?:#\s*(.*))?)?$', re.MULTILINE)
    
    changes_made = 0
    errors = 0
    new_content = content
    
    for match in action_pattern.finditer(content):
        prefix, repo, version, comment_part, comment_text = match.groups()
        
        # Determine the current version and whether it's a SHA
        is_sha = re.match(r'^[0-9a-f]{40}$', version)
        current_version = version
        
        if update_to_latest:
            # When updating to latest, always get the latest release
            latest_release = get_latest_release(repo, token)
            if not latest_release:
                print(f"Warning: No release found for {repo}, skipping")
                errors += 1
                continue
            
            # Get SHA for latest release
            sha, resolved_ref = get_commit_sha(repo, latest_release, token, False)
            if not sha:
                errors += 1
                continue
            
            # Check if we actually need to update
            if is_sha and comment_text and comment_text.strip() == latest_release:
                # Already at latest release
                continue
            elif not is_sha and version == latest_release:
                # Already at latest release
                continue
            
            print(f"Action: {repo}@{version} → {repo}@{sha}  # {latest_release}")
            new_line = f"{prefix}{repo}@{sha}  # {latest_release}"
            
        else:
            # Original behavior: skip SHA references unless converting main to release
            if is_sha:
                continue
            
            # Get the SHA for this tag
            sha, resolved_ref = get_commit_sha(repo, version, token, convert_main_to_release)
            if not sha:
                errors += 1
                continue
            
            # Debug output
            print(f"Action: {repo}@{version} → SHA with tag: {resolved_ref}")
            
            # Create the replacement with simplified comment format - always use resolved_ref
            if comment_part and comment_part.strip():
                new_line = f"{prefix}{repo}@{sha}{comment_part}"
            else:
                new_line = f"{prefix}{repo}@{sha}  # {resolved_ref}"
        
        # Replace this specific occurrence
        new_content = new_content.replace(match.group(0), new_line)
        changes_made += 1
    
    if changes_made > 0 and not dry_run:
        with open(file_path, 'w') as f:
            f.write(new_content)
    
    return changes_made, errors

def run_git_command(cmd, description=None, exit_on_error=True):
    """Run a git command and return its output."""
    try:
        result = subprocess.run(['git'] + cmd, check=True, 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if description:
            print(f"Error during {description}:", file=sys.stderr)
        print(f"Command 'git {' '.join(cmd)}' failed with code {e.returncode}", file=sys.stderr)
        print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        if exit_on_error:
            sys.exit(1)
        return None

def setup_git_branch(branch_name):
    """Create and switch to a new git branch."""
    print(f"Creating new branch: {branch_name}")
    
    # Check if branch already exists (locally)
    existing_branches = run_git_command(['branch'], 'checking existing branches')
    if branch_name in existing_branches.splitlines():
        # Branch exists locally, just switch to it
        run_git_command(['checkout', branch_name], f'switching to existing branch {branch_name}')
        return
    
    # Create and switch to new branch
    run_git_command(['checkout', '-b', branch_name], f'creating new branch {branch_name}')

def commit_changes(files, commit_msg):
    """Add files and commit changes."""
    print("Committing changes...")
    run_git_command(['add'] + files, 'adding files')
    run_git_command(['commit', '-m', commit_msg], 'committing changes')

def push_branch(branch_name, remote):
    """Push the branch to remote."""
    print(f"Pushing branch {branch_name} to {remote}...")
    run_git_command(['push', '-u', remote, branch_name], 'pushing branch')

def main():
    args = parse_args()
    
    if args.dry_run:
        print("Running in dry-run mode. No files will be changed.")
    if args.convert_main_to_release:
        print("Will convert main/master references to latest release tags.")
    if args.update_to_latest:
        print("Will update all actions to their latest releases.")
    
    # Set up git branch if not in dry-run mode and git operations are enabled
    if not args.dry_run and not args.no_git:
        setup_git_branch(args.branch)
    
    total_changes = 0
    total_errors = 0
    changed_files = []
    
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            continue
            
        print(f"Processing {file_path}...")
        changes, errors = process_workflow_file(
            file_path, 
            args.token, 
            args.dry_run,
            args.convert_main_to_release,
            args.update_to_latest
        )
        
        if changes > 0:
            changed_files.append(file_path)
            
        if args.dry_run and changes > 0:
            print(f"Would make {changes} changes to {file_path}")
        else:
            print(f"Made {changes} changes to {file_path}")
        
        if errors > 0:
            print(f"Encountered {errors} errors while processing {file_path}")
        
        total_changes += changes
        total_errors += errors
    
    print(f"\nSummary: Made {total_changes} changes with {total_errors} errors across {len(args.files)} files.")
    
    # Commit and push changes if we made any and we're not in dry-run mode
    if total_changes > 0 and not args.dry_run and not args.no_git:
        if changed_files:
            commit_changes(changed_files, args.commit_msg)
            
            if args.push:
                push_branch(args.branch, args.remote)
                print(f"Changes pushed to {args.remote}/{args.branch}")
            else:
                print(f"Changes committed to branch {args.branch}. Use --push to push to remote.")
    
    if total_errors > 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main()) 