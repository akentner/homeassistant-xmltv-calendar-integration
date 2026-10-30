---
phase: 01-first-filtered-calendar
plan: 06
subsystem: distribution
tags: [hacs, hassfest, github-actions, renovate, benchmark, tracemalloc, asyncio, tdd]

requires:
  - phase: 01-first-filtered-calendar
    provides: "01-01 skeleton (manifest.json, pyproject benchmark marker, tests/xmltv conftest without hass); 01-05 parser.parse with yield_every, caps and gzip sniffing"
provides:
  - "hacs.json (XMLTV Calendar, floor 2026.3.0), MIT LICENSE, README with HACS custom-repository install"
  - "brand/icon.png 256x256 and brand/icon@2x.png 512x512, rendered from docs/assets/icon.svg"
  - ".github/workflows/validate.yml (hassfest + hacs/action, daily cron) and ci.yml (independent lint, unit, benchmark jobs), all SHA-pinned and least-privilege"
  - "renovate.json: pytest-homeassistant-custom-component bumps need dashboard approval"
  - "tests/test_repo_structure.py: offline DST-01/DST-02 checks; tests/xmltv/test_purity.py: no homeassistant imports in xmltv/"
  - "scripts/generate_benchmark_feed.py: generate(path, *, target_bytes, gzip_output, seed, start_date) -> int plus CLI (--output, --size-mb, --gzip, --start-date)"
  - "tests/xmltv/test_benchmark.py: SRC-09 time, memory and event-loop gap benchmark (marker benchmark)"
affects: [01-09, 01-10, ci, distribution, parser-performance]

actuals:
  tokens: 34675   # chars/4 over the realized diff (138,699 chars incl. RED evidence JSON/XML; PNGs count as binary stubs)
  tasks: 3
  commits: 6
plan_head_before: f6c8ef3fb82a266f9c720557840b7ccc707c6dca
plan_head_after: ab2a5e46dbc1f22e1563121caaf86b778d2ff480

tech-stack:
  added: []
  patterns:
    - "Supply-chain tests parametrize over every *.yml/*.yaml in .github/workflows, so a new workflow cannot escape the SHA-pin, permissions, credentials, push-filter and path-filter checks"
    - "Benchmark feeds come from a seeded generator into tmp_path_factory; nothing generated is committed"
    - "Benchmark measurements go to record_property and are printed with capsys.disabled(), so CI logs show them"
    - "Scripts outside packages are loaded in tests with importlib.util.spec_from_file_location inside the test body (missing file fails the test, not collection)"

key-files:
  created:
    - hacs.json
    - LICENSE
    - README.md
    - docs/assets/icon.svg
    - custom_components/xmltv_calendar/brand/icon.png
    - custom_components/xmltv_calendar/brand/icon@2x.png
    - .github/workflows/validate.yml
    - .github/workflows/ci.yml
    - renovate.json
    - tests/test_repo_structure.py
    - tests/xmltv/test_purity.py
    - scripts/generate_benchmark_feed.py
    - tests/xmltv/test_benchmark.py
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-06-red.{xml,json}
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-06-red-2.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-06-red-2-{workflows,ci,renovate}.json
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-06-red-3.xml
    - .planning/phases/01-first-filtered-calendar/tdd-evidence/01-06-red-3-{generator,ci-job}.json
  modified: []

key-decisions:
  - "01-06: brand icons are asserted at exactly 256x256 and 512x512 (the plan truth), not just at least that size"
  - "01-06: the tags-ignore comment in validate.yml/ci.yml no longer points at release.yml, which does not exist in Phase 1; triggers are unchanged"
  - "01-06: SRC-09 loop-gap result is 86-164 ms max on the dev box (limit 250 ms). The research figure of about 10 ms covered only the iterparse phase; the max gap comes from gen2 GC pauses (about 50-90 ms, growing with heap size) and the C-level sorts in normalize_programmes (about 45-70 ms). The parser was not changed"
  - "01-06: generator gzip output is reproducible (GzipFile mtime=0, empty file name); target_bytes counts uncompressed XML"

