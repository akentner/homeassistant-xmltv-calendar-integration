---
phase: 01-first-filtered-calendar
plan: 10
subsystem: infra
tags: [github, ci, hacs, hassfest, publish, secret-scan, renovate]
requires:
  - phase: 01-06
    provides: ".github/workflows/ci.yml (Ruff, Unit tests, Benchmark) and validate.yml (hassfest, HACS), hacs.json, brand icons, local hassfest container command"
  - phase: 01-09
    provides: "Final Phase 1 code state (HEAD before publish) and the real-feed acceptance suite"
provides:
  - "Public repository github.com/akentner/homeassistant-xmltv-integration (description, issues enabled, topics calendar, custom-component, epg, hacs, home-assistant, integration, xmltv)"
  - "Green CI (Ruff, Unit tests, Benchmark 60 MB feed) and Validate (hassfest, HACS) runs for HEAD ffd5363 on GitHub-hosted runners (DST-02)"
  - "Anonymized public history: host names replaced by ha-host / dev-host before the first push"
  - "DST-01 HACS custom-repository acceptance queued as an end-of-phase UAT human-check"
affects: [phase-01-uat, phase-01-verify, release-workflow, renovate]
actuals:
  tokens: 0   # no repository files changed by this plan's tasks; this SUMMARY and state docs excluded
  tasks: 3
  commits: 0
plan_head_before: ffd5363d68fcce80800ccfe2e1f81f2b38ed4e30
plan_head_after: ffd5363d68fcce80800ccfe2e1f81f2b38ed4e30
tech-stack:
  added: []
  patterns:
    - "Publish gate: run every CI check locally (uv sync --locked, ruff check, ruff format --check, pytest incl. benchmark, hassfest container) plus a git grep secret scan before the first push"
    - "A new repository's first branch push may not emit a push event; both workflows keep workflow_dispatch so the first green run for HEAD can be triggered without a code change"
key-files:
  created: []
  modified: []
key-decisions:
  - "01-10 Task 2: before the first push, at the user's request, host names were rewritten across the full local history of main with git filter-repo --replace-text (dev laptop -> dev-host, 54 hits; HA host -> ha-host, 24 hits in 18 files). All SHAs changed (69 commits, HEAD dcebd6f -> ffd5363); SHAs cited in 01-01..01-09 SUMMARYs refer to the pre-rewrite history, commits stay findable by subject; local branch backup/pre-anonymize (not pushed) keeps the old history"
  - "01-10 Task 3: GitHub emitted only a CreateEvent for the initial push of main, so no push-triggered runs existed; CI and Validate were started with workflow_dispatch on main (same SHA, no code change). The next push (the 01-10 docs commits) is the first push-triggered run"
  - "01-10: Renovate is active on the public repo from the first minute (PR #1 home-assistant/actions digest, PR #2 setup-uv v10.3.0, issue #3 Dependency Dashboard); both PRs passed CI and Validate and are left for the user to merge"
patterns-established:
  - "New prose in .planning/ uses ha-host / dev-host, never real host names"
requirements-completed: [DST-02]
coverage:
  - id: D1
    description: "Local pre-publish gate green: uv sync --locked, ruff check, ruff format --check, pytest (213 passed, 1 skipped incl. benchmark), hassfest container 0 invalid integrations"
    requirement: "DST-02"
    verification:
      - kind: other
        ref: "uv run pytest -q (Task 1: 213 passed, 1 skipped; end of plan: pytest -q -m 'not benchmark' 209 passed, 1 skipped, 4 deselected)"
        status: pass
      - kind: other
        ref: "uv run ruff check . && uv run ruff format --check ."
        status: pass
      - kind: other
        ref: "hassfest container (01-06 command), 0 invalid integrations"
        status: pass
    human_judgment: false
  - id: D2
    description: "No real credential, token or private URL in tracked files or history; every secret-scan hit is a deliberate test dummy"
    verification:
      - kind: other
        ref: "git grep -nIE secret scan over HEAD and git log -p history, excluding uv.lock (Task 1)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Public repository with description, issues enabled and the seven topics; origin/main equals local HEAD ffd5363"
    requirement: "DST-01"
    verification:
      - kind: other
        ref: "gh repo view akentner/homeassistant-xmltv-integration --json visibility,hasIssuesEnabled,description,repositoryTopics"
        status: pass
      - kind: other
        ref: "git ls-remote origin main == git rev-parse HEAD"
        status: pass
    human_judgment: false
  - id: D4
    description: "CI (Ruff, Unit tests, Benchmark 60 MB feed) and Validate (hassfest, HACS) concluded success on GitHub for HEAD ffd5363"
    requirement: "DST-02"
    verification:
      - kind: other
        ref: "gh run list --repo akentner/homeassistant-xmltv-integration --commit ffd5363d68fcce80800ccfe2e1f81f2b38ed4e30 --json workflowName,conclusion (CI success, Validate success)"
        status: pass
    human_judgment: false
  - id: D5
    description: "HACS on a real Home Assistant accepts the repo as a custom repository of type Integration and lists 'XMLTV Calendar' with its brand icon"
    requirement: "DST-01"
    verification: []
    human_judgment: true
    rationale: "Needs the HACS UI on a live Home Assistant (ha-host); the HACS action validates repository structure but not the custom-repository add flow or icon rendering"
