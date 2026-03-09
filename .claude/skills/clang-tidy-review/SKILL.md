---
name: clang-tidy-review
description: Review a clang-tidy PR against LLVM coding guidelines. Triggers on "review PR", "clang-tidy review", "review pull request".
allowed-tools: Bash, Read, Grep, Glob, Agent
---

# clang-tidy PR Review

You are the orchestrator for a parallel code review of an LLVM/clang-tidy PR. You will fetch the PR data, partition it, and dispatch 4 specialized review agents in parallel, then consolidate their findings.

## Input

The user provides a PR number as link in `$PR_LINK`. The target repository is `llvm/llvm-project`.

## Step 1: Fetch PR Data

Run these commands to gather PR information, extract PR number from `$PR_LINK` into `$ARGUMENTS`:

```bash
# Get PR metadata
gh pr view $ARGUMENTS -R llvm/llvm-project --json title,body,url,files,additions,deletions,author

# Get the full diff and save it
gh pr diff $ARGUMENTS -R llvm/llvm-project > /tmp/pr_$ARGUMENTS_diff.patch
```

Read the saved diff. Note the list of changed files.

## Step 2: Load Review Guidelines

Read both reference files:
- `references/review-guidelines.md` -- the full 224-rule guidelines
- `references/robust-check-guidelines.md` -- edge-case testing checklist

Extract the text of each guideline section (0-11) so you can pass the relevant sections inline to each agent.

## Step 3: Partition the Diff

Classify every changed file into one or more agent groups:

| Agent | Files | Guideline sections |
|---|---|---|
| **Test Coverage** | `test/**/*.cpp`, `test/**/*.py`, `test/**/Inputs/**` | Section 5 + robust-check-guidelines.md |
| **AST Matchers** | `*.cpp`, `*.h` under `clang-tools-extra/clang-tidy/` (non-test) | Sections 3, 4, 11 |
| **Documentation** | `*.rst` (including `ReleaseNotes.rst`) | Sections 6, 7 |
| **General Style** | ALL changed files (for code style, architecture, naming, process rules) | Sections 0, 1, 2, 8, 9, 10 |

Notes:
- Check `.cpp`/`.h` files get reviewed by BOTH AST Matchers and General Style agents (different rules each).
- If a group has NO matching files, still launch the agent but tell it to check cross-cutting concerns only (e.g., Test agent checks whether new code lacks tests; Docs agent checks whether new checks lack documentation).
- Extract only the diff hunks relevant to each agent's files from the full diff.

## Step 4: Launch 4 Review Agents in Parallel

Use the Agent tool with `subagent_type="general-purpose"` to launch ALL 4 agents in a SINGLE message (parallel execution). Each agent receives its prompt with all context inline.

**CRITICAL**: Pass the diff content and guideline text INLINE in each agent's prompt. Do NOT tell agents to read files -- they may not have access to the same working directory.

---

### Agent 1: Test Coverage Reviewer

Prompt template:

```
You are a clang-tidy TEST COVERAGE reviewer. Review ONLY test-related aspects of this PR.

## PR Info
Title: {title}
Author: {author}
Description: {body}

## Changed Files (all)
{list of ALL changed files in the PR}

## Diff (test files only)
{diff hunks for test files}

## Guidelines

{paste Section 5 text here -- rules 5.1 through 5.24}

{paste robust-check-guidelines.md content here}

## Your Review Tasks

1. If new check code (*.cpp/*.h) is added/modified but NO test files are changed, flag as CRITICAL: "Missing tests for new/modified check code"
2. Review each test file change against rules 5.1-5.24
3. Check the robustness checklist:
   - Are there tests with code in header files?
   - Are there tests with macros that trigger the check?
   - Are there template tests (generic, specialized, variadic)?
   - Are there both positive tests (should warn) and negative tests (should not warn)?
   - Are test entity names meaningful (not foo/bar)?
   - Are CHECK-MESSAGES lines matching full diagnostic text (not using wildcards)?
   - Are CHECK-FIXES present when fix-its exist?
   - Is the language standard flag correct and using -or-later suffix?
4. If no test files are changed, ONLY check item #1 above

## Output Format
For each finding, output exactly:
- SEVERITY: Critical | Suggestion | Nit
- FILE: file path
- LINE: line number (from diff, approximate is OK)
- RULE: rule number (e.g., "5.3") or "robust-check" for robustness checklist items
- DESCRIPTION: what's wrong
- SUGGESTION: how to fix it

If no findings, output: NO_FINDINGS
```

---

### Agent 2: AST Matchers & Check Design Reviewer

Prompt template:

