---
name: fix-clang-tidy-fp
description: Find and fix false positive bugs in clang-tidy checks. Picks an open GitHub issue, analyzes the root cause, writes tests, verifies they reproduce the bug, then implements the fix.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Agent, WebFetch, WebSearch
---

# Fix Clang-Tidy False Positives

You are an expert LLVM/clang-tidy contributor. Your job is to find an open false-positive issue, write tests that reproduce it, and implement a fix -- all autonomously.

**CRITICAL: NEVER commit, push, create branches, or create PRs. NEVER run `git add`, `git commit`, `git push`, `git checkout -b`, `gh pr create`, or any similar git/gh commands that modify the repository state. Your job ends at writing code and verifying tests pass. The user will handle all git operations themselves.**

## Configuration

## Step 0: Read Reference Material

Read `references/bugfix-patterns.md` to load the taxonomy of root causes, fix strategies, test patterns, and conventions. This is critical context for every step below.

## Step 1: Find an Issue to Fix

Search GitHub for open issues with **both** `clang-tidy` and `false-positive` labels:

```bash
gh issue list -R llvm/llvm-project --label "clang-tidy" --label "false-positive" \
  --state open --limit 50 --json number,title,updatedAt,url,assignees
```

If that yields too few results, also try the `clang-tidy` label alone and filter for FP-related titles:

```bash
gh issue list -R llvm/llvm-project --label "clang-tidy" --state open \
  --limit 50 --json number,title,updatedAt,url,assignees
```

### Verify No One is Working on It

For each candidate issue, **before selecting it**, check:

1. **Not assigned**:
```bash
gh issue view <NUMBER> -R llvm/llvm-project --json assignees,labels
```

2. **No open PR already targets it** -- search for linked PRs:
```bash
gh pr list -R llvm/llvm-project --state open --search "<NUMBER>" --limit 5 --json number,title,url
```
Also look at the issue's timeline/comments for "I'm working on this" or linked PR references.

### Issue Selection Criteria

Filter for issues that:
1. Have a clear reproducer (C++ code that triggers the false positive)
2. Identify a specific check name (e.g., `bugprone-*`, `readability-*`)
3. Are **not assigned** and have **no open PR** targeting them
4. Look feasible based on the bugfix patterns (template handling, matcher exclusion, guard condition, etc.)
5. Preferably have recent activity (updated in last 6 months)

**Skip issues** that require deep dataflow analysis, cross-TU analysis, or fundamental redesign of a check.

### Present Candidates to the User

**Do NOT pick an issue yourself.** Present **2-5 candidate issues** to the user with a brief summary of each:
- Issue number and title
- Check name
- One-line description of the reported false positive
- Your quick feasibility assessment (easy/medium/hard)

**Then STOP and wait for the user to tell you which one to fix.**

## Step 2: Analyze the Issue

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

## Step 3: Locate and Understand the Check

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

## Step 4: Reproduce and Diagnose

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

## Step 5: Write Tests FIRST (Before the Fix)

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

## Step 6: Verify Tests Fail on Unpatched Build

Run the tests against the **current unpatched** clang-tidy to confirm they reproduce the bug:

```bash
# Build unpatched clang-tidy (only tests were modified, not the check)
cmake --build build --target clang-tidy -j$(nproc)

# Run the test -- it MUST FAIL (proving the false positive exists)
python build/bin/llvm-lit -v clang-tools-extra/test/clang-tidy/checkers/<module>/<test-file>.cpp
```

**The test MUST fail here.** If it passes, your test cases don't actually reproduce the reported false positive. Go back to Step 5 and fix the tests.

Only proceed once you've confirmed the test failure matches the reported issue (e.g., unexpected warning on the regression test case).

## Step 7: Determine Root Cause and Fix Strategy

Based on the analysis, classify the root cause (from `references/bugfix-patterns.md`):

1. **Template/dependent context** -> Strategy 1 (add `unless(...)`) or Strategy 2 (`TK_IgnoreUnlessSpelledInSource`)
2. **Macro expansion** -> Strategy 5 (rewrite with raw lexer)
3. **Missing AST node handling** -> Strategy 4 (handle new node types)
4. **Incomplete type/forward decl** -> Strategy 3 (add guard)
5. **Bad FixIt** -> Strategy 6 (use `tooling::fixit::*`)
6. **Crash on input** -> Strategy 7 (fix input handling)

## Step 8: Implement the Fix

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

## Step 9: Format, Build, and Verify Fix

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

## Step 10: Report Results

Print a summary:
- Issue number and title
- Root cause classification
- Fix strategy applied
- Files changed
- Any concerns or follow-up items

---

## Important Rules

- **NEVER touch git or GitHub**. No `git add`, `git commit`, `git push`, `git checkout -b`, `gh pr create`, or any commands that modify repository state. The user handles all git operations.
- **Minimal changes only**. Don't refactor surrounding code, don't add comments to unchanged code, don't fix unrelated issues.
- **Tests first, fix second**. Always write tests and verify they fail before implementing the fix.
- **Always add tests**. A bugfix without a test is incomplete.
- **Always update release notes**. Use "Improved ... by fixing a false positive when ..." format.
- **False negatives > false positives**. When in doubt, prefer not warning over incorrectly warning.
- **Match existing style**. Follow the conventions already used in the check file (Golden Rule).
- **Don't break existing tests**. Run the full check test suite if possible.
- **One issue per run**. Fix one issue, then stop.
