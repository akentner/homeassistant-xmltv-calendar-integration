---
phase: 04-automation-extras-release
plan: 03
subsystem: infra
tags: [github-actions, release, hacs, semver, shellcheck, supply-chain]

requires:
  - phase: 03
    provides: "ci.yml and validate.yml with workflow_call and push tags-ignore v*.*.* (DST-02)"
provides:
  - "Tag-triggered Release workflow: tag must equal manifest.json version, CI + Validate run as reusable workflows, gh release create --verify-tag --generate-notes, --prerelease for hyphen-suffixed tags"
  - "Executable tests of the check-version and release job scripts (bash, jq, stub gh) and shellcheck over every workflow run step"
affects: [04-08 UAT and first v0.1.0 tag push, future workflow edits]

actuals:
  tokens: 2052
  tasks: 2
  commits: 3
plan_head_before: b53a2b861359b4ecaca0a5ee6f9c65d5b529779b
plan_head_after: 0027a3717dc17793eddf56c28fa31b1046e7ef21

tech-stack:
  added: []
  patterns:
    - "Workflow shell scripts are tested by extracting the step's run value from YAML and executing it with bash in a controlled env"
    - "External CLIs in workflow scripts (gh) are replaced by a stub executable on PATH that records its argv"

key-files:
  created:
    - .github/workflows/release.yml
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-03-red.json
    - .planning/phases/04-automation-extras-release/tdd-evidence/04-03-red.xml
  modified:
    - tests/test_repo_structure.py

key-decisions:
  - "release.yml is a verbatim copy of the sibling mqtt-actions workflow with only the manifest path changed (D-29); shellcheck found nothing to fix"
  - "Release tests execute the real workflow scripts rather than grepping them, so the tag regex, manifest comparison and prerelease flag are behaviour-checked"

patterns-established:
  - "_job_script / _run_bash helpers in tests/test_repo_structure.py for running workflow step scripts"

requirements-completed: [DST-03]

coverage:
  - id: D1
    description: "A v-prefixed SemVer tag equal to the manifest version passes the check-version job; other versions, a missing v, a two-part version and shell metacharacters are rejected without executing the tag"
    requirement: DST-03
    verification:
      - kind: unit
        ref: "tests/test_repo_structure.py#test_release_tag_check"
        status: pass
    human_judgment: false
  - id: D2
    description: "Release workflow shape: push tags v*.*.* only, release needs check-version/ci/validate, contents write only on release, CI and Validate called as reusable workflows, supply-chain rules (permissions {}, SHA pins, persist-credentials false, pinned runner, no path filters)"
    requirement: DST-03
    verification:
      - kind: unit
        ref: "tests/test_repo_structure.py#test_release_workflow_shape"
        status: pass
      - kind: unit
        ref: "tests/test_repo_structure.py (workflow_files-parametrized supply-chain tests incl. release.yml)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Release job calls gh release create <tag> --repo <repo> --verify-tag --generate-notes, adding --prerelease only for hyphen-suffixed tags; all workflow scripts pass shellcheck"
    requirement: DST-03
    verification:
      - kind: unit
        ref: "tests/test_repo_structure.py#test_release_job_flags"
        status: pass
      - kind: unit
        ref: "tests/test_repo_structure.py#test_workflow_scripts_pass_shellcheck"
        status: pass
    human_judgment: false
  - id: D4
    description: "A real tag push on GitHub publishes a release HACS offers as an update"
    requirement: DST-03
    verification: []
    human_judgment: true
    rationale: "Needs the first v0.1.0 tag push on GitHub (user step in 04-08, D-29); runner behaviour and HACS release pickup cannot be exercised locally"

duration: 2min
completed: 2026-10-21
status: complete
---

# Phase 04 Plan 03: Release Workflow Summary

**Tag-triggered GitHub release workflow that rejects any tag other than v<manifest version>, runs CI and Validate as reusable workflows first, and publishes with generated notes (prerelease for -suffix tags), with its shell scripts executed and shellchecked in tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-10-21T09:19:07Z
- **Completed:** 2026-10-21T09:21:17Z
- **Tasks:** 2
- **Files modified:** 4 (2 source/test, 2 TDD evidence)

## Accomplishments