patterns-established:
  - "Pinned runner guard: every job in every workflow runs on one ubuntu-NN.NN label"
  - "Benchmark tests carry @pytest.mark.benchmark individually; generator sanity tests stay in the unit run"

requirements-completed: [DST-01, DST-02, SRC-09]

coverage:
  - id: D1
    description: "HACS metadata is valid offline: hacs.json keys allowed, name XMLTV Calendar, floor 2026.3.0; manifest has HACS keys and empty requirements; domain equals folder; brand PNGs 256 and 512; MIT LICENSE for Alexander Kentner; README names the repository URL, HACS and 2026.3"
    requirement: DST-01
    verification:
      - kind: unit
        ref: "tests/test_repo_structure.py#test_hacs_json_keys_allowed_and_floor, #test_manifest_has_hacs_required_keys, #test_domain_matches_folder_name, #test_brand_icon_is_valid_png, #test_license_is_mit_with_holder, #test_readme_documents_hacs_install_and_floor"
        status: pass
    human_judgment: false
  - id: D2
    description: "The official hassfest container, run locally against the repository, reports 0 invalid integrations and exits 0"
    requirement: DST-01
    verification:
      - kind: other
        ref: "podman run --rm -v \"$PWD\":/github/workspace:ro,Z ghcr.io/home-assistant/hassfest (image sha256:cf7088cd0eaf)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Validate and CI workflows: SHA-pinned actions, permissions {}, persist-credentials false, one ubuntu-24.04 runner, push without branch filter, no path filters, independent CI jobs, locked sync + ruff check/format + unit suite + benchmark job, hassfest + hacs (category integration, no ignore) + daily schedule"
    requirement: DST-02
    verification:
      - kind: unit
        ref: "tests/test_repo_structure.py#test_workflows_have_empty_permissions, #test_all_action_refs_are_pinned_by_sha, #test_checkout_does_not_persist_credentials, #test_push_trigger_has_no_branch_filter, #test_every_job_runs_on_one_pinned_runner, #test_workflows_have_no_path_filters, #test_ci_jobs_are_independent, #test_ci_runs_locked_sync_lint_format_and_pytest, #test_ci_has_benchmark_job, #test_validate_workflow_has_hassfest_and_hacs_jobs, #test_hacs_action_has_category_and_no_ignore"
        status: pass
    human_judgment: false
  - id: D4
    description: "Workflows go green on GitHub on every push (observable part of DST-02)"
    requirement: DST-02
    verification: []
    human_judgment: true
    rationale: "Needs the first public push, which is the human step of plan 01-10; only offline structure checks run here"
  - id: D5
    description: "Renovate requires dashboard approval for pytest-homeassistant-custom-component bumps"
    verification:
      - kind: unit
        ref: "tests/test_repo_structure.py#test_renovate_requires_approval_for_phcc"
        status: pass
    human_judgment: false
  - id: D6
    description: "No module under custom_components/xmltv_calendar/xmltv/ imports homeassistant (AST guard, with a self-test of the detector)"
    verification:
      - kind: unit
        ref: "tests/xmltv/test_purity.py#test_library_has_no_homeassistant_imports, #test_purity_guard_detects_homeassistant_import"
        status: pass
    human_judgment: false
  - id: D7
    description: "60 MB generated feed (plain and gzip): 80,773 programmes, parse well under 30 s, tracemalloc peak 102 MB (< 150 MB), max event-loop gap 86-164 ms (< 250 ms); generator deterministic and produces valid XMLTV"
    requirement: SRC-09
    verification:
      - kind: other
        ref: "uv run pytest -q -m benchmark (tests/xmltv/test_benchmark.py#test_parse_large_feed_time_and_memory[plain|gzip], #test_event_loop_stays_responsive[plain|gzip])"
        status: pass
      - kind: unit
        ref: "tests/xmltv/test_benchmark.py#test_generator_is_deterministic[plain|gzip], #test_generated_feed_is_valid_xmltv"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-13