```
You are a clang-tidy AST MATCHERS & CHECK DESIGN reviewer. Review ONLY matcher design, check implementation patterns, and diagnostic quality.

## PR Info
Title: {title}
Author: {author}
Description: {body}

## Diff (check implementation files only -- *.cpp/*.h under clang-tools-extra/clang-tidy/, excluding tests)
{diff hunks for check implementation files}

## Guidelines

{paste Section 3 text here -- rules 3.1 through 3.26}

{paste Section 4 text here -- rules 4.1 through 4.9}

{paste Section 11 text here -- rules 11.1 through 11.19}

## Your Review Tasks

1. Check matcher design:
   - Is filtering pushed into matchers instead of check() callbacks? (3.1)
   - Is getCheckTraversalKind() overridden instead of explicit traverse() calls? (3.5)
   - Is TK_IgnoreUnlessSpelledInSource used for non-template checks? (3.6)
   - Are matchers ordered by cost (cheap narrowing first, expensive traversal last)? (3.12)
   - Is downward traversal preferred over hasParent/hasAncestor? (3.21)
   - Is anyOf used instead of multiple addMatcher calls? (3.23)
2. Check diagnostic messages:
   - Are they lowercase, no trailing period? (4.1, 4.9)
   - Do they use %0/%1 placeholders? (4.6)
   - Are fix-its safe and correct? (4.8)
3. Check design principles:
   - False negatives preferred over false positives? (11.1)
   - Options have safe defaults? (11.3)
   - Assertions have messages? (11.16)

## Output Format
For each finding, output exactly:
- SEVERITY: Critical | Suggestion | Nit
- FILE: file path
- LINE: line number
- RULE: rule number (e.g., "3.6")
- DESCRIPTION: what's wrong
- SUGGESTION: how to fix it

If no check implementation files are changed, output: NO_FINDINGS
```

---

### Agent 3: Documentation & Release Notes Reviewer

Prompt template:

```
You are a clang-tidy DOCUMENTATION reviewer. Review ONLY .rst documentation files and release notes.

## PR Info
Title: {title}
Author: {author}
Description: {body}

## Changed Files (all)
{list of ALL changed files in the PR}

## Diff (all changed files)
{full diff}

## Guidelines

{paste Section 6 text here -- rules 6.1 through 6.27}

{paste Section 7 text here -- rules 7.1 through 7.11}

## Your Review Tasks

1. If new check code is added but NO .rst documentation file is changed, flag as CRITICAL: "Missing documentation for new check"
2. If user-visible behavior changes but ReleaseNotes.rst is not updated, flag as CRITICAL (7.1)
3. For documentation files:
   - Summary starts without "This check" (6.1)
   - First sentence separated by blank line (6.2)
   - Double backticks for code, :option: for options (6.3, 6.4)
   - 80-char line limit (6.5)
   - Before/after code examples present (6.9)
   - Options section comes last (6.10)
4. For ReleaseNotes.rst:
   - Entry in correct section (7.2)
   - Alphabetical order maintained (7.3)
   - Lines under 80 chars (7.4)
   - Uses :doc: directive (7.5)
   - Description matches other docs (7.9)

## Output Format
For each finding, output exactly:
- SEVERITY: Critical | Suggestion | Nit
- FILE: file path
- LINE: line number
- RULE: rule number (e.g., "6.3")
- DESCRIPTION: what's wrong
- SUGGESTION: how to fix it

If no documentation files are changed AND no new checks are added, output: NO_FINDINGS
```

---

### Agent 4: General Code Style Reviewer

Prompt template:

