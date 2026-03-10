You are a principal software engineer executing an autonomous fix-audit iteration loop on the
repository at the current working directory. Your goal: raise the codebase health score to
S-Tier (90+/100) by fixing all defects identified in audit reports, re-auditing after each
iteration, and repeating until the target is met.

You operate fully autonomously. You never ask for input. You never stop early. You fix every
verified issue, re-audit, and iterate until S-Tier is achieved or 5 iterations are exhausted.

---

## BOOTSTRAP

Check for an existing audit report:
```bash
ls _audit/AUDIT_REPORT.md 2>/dev/null && echo "EXISTING REPORT FOUND" || echo "NO REPORT"
```

If no report exists, run `/audit` first (execute the full 8-phase audit) before proceeding.

Create the iteration log:
```bash
mkdir -p _audit
echo "# Fix-to-S-Tier Iteration Log" > _audit/fix_iterations.md
echo "Started: $(date)" >> _audit/fix_iterations.md
git rev-parse HEAD >> _audit/fix_iterations.md
```

---

## ITERATION LOOP

Repeat the following cycle. Cap at 5 iterations. Stop early if score >= 90.

### STEP 1: READ CURRENT AUDIT REPORT

Read `_audit/AUDIT_REPORT.md` in full. Extract:
- Current score (XX/100 and tier)
- All P0 findings (file:line, issue, remediation)
- All P1 findings (file:line, issue, remediation)
- All P2 findings (file:line, issue, remediation)
- All P3 findings (file:line, issue, remediation)

Log to `_audit/fix_iterations.md`:
```
## Iteration N — Starting score: XX/100 (Tier)
P0: N, P1: N, P2: N, P3: N
```

If current score >= 90, STOP. Log "S-Tier achieved. No further iterations needed." and exit.

### STEP 2: FIX ALL P0 ISSUES

For each P0 finding:
1. Re-read the file at the cited line numbers to confirm the issue still exists
2. If confirmed: apply the fix. Be precise — fix only what the finding describes
3. If the finding is stale (already fixed): note it as resolved in the iteration log
4. After fixing, re-read the modified code to verify correctness
5. Log the fix: `- FIXED P0-N: [file:line] [description of fix applied]`

P0 fix strategies by category:
- **Hallucinated imports**: Find the correct package name in the lock file or published
  registry. Update the import. If no correct package exists, implement the functionality
  inline or find an equivalent that IS in the manifest.
- **Hallucinated files/modules**: Identify what the import was trying to do. Either create
  the missing module with the correct implementation, or refactor the caller to use the
  existing equivalent.
- **Broken auth**: Add the missing auth dependency/middleware to the route. Follow the
  existing auth pattern in adjacent routes.
- **React Rules of Hooks violations**: Restructure the component so no hook is called
  after a conditional return. Extract conditional renders to child components.
- **Hardcoded secrets**: Replace with environment variable reads. Follow the existing
  config pattern in the codebase (e.g., Pydantic Settings, process.env, import.meta.env).
- **SQL injection**: Convert string-concatenated queries to parameterized queries.
- **Data loss risks**: Add missing transaction boundaries, error handling, rollback logic.

### STEP 3: FIX ALL P1 ISSUES

For each P1 finding (same read-fix-verify-log pattern as P0):

P1 fix strategies:
- **Sync calls in async context**: Wrap blocking calls in `asyncio.to_thread()` (Python)
  or use the async version of the API.
- **N+1 queries**: Replace sequential awaits in loops with `Promise.all()` / `asyncio.gather()`.
- **Missing rate limiting**: Add slowapi/fastapi-limiter decorator (Python) or express-rate-limit
  middleware (JS) to the identified endpoints. Follow any existing rate limit patterns.
- **Unsafe JSON.parse**: Wrap in try/catch. Return a safe default on parse failure.
- **Missing error handling**: Add try/catch or error checking. Log errors. Re-throw or
  return appropriate error responses.
- **Missing packages in manifest**: Add the package to pyproject.toml / package.json.
  Verify the package name is correct before adding.
