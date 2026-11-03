# Fallbacks (when a helper skill is not installed)

Say plainly that the helper was not available and that you are using this short version. Do not claim the helper ran.

## Debugging (`systematic-debugging`)
1. Reproduce the failure and keep the exact command or steps.
2. Narrow it: smallest input, last change, which layer.
3. Form one hypothesis, test it with a log or a failing assertion, change one thing at a time.
4. Fix the cause, not the symptom. Add a regression test. Two failed attempts: stop and reassess.

## Test first (`test-driven-development`)
Write a test for the new behavior and watch it fail for the right reason. Write the smallest code that passes. Refactor with the test green. Test the denied, invalid and empty cases too.

## Smallest change (`ponytail`)
Solve exactly what was asked. No extra files, options, abstractions or dependencies. Prefer editing existing code. Explain in a few lines.

## Verify before "done" (`verification-before-completion`)
Run the real checks and read their output before claiming anything. Evidence is a command and its result, or what you did and saw. If something was not checked, say so.

## Review (`requesting-code-review`, `receiving-code-review`)
Read the diff against the slice's acceptance sentence. Look for: missing cases, security (access control, input handling, secrets), unrelated changes, tests that cannot fail. When feedback arrives, verify each point is correct before acting; push back on wrong ones.

## Browser check (`webapp-testing`)
If no browser tool exists, run the project's own tests and call the endpoints directly, and report the visual and click-through check as not run.

## Design review (`impeccable`, `design-taste-frontend`, `frontend-design`)
Pick one direction (type, spacing, color, layout) that fits the audience and avoid the generic centered-headline, three-icon-cards, soft-gradient look. Measure contrast with `scripts/contrast.py`. Check hover, focus, loading, empty and error states, and a phone layout.

## Everything else
Use your own judgment, keep to the smallest change, and verify.
