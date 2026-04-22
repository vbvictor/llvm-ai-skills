# Code Review Guidelines

Extracted from real code review comments on LLVM/clang-tidy PRs, community best practices from LLVM contributors, and the [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html).

**References**:
- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html)
- [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html)

---

## 0. The Golden Rule

**If you are extending, enhancing, or bug fixing already implemented code, use the style that is already being used so that the source is uniform and easy to follow.** Refer to typical files in the repo when reviewing code.

---

## 1. Formatting & Whitespace

### 1.1 Run formatters before review
- C++: `git clang-format HEAD~1`
- Python: `darker -r HEAD^ $(git diff --name-only --diff-filter=d HEAD^)`

Fix or report issues if the linter fails.

### 1.2 No trailing whitespace

### 1.3 Check UNIX newline at EOF

### 1.4 80-column line width for source code
Write code to fit within 80 columns.

### 1.5 Prefer spaces over tabs
In all cases, prefer spaces to tabs in source files.

### 1.6 Spaces before parentheses only in control flow
Space before `(` in `if`, `for`, `while`, `switch` -- not in function calls.

### 1.7 Don't indent namespaces
Avoid indenting namespace contents to reduce indentation depth.

### 1.8 Lambda formatting
Single multi-line lambdas should drop indentation to standard two-space block indentation when no expressions follow. Multiple multi-line lambdas should indent two spaces from the opening `[]`.

---

## 2. Code Style & Conventions

### 2.1 Use `StringRef` over `const char *` or `std::string`
Prefer `llvm::StringRef` for non-owning string parameters and return types. Avoid unnecessary `std::string` allocations when ownership is not needed.

### 2.2 Use `llvm::Twine` for string concatenation
When building strings by concatenation in LLVM code, use `llvm::Twine` instead of `std::string` with `+`.

### 2.3 Prefer early return to reduce nesting and diff size
Instead of wrapping large code blocks inside an `if` body, use an early return with the negated condition.

### 2.4 Combine conditions with init-statements
Use C++17 `if` init-statements (`if (auto x = ...; x)`) to avoid nested `if`s and reduce scope.

### 2.5 No braces for single-statement if/else/loop bodies
Following LLVM coding standards, single-statement bodies should not have curly braces.

### 2.6 Use `auto` only when type is explicit on the RHS
Spell out the type explicitly unless it is already apparent from a cast, constructor, or similar.

### 2.9 Use `const` reference in range-based for loops
When the loop variable is not modified, use `const auto &` or `const Type &`.

### 2.10 Use `!` instead of `not`
Use the `!` operator rather than the `not` alternative token.

### 2.11 Prefer `isInvalid()` over `!isValid()`
Use the positive predicate form for clarity.

### 2.12 Use `static` for function visibility, not anonymous namespaces
Anonymous namespaces should be used only for class declarations. Use `static` for file-scope function visibility.

### 2.13 Consolidate anonymous namespaces
When multiple anonymous namespaces exist in a file, consolidate them into one.

### 2.14 Avoid unnecessary casts
Don't use `cast<>` when the type is already the target type.

### 2.15 Use `std::next` over iterator arithmetic
Prefer `std::next(it)` over `it + 1` for clarity and safety.

### 2.16 Prefer `llvm::all_of`/`llvm::any_of` over `std::` with begin/end
Use LLVM's range-based algorithm wrappers.

### 2.17 Use named iterators with conventional names
When using `auto` for iterators, use conventional names like `It`.

### 2.18 Prefer `return expression` directly
Return boolean expressions directly instead of `if/else return true/false`.

### 2.19 Prefer `return` over `break` in switch statements
When the function should exit after a case, use `return` to eliminate ambiguity.

### 2.20 Use positive boolean variable names
Avoid double negation. Prefer `PossiblyFunctionLike` over `PossiblyNotFunctionLike`.

