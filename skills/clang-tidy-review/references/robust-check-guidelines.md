# Making Your Check Robust

Extracted from the [clang-tidy Contributing guide](https://clang.llvm.org/extra/clang-tidy/Contributing.html#making-your-check-robust).

## Core Principle

After covering basic scenarios, torture your check with as many edge cases as you can cover to ensure robustness. Run checks against large codebases like LLVM/Clang to identify unforeseen issues.

## Required Edge Case Testing

### Header Files
- Create header files that contain code matched by your check
- Validate that fix-its apply correctly to included headers
- Test with multiple inclusion of the same header

### Macros
- Define macros that contain code matched by your check
- Test macro expansions that produce matched patterns
- Verify diagnostics point to useful locations (not deep inside macro expansions)

### Templates
- Test with generic (uninstantiated) template classes and functions
- Test with explicit and implicit template specializations
- Test with variadic templates
- Verify no duplicate warnings from multiple instantiations

### Cross-Platform
- Test under both Windows and Linux environments
- Be aware of platform-specific behavior differences

## Managing False Positives

### Code Patterns That Silence Diagnostics
- Support explicit patterns (like void casts) that programmers can use to suppress warnings
- Document how users can silence specific diagnostics

### Configuration Options
- Provide settings that allow users to control checking behavior
- Enable more aggressive validation for those who want it without burdening typical users
- Default to the safest (least false-positive) behavior

### Expectations
- While ideally a check would have no false positives, some are expected given AST matching limitations regarding control and data flow analysis
- Higher false-positive rates reduce practical adoption
- When in doubt, prefer false negatives over false positives
