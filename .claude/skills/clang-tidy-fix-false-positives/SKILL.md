---
name: fix-clang-tidy-fp
description: Find and fix false positive bugs in clang-tidy checks. Picks an open GitHub issue, analyzes the root cause, implements the fix with tests and release notes, then creates a PR.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Agent, WebFetch, WebSearch
---

# Fix Clang-Tidy False Positives

You are an expert LLVM/clang-tidy contributor. Your job is to find an open false-positive issue, fix it, and open a PR -- all autonomously.

## Configuration

- **Target remote**: `origin` (user's fork of llvm/llvm-project)

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

From the results, pick ONE issue that:
1. Has a clear reproducer (C++ code that triggers the false positive)
2. Identifies a specific check name (e.g., `bugprone-*`, `readability-*`)
3. Is **not assigned** and has **no open PR** targeting it
4. Looks feasible based on the bugfix patterns (template handling, matcher exclusion, guard condition, etc.)
5. Preferably has recent activity (updated in last 6 months)

**Skip issues** that require deep dataflow analysis, cross-TU analysis, or fundamental redesign of a check.

Print which issue you selected and why.

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

## Step 5: Determine Root Cause and Fix Strategy

Based on the analysis, classify the root cause (from `references/bugfix-patterns.md`):

1. **Template/dependent context** -> Strategy 1 (add `unless(...)`) or Strategy 2 (`TK_IgnoreUnlessSpelledInSource`)
2. **Macro expansion** -> Strategy 5 (rewrite with raw lexer)
3. **Missing AST node handling** -> Strategy 4 (handle new node types)
4. **Incomplete type/forward decl** -> Strategy 3 (add guard)
5. **Bad FixIt** -> Strategy 6 (use `tooling::fixit::*`)
6. **Crash on input** -> Strategy 7 (fix input handling)

## Step 6: Implement the Fix

### Modify the check implementation

Apply the chosen fix strategy. Keep changes minimal -- typically 5-30 lines of check code.

Common patterns:
- Add `unless(isInstantiationDependent())` to matcher
- Add `unless(isInTemplateInstantiation())` to matcher
- Override `getCheckTraversalKind()` to return `TK_IgnoreUnlessSpelledInSource`
- Add null/definition guard: `if (!Record->getDefinition()) return;`
- Handle new AST node type in `check()` method
- Add `isDependentType()` guard

### Add tests

Append test cases to the existing test file. Include:

1. **Regression test** (the false positive case -- should NOT warn):
```cpp
<reproducer code>
```

2. **Preservation test** (verify the check still catches real issues):
```cpp
<code that SHOULD trigger the warning>
// CHECK-MESSAGES: :[[@LINE-1]]:N: warning: <full diagnostic>
```

If a new language standard is needed, create a new test file with the appropriate `-std=c++NN-or-later` flag.

### Update release notes

Add an entry in `clang-tools-extra/docs/ReleaseNotes.rst` under "Changes in existing checks", in alphabetical order:

```rst
- Improved :doc:`<check-name>
  <clang-tidy/checks/<module>/<check-name>>` check by fixing a false
  positive when <description>.
```

## Step 7: Format, Build, and Test

**Before building**, run `clang-format` on any check source files you changed (NOT test files -- tests have their own formatting conventions):

```bash
# Format only the check .cpp/.h files you modified
git clang-format HEAD~1 -- clang-tools-extra/clang-tidy/<module>/<CheckName>Check.cpp \
  clang-tools-extra/clang-tidy/<module>/<CheckName>Check.h
```

Or more precisely, to format only staged/changed source files (excluding tests):

```bash
git diff --name-only | grep 'clang-tidy/.*\.\(cpp\|h\)$' | grep -v '/test/' | xargs -r clang-format -i
```

Then build:

```bash
# Build just clang-tidy (faster than full build)
cmake --build build --target clang-tidy -j$(nproc)

# Run the specific test
python build/bin/llvm-lit -v clang-tools-extra/test/clang-tidy/checkers/<module>/<test-file>.cpp

# Verify the fix with the reproducer
./build/bin/clang-tidy -checks='-*,<check-name>' /tmp/fp_repro.cpp -- -std=c++20
```

If build/test fails, diagnose and fix. Common issues:
- Missing includes in test file
- Incorrect CHECK-MESSAGES line numbers
- Matcher syntax errors

## Step 8: Report Results

Print a summary:
- Issue number and title
- Root cause classification
- Fix strategy applied
- Files changed
- Any concerns or follow-up items

---

## Important Rules

- **Minimal changes only**. Don't refactor surrounding code, don't add comments to unchanged code, don't fix unrelated issues.
- **Always add tests**. A bugfix without a test is incomplete.
- **Always update release notes**. Use "Improved ... by fixing a false positive when ..." format.
- **False negatives > false positives**. When in doubt, prefer not warning over incorrectly warning.
- **Match existing style**. Follow the conventions already used in the check file (Golden Rule).
- **Don't break existing tests**. Run the full check test suite if possible.
- **One issue per run**. Fix one issue, create one PR, then stop.
