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

The user will provide a path to a triage markdown file (produced by `/triage-clang-tidy-fp`). If not provided, look for the most recent one:

```bash
ls -t /tmp/clang-tidy-fp-triage-*.md 2>/dev/null | head -1
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

### 3.1 Start the Branch

```bash
python3 <SKILLS_DIR>/scripts/branch_start.py <ISSUE_NUMBER> --repo-dir <LLVM_REPO>
```

This creates branch `fix-<ISSUE_NUMBER>` and switches to it.

### Step 3.2: Analyze the Issue

Read the full issue **including all comments**:

```bash
gh issue view <NUMBER> -R llvm/llvm-project --json title,body,comments
```

Extract:
- **Check name**: e.g., `readability-non-const-parameter`
- **Reproducer code**: the C++ snippet that triggers the false positive
- **Expected behavior**: no warning (or different warning)
- **Actual behavior**: incorrect warning emitted

### Read the Discussion Carefully

Pay close attention to comments from:
- **The issue author** -- may have additional reproducers, clarifications, or narrowed-down root causes
- **LLVM contributors** -- may have suggestions for fix approaches, point to related code, or mention caveats
- **Anyone saying "I think the issue is..."** -- leading questions and hypotheses from experienced contributors are valuable hints

Incorporate any suggestions or constraints from the discussion into your fix strategy.

### Step 3.3: Locate and Understand the Check

Convert check name (kebab-case) to file paths:
- Check name `readability-non-const-parameter` -> module `readability`, class `NonConstParameter`
- Source: `clang-tools-extra/clang-tidy/readability/NonConstParameterCheck.cpp`
- Header: `clang-tools-extra/clang-tidy/readability/NonConstParameterCheck.h`
- Test: `clang-tools-extra/test/clang-tidy/checkers/readability/non-const-parameter.cpp`

Read the full check implementation (`.cpp` and `.h`). Understand:
1. What matchers are registered in `registerMatchers()`
2. What logic runs in `check()`
3. What traversal kind is used (default `TK_AsIs` vs `TK_IgnoreUnlessSpelledInSource`)
4. What AST node types are handled

Read existing tests to understand the check's expected behavior.

### Check if Existing Options Already Cover This

Before concluding this is a bug, check whether the check already has **configuration options** that address the reporter's scenario:

1. Look at `storeOptions()` and `Options.get()`/`Options.getLocalOrGlobal()` calls in the check implementation
2. Read the check's `.rst` documentation for documented options
3. Check if enabling/disabling an existing option resolves the reported false positive

**If an existing option already handles the case**, this is likely **by design**, not a bug. Report this to the user and suggest picking a different issue. Examples:
- `IgnoreNonDeducedTemplateTypes` already exists for template-related FPs
- `AllowedTypes` / `AllowedFunctions` patterns let users suppress specific cases
- The check may intentionally warn on a pattern that looks wrong per the coding guideline

Only proceed to fix if there is **no existing option** that addresses the false positive, or if the false positive occurs even with correct option configuration.

### Step 3.4: Reproduce and Diagnose

Create a minimal reproducer file and run clang-tidy on it:

```bash
# Write the reproducer
cat > /tmp/fp_repro.cpp << 'EOF'
<reproducer code from the issue>
EOF

# Run clang-tidy
./build/bin/clang-tidy -checks='-*,<check-name>' /tmp/fp_repro.cpp -- -std=c++20
```

If no build directory exists, skip this step and work from code analysis alone.

Use `clang -Xclang -ast-dump` to understand the AST structure of the reproducer:

```bash
./build/bin/clang -Xclang -ast-dump -fsyntax-only -std=c++20 /tmp/fp_repro.cpp 2>/dev/null | head -200
```

### Step 3.5: Write Tests FIRST (Before the Fix)

Write the test cases **before** modifying the check code. This ensures we can verify the bug reproduces.

Append test cases to the existing test file. Include:

1. **Regression test** (the false positive case -- should NOT warn after the fix):
```cpp
<reproducer code>
```

2. **Preservation test** (verify the check still catches real issues):
```cpp
<code that SHOULD trigger the warning>
// CHECK-MESSAGES: :[[@LINE-1]]:N: warning: <full diagnostic>
```

If a new language standard is needed, create a new test file with the appropriate `-std=c++NN-or-later` flag.

### Step 3.6: Verify Tests Fail on Unpatched Build

Run the tests against the **current unpatched** clang-tidy to confirm they reproduce the bug:

```bash
# Build unpatched clang-tidy (only tests were modified, not the check)
cmake --build build --target clang-tidy -j$(nproc)

