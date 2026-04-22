---
name: clang-tidy-fp-finder
description: >
  Adversarial correctness testing for clang-tidy checks. Use this skill whenever
  the user gives a clang-tidy check name (e.g. "modernize-use-ranges",
  "readability-simplify-bool-expr") and wants to find false positives, bad
  fix-its, wrong-standard firings, or other correctness gaps. The skill
  orchestrates: intel gathering → attack planning → parallel reproducer
  generation → live clang-tidy execution → confirmed-bug reporting. Trigger on
  any phrase like "find FPs in X", "attack X", "test X check", "look for bugs
  in clang-tidy X", or when the user just pastes a check name and asks to
  investigate it.
---

# clang-tidy False-Positive Finder

Adversarially test a clang-tidy check for false positives, bad fix-its, and
correctness gaps. Produces confirmed, executable reproducers — not speculation.

---

## Assumptions

- You are running inside an **LLVM git repo**. The repo root will be
  auto-detected (see Phase 1).
- The build directory is `<llvm-root>/build/`. The binary to use is
  **always** `<llvm-root>/build/bin/clang-tidy` — never any other install.
- `repro/` lives at `<llvm-root>/repro/` (create it if absent).
- A bug is **confirmed** only when the bash script actually executes and
  produces output that demonstrates the problem (FP warning, corrupt fix-it,
  wrong-standard firing, etc.). Pure reasoning is not enough.

---

## Phase 1 — Orchestrator: Intel Gathering

**Locate the LLVM root:**
```bash
git rev-parse --show-toplevel
```

**Locate check sources** (adapt glob as needed):
```bash
find . -type f \( -name "*.cpp" -o -name "*.h" \) \
  | xargs grep -l "<CheckName>" \
  | grep -v test | grep -v unittest
```

**Read every source and header** for the check. Pay attention to:
- AST matchers used (`hasType`, `callee`, `hasName`, `unless`, etc.)
- Options declared (`Options.get(...)`)
- `getLangOpts()` guards — are there any? Are they correct?
- Fix-it construction — does it emit C++ grammar unconditionally?
- Any `TODO` / `FIXME` comments in the source

**Read the RST documentation:**
```bash
find . -name "<check-name>.rst" 2>/dev/null | head -1
```

**Read the existing test files** (these reveal what the authors thought to
test — gaps here are attack surface):
```bash
find . -path "*/test/clang-tidy/*<check-name>*"
```

**Read git history** for the check files (last 60 commits):
```bash
git log --follow --oneline -60 -- \
  clang-tools-extra/clang-tidy/<module>/<CheckFile>.cpp
```
For any commit that mentions "fix", "revert", "NFC", "wrong", "incorrect",
"regression" — read its diff:
```bash
git show <sha> -- clang-tools-extra/clang-tidy/<module>/<CheckFile>.cpp
```
These are gold: past bug fixes reveal the exact shape of fragile logic.

**Output of Phase 1:** a structured `CheckProfile` (keep it in your working
context) with these fields:

```
CheckProfile:
  name: <check-name>
  llvm_root: <path>
  clang_tidy_bin: <llvm_root>/build/bin/clang-tidy
  source_files: [...]
  matchers_summary: <brief prose of what the AST matchers select>
  lang_guards: <what getLangOpts() guards exist, or "none">
  options: [list of option names and their effect]
  fixits: <how fix-its are constructed>
  existing_tests_summary: <what patterns are already tested>
  git_regressions: [list of past fixes that hint at fragile areas]
  std_apis_targeted: [e.g. std::find, std::ranges::find, ...]
```

---

## Phase 2 — Attack Planner

Read the `CheckProfile` and generate a list of **attack hypotheses**. Each
hypothesis must be grounded in the actual check logic — not a generic
checklist. Ask: *given these specific matchers and fix-its, where could they
misfire on code a real developer would write?*

Draw from the attack taxonomy below, but only emit hypotheses that are
plausible given *this check's* implementation:

### Attack Taxonomy

| Category                                     | What to look for                                                                                                               |
|----------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| **Standard gates**                           | Check fires in `-std=c++14` suggesting an API that didn't exist yet; or refuses to fire in C++20 where it should               |
| **Language mode**                            | Check fires with `-x c` or `-x objective-c`; fix-it emits C++ syntax in C mode                                                 |
| **Overload / variant**                       | Execution policy overloads (`std::find(std::execution::par, ...)`); `std::ranges::` vs `std::` variants; `std::views::` chains |
| **Type aliases**                             | `using MyVec = std::vector<int>; MyVec v; std::find(v.begin(), v.end(), x)` — does the matcher see through the alias?          |
| **ADL / custom namespace**                   | User-defined `ranges::`, custom `begin()`/`end()`, or `using std::find; find(...)`                                             |
| **Template / dependent types**               | The matched call is inside a template; the type is dependent; SFINAE context                                                   |
| **Macro expansion**                          | The matched call is inside a macro — fix-it would corrupt the macro body                                                       |
| **`constexpr` / `if constexpr`**             | Fix-it output breaks `constexpr` validity                                                                                      |
| **`using`-decl shadowing**                   | `using std::X; X(...)` vs `std::X(...)` — matcher may miss one form                                                            |
| **Options / aggressive mode**                | An option widens the check's scope — does the wider scope have false positives?                                                |
| **Multi-argument / overloaded constructors** | The check's suggested replacement doesn't handle all argument combinations                                                     |
| **Interaction with `auto`**                  | `auto it = std::find(...); *it` — does the fix-it produce valid code after the transform?                                      |
| **Clang AST**                                | Clang may generate AST in an unexpected way, e.g. defaulted/bodyless functions                                                 |

