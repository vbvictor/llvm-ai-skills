# Code Review Guidelines

Extracted from real code review comments on LLVM/clang-tidy PRs and community best practices from LLVM contributors.

---

## 1. Code Style & Conventions

### 1.1 Use `StringRef` over `const char *` or `std::string`
Prefer `llvm::StringRef` for non-owning string parameters and return types. Avoid unnecessary `std::string` allocations when ownership is not needed.

### 1.2 Use `llvm::Twine` for string concatenation
When building strings by concatenation in LLVM code, use `llvm::Twine` instead of `std::string` with `+`.

### 1.3 Prefer early return to reduce nesting and diff size
Instead of wrapping large code blocks inside an `if` body, use an early return with the negated condition.

### 1.4 Combine conditions with init-statements
Use C++17 `if` init-statements (`if (auto x = ...; x)`) to avoid nested `if`s and reduce scope.

### 1.5 No braces for single-statement if/else/loop bodies
Following LLVM coding standards, single-statement bodies should not have curly braces.

### 1.6 Use `auto` only when type is explicit on the RHS
Spell out the type explicitly unless it is already apparent from a cast, constructor, or similar.

### 1.7 Left-qualified `const` (const before type)
In clang-tidy, write `const ParmVarDecl *Lhs` rather than `ParmVarDecl const *Lhs`.

### 1.8 Use `const` for unmodified variables
Variables assigned once and never modified should be `const`.

### 1.9 Use `const` reference in range-based for loops
When the loop variable is not modified, use `const auto &` or `const Type &`.

### 1.10 Use `!` instead of `not`
Use the `!` operator rather than the `not` alternative token.

### 1.11 Prefer `isInvalid()` over `!isValid()`
Use the positive predicate form for clarity.

### 1.12 Use `static` for function visibility, not anonymous namespaces
Anonymous namespaces should be used only for class declarations. Use `static` for file-scope function visibility.

### 1.13 Consolidate anonymous namespaces
When multiple anonymous namespaces exist in a file, consolidate them into one.

### 1.14 Avoid unnecessary casts
Don't use `cast<>` when the type is already the target type.

### 1.15 Use `std::next` over iterator arithmetic
Prefer `std::next(it)` over `it + 1` for clarity and safety.

### 1.16 Prefer `llvm::all_of`/`llvm::any_of` over `std::` with begin/end
Use LLVM's range-based algorithm wrappers.

### 1.17 Use named iterators with conventional names
When using `auto` for iterators, use conventional names like `It`.

### 1.18 Prefer `return expression` directly
Return boolean expressions directly instead of `if/else return true/false`.

### 1.19 Prefer `return` over `break` in switch statements
When the function should exit after a case, use `return` to eliminate ambiguity.

### 1.20 Use positive boolean variable names
Avoid double negation. Prefer `PossiblyFunctionLike` over `PossiblyNotFunctionLike`.

### 1.21 Prefer LLVM container types
Use `llvm::ArrayRef`, `llvm::SmallVector`, `llvm::StringLiteral`, etc., over standard library equivalents or C arrays.

### 1.22 Use `constexpr` for compile-time string constants
Prefer `static constexpr llvm::StringLiteral` over `const char*` for string constants.

### 1.23 Declare variables close to their first use
Don't declare variables at the top of a function if they are first used much later.

### 1.24 Move early-return checks before variable declarations
Avoid declaring unused variables by placing guard checks first.

### 1.25 Avoid C++ reserved identifiers in test code
Don't use identifiers that clash with reserved patterns like leading underscores.

### 1.26 Use `dyn_cast_if_present` for null-safe casts
When the input pointer might be null, use `dyn_cast_if_present` to safely propagate null.

---

## 2. AST Matchers & Check Design

### 2.1 Push filtering and option logic into matchers, not `check()`
When possible, express filtering in the AST matcher rather than doing it imperatively in the `check()` callback. This includes both simple narrowing conditions and configurable options. It makes the check more declarative, avoids unnecessary callback invocations, and often improves performance:
```cpp
// Don't do this:
check() {
  if (Function->isVariadic())
    return;
}
// Use this:
addMatcher(... functionDecl(unless(isVariadic())))
```

### 2.2 Use `assert()` for expected matcher results
When `getNodeAs` should always succeed due to matcher design, use `assert` not `if`.

### 2.3 Use `assert` liberally for invariants

### 2.4 Do not duplicate error handling with both `assert` and `if`
Use either `assert` (for invariants) or `if` (for runtime handling), not both.

### 2.5 Override `getCheckTraversalKind()` instead of explicit `traverse()` calls
When a check needs a specific traversal kind, override the method rather than wrapping matchers.