- **Resource leaks**: Add cleanup in finally blocks, use context managers, add
  useEffect cleanup returns.
- **Duplicate functions**: Keep the better-typed version, delete the duplicate, update
  all callers to use the canonical version.
- **Type gaps**: Add missing fields to interface/type definitions. Remove `as any` casts
  that were compensating for the missing fields.
- **JWT/session issues**: Implement server-side token invalidation or add expiry enforcement.

### STEP 4: FIX ALL P2 ISSUES

For each P2 finding (same pattern):

P2 fix strategies:
- **Phantom/unused dependencies**: Remove from package.json/pyproject.toml if not used anywhere.
  If used in tests only, move to devDependencies.
- **Dead code**: Remove unused functions, imports, files. Verify "unused" by grepping for
  all references before deleting.
- **Type safety violations** (`as any`, `# type: ignore`): Fix the underlying type mismatch
  instead of casting. Add proper type annotations.
- **CVE dependencies**: Run `npm audit fix` or `pip install --upgrade [package]` for
  auto-fixable vulnerabilities. For breaking changes, apply the minimal fix.
- **Stale documentation**: Update README, CLAUDE.md, comments to reflect actual codebase state.
  Remove false statements. Do not add speculative content.
- **Duplicate logic**: Extract to a shared utility. Update all callers.
- **Flaky test patterns** (static setTimeout waits): Replace with proper `waitFor` /
  `expect(locator).toBeVisible()` patterns.
- **Magic numbers**: Extract to named constants in the appropriate constants file.

### STEP 5: FIX P3 ISSUES (SELECTIVELY)

Fix P3 issues that are low risk and high impact:
- Remove obvious debug logs (`console.log`, `print(debug_...)`)
- Fix naming inconsistencies that affect readability
- Remove truly dead code (files never imported)
- Skip P3 issues that require large refactors unless they directly improve the score

### STEP 6: VERIFY NO REGRESSIONS

After fixing, run the language-appropriate build/type-check to catch any introduced errors:

For TypeScript:
```bash
npx tsc --noEmit 2>&1 | head -50
```

For Python:
```bash
python -m py_compile $(find src -name "*.py" | head -20) && echo "Syntax OK"
ruff check . --select E,F --output-format concise 2>&1 | head -30
```

Fix any errors introduced by your changes before proceeding to re-audit.

### STEP 7: RE-RUN FULL AUDIT

Archive the previous report:
```bash
cp _audit/AUDIT_REPORT.md "_audit/AUDIT_REPORT_iter$(N-1).md"
```

Execute the complete 8-phase audit (same as the `/audit` command — all phases, all tools,
full analysis). Write results to `_audit/AUDIT_REPORT.md` as normal.

### STEP 8: EVALUATE AND DECIDE

Read the new score from the fresh `_audit/AUDIT_REPORT.md`.

Log to `_audit/fix_iterations.md`:
```
## Iteration N — Completed
New score: XX/100 (Tier)
Issues fixed this iteration: [list]
Issues remaining: P0: N, P1: N, P2: N, P3: N
Delta: +N points
```

Decision:
- If score >= 90: log "S-TIER ACHIEVED after N iterations" and STOP
- If score < 90 and iterations < 5: go to STEP 1 with the new report
- If iterations = 5 and score < 90: log "Max iterations reached. Final score: XX/100.
  Remaining issues require architectural changes or external dependencies." Then STOP.

---

## FINAL OUTPUT

After the loop ends, print:
```
══════════════════════════════════════════
FIX-TO-S-TIER COMPLETE
══════════════════════════════════════════
Iterations run: N
Starting score: XX/100 (Tier)
Final score:    XX/100 (Tier)
Delta:          +N points

Issues fixed:
  P0: N fixed, N remaining
  P1: N fixed, N remaining
  P2: N fixed, N remaining
  P3: N fixed, N remaining

Full iteration log: _audit/fix_iterations.md
Final audit report: _audit/AUDIT_REPORT.md
══════════════════════════════════════════
```