status: complete
---

# Phase 1 Plan 06: HACS Distribution, CI and SRC-09 Benchmark Summary

**The repository is now a valid HACS custom integration: hacs.json, brand icons, MIT license and README are in place, and the official hassfest container reports 0 invalid integrations. Two SHA-pinned, least-privilege workflows (Validate: hassfest + HACS; CI: Ruff, unit, benchmark) are guarded by offline structure tests. A seeded 60 MB feed generator backs SRC-09 with measured numbers: 80,773 programmes, a 102 MB tracemalloc peak, and a maximum event-loop gap of 86-164 ms against a 250 ms limit.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-10-13T23:29:40Z
- **Completed:** 2026-10-13T23:39:49Z
- **Tasks:** 3
- **Files modified:** 13 plan files plus 9 RED-evidence artifacts

## Accomplishments

- **DST-01 (offline part).**
  - `hacs.json` is exactly `{"name": "XMLTV Calendar", "homeassistant": "2026.3.0"}`.
  - The MIT `LICENSE` names Alexander Kentner, and the short `README.md` covers HACS install, sources, calendars and the 2026.3 floor.
  - `docs/assets/icon.svg` (a calendar with a TV set) is rendered with `rsvg-convert` to `brand/icon.png` (256x256) and `brand/icon@2x.png` (512x512).
  - The local hassfest run (`ghcr.io/home-assistant/hassfest`, image `sha256:cf7088cd0eaf…`) prints `Invalid integrations: 0` and exits 0. It needed no fixes.
- **DST-02 (offline part).**
  - `validate.yml` is copied from the sibling repo (hassfest + `hacs/action` with `category: integration`, daily cron).
  - `ci.yml` has three independent jobs: `lint` (Ruff check + format), `unit` (`pytest -q -m "not benchmark"`) and `benchmark` (`pytest -q -m benchmark`).
  - Every action is pinned to a 40-character SHA. Each workflow has `permissions: {}`, every job gets `contents: read`, checkout uses `persist-credentials: false`, and all jobs run on `ubuntu-24.04`.
  - `renovate.json` holds back phcc bumps until they are approved on the dashboard.
- **Guards.**
  - `tests/test_repo_structure.py` (26 tests) runs the supply-chain checks over every workflow file in the directory and includes a self-test of the runner guard.
  - `tests/xmltv/test_purity.py` walks the AST of every `xmltv/*.py` file and finds no `homeassistant` import.
- **SRC-09.**
  - `scripts/generate_benchmark_feed.py` (stdlib only, seeded, streamed writes) and `tests/xmltv/test_benchmark.py` produce these numbers (dev box i5-10400H, Python 3.14):

| Variant | File size | Programmes | Parse (no tracemalloc) | Parse (under tracemalloc) | tracemalloc peak | Max loop gap (4 runs) |
|---------|-----------|------------|------------------------|---------------------------|------------------|-----------------------|
| plain   | 60.0 MB   | 80,773     | 2.55-2.72 s            | 8.56-8.63 s               | 102.0 MB         | 123-164 ms            |
| gzip    | 10.2 MB   | 80,773     | 2.62-2.77 s            | 8.61-8.95 s               | 102.0 MB         | 86-156 ms             |

- Limits: parse < 30 s, peak < 150 MB, gap < 250 ms, at least 75,000 programmes. All four benchmark tests pass. A full benchmark run takes about 31 s, including generating both feeds.
- Full suite: `uv run pytest -q` gives 148 passed. The unit selection gives 144 passed and 4 deselected. Ruff check and format are clean.

## Task Commits