### 2.21 Prefer LLVM container types
Use LLVM containers over standard library equivalents:
- **Sequences**: `llvm::ArrayRef`, `TinyPtrVector`, `SmallVector` over `std::vector`/`std::list`. Never use `<list>` (high constant factor from heap allocation). Avoid `std::vector<bool>`.
- **Sets**: `SmallSet`, `SmallPtrSet`, `StringSet`, `DenseSet`. Avoid `<set>` (malloc-intensive, large per-element overhead).
- **Maps**: `StringMap`, `IndexedMap`, `DenseMap`, `ValueMap`. Avoid `<map>` (large constant factor), `std::multimap`, and `std::unordered_map` (malloc-intensive).

### 2.22 Use `constexpr` for compile-time string constants
Prefer `static constexpr llvm::StringLiteral` over `const char*` for string constants.

### 2.23 Declare variables close to their first use
Don't declare variables at the top of a function if they are first used much later.

### 2.24 Move early-return checks before variable declarations
Avoid declaring unused variables by placing guard checks first.

### 2.25 Avoid C++ reserved identifiers in test code
Don't use identifiers that clash with reserved patterns like leading underscores.

### 2.26 Use `dyn_cast_if_present` for null-safe casts
When the input pointer might be null, use `dyn_cast_if_present` to safely propagate null.

### 2.27 Comments: `//` for normal, `///` for doxygen
In C code, maintain C89 compatibility for comments.

### 2.28 No RTTI or exceptions
`dynamic_cast<>` is not allowed. Use LLVM's `isa<>`, `cast<>`, and `dyn_cast<>`. For other casts, prefer `static_cast`, `reinterpret_cast`, `const_cast`.

### 2.29 `struct` when all members are public
All declarations and definitions of a given `class` or `struct` must use the same keyword.

### 2.30 Be aware of unnecessary copies with `auto`
When using `auto` in range-based `for` loops, use `auto &` or `auto *` to avoid unintended copies.

### 2.31 Minimize `#include`s
Less includes means less code, faster compile time, smaller binary size. Always double-check when reviewing or writing code.

### 2.32 Use `continue` to simplify loops
Like early returns simplify functions, `continue` simplifies loop bodies.

### 2.33 No predicate loops -- use predicate functions
Extract complex loop conditions into named predicate functions.

### 2.34 No static constructors

### 2.35 Don't use braced initializer lists to call a constructor (C++11)

### 2.36 `using namespace std` is forbidden

### 2.37 `#include <iostream>` is forbidden
Use `llvm::MemoryBuffer` API instead.

### 2.38 Use `llvm_unreachable` for impossible code paths
For code paths that should never be reached, use `llvm_unreachable` instead of `assert(false)`.

### 2.39 Use `llvm::Error` over exceptions and `std::error_code`

### 2.40 Include order
1. Main module header (the `.h` that this `.cpp` implements)
2. Local/private headers
3. LLVM project/subproject headers (most-to-least specific)
4. System `#include`s

Each category sorted lexicographically. The main module header must come first.

### 2.41 Use forward declarations to minimize includes
Use pointers or references without including full definitions when possible.

### 2.42 Header guard style
The guard should be the all-caps path a user would `#include`, using `_` instead of path separators and extension markers.

### 2.43 No default label in exhaustive enum switches
Omit `default:` in fully-covered switch statements over enumerations to preserve `-Wswitch` compiler warnings.

### 2.44 No `inline` keyword in class definitions
Member functions defined in a class body are implicitly inline; the keyword is redundant.

### 2.45 Prefer range-based for loops
Use range-based `for` loops wherever possible for all newly added code.

### 2.46 Use preincrement (`++X`) over postincrement (`X++`)
Preincrement may be faster and is never slower. Use it whenever possible.

### 2.47 Use `llvm::sort` over `std::sort`
`llvm::sort` can catch non-determinism with `-DEXPENSIVE_CHECKS`.

