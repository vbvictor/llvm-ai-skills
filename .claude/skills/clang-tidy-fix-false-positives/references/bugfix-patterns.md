# Clang-Tidy Bugfix Patterns Reference

Extracted from analysis of 50+ real bugfix commits in the LLVM repository.

## File Organization

Every clang-tidy check follows this layout:

| Component | Path |
|-----------|------|
| Check source | `clang-tools-extra/clang-tidy/<module>/<CheckName>Check.cpp` |
| Check header | `clang-tools-extra/clang-tidy/<module>/<CheckName>Check.h` |
| Tests | `clang-tools-extra/test/clang-tidy/checkers/<module>/<check-name>.cpp` |
| Docs | `clang-tools-extra/docs/clang-tidy/checks/<module>/<check-name>.rst` |
| Release notes | `clang-tools-extra/docs/ReleaseNotes.rst` |

Module names: `bugprone`, `readability`, `performance`, `misc`, `cppcoreguidelines`, `cert`, `modernize`, etc.

A typical bugfix touches **3 files**: check `.cpp`, test `.cpp`, `ReleaseNotes.rst`.

---

## Root Causes of False Positives (by frequency)

### 1. Template Instantiation / Dependent Context (most common)

The check matches AST nodes in template instantiations where types/expressions are not fully resolved.

**Indicators:**
- Bug report mentions templates, generic lambdas, or `auto` parameters
- Check uses `TK_AsIs` traversal (default) instead of `TK_IgnoreUnlessSpelledInSource`
- Matcher doesn't exclude `isInstantiationDependent()` or `isInTemplateInstantiation()`
- Check doesn't handle `CXXUnresolvedConstructExpr`, `SubstTemplateTypeParmType`, `DependentNameType`

### 2. Macro Expansion / Preprocessor

Source ranges collapse after macro expansion, making distinct constructs appear identical.

**Indicators:**
- Bug report mentions macros, `__has_builtin`, `__has_cpp_attribute`
- Check uses `Lexer::getSourceText()` on ranges that may be macro-expanded

### 3. Special Language Constructs

Checks don't account for `goto`, virtual inheritance, `ExprWithCleanups`, partially specialized templates, `constexpr if`, explicit object parameters, etc.

### 4. Incomplete Types / Forward Declarations

Check calls methods on `CXXRecordDecl` without verifying `getDefinition()` returns non-null.

### 5. Incorrect FixIt Generation

Manual character offset computation (`getLocWithOffset`, `MeasureTokenLength`) is off-by-one.

### 6. Crash on Invalid Input

`assert()` on user-controlled input, or signed `char` producing negative array indices.

---

## Fix Strategies (taxonomy)

### Strategy 1: Add `unless(...)` exclusion to AST matcher

The simplest fix for template-related FPs. Add `unless(isInstantiationDependent())` or similar:

```cpp
// Before:
const auto Matched = arraySubscriptExpr(hasBase(Expr));
// After:
const auto Matched = expr(arraySubscriptExpr(hasBase(Expr)),
                          unless(isInstantiationDependent()));
```

This is the LLVM-preferred approach when the check doesn't need to inspect template instantiations.

### Strategy 2: Add early-return / guard condition in `check()`

Add a condition check before the core logic to bail out in problematic cases:

```cpp
// Guard for incomplete types
const CXXRecordDecl *Def = Record->getDefinition();
if (!Def)
    return;

// Guard for constexpr value-dependent init
if (VD->isConstexpr())
    return;

// Guard for explicit object parameters with type constraints
if (Param->isExplicitObjectParameter())
    if (const auto *TTPT = ParamType->getAs<TemplateTypeParmType>())
        if (const auto *D = TTPT->getDecl(); D && D->hasTypeConstraint())
            return;
```

### Strategy 3: Handle additional AST node types

Extend `check()` to recognize previously unhandled node types:

- `CXXUnresolvedConstructExpr` -- unresolved constructor in templates
- `ExprWithCleanups` -- wrapper from temporary creation
- `CXXBindTemporaryExpr` -- temporary binding wrapper
- `ParenListExpr` -- parenthesized expression lists
- `SubstTemplateTypeParmType` -- substituted template type parameter

### Strategy 4: Rewrite matching logic

When the approach is fundamentally flawed, replace the algorithm entirely. Examples:
- Replace "scan all substatements" with "check only the final statement"
- Replace simple count with deduplication that handles virtual bases
- Replace `Lexer::getSourceText` with raw-lexer approach for macro contexts

### Strategy 5: Fix FixIt generation

Replace manual offset arithmetic with `tooling::fixit::createRemoval()` or `tooling::fixit::createReplacement()`.

### Strategy 6: Fix input handling

- Cast `char` to `unsigned char` before comparison: `static_cast<unsigned char>(Ch)`
- Replace `assert(!Value.empty())` with `configurationDiag()` for user options

---

## Test Patterns for Bugfixes

### RUN line format
```
// RUN: %check_clang_tidy %s <check-name> %t
// RUN: %check_clang_tidy -std=c++20-or-later %s <check-name> %t -- -- -fno-delayed-template-parsing
```

### False positive test (should NOT warn)
```cpp
template <typename T>
void templateCase() {
    T val{};
    auto &x = container[val];
}
```

### False negative test (should warn)
```cpp
void shouldWarn() {
    container.data()[10];
    // CHECK-MESSAGES: :[[@LINE-1]]:5: warning: <full diagnostic text>
    // CHECK-FIXES: container[10];
}
```

### Key conventions
- Append new test cases to existing test files (don't create new files unless different language standard needed)
- First occurrence of each diagnostic must spell out full text
- Both positive (should warn) and negative (should not warn) test cases
- Use `-or-later` suffix for language standards
- Include `CHECK-FIXES` when fix-its exist

---

## Release Notes Format

Entry in `clang-tools-extra/docs/ReleaseNotes.rst` under "Changes in existing checks":

```rst
- Improved :doc:`<check-name>
  <clang-tidy/checks/<module>/<check-name>>` check by fixing a false
  positive when <description of what triggered the FP>.
```

Always starts with "Improved", uses `:doc:` cross-reference, describes what was fixed.

---

## Commit Message Format

```
[clang-tidy] Fix false positive in `<check-name>` <brief description>

Fixes #<issue number>
```