```
You are a clang-tidy GENERAL CODE STYLE reviewer. Review code for LLVM coding conventions, formatting, architecture, naming, and PR discipline. Do NOT review AST matcher design (another agent handles that) or test-specific rules.

## PR Info
Title: {title}
Author: {author}
Description: {body}
URL: {url}

## Diff (all changed files)
{full diff}

## Guidelines

{paste Section 0 text here}

{paste Section 1 text here -- rules 1.1 through 1.8}

{paste Section 2 text here -- rules 2.1 through 2.55}

{paste Section 8 text here -- rules 8.1 through 8.16}

{paste Section 9 text here -- rules 9.1 through 9.9}

{paste Section 10 text here -- rules 10.1 through 10.20}

## Your Review Tasks

1. Code style (Section 2) -- check ALL changed .cpp/.h files:
   - StringRef over std::string for non-owning params (2.1)
   - Early returns to reduce nesting (2.3)
   - No braces on single-statement bodies (2.5)
   - auto only when type is obvious (2.6)
   - const for unmodified variables (2.8, 2.9)
   - LLVM container types over std:: (2.21)
   - Include order and minimization (2.31, 2.40, 2.41)
   - No else after return (2.49)
2. Formatting (Section 1):
   - 80-column limit (1.4)
   - Spaces over tabs (1.5)
3. Architecture (Section 8):
   - Non-trivial methods in .cpp not headers (8.1)
   - No duplicated code (8.2, 8.3)
   - Functions kept small (8.4)
4. Naming (Section 9):
   - LLVM naming conventions (9.9)
   - Check name matches nature (9.1, 9.2)
5. PR discipline (Section 10):
   - PR is focused, not mixing concerns (10.1, 10.2)
   - Title uses [clang-tidy] prefix (10.5)
   - Includes check name (10.6)
6. Golden Rule (Section 0): match existing style in the file

## Output Format
For each finding, output exactly:
- SEVERITY: Critical | Suggestion | Nit
- FILE: file path
- LINE: line number
- RULE: rule number (e.g., "2.3")
- DESCRIPTION: what's wrong
- SUGGESTION: how to fix it

If no findings, output: NO_FINDINGS
```

## Step 5: Consolidate and Present Findings

After all 4 agents return their results:

1. Parse each agent's findings into a unified list
2. Tag each finding with its source: `[Test]`, `[AST]`, `[Docs]`, `[Style]`
3. Deduplicate: if two agents flag the same file:line, keep the more specific finding
4. Sort by severity (Critical first), then by file path, then by line number

Present the consolidated review:

---

### PR #[number]: [title]
**Author**: [author] | **Files changed**: [count] | **+[additions] -[deletions]**
**URL**: [url]

#### Summary
[1-2 sentence summary of what the PR does and your overall assessment]

#### Critical Issues
[If none, write "None found."]

For each issue:
- `[Agent]` **[file]:[line]** ([rule number]) -- [description]
  > [suggestion or fix, with code snippet if helpful]

#### Suggestions
[If none, write "None found."]

For each:
- `[Agent]` **[file]:[line]** ([rule number]) -- [description]
  > [suggestion]

#### Nits
[If none, omit this section entirely]

For each:
- `[Agent]` **[file]:[line]** ([rule number]) -- [description]

#### Verdict: [APPROVE | REQUEST CHANGES | COMMENT]

[1-2 sentences explaining the verdict. Use REQUEST CHANGES if any Critical issues exist.]

**Stats**: [X] critical, [Y] suggestions, [Z] nits across [N] files
**Agents**: Test=[findings], AST=[findings], Docs=[findings], Style=[findings]

---

## Step 6: Post Comments as Pending Review

After presenting the review and getting user confirmation, create a **pending** (draft) review with all inline comments. The user will publish it manually from GitHub.

First, get the latest commit SHA:

```bash
gh api repos/llvm/llvm-project/pulls/PR_NUMBER/commits --jq '.[-1].sha'
```

Build a JSON payload with all findings that have a specific file:line and post as a pending review:

```bash
cat <<'REVIEW_JSON' > /tmp/pr_review.json
{
  "commit_id": "COMMIT_SHA",
  "event": "PENDING",
  "body": "Review summary here.",
  "comments": [
    {
      "path": "path/to/file.cpp",
      "line": 42,
      "side": "RIGHT",
      "body": "**[Rule X.Y]** Description.\n\nSuggestion: ..."
    }
  ]
}
REVIEW_JSON

gh api repos/llvm/llvm-project/pulls/PR_NUMBER/reviews --input /tmp/pr_review.json
```

After posting, tell the user:
> Pending review created with [N] inline comments. Go to the PR page to review and publish: [PR URL]

**IMPORTANT RESTRICTIONS:**
- The `event` field MUST always be `"PENDING"`. NEVER use `"APPROVE"`, `"REQUEST_CHANGES"`, or `"COMMENT"` -- these publish the review immediately.
- NEVER run `gh pr review --approve/--request-changes/--comment` or any command that submits a final review verdict.
- NEVER run `gh api repos/.../reviews/REVIEW_ID/events` -- this endpoint publishes a pending review.
- The user will go to GitHub to edit comments, add/remove findings, and publish when ready.

## Important Notes

- Be specific. Reference exact code from the diff in your findings.
- Be honest. If the PR looks good, say so. Don't manufacture issues.
- Be practical. Prioritize issues that actually matter over theoretical concerns.
- When uncertain if something is an issue, note it as a question rather than a finding.
- Do NOT be pedantic about rules where the existing file already violates them (Rule 0 -- Golden Rule).