duration: 5min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 10: Publish to GitHub Summary

**Public repo akentner/homeassistant-xmltv-integration with anonymized history, green CI (Ruff, unit, 60 MB benchmark) and Validate (hassfest, HACS) for HEAD ffd5363, and the HACS custom-repository check queued for UAT**

## Performance

- **Duration:** about 5 min of executor time for Task 3 and docs. Task 1 ran in the earlier executor session, and Task 2 was the user's push.
- **Started:** 2026-10-14T10:55:00Z (continuation at Task 3)
- **Completed:** 2026-10-14T10:59:26Z
- **Tasks:** 3 of 3
- **Files modified:** 0 repository files (planning docs only)

## Accomplishments

- **Local gate (Task 1):** everything CI runs was green before the push:
  - `uv sync --locked`, `ruff check`, `ruff format --check`
  - pytest: 213 passed, 1 skipped (the D-15 real-feed excerpt is deferred)
  - hassfest container (image 369f29bbac85): 0 invalid integrations
- **Benchmark (local):**
  - plain: 8.3 s, 101.9 MB, event-loop gap 106.6 ms
  - gzip: 8.83 s, 102.0 MB, gap 73.3 ms
- **Secret scan:** no real secrets in HEAD or in the full history. Every hit is the deliberate `s3cret` dummy (table below).
- **Repository (Task 2):**
  - Public, with description and issues enabled.
  - Seven topics, set before the first push so the first Validate run already had them.
  - `origin/main` = `ffd5363`.
- **GitHub runs (Task 3):** CI and Validate concluded `success` for `ffd5363`. DST-02 is observed live.

## GitHub Runs (HEAD ffd5363d68fcce80800ccfe2e1f81f2b38ed4e30)

| Workflow | Event | Jobs | Conclusion | URL |
|----------|-------|------|------------|-----|
| CI | workflow_dispatch | Ruff, Unit tests, Benchmark (60 MB feed) | success | https://github.com/akentner/homeassistant-xmltv-integration/actions/runs/38553243429 |
| Validate | workflow_dispatch | hassfest, HACS | success | https://github.com/akentner/homeassistant-xmltv-integration/actions/runs/38553246496 |

Renovate PR runs on branches based on `ffd5363` were also green:
- PR #1, home-assistant/actions digest: CI 38552941739, Validate 38552941725
- PR #2, setup-uv v10.3.0: CI 38552955690, Validate 38552955742

## Secret-Scan Review (Task 1)

The scan used `git grep -nIE` over HEAD and the full history (`git log -p`) for assignments to api key / token / secret / password names with values of eight or more characters, excluding `uv.lock`.

| Hit | Location | Justification |
|-----|----------|---------------|
| `s3cret` query token on `epg.example.com` | `tests/test_source.py:24` | Deliberate dummy. It shows that the URL query is kept but never logged. |
| `s3cret` query token on `epg.example.com` | `tests/test_identity.py:88`, `:90` | Deliberate dummy. It shows that the normalized URL keeps the query while unique_id hashing hides it. |
| Same dummy, copied into the test output | `.planning/phases/01-first-filtered-calendar/tdd-evidence/01-07-red-2*.xml` / `.json` (also `01-05-red-3*`) | RED-phase JUnit/JSON evidence of the tests above. Same dummy value. |
| Same dummy, quoted in prose | `01-05-PLAN.md`, `01-05-SUMMARY.md`, `01-10-PLAN.md` | Plan and summary text that describes the log-redaction tests. |

- No credential-shaped strings and no private IPs.
- `example.com` is a reserved domain.

