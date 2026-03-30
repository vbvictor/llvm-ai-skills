#!/usr/bin/env python3
"""Commit changes, switch back to main, and log the result.

Usage: branch_finish.py <issue_number> --status success|skipped|failed
           --title TITLE --summary SUMMARY [--files-changed FILES]
           [--repo-dir DIR] [--tracker FILE]

Commits all changes on fix-<issue_number>, switches back to main,
and appends a record to the tracker file.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue", type=int)
    parser.add_argument("--status", required=True, choices=["success", "skipped", "failed"])
    parser.add_argument("--title", required=True, help="Issue title")
    parser.add_argument("--summary", required=True, help="What was done")
    parser.add_argument("--files-changed", default="", help="Comma-separated list of changed files")
    parser.add_argument("--repo-dir", default=".", help="Path to LLVM repo")
    parser.add_argument("--tracker", default="/tmp/clang-tidy-batch-fix-tracker.json",
                        help="Path to tracker JSON file")
    args = parser.parse_args()

    branch = f"fix-{args.issue}"

    # Verify we're on the right branch
    r = run(["git", "branch", "--show-current"], cwd=args.repo_dir)
    current = r.stdout.strip()
    if current != branch:
        print(f"ERROR: Expected branch '{branch}', but on '{current}'", file=sys.stderr)
        sys.exit(1)

    if args.status == "success":
        # Stage and commit all changes
        r = run(["git", "add", "-A"], cwd=args.repo_dir)
        if r.returncode != 0:
            print(f"ERROR: git add failed: {r.stderr}", file=sys.stderr)
            sys.exit(1)

        commit_msg = (
            f"[clang-tidy] Fix false positive in issue #{args.issue}\n\n"
            f"{args.summary}\n\n"
            f"Fixes https://github.com/llvm/llvm-project/issues/{args.issue}"
        )
        r = run(["git", "commit", "-m", commit_msg], cwd=args.repo_dir)
        if r.returncode != 0:
            print(f"ERROR: git commit failed: {r.stderr}", file=sys.stderr)
            sys.exit(1)

        # Get the commit hash
        r = run(["git", "rev-parse", "--short", "HEAD"], cwd=args.repo_dir)
        commit_hash = r.stdout.strip()
    else:
        commit_hash = None
        # Discard any partial changes
        run(["git", "checkout", "."], cwd=args.repo_dir)
        run(["git", "clean", "-fd"], cwd=args.repo_dir)

    # Switch back to main
    r = run(["git", "checkout", "main"], cwd=args.repo_dir)
    if r.returncode != 0:
        print(f"ERROR: Failed to checkout main: {r.stderr}", file=sys.stderr)
        sys.exit(1)

    # If skipped/failed, delete the empty branch
    if args.status != "success":
        run(["git", "branch", "-D", branch], cwd=args.repo_dir)

    # Append to tracker
    tracker_path = args.tracker
    if os.path.exists(tracker_path):
        with open(tracker_path) as f:
            tracker = json.load(f)
    else:
        tracker = {"fixes": [], "created_at": datetime.now(timezone.utc).isoformat()}

    tracker["fixes"].append({
        "issue": args.issue,
        "title": args.title,
        "status": args.status,
        "branch": branch if args.status == "success" else None,
        "commit": commit_hash,
        "summary": args.summary,
        "files_changed": [f.strip() for f in args.files_changed.split(",") if f.strip()],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    tracker["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(tracker_path, "w") as f:
        json.dump(tracker, f, indent=2)

    print(f"OK: Finished issue #{args.issue} (status={args.status}), back on main")
    if args.status == "success":
        print(f"    Branch: {branch}, Commit: {commit_hash}")


if __name__ == "__main__":
    main()