### 2.6 Use `TK_IgnoreUnlessSpelledInSource` for non-template checks
When a check doesn't need to inspect template instantiations or implicit code, override `getCheckTraversalKind()`. This can also speed up checks significantly, especially when matching popular AST nodes like `IfStmt`, `binaryOperator`, etc. You can also switch the traversal kind for part of your matcher when needed.

### 2.7 Use `unless(isInTemplateInstantiation())` to avoid duplicate warnings
Add this to matchers to prevent duplicates from template instantiations.

### 2.8 Use `unless(isExpansionInSystemHeader())` to ignore system headers
Checks should generally not flag issues in system headers users cannot control.

### 2.9 Be cautious with `TK_AsIs`
It may cause false positives on template specializations where only some instantiations match.

### 2.10 Use specific AST matchers over manual filtering
Prefer `cxxConversionDecl` and similar specific matchers over post-match `dyn_cast` filtering.

### 2.11 Use `has` instead of `hasDescendant` when only direct children matter
Prefer the more restrictive matcher for efficiency.

### 2.12 Order matcher predicates by cost/likelihood
Place cheaper or more discriminating checks first for early exit. Narrowing matchers (like `isVariadic()`, `hasName()`, `isConst()`) mostly do simple boolean checks and are cheap. Traversal matchers (`has`, `hasDescendant`, `forEach`) are more expensive. Placing narrowing matchers first allows early exit before expensive traversals.

### 2.13 Use distinct binding names for different matchers
Same string bound to different matchers causes confusion.

### 2.14 Simplify matchers by factoring out common sub-expressions
If every entry in `anyOf` has the same wrapper, move it outside.

### 2.15 Move reusable matchers to shared locations
If a locally-defined matcher could be useful to other checks, move it to a general location.

### 2.16 Override `isLanguageVersionSupported` for language-specific checks
Don't silently do nothing; override the method to declare supported language versions.

### 2.17 Wrap ternary matcher branches for type compatibility
Both branches must have compatible types. Wrap with `stmt()` or similar.

### 2.18 Be cautious with static locals in matchers
`static` local variables for sub-matchers may cause issues if constructed multiple times.

### 2.19 Avoid unnecessary lambdas
If a lambda just wraps a direct expression, assign the expression directly.

