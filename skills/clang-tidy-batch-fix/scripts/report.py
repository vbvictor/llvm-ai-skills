#!/usr/bin/env python3
"""Generate a markdown report from the batch fix tracker JSON.

Usage: report.py [--tracker FILE] [--output FILE]

Reads the tracker JSON and writes a markdown summary.
If --output is omitted, prints to stdout.
"""
import argparse
import json
import os
import sys
from datetime import datetime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracker", default="/tmp/clang-tidy-batch-fix-tracker.json")
    parser.add_argument("--output", default=None, help="Output markdown file (default: stdout)")
    args = parser.parse_args()

    if not os.path.exists(args.tracker):
        print(f"ERROR: Tracker file not found: {args.tracker}", file=sys.stderr)
        sys.exit(1)

    with open(args.tracker) as f:
        tracker = json.load(f)

    fixes = tracker["fixes"]
    success = [f for f in fixes if f["status"] == "success"]
    skipped = [f for f in fixes if f["status"] == "skipped"]
    failed = [f for f in fixes if f["status"] == "failed"]

    lines = []
    lines.append(f"# Clang-Tidy Batch Fix Report")
    lines.append(f"")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"")
    lines.append(f"**Total: {len(fixes)}** | "
                 f"Success: {len(success)} | "
                 f"Skipped: {len(skipped)} | "
                 f"Failed: {len(failed)}")
    lines.append(f"")

    # Summary table
    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"| # | Issue | Status | Branch | Summary |")
    lines.append(f"|---|-------|--------|--------|---------|")
    for i, fix in enumerate(fixes, 1):
        issue_link = f"[#{fix['issue']}](https://github.com/llvm/llvm-project/issues/{fix['issue']})"
        status_icon = {"success": "done", "skipped": "skipped", "failed": "FAILED"}[fix["status"]]
        branch = f"`{fix['branch']}`" if fix["branch"] else "—"
        summary = fix["summary"][:80]
        lines.append(f"| {i} | {issue_link} | {status_icon} | {branch} | {summary} |")
    lines.append(f"")

    # Successful fixes detail
    if success:
        lines.append(f"## Successful Fixes")
        lines.append(f"")
        for fix in success:
            lines.append(f"### #{fix['issue']} — {fix['title']}")
            lines.append(f"- **Branch**: `{fix['branch']}`")
            lines.append(f"- **Commit**: `{fix['commit']}`")
            lines.append(f"- **Summary**: {fix['summary']}")
            if fix["files_changed"]:
                lines.append(f"- **Files changed**:")
                for fc in fix["files_changed"]:
                    lines.append(f"  - `{fc}`")
            lines.append(f"- **URL**: https://github.com/llvm/llvm-project/issues/{fix['issue']}")
            lines.append(f"")

    # Skipped
    if skipped:
        lines.append(f"## Skipped Issues")
        lines.append(f"")
        for fix in skipped:
            lines.append(f"- **#{fix['issue']}** — {fix['title']}: {fix['summary']}")
        lines.append(f"")

    # Failed
    if failed:
        lines.append(f"## Failed Issues")
        lines.append(f"")
        for fix in failed:
            lines.append(f"- **#{fix['issue']}** — {fix['title']}: {fix['summary']}")
        lines.append(f"")

    # Branches for easy copy-paste
    if success:
        lines.append(f"## Branches Created")
        lines.append(f"")
        lines.append(f"```")
        for fix in success:
            lines.append(fix["branch"])
        lines.append(f"```")
        lines.append(f"")

    report = "\n".join(lines)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