### 2.48 Use `raw_ostream`, not `ostream`; avoid `std::endl`
All new code should use `raw_ostream`. Use `'\n'` instead of `std::endl` (which flushes unnecessarily).

### 2.49 No `else` after `return`/`break`/`continue`
Do not use `else` or `else if` after something that interrupts control flow.

### 2.50 Don't re-evaluate `end()` in loops
Cache the result of `end()` before looping when the container isn't being mutated.

### 2.51 Self-contained headers
Header files should compile on their own and end in `.h`. Non-header includes should end in `.inc`.

### 2.52 Virtual method anchor
If a class has a vtable and is defined in a header, it must have at least one out-of-line virtual method.

### 2.53 Use namespace qualifiers for out-of-line definitions
Prefer `llvm::Foo::bar()` over opening namespace blocks in `.cpp` files.

### 2.54 Don't put internal interfaces in public headers
Complex modules with multiple `.cpp` files should use private headers for internal communication.

### 2.55 Restrict visibility
Functions and variables should have the most restricted visibility possible.

---

## 3. AST Matchers & Check Design

### 3.1 Push filtering and option logic into matchers, not `check()`
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

### 3.2 Use `assert()` for expected matcher results
When `getNodeAs` should always succeed due to matcher design, use `assert` not `if`.

### 3.3 Use `assert` liberally for invariants

### 3.4 Do not duplicate error handling with both `assert` and `if`
Use either `assert` (for invariants) or `if` (for runtime handling), not both.

### 3.5 Override `getCheckTraversalKind()` instead of explicit `traverse()` calls
When a check needs a specific traversal kind, override the method rather than wrapping matchers.

### 3.6 Use `TK_IgnoreUnlessSpelledInSource` for non-template checks
When a check doesn't need to inspect template instantiations or implicit code, override `getCheckTraversalKind()`. This can also speed up checks significantly, especially when matching popular AST nodes like `IfStmt`, `binaryOperator`, etc. You can also switch the traversal kind for part of your matcher when needed.

### 3.7 Use `unless(isInTemplateInstantiation())` to avoid duplicate warnings
Add this to matchers to prevent duplicates from template instantiations.

### 3.8 Use `unless(isExpansionInSystemHeader())` to ignore system headers
Checks should generally not flag issues in system headers users cannot control.

### 3.9 Be cautious with `TK_AsIs`
It may cause false positives on template specializations where only some instantiations match.

### 3.10 Use specific AST matchers over manual filtering
Prefer `cxxConversionDecl` and similar specific matchers over post-match `dyn_cast` filtering.

### 3.11 Use `has` instead of `hasDescendant` when only direct children matter
Prefer the more restrictive matcher for efficiency.

### 3.12 Order matcher predicates by cost/likelihood
Place cheaper or more discriminating checks first for early exit. Narrowing matchers (like `isVariadic()`, `hasName()`, `isConst()`) mostly do simple boolean checks and are cheap. Traversal matchers (`has`, `hasDescendant`, `forEach`) are more expensive. Placing narrowing matchers first allows early exit before expensive traversals.

### 3.13 Use distinct binding names for different matchers
Same string bound to different matchers causes confusion.

### 3.14 Simplify matchers by factoring out common sub-expressions
If every entry in `anyOf` has the same wrapper, move it outside.

### 3.15 Move reusable matchers to shared locations
If a locally-defined matcher could be useful to other checks, move it to a general location.

### 3.16 Override `isLanguageVersionSupported` for language-specific checks
Don't silently do nothing; override the method to declare supported language versions.

### 3.17 Wrap ternary matcher branches for type compatibility
Both branches must have compatible types. Wrap with `stmt()` or similar.

### 3.18 Be cautious with static locals in matchers
`static` local variables for sub-matchers may cause issues if constructed multiple times.

### 3.19 Avoid unnecessary lambdas
If a lambda just wraps a direct expression, assign the expression directly.