### 2.20 Use clang-query on Compiler Explorer for prototyping matchers
Use [clang-query on Compiler Explorer](https://godbolt.org/) to rapidly prototype and test matchers before writing C++ code. Note: a matcher that works in C++ does not always work in clang-query because clang-query can't do overload resolution well. However, any matcher that works in clang-query will almost certainly work in C++. Use `let` bindings in clang-query to build up complex matchers incrementally, and keep your C++ code and clang-query inputs similar-looking for easier debugging.

### 2.21 Prefer traversing down, not up
Always prefer to traverse downward using `has`, `hasDescendant`, `forEach`, etc. The matchers `hasParent` and `hasAncestor` are expensive because each is a map lookup in a data structure containing the parent mapping for the entire AST. Furthermore, the parent map is lazily constructed on first upward traversal, so the first `hasParent`/`hasAncestor` call triggers building the entire map. Anchor your matcher at the outermost node you care about and traverse down to the target -- the node you care about does not have to be the outermost.

### 2.22 Efficient upward traversal through DeclContext
You can efficiently traverse upward when you are at something that has a DeclContext and you only need to reach something that also inherits from DeclContext (or access its descendants). Anchor your matcher at such a node and go downward to your target, then upward if needed.

### 2.23 Prefer `anyOf(...)` over multiple `addMatcher()` calls
Register a single matcher with `anyOf` instead of calling `addMatcher` multiple times for related patterns:
```cpp
// Prefer:
Finder->addMatcher(binaryOperator(anyOf(hasOperatorName("!="), hasOperatorName("=="))));
// Instead of:
Finder->addMatcher(binaryOperator(hasOperatorName("!=")));
Finder->addMatcher(binaryOperator(hasOperatorName("==")));
```

### 2.24 Template code: instantiated vs. uninstantiated matching
When working with template code, you can write matchers against either the instantiated or uninstantiated templates. Matching against instantiated templates is easier when you need type information, but produces many additional AST nodes (implicit conversions, `MaterializeTemporaryExpr`, etc.). Matching against uninstantiated templates also works if the template is never instantiated in the source file being inspected. Look at AST dumps to understand the difference: uninstantiated code has dependent names, unresolved lookup expressions, and `ElaboratedType` nodes, while instantiated code has concrete types with intermediate implicit nodes.

### 2.25 Transformers and `applyFirst` with `forEachXXX` matchers
Clang-tidy `TransformerClangTidyCheck` and especially the `applyFirst` rule are tricky when combined with `forEachXXX` matchers. You may need to match the inner pattern of the `forEach` and then use `hasParent`/`hasAncestor` to check for the outer pattern. Also remember to explore `clang-tools-extra/clang-tidy/utils/` for existing utilities.

### 2.26 Follow the Contributing guide for robust checks
Follow advice on the [Contributing guide](https://clang.llvm.org/extra/clang-tidy/Contributing.html#getting-involved), in particular the section on [Making Your Check Robust](https://clang.llvm.org/extra/clang-tidy/Contributing.html#making-your-check-robust).

---

## 3. Diagnostics & Error Messages

### 3.1 Diagnostic messages should be lowercase
Following LLVM conventions, warnings should start with a lowercase letter.

### 3.2 Provide clear, actionable rationale
Explain *why* something is problematic, not just label it.

### 3.3 Use note diagnostics for per-item details
Keep the main warning concise; emit individual items as separate notes.

### 3.4 Include enough context in error messages
Dump relevant identifiers and values so problems can be easily identified.

### 3.5 Use single quotes for type placeholders in diagnostics
Use `'%0'` format for type name references in diagnostic messages.

### 3.6 Use `%0`, `%1` formatting placeholders
Follow clang diagnostic conventions instead of string concatenation.

### 3.7 Always emit diagnostics even when fix-its are unavailable
Users can still manually fix based on the warning.

### 3.8 Do not create fix-its that broadly break code
If a transformation would break many usages, either fix all affected locations or omit the fix-it.

---

## 4. Testing Requirements

### 4.1 Match full diagnostic messages in tests
Don't use `{{.*}}` wildcards; spell out the whole warning to catch regressions.

### 4.2 Add both positive and negative tests
Verify both cases that trigger warnings and cases that should not.

### 4.3 Add comprehensive edge-case tests
Cover templates (instantiation, specialization), macros, lambdas (captures, nesting), type aliases/typedefs, raw strings, nested/interacting constructs (lambdas inside functions, constexpr-if branches), forward declarations, overloaded operators, and other language features that could cause false positives or incorrect fixes.

### 4.4 Use `-or-later` suffix for language standard specifications
Use `-std=c++17-or-later` instead of `-std=c++17`.

### 4.5 Do not increase minimum language standard in existing tests
Create a new test file for higher standards instead of bumping the existing one.

### 4.6 Use correct C++ standard version in tests
The standard flag should match the features being tested.

### 4.7 Separate test files by language standard when behavior differs
Create separate files (e.g., `check.cpp` and `check-cxx20.cpp`).

### 4.8 Use shared mock headers instead of inline mocks
Reuse headers from `Inputs/Headers` instead of defining `namespace std { ... }` inline.

### 4.9 Tests should not depend on real-world system headers
Use fake/mock headers from test infrastructure.

### 4.10 Tests should not depend on platform-specific tools
Avoid `grep` or other tools that may not exist on all platforms.

### 4.11 Remove unnecessary `// Should NOT trigger warning` comments
Silence is the default expectation; explicit no-warn comments are noise.

### 4.12 FileCheck negative tests do not need CHECK-NOT
Unmatched messages are treated as failures by default.

### 4.13 Add CHECK-FIXES alongside CHECK-MESSAGES when fix-its exist
Both the diagnostic and the fixed output must be verified.

### 4.14 Write tests for all diagnostic notes, not just warnings
If a check emits notes, they should be tested too.

### 4.15 Split long RUN lines for readability
Use line continuation (`\`) for long `-config` options.

### 4.16 Write tests in existing test files when possible
Prefer adding RUN commands to existing files over creating new ones.

### 4.17 Give test entities meaningful names

### 4.18 Avoid built-ins in test code
Use standard constructs when possible for portability and readability.

### 4.19 Avoid test-only namespaces referencing issue numbers in small files
`git blame` can serve that purpose; `GH-XXXX` namespaces are bloat.

### 4.20 Preserve false-positive tests for regression detection
Keep FP test cases (possibly with FIXME) so refactoring patches detect accidental fixes.

### 4.21 Run checks on real codebases before merging
Test on LLVM, libc++, Boost, etc., to find false positives or crashes. If the check supports fixes, also verify that the fixed code still compiles. Consider using tooling similar to the [Clang Static Analyzer test infrastructure](https://github.com/llvm/llvm-project/tree/main/clang/utils/analyzer) for systematic validation across codebases.

### 4.22 Test all meaningful matcher paths
Every meaningful condition in a matcher should have a corresponding test.

### 4.23 Remove check name suffix from CHECK-MESSAGES when only one check is run

### 4.24 Place test files in the correct directory
Follow the project-standard test directory structure.

---

## 5. Documentation Standards

### 5.1 Omit "this check" in documentation summaries
Start directly with what the check does: "Flags uses of..." not "This check flags...".

### 5.2 Separate first sentence from the rest with a blank line
The summary sentence should stand alone.

### 5.3 Use double backticks for code in RST docs
Language constructs use ` `` `, option names use single backticks.

### 5.4 Use `:option:` directive for referencing options
Use RST `:option:` rather than plain backticks when referencing check options.

### 5.5 Respect 80-character line limit in documentation

### 5.6 Use correct RST heading hierarchy
Heading underline characters should be consistent with the existing document style.

### 5.7 Document known limitations in a "Limitations" section

### 5.8 Document what to use instead
When flagging a pattern, explain the recommended alternative.

### 5.9 Provide before/after code examples
Show both bad and good code patterns.

### 5.10 Options section comes last in check documentation
Place options after examples and all other content.

### 5.11 Default value stated last in option description

### 5.12 Document built-in defaults before options
When a check has built-in default lists, document them prominently.

### 5.13 Document regex support explicitly
If an option accepts regex patterns, state it clearly.

### 5.14 Document how to suppress diagnostics
Explain how users can suppress or work around unwanted diagnostics.

### 5.15 Don't remove existing documentation when redirecting checks
Preserve content when creating aliases; note option default differences.

### 5.16 Preserve CERT/standard reference links in alias docs
Keep original reference links in both the alias page and the new check page.

### 5.17 Put detailed documentation in `.rst` files, not header comments
Headers should have only a brief summary.

### 5.18 Keep documentation concise
Avoid verbose rationale sections. Use 2-space indent in code-blocks.

### 5.19 One-per-line for nested/chained code examples
Break nested casts and similar constructs across lines for readability.

### 5.20 Add hyperlinks for tools and references
Provide links for external tools and standards.

### 5.21 Grammar and spelling corrections matter
Proofread documentation for proper English.

### 5.22 Use consistent terminology
Don't alternate between qualified and unqualified forms or between "definition" and "declaration" arbitrarily.

---

## 6. Release Notes

### 6.1 Include release notes for user-visible changes
New checks, bug fixes, option changes, behavioral changes all need entries. NFC doc changes do not.

### 6.2 Place entries in the correct section
"New checks", "New check aliases", "Changes in existing checks", "Potentially Breaking Changes" -- each has its place.

### 6.3 Maintain alphabetical order by check name

### 6.4 Lines under 80 characters

### 6.5 Use `:doc:` directive and proper formatting
Double backticks for language constructs, single for option names.

### 6.6 Separate entries with empty lines

### 6.7 Prefer separate entries over combined ones
Multiple smaller entries are easier to read than one long paragraph.

### 6.8 Describe full scope of changes
Mention all affected components (CLI, config, helper scripts).

### 6.9 Synchronize descriptions across docs, release notes, and headers
The one-line description should be identical everywhere.

### 6.10 Follow established wording patterns
Use "Improved XXX check by..." for existing check improvements.

### 6.11 Note potentially breaking changes

---

## 7. Architecture & Code Quality

### 7.1 Implement non-trivial methods in `.cpp` files, not headers
Including constructors with logic and override methods.

### 7.2 Extract duplicated code into helpers
When patterns repeat with minor variations, extract into parameterized functions/lambdas.

### 7.3 Don't duplicate code when branching on options
Build up results incrementally rather than duplicating blocks with minor differences.

### 7.4 Keep functions small and readable
Break large functions into smaller helpers with clear names.

### 7.5 Use map/lookup instead of long if-else chains
Prefer a map or lookup table for type/name mappings.

### 7.6 Avoid double-lookups in containers
Use `find()` for a single lookup instead of `contains()` followed by `operator[]`.

### 7.7 Limit scope of helper functions
Local lambdas for single-use helpers; `static` for file-scope functions.

### 7.8 Avoid constructing expensive objects repeatedly
Build regex, matchers, etc., once (in constructor or `storeOptions`), not on each callback.

### 7.9 Avoid premature optimization that hurts readability
Don't sacrifice clarity for micro-optimizations without demonstrated benefit.

### 7.10 Avoid over-engineering
Don't add complexity without clear benefit.

### 7.11 Prefer simpler types over unnecessary wrappers
Don't use `std::optional` when the type already has a natural empty state.

### 7.12 Use a single input type per function
Don't accept both `str` and `List[str]` and branch internally.

### 7.13 Remove dead/useless code
Remove redundant returns, unused casts, unnecessary variables.

### 7.14 Remove debug output before merging

### 7.15 Use `clang-format OFF/ON` to preserve readable list formatting
When a list is organized one-per-line for readability, protect it from reformatting.

### 7.16 Deprecate API functions before removing them
Mark `[[deprecated]]` for at least 2 releases before removal.

---

## 8. Naming & Categorization

### 8.1 Check names should not use "don't"/"avoid" in `bugprone-` category
The category already implies avoidance. Use descriptive noun phrases.

### 8.2 Check category should match the nature of the issue
- `bugprone-` for likely bugs
- `readability-` for style/consistency
- `modernize-` for C++ modernization (should not break code)
- `cppcoreguidelines-` for strict guideline adherence
- `portability-` for cross-platform

### 8.3 Use unambiguous, descriptive names
Prefer user-facing terminology over internal compiler jargon.

### 8.4 Function names should reflect return types

### 8.5 Name files after check names, not class names
Makes files easier to find.

### 8.6 Prefer well-known option names (e.g., `StrictMode`)
Reuse established option names from the clang-tidy ecosystem.

### 8.7 Use standard namespace depth for check modules
`clang::tidy::CHECK_CATEGORY` -- no additional nesting.

### 8.8 Use consistent naming with existing conventions
Match prefixes, suffixes, and naming patterns established in the codebase.

---

## 9. PR & Process Discipline

### 9.1 Keep PRs small and focused
Each PR should contain one logical unit of work. Split unrelated changes into separate PRs.

### 9.2 Don't include unrelated formatting changes

### 9.3 Do not use AI-generated PR descriptions

### 9.4 PR title must match actual changes
Update title and description when scope changes during iteration.

### 9.5 Use `[clang-tidy]` prefix in PR titles

### 9.6 Include check name in PR title

### 9.7 Follow conventional commit message format
Start with an action verb (Add/Fix/Update/Make).

### 9.8 Link PR descriptions to related issues
Use "Closes https://github.com/llvm/llvm-project/issues/XXXX".

### 9.9 Require multiple reviews for new checks
At least 2 reviews for new checks; bug fixes may need only 1.

### 9.10 Wait for second reviewer on large/impactful changes

### 9.11 Wait for domain expert approval on cross-cutting changes
Get approval from relevant maintainers before merging.

### 9.12 Respect the blocking-review protocol
Don't merge while a reviewer has "requested changes". Don't request changes unless it's a major blocker.

### 9.13 Don't resolve conversations prematurely
Let the reviewer acknowledge before resolving.

### 9.14 Rebase on fresh main before merging

### 9.15 Verify CI/tests pass before merging

### 9.16 Make email addresses public per LLVM developer policy

### 9.17 Create follow-up issues for deferred work
When deferring a feature, create a tracking issue.

### 9.18 Follow revert policy for broken patches
Re-applied patches must describe what was wrong and how it was fixed.

### 9.19 Separate bug fixes from design discussions into different PRs

### 9.20 Provide high-level overview for complex changes

---

## 10. Design Principles

### 10.1 False negatives are preferable to false positives
When a check cannot be perfectly accurate, better to miss some true positives than to report incorrect warnings.

### 10.2 Consider making behavior configurable via options
When behavior might not be universally desired, put it behind an option.

### 10.3 Expose options with safe defaults
Default to the safest behavior for ordinary users.

### 10.4 Prefer single multi-level option over multiple booleans
Consolidate related booleans into an option with enumerated levels.

### 10.5 Be cautious with warnings in macro contexts
Macro expansions can produce confusing diagnostics. Consider suppressing by default.

### 10.6 Verify fix-its produce correct output
Fixes that produce broken code must be caught.

### 10.7 Use `--enable-check-profile` for performance claims
Provide check-specific profile data rather than overall benchmarks.

### 10.8 Leave FIXME comments for temporary workarounds

### 10.9 Add comments explaining non-obvious logic
Regex patterns, magic values, cron schedules, and complex algorithms need inline explanation.

### 10.10 Use type aliases for complex types

### 10.11 Gather maintainer consensus before adding third-party config files
Adding `.editorconfig`, `.vscode/`, etc., requires broader agreement.

### 10.12 Avoid text duplication -- reference existing descriptions

### 10.13 `.git-blame-ignore-revs` only for large-scale reformatting
Small changes don't warrant inclusion. Maintain chronological order.

### 10.14 Format Python code with Black
Per LLVM coding standards.

### 10.15 Respect minimum version requirements
Code must work with the minimum supported version (e.g., Python 3.8 for LLVM).
