---
name: triage-clang-tidy-fp
description: Search for open clang-tidy false-positive issues on GitHub, deep-analyze each candidate, and present 10 fixable issues with root cause and fix strategy.
allowed-tools: Bash, Read, Write, Grep, Glob, Agent
---

# Triage Clang-Tidy False Positive Issues

You are an expert LLVM/clang-tidy contributor. Your job is to search for open false-positive issues, deeply analyze each one, filter out non-fixable or already-handled cases, and present 10 actionable issues to the user.

**NEVER commit, push, or create PRs. The only file you write is the output report.**

## Step 0: Read Reference Material

`<SHARED_DIR>` is the `_shared` directory next to this skill's directory (`<this skill's directory>/../_shared`).

Read `<SHARED_DIR>/references/bugfix-patterns.md` to load the taxonomy of root causes, fix strategies, and file organization. You need this to assess feasibility.

Read `<SHARED_DIR>/references/triage-agent-reports.md` to learn how to use the triage-agent's reports and how far to trust them.

## Step 1: Gather Candidate Issues

Search GitHub for open issues. Cast a wide net -- you will filter aggressively later.

```bash
# Primary: both labels
gh issue list -R llvm/llvm-project --label "clang-tidy" --label "false-positive" \
  --state open --limit 50 --json number,title,updatedAt,url,assignees

# Secondary: clang-tidy label, FP-related titles
gh issue list -R llvm/llvm-project --label "clang-tidy" --state open \
  --limit 80 --json number,title,updatedAt,url,assignees
```

Also list the triage-agent's reports. This finds issues the searches above miss, because the bot tags issues that have no `false-positive` label upstream:

```bash
python3 <SHARED_DIR>/scripts/triage_reports.py list
```

From all three sources, build a deduplicated list of candidates whose titles suggest false positives, incorrect warnings, or spurious diagnostics. Favor issues with a `Reproduced` report, since they already have a working reproducer.

## Step 2: Deep-Analyze Each Candidate

For each candidate (aim for 15-25 to ensure you end up with 10 good ones), run this analysis **in parallel using Agent subagents** where possible. Give each subagent the absolute path of `<SHARED_DIR>`, because it cannot resolve that on its own:

### 2a. Read the Full Issue

```bash
gh issue view <NUMBER> -R llvm/llvm-project --json title,body,comments,assignees,labels
python3 <SHARED_DIR>/scripts/triage_reports.py show <NUMBER>
```

Extract:
- **Check name** (e.g., `bugprone-*`, `readability-*`)
- **Reproducer code** -- must exist and be clear. The Godbolt source in a triage-agent report counts
- **Discussion hints** -- any suggestions from contributors, root cause theories, or "I'm working on this" claims
- **Triage-agent report** -- verdict, Godbolt link, flags, Rationale and Similar Issues, if a report exists

**Disqualify** if the report's verdict rules the issue out, per the table in `<SHARED_DIR>/references/triage-agent-reports.md`.

### 2b. Verify No One is Working on It

```bash
gh pr list -R llvm/llvm-project --state open --search "<NUMBER>" --limit 5 --json number,title,url
```

Also check the issue's comments for linked PRs or "I'll take this" messages.

**Disqualify** if assigned or has an active PR.

### 2c. Check if Existing Options Already Handle It

Read the check's implementation (`.cpp` and `.h`) and documentation (`.rst`):
- Look at `storeOptions()` and `Options.get()`/`Options.getLocalOrGlobal()` calls
- Check if an existing option resolves the reported false positive
- Check if the behavior is intentional per the coding guideline the check enforces

**Disqualify** if an existing option already addresses the reporter's scenario. Note what the option is.

### 2d. Classify Root Cause and Fix Strategy

Based on the reproducer and the check code, classify using the taxonomy from `<SHARED_DIR>/references/bugfix-patterns.md`. If there is a triage-agent report, start from its Rationale, then confirm it against the check code. If they disagree, trust the code:

| Root Cause | Likely Fix Strategy |
|------------|-------------------|
| Template/dependent context | Add `unless(...)` or switch to `TK_IgnoreUnlessSpelledInSource` |
| Macro expansion | Rewrite with raw lexer |
| Missing AST node handling | Handle new node types in `check()` |
| Incomplete type/forward decl | Add null/definition guard |
| Bad FixIt | Use `tooling::fixit::*` |
| Crash on input | Fix input handling |

### 2e. Assess Feasibility

Rate as **easy**, **medium**, or **hard**:

- **Easy**: Add `unless(...)` to matcher, add guard condition, handle one new AST node type. Typically 5-15 lines of check code.
- **Medium**: Rewrite part of the matching logic, handle multiple AST node types, fix FixIt generation. 15-40 lines.
- **Hard**: Fundamental redesign, dataflow analysis needed, cross-TU concerns, or ambiguous whether it's a real bug. Skip these.

**Disqualify** issues rated "hard".

## Step 3: Present the Top 10

After filtering, present **exactly 10** issues to the user in a table format:

```
| # | Issue | Check | Problem | Root Cause | Fix Strategy | Difficulty | Godbolt |
|---|-------|-------|---------|-----------|-------------|-----------|---------|
| 1 | #XXXXX title | `check-name` | one-line description | category | strategy | easy/medium | link or N/A |
```

For each issue, also include a **2-3 sentence analysis** below the table:

> **#XXXXX**: The check warns on `<pattern>` because `<root cause>`. Fix: `<strategy>`. The check has no existing option for this case. Discussion mentions `<any useful hints>`. Triage-agent: `<verdict>` on `<analysed date>`, or no report. Say so if your root cause differs from its Rationale.

### Disqualified Issues

After the main table, briefly list issues you examined but disqualified, with the reason:
- `#XXXXX` -- already has PR #YYYYY
- `#XXXXX` -- covered by existing `OptionName` option
- `#XXXXX` -- requires fundamental redesign of check
- `#XXXXX` -- no clear reproducer
- `#XXXXX` -- assigned to @username
- `#XXXXX` -- triage-agent could not reproduce it on YYYY-MM-DD