## Task Commits

1. **Task 1: Pre-publish gate.** No commit; every check was green and nothing needed fixing.
2. **Task 2: Create the public GitHub repository and push.** User action, no commit. The history rewrite before the push is described under Deviations.
3. **Task 3: Confirm CI and Validate are green.** No commit, since no fix was needed.

**Plan metadata:** see the `docs(01-10)` commit that adds this SUMMARY.

## Files Created/Modified

- None in the repository code. Only `.planning/` docs: this SUMMARY, STATE.md, ROADMAP.md, REQUIREMENTS.md.

## Decisions Made

- **Hosts anonymized before the first push.** This was the user's request. Host names were rewritten to `ha-host` / `dev-host` across the full local history, so the public history carries no real host names.
- **First green run via `workflow_dispatch`.** The initial branch push produced no push-triggered runs, so `workflow_dispatch` on `main` was used for the first green run of HEAD. No code changed and nothing was pushed by Claude.
- **Renovate PRs #1 and #2 are left open for the user** (both green).

## Deviations from Plan

### 1. [User-requested, Task 2] History rewritten to anonymize host names before the first push

- **Found during:** Task 2, before the push.
- **Issue:** Tracked files and history named the real dev laptop and HA host. Hits were in the tdd-evidence JUnit/JSON, `.claude/CLAUDE.md`, `.planning/` and the research notes. The repo was about to become public.
- **Fix:** The orchestrator ran `git filter-repo --refs main --replace-text` at the user's explicit request:
  - dev laptop → `dev-host`: 54 hits
  - HA host → `ha-host`: 24 hits in 18 files
- **Verification:**
  - 0 hits in HEAD and in the history.
  - The diff against the backup is exactly 78/78 lines.
  - Tests are green.
- **Impact:**
  - Every commit SHA changed. There are still 69 commits; HEAD went from `dcebd6f` to `ffd5363`.
  - SHAs cited in the 01-01..01-09 SUMMARYs refer to the pre-rewrite history. Those commits can still be found by subject.
  - Local branch `backup/pre-anonymize` keeps the old history. It is not pushed.
- **Committed in:** history rewrite, so there is no separate commit.

### 2. [Rule 3 - Blocking, Task 3] No push-triggered runs for the initial push; used workflow_dispatch

- **Found during:** Task 3.
- **Issue:** `gh run list --commit ffd5363` returned `[]`. The repo events show a `CreateEvent` for `main` (10:54:27Z) but no `PushEvent`, so GitHub did not run push workflows for the repository's first branch push. Both workflows were registered and active, and Actions was enabled.
- **Fix:** Ran `gh workflow run CI --ref main` and `gh workflow run Validate --ref main`. Both workflows declare `workflow_dispatch`. Same SHA, no code change, no push.
- **Verification:** `gh run watch --exit-status` exited 0 for both runs, and `gh run list --commit HEAD` shows CI and Validate as `success`.
- **Follow-up:** the user's next push, which carries these docs commits, will produce the first push-triggered CI and Validate runs. That is the "on every push" half of DST-02.

---

**Total deviations:** 2 (1 user-requested history rewrite, 1 Rule 3 trigger workaround)
**Impact on plan:** No code changes. All acceptance criteria were met.

## Issues Encountered

None beyond the missing push event above.

## Pending Human Check (UAT, DST-01)

1. In HACS on ha-host: HACS → menu → Custom repositories → add `https://github.com/akentner/homeassistant-xmltv-integration` as type **Integration**.
   - HACS accepts it without a validation error.
   - It lists **XMLTV Calendar** with the brand icon.
   - Installing it is not required in Phase 1 (D-16).
2. On GitHub, the Actions tab shows CI (Ruff, Unit tests, Benchmark) and Validate (hassfest, HACS) green for the latest commit. After the docs push, this should also be true for a `push` event.

## User Setup Required

- Push the local docs commits (`git push`). Local `main` is ahead of `origin/main` by the 01-10 docs commits, and this push triggers the first push-event CI/Validate runs.
- Optional: merge the Renovate PRs #1 and #2.

## Next Phase Readiness

- Phase 1 has all 10 plans executed. Next steps are the phase verification and UAT, including the DST-01 HACS check and the ha-dev walkthrough from 01-09.
- The CI benchmark job passed on a GitHub-hosted runner. The event-loop-gap concern in STATE.md stays open for ha-host hardware.

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-14*