### 3.20 Use clang-query on Compiler Explorer for prototyping matchers
Use [clang-query on Compiler Explorer](https://godbolt.org/) to rapidly prototype and test matchers before writing C++ code. Note: a matcher that works in C++ does not always work in clang-query because clang-query can't do overload resolution well. However, any matcher that works in clang-query will almost certainly work in C++. Use `let` bindings in clang-query to build up complex matchers incrementally, and keep your C++ code and clang-query inputs similar-looking for easier debugging.

### 3.21 Prefer traversing down, not up
Always prefer to traverse downward using `has`, `hasDescendant`, `forEach`, etc. The matchers `hasParent` and `hasAncestor` are expensive because each is a map lookup in a data structure containing the parent mapping for the entire AST. Furthermore, the parent map is lazily constructed on first upward traversal, so the first `hasParent`/`hasAncestor` call triggers building the entire map. Anchor your matcher at the outermost node you care about and traverse down to the target -- the node you care about does not have to be the outermost.

### 3.22 Efficient upward traversal through DeclContext
You can efficiently traverse upward when you are at something that has a DeclContext and you only need to reach something that also inherits from DeclContext (or access its descendants). Anchor your matcher at such a node and go downward to your target, then upward if needed.

### 3.23 Prefer `anyOf(...)` over multiple `addMatcher()` calls
Register a single matcher with `anyOf` instead of calling `addMatcher` multiple times for related patterns:
```cpp
// Prefer:
Finder->addMatcher(binaryOperator(anyOf(hasOperatorName("!="), hasOperatorName("=="))));
// Instead of:
Finder->addMatcher(binaryOperator(hasOperatorName("!=")));
Finder->addMatcher(binaryOperator(hasOperatorName("==")));
```

### 3.24 Template code: instantiated vs. uninstantiated matching
When working with template code, you can write matchers against either the instantiated or uninstantiated templates. Matching against instantiated templates is easier when you need type information, but produces many additional AST nodes (implicit conversions, `MaterializeTemporaryExpr`, etc.). Matching against uninstantiated templates also works if the template is never instantiated in the source file being inspected. Look at AST dumps to understand the difference: uninstantiated code has dependent names, unresolved lookup expressions, and `ElaboratedType` nodes, while instantiated code has concrete types with intermediate implicit nodes.

### 3.25 Transformers and `applyFirst` with `forEachXXX` matchers
Clang-tidy `TransformerClangTidyCheck` and especially the `applyFirst` rule are tricky when combined with `forEachXXX` matchers. You may need to match the inner pattern of the `forEach` and then use `hasParent`/`hasAncestor` to check for the outer pattern. Also remember to explore `clang-tools-extra/clang-tidy/utils/` for existing utilities.

### 3.26 Follow the Contributing guide for robust checks
Follow advice on the [Contributing guide](https://clang.llvm.org/extra/clang-tidy/Contributing.html#getting-involved), in particular the section on [Making Your Check Robust](https://clang.llvm.org/extra/clang-tidy/Contributing.html#making-your-check-robust).

---

## 4. Diagnostics & Error Messages

### 4.1 Diagnostic messages should be lowercase
Following LLVM conventions, warnings should start with a lowercase letter.

### 4.2 Provide clear, actionable rationale
Explain *why* something is problematic, not just label it.

### 4.3 Use note diagnostics for per-item details
Keep the main warning concise; emit individual items as separate notes.

### 4.4 Include enough context in error messages
Dump relevant identifiers and values so problems can be easily identified.

### 4.5 Use single quotes for type placeholders in diagnostics
Use `'%0'` format for type name references in diagnostic messages.

### 4.6 Use `%0`, `%1` formatting placeholders
Follow clang diagnostic conventions instead of string concatenation.

### 4.7 Always emit diagnostics even when fix-its are unavailable
Users can still manually fix based on the warning.

### 4.8 Do not create fix-its that broadly break code
If a transformation would break many usages, either fix all affected locations or omit the fix-it.

### 4.9 Error messages: lowercase, no trailing period
Error messages should start with a lowercase letter and not end with a period (unless other punctuation applies). Provide context needed to understand what went wrong.

---

## 5. Testing Requirements

### 5.1 Match full diagnostic messages in tests
The first occurrence of each unique diagnostic in a test file must spell out the full warning text (to catch typos/regressions). Subsequent occurrences of the same diagnostic may be truncated if the full text exceeds 120 characters. Do not use `{{.*}}` wildcards.

### 5.2 Add both positive and negative tests
Verify both cases that trigger warnings and cases that should not.

### 5.3 Add comprehensive edge-case tests
Cover templates (instantiation, specialization), macros, lambdas (captures, nesting), type aliases/typedefs, raw strings, nested/interacting constructs (lambdas inside functions, constexpr-if branches), forward declarations, overloaded operators, and other language features that could cause false positives or incorrect fixes.

### 5.4 Use `-or-later` suffix and match the check's `isLanguageVersionSupported`
Use `-std=c++17-or-later` instead of `-std=c++17`. The language standard in tests must match the check's `isLanguageVersionSupported()` override (or equivalent `LangOpts` guard). For example, if a check only requires `LangOpts.CPlusPlus`, tests should use `-std=c++98-or-later`. All supported language modes should be covered — use separate test files if tests cannot be written in a single file due to language standard differences.

### 5.5 Do not increase minimum language standard in existing tests
Create a new test file for higher standards instead of bumping the existing one.

### 5.6 Use correct C++ standard version in tests
The standard flag should match the features being tested.

### 5.7 Separate test files by language standard when behavior differs
Create separate files (e.g., `check.cpp` and `check-cxx20.cpp`).

### 5.8 Use shared mock headers instead of inline mocks
Reuse headers from `Inputs/Headers` instead of defining `namespace std { ... }` inline.

### 5.9 Tests should not depend on real-world system headers
Use fake/mock headers from test infrastructure.

### 5.10 Tests should not depend on platform-specific tools
Avoid `grep` or other tools that may not exist on all platforms.

### 5.11 Remove unnecessary `// Should NOT trigger warning` comments
Silence is the default expectation; explicit no-warn comments are noise.

### 5.12 FileCheck negative tests do not need CHECK-NOT
Unmatched messages are treated as failures by default.

### 5.13 Add CHECK-FIXES alongside CHECK-MESSAGES when fix-its exist
Both the diagnostic and the fixed output must be verified. When a test case intentionally has no fix-it (e.g., side effects, condition variables), simply omit CHECK-FIXES — no explanatory comment is needed.

### 5.14 Write tests for all diagnostic notes, not just warnings
If a check emits notes, they should be tested too.

### 5.15 Split long RUN lines for readability
Use line continuation (`\`) for long `-config` options.

### 5.16 Write tests in existing test files when possible
Prefer adding RUN commands to existing files over creating new ones.

### 5.17 Give test entities meaningful names

### 5.18 Avoid built-ins in test code
Use standard constructs when possible for portability and readability.

### 5.19 Avoid test-only namespaces referencing issue numbers in small files
`git blame` can serve that purpose; `GH-XXXX` namespaces are bloat.

### 5.20 Preserve false-positive tests for regression detection
Keep FP test cases (possibly with FIXME) so refactoring patches detect accidental fixes.

### 5.21 Run checks on real codebases before merging
Test on LLVM, libc++, Boost, etc., to find false positives or crashes. If the check supports fixes, also verify that the fixed code still compiles. Consider using tooling similar to the [Clang Static Analyzer test infrastructure](https://github.com/llvm/llvm-project/tree/main/clang/utils/analyzer) for systematic validation across codebases.

### 5.22 Test all meaningful matcher paths
Every meaningful condition in a matcher should have a corresponding test.

### 5.23 Remove check name suffix from CHECK-MESSAGES when only one check is run

### 5.24 Place test files in the correct directory
Follow the project-standard test directory structure.

---

## 6. Documentation Standards

### 6.1 Omit "this check" in documentation summaries
Start directly with what the check does: "Flags uses of..." not "This check flags...".

### 6.2 Separate first sentence from the rest with a blank line
The summary sentence should stand alone.

### 6.3 Use double backticks for code in RST docs
Language constructs use ` `` `, option names use single backticks.

### 6.4 Use `:option:` directive for referencing options
Use RST `:option:` rather than plain backticks when referencing check options.

### 6.5 Respect 80-character line limit in documentation

### 6.6 Use correct RST heading hierarchy
Heading underline characters should be consistent with the existing document style.

### 6.7 Document known limitations in a "Limitations" section

### 6.8 Document what to use instead
When flagging a pattern, explain the recommended alternative.

### 6.9 Provide before/after code examples
Show both bad and good code patterns. The "after" examples should show the actual fix-it output from the check, not hand-written idealized code.

### 6.10 Options section comes last in check documentation
Place options after examples and all other content.

### 6.11 Default value stated last in option description

### 6.12 Document built-in defaults before options
When a check has built-in default lists, document them prominently.

### 6.13 Document regex support explicitly
If an option accepts regex patterns, state it clearly.

### 6.14 Document how to suppress diagnostics
Explain how users can suppress or work around unwanted diagnostics.

### 6.15 Don't remove existing documentation when redirecting checks
Preserve content when creating aliases; note option default differences.

### 6.16 Preserve CERT/standard reference links in alias docs
Keep original reference links in both the alias page and the new check page.

### 6.17 Put detailed documentation in `.rst` files, not header comments
Headers should have only a brief summary.

### 6.18 Keep documentation concise
Avoid verbose rationale sections. Use 2-space indent in code-blocks.

### 6.19 One-per-line for nested/chained code examples
Break nested casts and similar constructs across lines for readability.

### 6.20 Add hyperlinks for tools and references
Provide links for external tools and standards.

### 6.21 Grammar and spelling corrections matter
Proofread documentation for proper English.

### 6.22 Use consistent terminology
Don't alternate between qualified and unqualified forms or between "definition" and "declaration" arbitrarily.

### 6.23 Write comments as English prose
Use proper capitalization, punctuation, and complete sentences. Describe *what* and *why*, not *how* at a micro level.

### 6.24 Document every non-trivial class with doxygen
Every non-trivial class should have a `///` doxygen comment block.

### 6.25 Use doxygen parameter conventions
Use `\p name` to refer to parameters in prose, `\param name` to document them, `\returns` for return values, and `\code ... \endcode` for code examples.

### 6.26 Every source file needs a header
Every source file should have a header describing its basic purpose, including the license notice. The modern preferred style omits the filename and `C++` mode line from the header comment (i.e., just the `//===---` delimiter, description, and license — no `//===--- Filename.cpp - description ---*- C++ -*-===//`).

### 6.27 Use `#if 0` for commented-out code
Don't use C-style `/* */` comments to disable code blocks; use `#if 0` / `#endif`.

---

## 7. Release Notes

### 7.1 Include release notes for user-visible changes
New checks, bug fixes, option changes, behavioral changes all need entries. NFC doc changes do not.

### 7.2 Place entries in the correct section
"New checks", "New check aliases", "Changes in existing checks", "Potentially Breaking Changes" -- each has its place.

### 7.3 Maintain alphabetical order by check name

### 7.4 Lines under 80 characters

### 7.5 Use `:doc:` directive and proper formatting
Double backticks for language constructs, single for option names.

### 7.6 Separate entries with empty lines

### 7.7 Prefer separate entries over combined ones
Multiple smaller entries are easier to read than one long paragraph.

### 7.8 Describe full scope of changes
Mention all affected components (CLI, config, helper scripts).

### 7.9 Synchronize descriptions across docs, release notes, and headers
The one-line description should be identical everywhere.

### 7.10 Follow established wording patterns
Use "Improved XXX check by..." for existing check improvements.

### 7.11 Note potentially breaking changes

---

## 8. Architecture & Code Quality

### 8.1 Implement non-trivial methods in `.cpp` files, not headers
Including constructors with logic and override methods.

### 8.2 Extract duplicated code into helpers
When patterns repeat with minor variations, extract into parameterized functions/lambdas.

### 8.3 Don't duplicate code when branching on options
Build up results incrementally rather than duplicating blocks with minor differences.

### 8.4 Keep functions small and readable
Break large functions into smaller helpers with clear names.

### 8.5 Use map/lookup instead of long if-else chains
Prefer a map or lookup table for type/name mappings.

### 8.6 Avoid double-lookups in containers
Use `find()` for a single lookup instead of `contains()` followed by `operator[]`.

### 8.7 Limit scope of helper functions
Local lambdas for single-use helpers; `static` for file-scope functions.

### 8.8 Avoid constructing expensive objects repeatedly
Build regex, matchers, etc., once (in constructor or `storeOptions`), not on each callback.

### 8.9 Avoid premature optimization that hurts readability
Don't sacrifice clarity for micro-optimizations without demonstrated benefit.

### 8.10 Avoid over-engineering
Don't add complexity without clear benefit.

### 8.11 Prefer simpler types over unnecessary wrappers
Don't use `std::optional` when the type already has a natural empty state.

### 8.12 Use a single input type per function
Don't accept both `str` and `List[str]` and branch internally.

### 8.13 Remove dead/useless code
Remove redundant returns, unused casts, unnecessary variables.

### 8.14 Remove debug output before merging

### 8.15 Use `clang-format OFF/ON` to preserve readable list formatting
When a list is organized one-per-line for readability, protect it from reformatting.

### 8.16 Deprecate API functions before removing them
Mark `[[deprecated]]` for at least 2 releases before removal.

---

## 9. Naming & Categorization

### 9.1 Check names should not use "don't"/"avoid" in `bugprone-` category
The category already implies avoidance. Use descriptive noun phrases.

### 9.2 Check category should match the nature of the issue
- `bugprone-` for likely bugs
- `readability-` for style/consistency
- `modernize-` for C++ modernization (should not break code)
- `cppcoreguidelines-` for strict guideline adherence
- `portability-` for cross-platform

### 9.3 Use unambiguous, descriptive names
Prefer user-facing terminology over internal compiler jargon.

### 9.4 Function names should reflect return types

### 9.5 Name files after check names, not class names
Makes files easier to find.

### 9.6 Prefer well-known option names (e.g., `StrictMode`)
Reuse established option names from the clang-tidy ecosystem.

### 9.7 Use standard namespace depth for check modules
`clang::tidy::CHECK_CATEGORY` -- no additional nesting.

### 9.8 Use consistent naming with existing conventions
Match prefixes, suffixes, and naming patterns established in the codebase.

### 9.9 LLVM naming conventions
- **Types**: start with an upper-case letter (UpperCamelCase)
- **Variables**: camelCase, start with an upper-case letter
- **Functions**: imperative verb phrases, camelCase, start with a lowercase letter
- **Enums**: add `Kind` suffix if discriminator for a union or subclass indicator; otherwise align with Type naming
- **Exception**: classes that mimic STL can use STL-style `lowercase_with_underscores`

---

## 10. PR & Process Discipline

### 10.1 Keep PRs small and focused
Each PR should contain one logical unit of work. Split unrelated changes into separate PRs.

### 10.2 Don't include unrelated formatting changes

### 10.3 Do not use AI-generated PR descriptions

### 10.4 PR title must match actual changes
Update title and description when scope changes during iteration.

### 10.5 Use `[clang-tidy]` prefix in PR titles

### 10.6 Include check name in PR title

### 10.7 Follow conventional commit message format
Start with an action verb (Add/Fix/Update/Make).

### 10.8 Link PR descriptions to related issues
Use "Closes https://github.com/llvm/llvm-project/issues/XXXX".

### 10.9 Require multiple reviews for new checks
At least 2 reviews for new checks; bug fixes may need only 1.

### 10.10 Wait for second reviewer on large/impactful changes

### 10.11 Wait for domain expert approval on cross-cutting changes
Get approval from relevant maintainers before merging.

### 10.12 Respect the blocking-review protocol
Don't merge while a reviewer has "requested changes". Don't request changes unless it's a major blocker.

### 10.13 Don't resolve conversations prematurely
Let the reviewer acknowledge before resolving.

### 10.14 Rebase on fresh main before merging

### 10.15 Verify CI/tests pass before merging

### 10.16 Make email addresses public per LLVM developer policy

### 10.17 Create follow-up issues for deferred work
When deferring a feature, create a tracking issue.

### 10.18 Follow revert policy for broken patches
Re-applied patches must describe what was wrong and how it was fixed.

### 10.19 Separate bug fixes from design discussions into different PRs

### 10.20 Provide high-level overview for complex changes

---

## 11. Design Principles

### 11.1 False negatives are preferable to false positives
When a check cannot be perfectly accurate, better to miss some true positives than to report incorrect warnings.

### 11.2 Consider making behavior configurable via options
When behavior might not be universally desired, put it behind an option.

### 11.3 Expose options with safe defaults
Default to the safest behavior for ordinary users. Do not flag `StringRef` usage in option storage (e.g., `std::vector<StringRef>` from `parseStringList`) as a dangling-reference risk — the option strings are owned by the check infrastructure and remain valid for the check's lifetime.

### 11.4 Prefer single multi-level option over multiple booleans
Consolidate related booleans into an option with enumerated levels.

### 11.5 Be cautious with warnings in macro contexts
Macro expansions can produce confusing diagnostics. Consider suppressing by default.

### 11.6 Verify fix-its produce correct output
Fixes that produce broken code must be caught.

### 11.7 Use `--enable-check-profile` for performance claims
Provide check-specific profile data rather than overall benchmarks.

### 11.8 Leave FIXME comments for temporary workarounds

### 11.9 Add comments explaining non-obvious logic
Regex patterns, magic values, cron schedules, and complex algorithms need inline explanation. Do not request comments for well-known C++ patterns like `std::nullopt` vs `""` return value semantics, or other patterns obvious to experienced LLVM developers.

### 11.10 Use type aliases for complex types

### 11.11 Gather maintainer consensus before adding third-party config files
Adding `.editorconfig`, `.vscode/`, etc., requires broader agreement.

### 11.12 Avoid text duplication -- reference existing descriptions

### 11.13 `.git-blame-ignore-revs` only for large-scale reformatting
Small changes don't warrant inclusion. Maintain chronological order.

### 11.14 Format Python code with Black
Per LLVM coding standards.

### 11.15 Respect minimum version requirements
Code must work with the minimum supported version (e.g., Python 3.8 for LLVM). LLVM requires C++17 as the minimum standard.

### 11.16 Always include messages in assertions
Assertions should have descriptive error messages: `assert(Ptr && "Ptr must not be null")`.

### 11.17 Use `[[maybe_unused]]` for assert-only values
Suppress "unused value" warnings for variables used only inside `assert()`.

### 11.18 Use `report_fatal_error` for unrecoverable user-triggered errors
When an error condition can be triggered by user input and recovery isn't practical.

### 11.19 Beware of pointer non-determinism
Pointers have no relative ordering. When using sets/maps with pointer keys, sort before iterating if order matters. Prefer `MapVector`, `SetVector`, or sorted `vector` for deterministic iteration.