# Run the test -- it MUST FAIL (proving the false positive exists)
python build/bin/llvm-lit -v clang-tools-extra/test/clang-tidy/checkers/<module>/<test-file>.cpp
```

**The test MUST fail here.** If it passes, your test cases don't actually reproduce the reported false positive. Go back to Step 5 and fix the tests.

Only proceed once you've confirmed the test failure matches the reported issue (e.g., unexpected warning on the regression test case).

### Step 3.7: Determine Root Cause and Fix Strategy

Based on the analysis, classify the root cause (from `references/bugfix-patterns.md`):

1. **Template/dependent context** -> Strategy 1 (add `unless(...)`) or Strategy 2 (`TK_IgnoreUnlessSpelledInSource`)
2. **Macro expansion** -> Strategy 5 (rewrite with raw lexer)
3. **Missing AST node handling** -> Strategy 4 (handle new node types)
4. **Incomplete type/forward decl** -> Strategy 3 (add guard)
5. **Bad FixIt** -> Strategy 6 (use `tooling::fixit::*`)
6. **Crash on input** -> Strategy 7 (fix input handling)

### Step 3.8: Implement the Fix

### Modify the check implementation

Apply the chosen fix strategy. Keep changes minimal -- typically 5-30 lines of check code.

Common patterns:
- Add `unless(isInstantiationDependent())` to matcher
- Add `unless(isInTemplateInstantiation())` to matcher
- Override `getCheckTraversalKind()` to return `TK_IgnoreUnlessSpelledInSource`
- Add null/definition guard: `if (!Record->getDefinition()) return;`
- Handle new AST node type in `check()` method
- Add `isDependentType()` guard

### Update release notes

Add an entry in `clang-tools-extra/docs/ReleaseNotes.rst` under "Changes in existing checks", in alphabetical order:

```rst
- Improved :doc:`<check-name>
  <clang-tidy/checks/<module>/<check-name>>` check by fixing a false
  positive when <description>.
```

### Step 3.9: Format, Build, and Verify Fix

**Before building**, run `clang-format` on any check source files you changed (NOT test files -- tests have their own formatting conventions):

```bash
git diff --name-only | grep 'clang-tidy/.*\.\(cpp\|h\)$' | grep -v '/test/' | xargs -r clang-format -i
```

Then build and run tests:

```bash
# Build and run all tests
ninja -C build check-clang-tools

# Verify the fix with the reproducer
./build/bin/clang-tidy -checks='-*,<check-name>' /tmp/fp_repro.cpp -- -std=c++20
```

If build/test fails, diagnose and fix. Common issues:
- Missing includes in test file
- Incorrect CHECK-MESSAGES line numbers
- Matcher syntax errors

### Step 3.10. Finish the Branch

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

### Step 3.11. Proceed to Next Issue

Repeat from 3.1 for the next issue. You are now back on `main` with a clean tree.

## Step 4: Generate Final Report

After all issues are processed, generate the report to `/tmp/` then copy to the user's working directory:

```bash
python3 <SKILLS_DIR>/scripts/report.py \
  --output /tmp/clang-tidy-batch-fix-report-$(date +%Y-%m-%d).md

# Copy to user's working directory
cp /tmp/clang-tidy-batch-fix-report-$(date +%Y-%m-%d).md ./
```

Print the full report contents to the user and both file paths.

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