1. **Task 1 (tracer): the repository passes hassfest locally and the HACS metadata checks offline**
   - `c821de5` test(01-06): RED, structure tests plus evidence
   - `5dc8a7b` feat(01-06): GREEN, hacs.json, LICENSE, README, icons, validate.yml
   - Tracer feedback gate: interactive, `end-of-phase`, automated-only verify. Re-ran it (15 passed, hassfest exit 0), then expanded.
2. **Task 2: CI workflow, Renovate and library purity guard**
   - `1b5fce2` test(01-06): RED, CI/Renovate/path/needs tests, purity guard, evidence
   - `6ce0199` feat(01-06): GREEN, ci.yml and renovate.json
3. **Task 3: 60 MB benchmark (SRC-09)**
   - `5a32470` test(01-06): RED, benchmark and generator tests, CI benchmark-job test, evidence
   - `ab2a5e4` feat(01-06): GREEN, generator plus CI benchmark job

## TDD Gate Compliance

| Cycle | RED | GREEN | REFACTOR |
|-------|-----|-------|----------|
| Task 1 (tracer) | `c821de5` | `5dc8a7b` | none needed |
| Task 2 | `1b5fce2` | `6ce0199` | none needed |
| Task 3 | `5a32470` | `ab2a5e4` | none needed |

**RED 1** (`01-06-red.xml/json`): target `test_hacs_json_keys_allowed_and_floor`. Classifier verdict: RED_EVIDENCE_OK (target_test_failed).
- Semantic: the target ran and failed in its body because `hacs.json` was missing, which is the failure the plan names.
- 8 failed and 3 passed. The manifest and domain checks were already green from 01-01.

**RED 2** (`01-06-red-2.xml`): three targets, all RED_EVIDENCE_OK.
- `test_expected_workflows_exist` failed on its assertion (missing `['ci.yml']`).
- `test_ci_runs_locked_sync_lint_format_and_pytest` and `test_renovate_requires_approval_for_phcc` failed on the missing files.
- The purity test and the path-filter test (validate.yml only) passed. The plan expects this: both are regression guards.

**RED 3** (`01-06-red-3.xml`): two targets, both RED_EVIDENCE_OK.
- `test_generator_is_deterministic[plain]`: the generator is loaded inside the test body, so the missing script fails the test, not collection.
- `test_ci_has_benchmark_job` failed on its assertion (no job runs the benchmark).
- The benchmark tests were deselected in that run.

**GREEN:** every target passes.

## Files Created/Modified

- `hacs.json`, `LICENSE`, `README.md`: HACS metadata, MIT license, install and usage overview.
- `docs/assets/icon.svg`, `custom_components/xmltv_calendar/brand/icon.png`, `icon@2x.png`: brand source and rendered icons.
- `.github/workflows/validate.yml`: hassfest + HACS validation, push/PR/dispatch/call/daily schedule.
- `.github/workflows/ci.yml`: `lint`, `unit` and `benchmark` jobs.
- `renovate.json`: config:recommended plus phcc dashboard approval.
- `tests/test_repo_structure.py`: DST-01/DST-02 offline checks.
- `tests/xmltv/test_purity.py`: AST purity guard.
- `scripts/generate_benchmark_feed.py`: deterministic feed generator and CLI.
- `tests/xmltv/test_benchmark.py`: generator tests and the SRC-09 benchmark.

## Decisions Made

- Brand icon sizes are asserted exactly (256 and 512), matching the plan truth.
- The `tags-ignore` comment in both workflows now says a tag points at a commit whose branch push already ran the checks. The sibling's comment pointed at a `release.yml` that does not exist here. The trigger itself is unchanged.
- Benchmark timing is recorded twice:
  - under tracemalloc in the memory test, which is an upper bound and is the value checked against the 30 s limit
  - without tracemalloc in the loop-gap test
- The generator's `target_bytes` counts uncompressed XML. Gzip output uses `mtime=0` and an empty file name, so it is byte-reproducible.

## Deviations from Plan

### Auto-fixed Issues

None needed: hassfest passed on its first run, and no code fixes were required.

### Plan adjustments (documented, not rule-driven)