- `.github/workflows/release.yml`: jobs `check-version` (anchored SemVer regex on `$GITHUB_REF_NAME`, `jq -r .version custom_components/xmltv_calendar/manifest.json` comparison), `ci` and `validate` (reusable `./.github/workflows/*.yml`, contents read), `release` (contents write, `gh release create --verify-tag --generate-notes`, `--prerelease` for `*-*`).
- `release.yml` added to `WORKFLOW_FILES`; the existing parametrized supply-chain tests (empty top-level permissions, SHA pins incl. local refs, no persisted credentials, push without branch filters, no path filters, one pinned runner) now cover it.
- `test_release_tag_check` runs the real check-version script with bash for five tags, including `v0.1.0;touch pwned` (no file created).
- `test_release_job_flags` runs the release script against a stub `gh` and pins the exact argv for `v0.1.0` and `v0.2.0-rc1`.
- `test_workflow_scripts_pass_shellcheck` runs `shellcheck --shell=bash -` on every run step of every workflow.

## TDD Gate Compliance

- **RED** (`76b6f52`): `test_release_tag_check[manifest-version]` failed in the test body with `FileNotFoundError` for `.github/workflows/release.yml` (JUnit: 32 tests, 7 failures, 0 errors; 25 pre-existing tests green). Classifier: `RED_EVIDENCE_OK (target_test_failed)`. Semantic assessment: the target executed and failed because the release workflow did not exist yet, which is exactly the behaviour this tracer adds; no collection, import or fixture fault. Record: `tdd-evidence/04-03-red.json`.
- **GREEN** (`113355b`): release.yml created; `tests/test_repo_structure.py` 37 passed, ruff clean.
- **REFACTOR:** none needed.
- **Tracer gate:** end-of-phase mode with automated-only verify; re-run passed (37 passed, `release_tag_check` not skipped), so expansion to Task 2 went ahead.
- Task 2 tests are regression guards over configuration Task 1 already wrote (not a TDD task, per plan). They passed at once; a manual mutation check (removing the `*-*` case and unquoting `"${flags[@]}"`) made `test_release_job_flags[prerelease]` and `test_workflow_scripts_pass_shellcheck[release.yml]` fail, then the file was restored.

## Task Commits

1. **Task 1 RED: failing release workflow tests** - `76b6f52` (test)
2. **Task 1 GREEN: release workflow** - `113355b` (feat)
3. **Task 2: release job flags and shellcheck guards** - `0027a37` (test)

## Files Created/Modified

- `.github/workflows/release.yml` - Release workflow (66 lines, sibling copy with this repo's manifest path)
- `tests/test_repo_structure.py` - `WORKFLOW_FILES` + `MANIFEST_VERSION`, helpers `_job_script` / `_run_bash`, four new tests
- `.planning/phases/04-automation-extras-release/tdd-evidence/04-03-red.json` / `04-03-red.xml` - RED evidence

## Decisions Made

- Copied the sibling workflow verbatim except for the manifest path (D-29); shellcheck reported no findings, so no behaviour-preserving edits were needed.
- The tag-check tests run the extracted script, not string matches, so a regex or comparison regression fails the suite.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Ruff flagged an unused `noqa: S603` on the shellcheck call (the argv is a literal list, so S603 does not fire there); removed it. The `bash -c` helper keeps both S603 and S607 noqa with a reason comment.

## Verification

- `uv run pytest tests/test_repo_structure.py -q -rs`: 42 passed, no skips.
- `uv run pytest -q -m "not benchmark"`: 865 passed, 1 skipped (pre-existing real-feed test, D-15), 4 deselected.
- `uv run ruff check . && uv run ruff format --check .`: clean.

## User Setup Required

None. The first `v0.1.0` tag push is a human step in 04-08 (D-29); the assistant never pushes.

## Next Phase Readiness

- DST-03 workflow part is in place. A prerelease tag needs the same suffix in manifest.json (`v0.2.0-rc1` → `"0.2.0-rc1"`), as in the sibling repo.
- `shellcheck` may be missing on the CI runner; `test_workflow_scripts_pass_shellcheck` then skips in CI and only runs locally.

## Self-Check: PASSED

- FOUND: `.github/workflows/release.yml`, `tests/test_repo_structure.py`, `tdd-evidence/04-03-red.json`, `tdd-evidence/04-03-red.xml`
- FOUND commits: `76b6f52`, `113355b`, `0027a37` (evaluation-scope resolved 3 commits for 04-03)

---
*Phase: 04-automation-extras-release*
*Completed: 2026-10-21*