This helps the user understand your filtering and catch any mistakes.

## Step 4: Write the Report File

Save the full report as a markdown file at `/tmp/clang-tidy-fp-triage-YYYY-MM-DD.md` (using today's date). Writing to `/tmp/` avoids dirtying the LLVM repo working tree for downstream batch-fix workflows.

The file should contain everything from Step 3 in proper markdown format:

```markdown
# Clang-Tidy False Positive Triage — YYYY-MM-DD

## Fixable Issues (10)

| # | Issue | Check | Problem | Root Cause | Fix Strategy | Difficulty | Godbolt |
|---|-------|-------|---------|-----------|-------------|-----------|---------|
| 1 | [#XXXXX](url) title | `check-name` | ... | ... | ... | easy | [link](url) |
...

### Detailed Analysis

#### 1. #XXXXX — title
- **Check**: `check-name`
- **Reproducer**: (brief description or code snippet)
- **Godbolt**: https://godbolt.org/z/XXXXXXXXX, with its compiler flags (or N/A)
- **Triage-agent report**: [#NNN](url), `<verdict>`, analysed YYYY-MM-DD (or none)
- **Root cause**: ...
- **Fix strategy**: ...
- **Difficulty**: easy/medium
- **Discussion notes**: ...
- **URL**: https://github.com/llvm/llvm-project/issues/XXXXX

...repeat for all 10...

## Disqualified Issues

- [#XXXXX](url) — reason
- [#XXXXX](url) — reason
...
```

After writing, copy the report to the current working directory so the user has it handy:

```bash
cp /tmp/clang-tidy-fp-triage-YYYY-MM-DD.md ./
```

Print both paths.

## Important Rules

- **No repo modifications**. Reports go to `/tmp/` first, then get copied to cwd. Do not run git commands that change state.
- **Be thorough**. Read the actual check code for each candidate, don't guess from the title alone.
- **Be honest about difficulty**. If something looks hard, say so. Don't inflate the list with dubious candidates.
- **Parallelize**. Use Agent subagents to analyze multiple issues concurrently. This skill is research-heavy.
- **Check options first**. The #1 mistake is treating "by design" behavior as a bug.
- **Verify triage-agent reports**. They are machine-generated hints that can be wrong or stale. Confirm them against the check code and your own build.
- **Never write to `clang-tidy-infra/triage-agent`**. No comments, no closing, no `/redo`. If a report looks wrong or stale, tell the user.