**1. Workflow comment changed in the "verbatim" copies**
- **Found during:** Task 1 (validate.yml) and Task 2 (ci.yml)
- **Issue:** the sibling comment "A version tag runs these checks once, through release.yml" points at a file that does not exist in this repo (PATTERNS: "no release.yml in Phase 1").
- **Fix:** comment text only. Triggers, pins and jobs are identical to the sibling.
- **Committed in:** 5dc8a7b, 6ce0199

**2. Extra guard tests beyond the behaviour list**
- `test_expected_workflows_exist` and `test_runner_guard_flags_unpinned_and_mixed_runners` (test_repo_structure.py), `test_purity_guard_detects_homeassistant_import` (test_purity.py), `test_generated_feed_is_valid_xmltv` and the gzip variant of the determinism test (test_benchmark.py).
- **Why:** the supply-chain tests parametrize over the workflow files that exist, so a deleted ci.yml would otherwise just drop its checks without failing. The detector self-tests prove the guards can fail.
- **Committed in:** 1b5fce2, 5a32470

---

**Total deviations:** 0 rule-driven auto-fixes, 2 documented plan adjustments.
**Impact on plan:** None on interfaces. There is no scope creep.

## Issues Encountered

- **Loop gap is much higher than the research estimate, though still under the limit.**
  - The research put the max gap at about 10 ms with `yield_every=250`. The real maximum is 86-164 ms.
  - Diagnosis (a scratch script with `gc.callbacks` and phase timestamps; the parser was not changed):
    - Gen2 GC pauses take about 47 ms standalone and about 90 ms with Home Assistant modules imported.
    - The C-level sorts and tuple building in `normalize_programmes` hold the GIL for about 45-70 ms in one go.
    - `yield_every` only covers the iterparse loop.
  - The 250 ms limit still holds with about 90 ms margin on the dev box.
  - **Risk:**
    - A slower CI runner could make the benchmark job flaky.
    - On `ha-host`, with a larger heap, GC pauses may be longer.
    - Plan 01-09's manual check should look at this.
  - **Possible later fix:** merge the per-channel groups with `heapq.merge` instead of one final `list.sort`. The GC part cannot be fixed inside the library.
- Commits landed on `main`. The orchestrator dispatched this executor sequentially on the main working tree (`branching_strategy: none`, no remote) and explicitly authorized that, as for 01-01 to 01-05.
- The README already describes local-file sources and include/exclude patterns, which plans 01-07 and 01-08 add to the flows. The README is meant for the first public push (01-10), after those plans.

## User Setup Required

None. No external service configuration is required. GitHub repository metadata (description, topics, issues) for HACS validation is the human step of plan 01-10.

## Next Phase Readiness

- Plan 01-09 can build feeds for the ha-dev check with `uv run python scripts/generate_benchmark_feed.py --output <path> [--gzip] --start-date <today>`.
- Plan 01-10: after the push, the Validate and CI workflows should go green as they are. hassfest is already clean locally, and the brand icons exist, so no `ignore: brands` is needed.

## Self-Check: PASSED

- All 13 plan files exist on disk.
- Commits c821de5, 5dc8a7b, 1b5fce2, 6ce0199, 5a32470 and ab2a5e4 are ancestors of HEAD. That is 6 commits since f6c8ef3, measured with `git rev-list --count`.
- `uv run pytest -q` gives 148 passed. `uv run pytest -q -m "not benchmark"` gives 144 passed. `uv run ruff check . && uv run ruff format --check .` is clean. hassfest exits 0.
- The acceptance greps pass:
  - `hacs/action@`, `category: integration`, `uv sync --locked`, `persist-credentials: false`, `dependencyDashboardApproval`, `pytest -q -m benchmark`
  - `file` reports `PNG image data, 256 x 256`
  - `git status --porcelain` shows no generated `.xml`/`.xml.gz`

---
*Phase: 01-first-filtered-calendar*
*Completed: 2026-10-13*
