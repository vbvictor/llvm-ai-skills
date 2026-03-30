#!/usr/bin/env python3
"""Create a fix branch for a given issue number.

Usage: branch_start.py <issue_number> [--repo-dir DIR]

Creates branch 'fix-<issue_number>' from main.
Fails if working tree is dirty or branch already exists.
"""
import argparse
import subprocess
import sys


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue", type=int, help="GitHub issue number")
    parser.add_argument("--repo-dir", default=".", help="Path to LLVM repo")
    args = parser.parse_args()

    branch = f"fix-{args.issue}"

    # Check for dirty working tree
    r = run(["git", "status", "--porcelain"], cwd=args.repo_dir)
    if r.stdout.strip():
        print(f"ERROR: Working tree is dirty. Clean up before starting.", file=sys.stderr)
        print(r.stdout, file=sys.stderr)
        sys.exit(1)

    # Check branch doesn't already exist
    r = run(["git", "rev-parse", "--verify", branch], cwd=args.repo_dir)
    if r.returncode == 0:
        print(f"ERROR: Branch '{branch}' already exists.", file=sys.stderr)
        sys.exit(1)

    # Make sure we're on main
    r = run(["git", "checkout", "main"], cwd=args.repo_dir)
    if r.returncode != 0:
        print(f"ERROR: Failed to checkout main: {r.stderr}", file=sys.stderr)
        sys.exit(1)

    # Create and checkout new branch
    r = run(["git", "checkout", "-b", branch], cwd=args.repo_dir)
    if r.returncode != 0:
        print(f"ERROR: Failed to create branch: {r.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: Created and switched to branch '{branch}'")


if __name__ == "__main__":
    main()
