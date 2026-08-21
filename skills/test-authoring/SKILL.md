---
name: test-authoring
description: Write tests that can actually fail — a regression test for a bug just fixed, coverage for an untested module, or a first suite for a project that has none. Use when the user asks for tests, when a fix lands without one, or when the pre-commit gate reports that a project has no suite.
---

# Write tests

Produces tests that fail when the behaviour they describe breaks, and pass otherwise. That
sounds trivial and is the hard part: a test that cannot fail costs the same to run as one
that can, and reads as protection while providing none.

This is deliberately separate from running tests. The `test-summary` skill compresses a run;
`pre-commit-gate` refuses to invent a suite mid-commit and sends you here instead, because
tests written to make a commit go through assert whatever the code does at that moment —
including the bug nobody has found yet.

## Delegation

| Work | Owner | Tier | Why that tier |
| --- | --- | --- | --- |
| Decide what is worth testing | you, or `../../agents/bug-fixer.md` | deep | Choosing the cases is the judgement; writing them is not |
| Write the cases | `../../agents/test-author.md` | standard | Matching an existing convention and phrasing assertions |
| Run and report | `../../agents/test-runner.md` | cheap | Command running and parsing |

If your runtime has no subagents, follow the procedure below inline — it is complete on its
own.

## Step 1 — read the project's conventions before writing anything

Tests that ignore the house style get rewritten or deleted. Gather these first:

| Find | From |
| --- | --- |
| Framework and runner | the dependency manifest, plus how CI invokes the suite |
| Where tests live | the existing tree — alongside source, or a top-level test directory |
| Naming convention | existing test function and file names, copied exactly |
| Fixture and setup style | conftest, factories, builders, setup helpers already in use |
| What is already covered | the existing tests for the module you are about to touch |

If the project has no tests at all, the CI workflow is still the best source for the intended
runner, because it is the command that has to pass. If there is no CI either, choose the
stack's default and say plainly which you chose and why.

Do not introduce a second framework alongside an existing one. Two runners means two commands,
two config files, and a suite where half the tests silently stop running.

## Step 2 — write the failing test first, when there is a bug

For a regression test this order is not a style preference, it is the only way to know the
test works:

1. Write the test that describes the correct behaviour.
2. Run it against the **unfixed** code and watch it fail.
3. Read the failure. It must fail for the reason you intended, not because of a typo, a
   missing import, or a fixture error.
4. Apply the fix.
5. Run again and watch it pass.

Skipping step 2 is how a test that asserts nothing enters the suite. A test written against
already-fixed code passes on its first run, and a first-run pass tells you nothing about
whether the assertion is connected to the behaviour.

## Step 3 — choose what to test

Rank candidates by what a failure would cost, not by what is easy to reach:

| Priority | Test | Because |
| --- | --- | --- |
| 1 | A bug that has occurred | It has already proven it can happen, and it is the only case with evidence |
| 2 | Boundaries — empty, one, many, maximum, off-by-one, zero, negative | Defects cluster at edges; the middle of a range is where code is usually right |
| 3 | Error paths and invalid input | Rarely exercised by hand, and the branch most likely to be wrong |
| 4 | Documented behaviour — the README's promises, a public API contract | It is what users rely on, so breaking it breaks them |
| 5 | The happy path | Usually already covered incidentally by everything else |

Test the public surface, not the internals. A test that reaches into a private function
locks the implementation in place: the refactor that should be free now breaks tests, and the
person doing it deletes them rather than understanding them.

## Step 4 — write the case

One behaviour per test. A test asserting five unrelated things reports only the first failure,
so the other four stay hidden until you fix that one and run again.

Name the test for the behaviour and the condition, so a failure is readable without opening
the file. `test_rejects_expired_token` beats `test_auth_2`.

Structure every test in three visible parts — set up the situation, perform the one action,
assert the outcome. Keep the action to a single line where the language allows; when it takes
five, the test is describing a workflow rather than a behaviour.

Assert on values, not on shape. `assert result == 3` is a test; `assert result is not None` is
a test that passes for `0`, `[]`, `False`, and an error object.

### Determinism

A test that fails intermittently gets re-run until it passes, and then it protects nothing.
Remove the four common sources at the point of writing:

| Source | Instead |
| --- | --- |
| The real clock | Inject or freeze time; assert against a fixed instant |
| Unseeded randomness | Seed it, or assert the property rather than the value |
| Real network or a live service | A stub at your own boundary, with the real contract pinned by a separate integration test |
| Shared state — a real database, a temp file at a fixed path, execution order | Isolate per test; each must pass when run alone and in any order |

Confirm the last one directly: run the new test on its own, then run the full suite. A test
that only passes as part of the suite depends on something another test left behind.

## Step 5 — prove the test can fail

This is the step that separates a test from a comment. For each new test, break the behaviour
deliberately — invert a condition, return a constant, delete the line the test is about — and
confirm the test fails. Then restore the code.

If the test still passes with the behaviour broken, it is asserting something else: a mock's
return value, a default that masks the real path, or nothing at all. Fix the test before
moving on. Do not keep it on the grounds that it does no harm; it does, by making the suite
look like it covers a case it does not.

## Step 6 — what not to write

| Never | Because |
| --- | --- |
| A test that mocks the unit under test | It asserts that the mock works, which was never in doubt |
| A snapshot as the only assertion | Nobody reads a regenerated snapshot; it records behaviour rather than requiring it |
| A test with no assertion, relying on "it did not throw" | Any refactor that silently returns early keeps it passing |
| Tests written to raise a coverage number | A line executed is not a line tested, and the metric stops meaning anything |
| A test asserting log output or internal call counts | It pins the implementation, not the behaviour |
| Duplicating one test across many inputs by copy-paste | Use the framework's parameterisation; twelve near-identical tests hide the one that differs |
| Editing an existing test to accommodate new code | That test encodes a requirement — if the requirement changed, say so explicitly and get confirmation |

## Step 7 — report

State: the framework and where the tests were placed, one line per test naming the behaviour
it protects, the result of the fail-first check for each, and the full-suite result afterwards.

Name anything you deliberately did not test and why. An untested branch that someone chose to
leave is fine; an untested branch nobody noticed is the next bug.

## Verify

- [ ] Every new test was observed failing before it was observed passing.
- [ ] Each test asserts a value or an effect, not merely that something is non-null.
- [ ] Each test covers one behaviour, and its name states that behaviour.
- [ ] No test depends on the clock, the network, unseeded randomness, or another test.
- [ ] Each new test passes when run alone, and the full suite passes afterwards.
- [ ] The framework, layout, and naming match what the project already uses.
- [ ] No existing test was weakened, rewritten, or deleted to accommodate new code.
- [ ] Nothing was added purely to move a coverage number.
