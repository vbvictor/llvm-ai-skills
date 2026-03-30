---
name: batch-fix-clang-tidy-fp
description: Read issues from a triage markdown file and fix them all one by one, creating a branch per fix. Produces a final report of all branches and results.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Agent
---

# Batch Fix Clang-Tidy False Positives

You are an expert LLVM/clang-tidy contributor. Your job is to read a triage report file, then fix every issue in it one by one -- each on its own branch.

**CRITICAL: NEVER push, merge, or create PRs. NEVER run `git push`, `git merge`, `gh pr create`. You ONLY create local branches via the helper scripts.**

## Configuration

- **LLVM repo**: The user will provide or it defaults to `/home/victor/repos/addon-llvm/llvm-project`
- **Scripts directory**: Relative to this skill at `scripts/`
- **Tracker file**: `/tmp/clang-tidy-batch-fix-tracker.json` (auto-managed by scripts)

## Step 0: Read Reference Material

Read `references/bugfix-patterns.md` for root cause taxonomy, fix strategies, test patterns, and conventions.

## Step 1: Read the Triage File

The user will provide a path to a triage markdown file (produced by `/triage-clang-tidy-fp`). If not provided, look for the most recent file matching `/tmp/clang-tidy-fp-triage-*.md`.

```bash
ls -t clang-tidy-fp-triage-*.md 2>/dev/null | head -1
```

Parse the "Detailed Analysis" section to extract for each issue:
- **Issue number**
- **Title**
- **Check name**
- **Reproducer** (description or code)
- **Root cause**
- **Fix strategy**
- **Difficulty**
- **URL**

Print the list of issues you will attempt and ask the user to confirm before proceeding.

## Step 2: Clean Start

Delete any previous tracker file and ensure you are on `main` with a clean tree:

```bash
rm -f /tmp/clang-tidy-batch-fix-tracker.json
cd <LLVM_REPO> && git checkout main && git status --porcelain
```

If the tree is dirty, **STOP and ask the user** to clean it up.

## Step 3: Fix Each Issue

For each issue from the triage file, execute this loop:

### 3a. Start the Branch

```bash
python3 <SKILLS_DIR>/scripts/branch_start.py <ISSUE_NUMBER> --repo-dir <LLVM_REPO>
```

This creates branch `fix-<ISSUE_NUMBER>` and switches to it.

### 3b. Analyze the Issue

Read the full issue including all comments:

```bash
gh issue view <NUMBER> -R llvm/llvm-project --json title,body,comments
```

Pay close attention to discussion hints, contributor suggestions, and "I'm working on this" claims. If someone claimed it since triage, **skip this issue**.

### 3c. Locate and Understand the Check

Convert check name to file paths and read:
- Source: `clang-tools-extra/clang-tidy/<module>/<CheckName>Check.cpp`
- Header: `clang-tools-extra/clang-tidy/<module>/<CheckName>Check.h`
- Test: `clang-tools-extra/test/clang-tidy/checkers/<module>/<check-name>.cpp`

### 3d. Check Existing Options

Before fixing, verify this is a real bug:
- Look at `storeOptions()` and `Options.get()` in the check
- Read the check's `.rst` documentation
- If an existing option handles the case, **skip this issue**

### 3e. Write Tests FIRST

Append test cases to the existing test file:
1. **Regression test** (false positive case -- should NOT warn after fix)
2. **Preservation test** (should still warn on real issues)

### 3f. Verify Tests Fail on Unpatched Build

```bash
cmake --build build --target clang-tidy -j$(nproc)
python build/bin/llvm-lit -v <TEST_FILE>
```

**The test MUST fail here.** If it passes, the tests don't reproduce the bug -- fix them or skip.

### 3g. Implement the Fix

Apply the fix strategy. Keep changes minimal (5-30 lines typically).

Update release notes in `clang-tools-extra/docs/ReleaseNotes.rst`.

### 3h. Format Source Files

Run `clang-format` on check source files only (NOT tests):

```bash
git diff --name-only | grep 'clang-tidy/.*\.\(cpp\|h\)$' | grep -v '/test/' | xargs -r clang-format -i
```

### 3i. Build and Verify Fix

```bash
cmake --build build --target clang-tidy -j$(nproc)
python build/bin/llvm-lit -v <TEST_FILE>
```

**The test MUST pass now.**

### 3j. Finish the Branch

On **success**:
```bash
python3 <SKILLS_DIR>/scripts/branch_finish.py <ISSUE_NUMBER> \
  --status success \
  --title "<issue title>" \
  --summary "<what was fixed and how>" \
  --files-changed "<comma-separated file list>" \
  --repo-dir <LLVM_REPO>
```

On **skip** (by-design, already claimed, existing option covers it):
```bash
python3 <SKILLS_DIR>/scripts/branch_finish.py <ISSUE_NUMBER> \
  --status skipped \
  --title "<issue title>" \
  --summary "<reason for skipping>" \
  --repo-dir <LLVM_REPO>
```

On **failure** (couldn't fix, tests don't pass, too complex):
```bash
python3 <SKILLS_DIR>/scripts/branch_finish.py <ISSUE_NUMBER> \
  --status failed \
  --title "<issue title>" \
  --summary "<what went wrong>" \
  --repo-dir <LLVM_REPO>
```

The script commits (on success), switches back to `main`, and logs to the tracker.

### 3k. Proceed to Next Issue

Repeat from 3a for the next issue. You are now back on `main` with a clean tree.

## Step 4: Generate Final Report

After all issues are processed, generate the report:

```bash
python3 <SKILLS_DIR>/scripts/report.py \
  --output /tmp/clang-tidy-batch-fix-report-$(date +%Y-%m-%d).md
```

Print the full report contents to the user and the file path.

---

## Important Rules

- **One branch per issue**. Branch name is always `fix-<issue_number>`.
- **Always return to main**. Never start a new fix while on a fix branch.
- **Use the scripts**. Always use `branch_start.py` and `branch_finish.py` -- never run raw git branch/checkout/commit commands yourself.
- **Never push or create PRs**. Only local branches.
- **Tests first, fix second**. Write tests, verify they fail, then fix.
- **Skip gracefully**. If an issue turns out to be by-design or too hard, use `--status skipped` and move on. Don't get stuck.
- **Minimal changes only**. Don't refactor, don't add comments to unchanged code.
- **Always update release notes** for successful fixes.
- **clang-format source, not tests**. Run clang-format only on check `.cpp`/`.h` files.