For each hypothesis, produce:
```
AttackPlan:
  id: <short slug, e.g. "exec-policy-overload">
  category: <from taxonomy>
  rationale: <1-2 sentences: why THIS check might fail here, citing the matcher/fixit>
  code_sketch: <5-15 line C/C++ pattern to try>
  flags: <compiler flags, e.g. -std=c++17 -x c++>
  expected_bad_behavior: <what wrong output we hope to see>
```

Aim for **5–10 hypotheses**. Prune any that the existing tests already cover
exactly.

---

## Phase 3 — Subagents: Reproduce & Verify

For **each** `AttackPlan`, spawn a subagent (Use your tool call) that
does the following. All subagents are independent; they share only the
`CheckProfile`.

You **MUST** use the subagents.

### 3a. Write the reproducer

Write a minimal, realistic C/C++ file. Rules:
- Code must look like something a real developer would write — not a fuzzer
  output. Prefer idiomatic patterns.
- Include only the standard headers needed.
- Add a comment `// expected: <what we think clang-tidy will say>` at the
  relevant line.
- Keep it under 60 lines. Shorter is better.

### 3b. Write the bash script

```bash
#!/usr/bin/env bash
set -euo pipefail
CLANG_TIDY="<llvm_root>/build/bin/clang-tidy"   # exact binary, no PATH lookup
CHECK="<check-name>"
FILE="repro.cpp"   # or repro.c for C mode attacks

echo "=== Running: $CHECK on $FILE ==="
"$CLANG_TIDY" -checks="-*,${CHECK}" \
  --warnings-as-errors="" \
  "$FILE" -- <compiler_flags>

echo "=== Fix-it output (if any) ==="
"$CLANG_TIDY" -checks="-*,${CHECK}" \
  --fix --fix-errors \
  "$FILE" -- <compiler_flags> 2>&1 || true

echo "=== File after fix-it ==="
cat "$FILE"
```

Important: capture both the diagnostic output **and** the post-fix-it file
content. A fix-it that silently corrupts code is a bug too.

### 3c. Run and parse

Execute the bash script. Then evaluate the output:

| Outcome                                                                                          | Verdict                      |
|--------------------------------------------------------------------------------------------------|------------------------------|
| clang-tidy warns on code it should not warn on                                                   | **FP confirmed**             |
| clang-tidy emits a fix-it that does not compile, changes semantics, or uses C++ syntax in C mode | **Bad fix-it confirmed**     |
| clang-tidy warns under a standard where the suggested replacement doesn't exist                  | **Wrong-standard confirmed** |
| clang-tidy crashes or ICEs                                                                       | **Crash confirmed**          |
| No warning, no bad output                                                                        | **OK — discard**             |

Only confirmed verdicts proceed to Phase 4. Discard OK results silently.

---

## Phase 4 — Reporter

For each confirmed bug, create a directory:
```
<llvm_root>/repro/<check-name>-<id>/
  repro.cpp       (or repro.c)
  run.sh
  writeup.md
```

Where `<id>` is a short slug from the `AttackPlan` (e.g.
`modernize-use-ranges-exec-policy`).

### writeup.md template

```markdown
# <check-name>: <short title of the bug>

## Category
<from taxonomy, e.g. "Overload / variant">

## Summary
<2–4 sentences: what the check does, what goes wrong, what a developer
would observe. No severity — leave that to the maintainer.>

## Reproducer

\`\`\`cpp
// contents of repro.cpp
\`\`\`

## Invocation

\`\`\`bash
# contents of run.sh (abbreviated)
\`\`\`

## Observed Output

\`\`\`
<paste the actual clang-tidy output from Phase 3>
\`\`\`

## Expected Output
<what should have happened instead — no warning, no fix-it, different fix-it, etc.>

## Root Cause Hypothesis
<1–3 sentences pointing at the specific matcher or fix-it construction
in the source that likely causes this, with file:line if known.>
```

---

## Phase 5 — Summary to User

After all subagents complete, print a brief summary table in the conversation:

```
Check: <check-name>
Hypotheses tried: N
Confirmed bugs:   M

| ID                          | Category            | Verdict          |
|-----------------------------|---------------------|------------------|
| exec-policy-overload        | Overload / variant  | FP confirmed     |
| c-mode-fixit                | Language mode       | Bad fix-it       |
| ...                         | ...                 | ...              |

Reproducers written to: <llvm_root>/repro/
```

Then list the path to each `writeup.md` so the user can review immediately.

---

## Operational Notes

- **Never use any `clang-tidy` binary except `<llvm_root>/build/bin/clang-tidy`.**
  The user has multiple LLVM installs; using the wrong one produces garbage results.
- If `./build/bin/clang-tidy` does not exist, stop and tell the user —
  do not fall back to `which clang-tidy`.
- If a reproducer does not compile at all (independent of clang-tidy), it is
  not a valid test. Fix or discard it before running.
- Restore `repro.cpp` to its original state after a `--fix` run (copy before,
  restore after) so subsequent fix-it tests start clean.
- Git operations are read-only (log, show, diff). Never commit anything.
