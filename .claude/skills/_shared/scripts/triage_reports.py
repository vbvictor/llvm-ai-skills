#!/usr/bin/env python3
"""Look up triage-agent reports for LLVM clang-tidy issues.

clang-tidy-infra/triage-agent files one tracking issue per LLVM issue, holding
a verdict, a Godbolt reproducer and a root-cause rationale. This script only
reads: it never comments on, closes, or /redo's anything.

Usage:
  triage_reports.py show <llvm_issue> [<llvm_issue> ...]
  triage_reports.py list [--tag TAG] [--check NAME] [--include-closed]

show prints the latest analysis of each LLVM issue, plus the exact source and
flags behind its Godbolt link. Having no report is normal, not an error.

list prints one row per LLVM issue. By default it covers reports tagged
false-positive whose LLVM issue is still open; pass --tag any to drop the tag
filter.
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request

TRIAGE_REPO = "clang-tidy-infra/triage-agent"
LLVM_REPO = "llvm/llvm-project"
TRACKING_LABELS = {"clang-tidy-triage", "clang-tidy-triage-backlog"}
BOT_LOGIN = "github-actions"
GH_LIMIT = "5000"
ISSUE_JSON = "number,title,url,state,labels,body,comments,createdAt"

# In report order. Older reports have no "Similar Issues".
FIELDS = [
    "Check Name",
    "Extracted Snippet",
    "Flags/Config",
    "Verdict",
    "Type",
    "Tags",
    "Godbolt Link",
    "Similar Issues",
    "Rationale",
]

SOURCE_RE = re.compile(
    r"-\s*\*\*Issue:\*\*\s*https://github\.com/llvm/llvm-project/issues/(\d+)"
)
ANALYSIS_RE = re.compile(r"^## Analysis\b", re.MULTILINE)
AGENT_SUMMARY_RE = re.compile(r"\n<details>\s*<summary><b>Agent Summary")
GODBOLT_RE = re.compile(r"https://godbolt\.org/z/([\w-]+)")


def gh_json(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: gh {' '.join(args)}: {r.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return json.loads(r.stdout)


def latest_analysis(issue):
    """Return (analysis text, timestamp, origin) for a tracking issue.

    /redo posts its fresh analysis as a bot comment, leaving the issue body
    stale. The body quotes the original LLVM issue, which could itself contain
    an "## Analysis" line, so the real section is the last one.
    """
    redos = [
        c
        for c in issue["comments"]
        if (c.get("author") or {}).get("login") == BOT_LOGIN
        and ANALYSIS_RE.match(c["body"].lstrip())
    ]
    if redos:
        newest = max(redos, key=lambda c: c["createdAt"])
        text, timestamp, origin = newest["body"], newest["createdAt"], "/redo comment"
    else:
        headings = list(ANALYSIS_RE.finditer(issue["body"]))
        start = headings[-1].start() if headings else len(issue["body"])
        text, timestamp, origin = issue["body"][start:], issue["createdAt"], "issue body"
    return AGENT_SUMMARY_RE.split(text)[0].strip(), timestamp, origin


def parse_fields(analysis):
    """Split an Analysis section into {field name: value}."""
    spans = []
    position = 0
    for name in FIELDS:
        label = re.compile(rf"^- \*\*{re.escape(name)}:\*\*", re.MULTILINE)
        match = label.search(analysis, position)
        if match:
            spans.append((name, match.start(), match.end()))
            position = match.end()
    fields = {}
    for index, (name, _, value_start) in enumerate(spans):
        is_last = index + 1 == len(spans)
        value_end = len(analysis) if is_last else spans[index + 1][1]
        fields[name] = analysis[value_start:value_end].strip()
    return fields


def parse_report(issue):
    """Turn a tracking issue into a report dict, or None if it is not one."""
    if not TRACKING_LABELS & {label["name"] for label in issue["labels"]}:
        return None
    source = SOURCE_RE.search(issue["body"] or "")
    if not source:
        return None
    analysis, analysed_at, origin = latest_analysis(issue)
    return {
        "llvm_issue": int(source.group(1)),
        "title": re.sub(r"\s*\(llvm#\d+\)$", "", issue["title"]),
        "url": issue["url"],
        "tracker": issue["number"],
        "analysis": analysis,
        "analysed_at": analysed_at,
        "origin": origin,
        "fields": parse_fields(analysis),
    }


def group_by_llvm_issue(issues):
    """Map LLVM issue number to its reports, newest first.

    A few LLVM issues have two tracking issues, and their verdicts can differ.
    """
    grouped = {}
    for issue in issues:
        report = parse_report(issue)
        if report:
            grouped.setdefault(report["llvm_issue"], []).append(report)
    for reports in grouped.values():
        reports.sort(key=lambda report: report["analysed_at"], reverse=True)
    return grouped


def godbolt_ids(report):
    return GODBOLT_RE.findall(report["fields"].get("Godbolt Link", ""))


def godbolt_details(short_id):
    """Describe a Godbolt link, or say why it could not be read."""
    request = urllib.request.Request(
        f"https://godbolt.org/api/shortlinkinfo/{short_id}",
        headers={"User-Agent": "clang-tidy-skills", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            state = json.load(response)
    except (OSError, ValueError) as error:
        return f"(could not read this link: {error})"

    lines = []
    for session in state.get("sessions", []):
        lines.append(f"language: {session.get('language')}")
        for compiler in session.get("compilers", []):
            lines.append(f"compiler: {compiler.get('id')} {compiler.get('options')}")
            for tool in compiler.get("tools", []):
                lines.append(f"tool: {tool.get('id')} {tool.get('args')}")
        lines += ["```", session.get("source", "").rstrip(), "```"]
    return "\n".join(lines)


def print_report(report):
    date = report["analysed_at"][:10]
    print(f"# llvm#{report['llvm_issue']}: {report['title']}")
    print(f"Report: {report['url']} (from {report['origin']}, analysed {date})\n")
    print(report["analysis"])
    for short_id in godbolt_ids(report):
        print(f"\n## Godbolt {short_id}: exact source and flags behind this link\n")
        print(godbolt_details(short_id))
    print()


def cmd_show(args):
    for number in args.issues:
        found = gh_json(
            "issue", "list", "-R", TRIAGE_REPO, "--state", "all",
            "--search", f"llvm#{number} in:title",
            "--json", ISSUE_JSON, "--limit", "20",
        )
        reports = group_by_llvm_issue(found).get(number)
        if not reports:
            print(f"# llvm#{number}: no triage-agent report\n")
            continue
        for report in reports:
            print_report(report)


def tags_of(report):
    return {tag.strip() for tag in report["fields"].get("Tags", "").split(",")}


def is_selected(reports, args):
    if args.tag != "any" and not any(args.tag in tags_of(r) for r in reports):
        return False
    wanted = (args.check or "").lower()
    return any(wanted in r["fields"].get("Check Name", "").lower() for r in reports)


def verdict_cell(reports):
    verdict = reports[0]["fields"].get("Verdict", "?")
    others = {r["fields"].get("Verdict", "?") for r in reports} - {verdict}
    return f"{verdict} (other run: {', '.join(sorted(others))})" if others else verdict


def upstream_cell(issue):
    """Describe an entry of the open-issue list; None means not open."""
    if issue is None:
        return "closed"
    status = "open"
    if "false-positive" in {label["name"] for label in issue["labels"]}:
        status += ", fp-label"
    if issue["assignees"]:
        logins = ", ".join(person["login"] for person in issue["assignees"])
        status += f", assigned {logins}"
    return status


def table_row(cells):
    return "| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |"


def cmd_list(args):
    grouped = group_by_llvm_issue(
        gh_json(
            "issue", "list", "-R", TRIAGE_REPO, "--state", "all",
            "--limit", GH_LIMIT, "--json", ISSUE_JSON,
        )
    )
    open_issues = {
        issue["number"]: issue
        for issue in gh_json(
            "issue", "list", "-R", LLVM_REPO, "--label", "clang-tidy",
            "--state", "open", "--limit", GH_LIMIT,
            "--json", "number,labels,assignees",
        )
    }

    selected = [
        (number, reports)
        for number, reports in grouped.items()
        if is_selected(reports, args)
        and (args.include_closed or number in open_issues)
    ]
    selected.sort(
        key=lambda item: (
            item[1][0]["fields"].get("Verdict") != "Reproduced",
            -item[0],
        )
    )

    if not selected:
        print("No matching triage-agent reports.")
        return
    header = ["LLVM", "Verdict", "Check", "Tags", "Upstream", "Godbolt", "Report", "Title"]
    print(table_row(header))
    print(table_row(["---"] * len(header)))
    for number, reports in selected:
        newest = reports[0]
        check = newest["fields"].get("Check Name", "?").split(" (")[0].replace("`", "")
        links = " ".join(f"https://godbolt.org/z/{i}" for i in godbolt_ids(newest))
        print(
            table_row(
                [
                    f"#{number}",
                    verdict_cell(reports),
                    check[:60],
                    newest["fields"].get("Tags", "?"),
                    upstream_cell(open_issues.get(number)),
                    links or "N/A",
                    f"#{newest['tracker']}",
                    newest["title"],
                ]
            )
        )
    print(f"\n{len(selected)} LLVM issue(s). Use `show <number>` for full reports.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    show = commands.add_parser("show", help="Print reports for specific LLVM issues")
    show.add_argument("issues", type=int, nargs="+", help="LLVM issue numbers")
    show.set_defaults(run=cmd_show)

    listing = commands.add_parser("list", help="Print a table of reports")
    listing.add_argument(
        "--tag",
        default="false-positive",
        help="Only reports with this tag, or 'any' (default: false-positive)",
    )
    listing.add_argument("--check", help="Only reports whose check name contains this")
    listing.add_argument(
        "--include-closed",
        action="store_true",
        help="Also include LLVM issues that are no longer open",
    )
    listing.set_defaults(run=cmd_list)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
