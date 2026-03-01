# LLVM Coding Standard, in a Nutshell.

**References**:

- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html)

- [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html)

## The Golden Rule

**If you are extending, enhancing, or bug fixing already implemented code, use the style that is already being used so that the source is uniform and easy to follow.**

You should refer to typical files in the repo when reviewing user's code. (e.g. `grep -rn *.cpp`)

## Formatting

Run these commands after making changes/ before starting code review:

- Python: `darker -r HEAD^ $(git diff --name-only --diff-filter=d HEAD^)`
- C++: `git clang-format HEAD~1`

Fix/Report issues if linter failed.

## Comments

- C++: `//` for normal comments, `///` for doxygen
- C: Maintain C89 compatibility

## Whitespace

**No trailing whitespaces**

## Casts

- No **RTTI** or **Exceptions**: `dynamic_cast<>` not allowed
- Handrolled `isa<>, cast<>, and dyn_cast<>` is allowed
- Prefer `static_cast, reinterpret_cast, const_cast`

## `class` and `struct`

- `struct` should be used when all members are declared public.
- All declarations and definitions of a given `class` or `struct` must use the same keyword.

## `auto`

- Use `auto`, but be aware of unnecessary copies (e.g. range-based `for` loops, use `auto &/*`)

## `#include` as Little as Possible

- Less include means less code, means faster compile time/binary size/speed.
- This one is **very very important**, you should **never forget it**.
- **Double check when reviewing/writing code.**

## `continue` and Early Exits

- To simplify code.

## No Predicate Loops, use Predicate Functions

## Miscs

- No Static Constructors
- Don't use Braced Initializer Lists to Call a Constructor (C++11)
- **Always check if user's `git branch` name is ideal, rename when necessary.**

## Naming

Always check inconsistent naming when reviewing/writing code:

- Type: start with an upper-case letter
- Var: camel case, start with an upper-case letter
- Func: imperative, verb phrases, camel case, start with a lowercase letter
- Enum: If discriminator for a union, or an indicator of a subclass, add `Kind` Suffix, otherwise align with `Type`

**Exception:** classes that mimic STL classes can have member names in STL’s style of lowercase words separated by underscores.

## Assert

- **Use the "assert" macro to its fullest.**

Also, see `llvm_unreachable`

## Forbidden usage

- `using namespace std`
- `#include <iostream>`: use `llvm::MemoryBuffer`

## Omit braces when possible

## Check UNIX newline at EOF

## Preferred APIs

**Please remember the #include rule**

- `StringRef` when handling `std::string`
- `Error` as replacement to `Exception`/`std::error_code`
- `llvm::ArrayRef`, `TinyPtrVector`, `SmallVector` over `std::vector/list`
- Never use `<list>` to avoid heap allocation (extremely high constant factor).
- Sets: `SmallSet`, `SmallPtrSet`, `StringSet`, `DenseSet`, `RadixTree`, `SparseSet`, `FoldingSet`..
  - Avoid `<set>`: malloc intensive, large per-element space overhead)
- Map: `StringMap`, `IndexedMap`, `DenseMap`, `ValueMap`
  - Avoid `<map>`: large constant factor
  - Avoid `std::multimap` and `std::unordered_map`: malloc intensive
  - Avoid `std::vector<bool>`.
