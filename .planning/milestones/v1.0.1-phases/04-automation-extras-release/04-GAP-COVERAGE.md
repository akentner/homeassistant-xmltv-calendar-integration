# Phase 04 additive gap-plan coverage

Scope authority: user chose **ADD** after `4 --gaps`. Preserve executed 04-01..04-08 and all eight summaries. Primary source: `04-VERIFICATION.md` gaps, not the whole review backlog. No Phase 04 UAT file exists; `01-UAT.md`, `02-UAT.md` and `03-UAT.md` are prior-phase artifacts, not additional Phase 04 gap inputs.

## Dependency graph and estimates

| Plan | Wave | Needs | Creates / user outcome | Checkpoint |
|---|---|---|---|---|
| 04-09 | 1 | Executed 04-01/04-04/04-05/04-06, current Store | CalendarMatcher and disabled-calendar automation/retention plus lifecycle tests | none |
| 04-11 | 1 | Executed 04-05/04-08, FAILURE_REASONS | Translated diagnostic failure states enforced through HA loader | none |
| 04-10 | 2 | New 04-09 matcher and lifecycle | Race-safe silent baseline/recheck, template-only edit scan avoidance | none |

Same-wave files are disjoint. 04-09 and 04-10 both modify matcher.py, so 04-10 explicitly depends on 04-09. Completed predecessors are satisfied, allowing fresh gap waves to start at 1. No new one-way door: D-03/D-07/D-14 contracts are preserved, not renegotiated. Estimate calibration returned factor 1, sample_count 0, confidence low; raw projections 42000/26000/11000 include source/test reading and repeated TDD verification. Three/two/two tasks respectively, at most five modified paths per task. Each leading tracer must be green before expansion. Nyquist is disabled; no validation scaffold is needed.

## Discovery / active hooks

- Project instructions: `.claude/CLAUDE.md`; no local AGENTS.md or project skills directories found. Configured `gsd-planner --skills-only` block is empty. Current source, not stale zero-symbol API-SURFACE.md, grounds interfaces.
- Reuse current 04-RESEARCH and 04-PATTERNS, Level 0 internal changes, no new library/service; no new research or package install.
- Active plan:pre contributions were rendered through the installed CLI and consumed in order: API coverage detector, assumption delta, schema detection, security, TDD. No new AI or frontend functionality. ui-plan-gate frontend:false; context drift clear; codebase drift skipped (no map), as supplied by orchestrator.
- API detector installed at `/home/akentner/.config/opencode/gsd-core/bin/lib/api-coverage.cjs` returned detected:false over existing phase plans and roadmap, then again over all eleven final plans and roadmap before handoff. No external service capability surface added; a coverage matrix is not triggered by a real external API.
- Assumption-delta scan returned detected:true (also/configurable). 04-09 records promote: calendar subentry stays primary; matching is runtime-owned rather than presentation-owned. This is not adding a second identity model.
- Schema scan: no Payload/Prisma/Drizzle/Supabase/TypeORM paths in phase/context/research or plan files_modified. Existing HA Store serialization is not an ORM schema push. No install/migration/deployment task is required.
- Security ASVS L1, high blocking: all new plans have trust boundaries, threat dispositions and unique numeric IDs T-04-24..T-04-32, continuing after executed maximum T-04-23; reserved T-04-SC repeats by design. TDD enabled: all behavior tasks carry explicit RED/GREEN/REFACTOR and failing-direction commands.
- Existing modified source paths were checked with `git ls-files`; matcher.py and the two named test modules are intentionally new. No runtime/install mirrors are editing targets. All verify commands assume repository-root cwd; no new runner or dependency install.

## Multi-source coverage audit

“Covered” means executable plan ownership, not a claim of passing verification or completed human judgment.

| Source | ID | Contract / feature | Plan ownership | Status / notes |
|---|---|---|---|---|
| GOAL | SC1 | Next-match sensor beyond calendar triggers | 04-01 + 04-09/04-10 | COVERED; CR-01 and edit expansion |
| GOAL | SC2 | New-match events and recent-past retention across restart | 04-04/04-06/04-07 + 04-09/04-10 | COVERED; disabled path and CONFIG/DATA ordering |
| GOAL | SC3 | Blueprint one notification per overlapping match | 04-02 | COVERED executed owner; import/notify UAT pending |
| GOAL | SC4 | English/German UI | 04-07/04-08 + 04-11 | COVERED; failure_reason gap closure, frontend pending |
| GOAL | SC5 | Tagged HACS release and documentation | 04-03/04-08 | COVERED; user release/HACS pickup pending, never automatic acceptance |
| REQ | AUT-03 | Next-match timestamp/attributes | 04-01, 04-09, 04-10 | COVERED |
| REQ | AUT-05 | Queued blueprint | 04-02 | COVERED, no redo |
| REQ | AUT-06 | Last-fetch diagnostic | 04-05, 04-09, 04-11 | COVERED; disabled counts and localized reason values |
| REQ | EVT-07 | Ended-match retention up to seven days | 04-06/04-07, 04-09/04-10 | COVERED |
| REQ | EVT-08 | Persisted new-match event | 04-04, 04-09/04-10 | COVERED |
| REQ | CFG-04 | Bilingual UI | 04-01/04-05/04-07/04-08, 04-11 | COVERED |
| REQ | DST-03 | Version-matched tagged release | 04-03/04-08 | COVERED; actual publish remains human |
| REQ | DST-04 | Single English README | 04-08 | COVERED; fixing CR-01 restores stated unknown semantics without a warning-only documentation workaround |
| RESEARCH | Constraints/stack | HA 2026.3 floor, Python/uv/Ruff, no runtime deps, UI-only, no blocking work, safe logs | 04-01..04-08; all new plans | COVERED; no new install or platform requirement |
| RESEARCH | Pattern 1 / map | Reason-aware initial/DATA/CONFIG, silent baselines | 04-04 → 04-09/04-10 | COVERED; entity ownership recommendation superseded by CR-01 evidence, matching remains HA glue, pure rules remain xmltv/ |
| RESEARCH | Pattern 2 / map | next_after, timer, device/translation/recorder contracts | 04-01 → 04-09 | COVERED; runtime replaces calendar as producer, sensor timer remains entity-owned |
| RESEARCH | Pattern 3 / map | Shared private bounded Store, tolerant readers, captures/merge, raw data | 04-04/04-06 → 04-09/04-10 | COVERED; serialized schema unchanged |
| RESEARCH | Pattern 4 / map | RefreshAttempt, all run types, persistence/signals | 04-05 | COVERED; 04-09 changes counts only, cancellation backstop remains human |
| RESEARCH | Pattern 5 / map | retention_days flat 0..7 default 1, advanced field | 04-06/04-07 → 04-09/04-10 edit tests | COVERED |
| RESEARCH | Pattern 6 / map | Legacy trigger/floor, negative duration, queued, action variables | 04-02 | COVERED; UAT remains pending |
| RESEARCH | Pattern 7 / map | Tag validation, release, README/import link/limitations | 04-03/04-08 | COVERED; user-only publish |
| RESEARCH | Pitfall 1 | Concurrent platform setup | 04-01 → 04-09 T1 | COVERED; initialize matcher independently |
| RESEARCH | Pitfall 2 | Platform callbacks and later subentry additions | 04-01 → 04-09 T3 | COVERED |
| RESEARCH | Pitfall 3 | Old delayed save overwrites new Store | 04-04 → 04-09 T3 / 04-10 | COVERED; deterministic teardown gates |
| RESEARCH | Pitfall 4 | Parser cutoff and missing ended-match capture | 04-06 → 04-09 T2/T3 | COVERED |
| RESEARCH | Pitfall 5 | Event burst | 04-04 → 04-09/04-10 preserved cap tests | COVERED |
| RESEARCH | Pitfall 6 | JSON-safe local ISO event data | 04-04 → 04-09 exact payload | COVERED |
| RESEARCH | Pitfall 7 | Last fetch disabled by default in tests | 04-05 → 04-09 T2 class-local enablement | COVERED |
| RESEARCH | Pitfall 8 | Empty notify target | 04-02 | COVERED; shipped guarded default action |
| RESEARCH | Pitfall 9 | 15-minute trigger window | 04-08 | COVERED plan owner; unconfirmed backstop stays pending |
| RESEARCH | Pitfall 10 | Code-derived translation completeness | 04-08 → 04-11 | COVERED |
| RESEARCH | Pitfall 11 | Retained channel display-name fallback | 04-06 → 04-09 unchanged helpers | COVERED |
| RESEARCH | Questions 1..4 | Diagnostics last attempt, tz retained invalidation, downtime cutoff, AUT-06 bookkeeping | 04-05/04-06/04-08 | COVERED; do not expand to effective HA timezone IN-04; downtime limitation remains documented |
| RESEARCH | A1/A2/A5 | Negative duration, default variables, HACS prerelease selection | 04-02/04-03/04-08 | COVERED test ownership plus pending frontend/HACS judgment |
| RESEARCH | A3/A4/A6 | Dispatcher/bus, 5000 retained cap, finalized names | 04-01/04-04/04-05/04-06 → 04-09 | COVERED; names/caps retained |
| RESEARCH | Security domain | V5/V7/V8/V10/V12, event flood, Store bounds, private data, release shell | 04-03/04-04/04-05/04-06 and all new threat models | COVERED; no new supply-chain task |

### Locked decisions (31/31 retained)

| Source | ID | Decision | Plan ownership | Status |
|---|---|---|---|---|
| CONTEXT | D-01 | Strict future timestamp | 04-01, 04-09 | COVERED |
| CONTEXT | D-02 | Available unknown vs no source data | 04-01, 04-09 | COVERED |
| CONTEXT | D-03 | Existing nine sensor attributes | 04-01, 04-09/04-10 | COVERED, no rename |
| CONTEXT | D-04 | Recorder excludes description | 04-01, 04-09 | COVERED |
| CONTEXT | D-05 | Device, translated name, enabled sensor and unique ID | 04-01, 04-09 | COVERED |
| CONTEXT | D-06 | Live time/feed/edit updates | 04-01, 04-09/04-10 | COVERED |
| CONTEXT | D-07 | Event name and exact nine payload keys | 04-04, 04-09/04-10 | COVERED, registry identity preserved |
| CONTEXT | D-08 | UID-based newness | 04-04, 04-09/04-10 | COVERED |
| CONTEXT | D-09 | Only future matches announce | 04-04, 04-09/04-10 | COVERED |
| CONTEXT | D-10 | Persisted silent first/restart/reload | 04-04, 04-09/04-10 | COVERED |
| CONTEXT | D-11 | Silent config/source timezone baseline | 04-04, 04-10 | COVERED |
| CONTEXT | D-12 | 50 event cap | 04-04, 04-09/04-10 | COVERED |
| CONTEXT | D-13 | Pruned seen-set | 04-04/04-06, 04-09/04-10 | COVERED |
| CONTEXT | D-14 | Flat retention_days, in-place 0..7 | 04-06/04-07, 04-09/04-10 | COVERED, stored key unchanged |
| CONTEXT | D-15 | Default one day, missing-key fallback | 04-06/04-07, 04-09 | COVERED |
| CONTEXT | D-16 | Only ended retained; future feed truth | 04-06, 04-09 | COVERED |
| CONTEXT | D-17 | Raw retained/filter recheck/render templates | 04-06, 04-09/04-10 | COVERED |
| CONTEXT | D-18 | Feed wins UID merge | 04-06, 04-09 | COVERED |
| CONTEXT | D-19 | Separate feed/retained diagnostics | 04-06, 04-09 | COVERED |
| CONTEXT | D-20 | Last-fetch timestamp per device | 04-05, 04-09/04-11 | COVERED |
| CONTEXT | D-21 | Every refresh attempt/run kind | 04-05 | COVERED, no new bookkeeping changes |
| CONTEXT | D-22 | Diagnostic attributes and translated reason keys | 04-05, 04-09/04-11 | COVERED |
| CONTEXT | D-23 | Persist attempt with health | 04-05 | COVERED |
| CONTEXT | D-24 | Diagnostic/default-disabled/no locators | 04-05, 04-09/04-11 | COVERED |
| CONTEXT | D-25 | No added stale attributes on calendar | 04-05, 04-09 | COVERED |
| CONTEXT | D-26 | Queued legacy start trigger negative offset | 04-02 | COVERED |
| CONTEXT | D-27 | Calendar/lead/action selectors and variables | 04-02 | COVERED |
| CONTEXT | D-28 | Shipped blueprint plus import button | 04-02/04-08 | COVERED |
| CONTEXT | D-29 | 0.1.0 release workflow, user pushes/tags | 04-03/04-08; every new verification reminder | COVERED, actual release pending |
| CONTEXT | D-30 | Single English README, full required topics | 04-08 | COVERED, human accuracy review pending |
| CONTEXT | D-31 | New en/de strings and parity | 04-07/04-08, 04-11 | COVERED |

## Spec-less edge fallback: every one of 17 items surfaced

Input: deterministic `phase04-gap-coverage.json` provided by orchestrator. No SPEC exists; do not rerun taxonomy or silently dismiss it. All 17 remain explicit **FLAGGED ASSUMPTIONS**, status `unresolved`, verification `null`. The ownership/evidence below is a route for later verification, **not resolution**. In particular all five unclassified rows stay unresolved. No new backstop is silently asserted green.

| Flag | Requirement/category | Explicit flagged assumption / unresolved question | Existing owner / evidence route |
|---|---|---|---|
| EDGE-01 | AUT-03 adjacency | At start == now, that programme is no longer next; exact-touch programmes are separate. Flag until confirmed for the moved runtime. | 04-01 truths 8/10, tests/test_sensor.py::test_sensor_moves_on_at_match_start; 04-09 runtime regression preserves |
| EDGE-02 | AUT-03 empty | Empty/no future/invalid-initial-filter yields available unknown with absent attributes; no source data yields unavailable. Flag moved-runtime equivalence. | 04-01 truth 9; tests/test_sensor.py::test_no_future_match_is_unknown_but_available and test_invalid_stored_pattern_gives_unknown; 04-09 |
| EDGE-03 | AUT-03 ordering | Equal starts keep existing stable feed order. Flag preservation through runtime extraction, not a new sorting policy. | 04-01 truth 10; tests/test_sensor.py::test_same_start_picks_feed_order |
| EDGE-04 | AUT-05 unclassified | Taxonomy cannot classify blueprint edge surface; manual review needed; no automatic backstop resolution. | 04-02 schema/overlap tests and pending import/negative-duration/real-notify UAT |
| EDGE-05 | AUT-06 adjacency | Distinct runs with equal timestamps still replace the recorded attempt in completion order. Flag exact equality contract for review. | 04-05; tests/test_last_fetch_sensor.py::test_same_instant_runs_keep_the_latest |
| EDGE-06 | AUT-06 empty | Missing/malformed attempt yields available unknown/no attempt attributes rather than fabricated timestamp. Flag existing reader contract. | 04-05; test_no_run_yet_is_unknown, test_phase3_store_without_attempt_loads, test_malformed_attempt_reads_as_none |
| EDGE-07 | AUT-06 ordering | The last completed equal-time run supplies fields; no mixed attempt attributes. Flag stable ordering semantics. | 04-05 same-instant test and as_dict contract; no new runtime ordering feature |
| EDGE-08 | AUT-06 concurrency | Cancellation half of T13 lacks direct last_attempt evidence; coordinator serialization/cancelled-attempt behavior still needs acceptance or a later authorized test. **Not closed by match-refilter race tests.** | 04-05 T13 structured backstop, 04-VERIFICATION.md human item; pending |
| EDGE-09 | EVT-07 unclassified | Manual review of retention intent still required; no automatic classification/resolution. | 04-06/04-07; 04-09/04-10 close specific disabled/lost-recheck gaps only |
| EDGE-10 | EVT-08 unclassified | Manual review of event intent still required; deterministic fixes do not accept judgment prohibitions. | 04-04; 04-09/04-10 tests plus pending real event/restart UAT |
| EDGE-11 | CFG-04 unclassified | Frontend/UI presentation cannot be auto-classified or accepted from JSON tests. | 04-08; 04-11 closes failure_reason string-serving gap; frontend walkthrough pending |
| EDGE-12 | DST-03 unclassified | Actual publish and HACS pickup require user tag push and observation; no automatic resolution. | 04-03/04-08; D-29 user-only release |
| EDGE-13 | DST-04 boundary | Match added less than 15 minutes before trigger may not fire; exact boundary behavior is unconfirmed HA-core backstop. | 04-08 T9, README accuracy/HA behavior human item pending |
| EDGE-14 | DST-04 adjacency | Overlap/touch remains one event per programme, one entity current/next view; prose accuracy at exact-touch boundary needs review. | 04-08 documentation truth, 04-02 overlap notification tests; no documentation rewrite scope |
| EDGE-15 | DST-04 empty | README unknown means no upcoming match, not disabled presentation. Flag accuracy after CR-01 behavior fix. | 04-08 empty truth + 04-09 disabled runtime test; human README read pending |
| EDGE-16 | DST-04 ordering | README current/next one-event view vs all overlapping triggers describes existing ordering accurately; flag review. | 04-08 ordering/adjacency truth; tests/test_calendar.py and test_blueprint.py |
| EDGE-17 | DST-04 precision | Start/end public strings stay ISO 8601 in HA local time; flag prose/runtime correspondence. | 04-08 precision truth, 04-09 exact payload and unchanged describe_match behavior |

Equality accounting: 17 input items = 17 explicitly flagged assumptions; zero dismissed; five unclassified remain unresolved. Existing explicit/backstop truths in executed plans retain their original verification tiers. Do not turn this ledger into 17 new implementation tasks or drop executed ownership.

## Scoped prohibition fallback / human judgment

Recall question applied to phase requirements: what could the feature silently become that the author would not want? Routine mechanics (empty lists, locking, invalid input, cleanup) are owned by edge/regression testing, not new moral constraints. Product-specific retained candidates are below; generic credential disclosure, injection, access control and generic data protection are canon referrals to threat models and `/gsd-secure-phase`, not additional bespoke prohibitions.

New scoped retained prohibitions are projected through installed `probe-core.cjs.projectProhibitions` into the new plans, with no `check_*` descriptors:

1. Disabled calendar presentation must not silently opt the user out of automation/retention (04-09).
2. Long programme texts must not turn every match transition into recorder history growth (D-04, 04-09; original owner 04-01).
3. Filter/template edits, restart/reload and source timezone changes must not announce edit-only matches (D-10/D-11, 04-10; original owner 04-04).

All serialize as status `resolved`, verification `judgment` to record the stated intent; **their verification disposition is flagged-unverified**, not accepted. No wired check descriptors or human verdicts are fabricated. Existing burst/retention/blueprint/release/assistant-push prohibitions remain owned by executed 04-02/04-03/04-04/04-06/04-07/04-08. User-only release authority D-29 remains in force for all new plans. Tests are supporting evidence; human prohibition judgments still pending per 04-VERIFICATION.md.

## Review boundary and pending human work

- Incorporate CR-01 in 04-09, WR-01 in 04-10, IN-05 in 04-11; IN-01 is included only as the template-only refilter expansion directly related to WR-01.
- IN-02 oversized HTTP status, IN-03 nonstandard status persistence, IN-04 effective HA timezone fingerprint, IN-06 blueprint title variable remain **open / outside this gap invocation**. Their disposition is not decided by this planner; keep existing review-disposition ledger unchanged for human triage. This is not a new deferral or approval.
- All eleven `04-VERIFICATION.md` human entries stay pending: seven ha-dev frontend/automation/restart/retention/field walkthroughs; README accuracy plus 15-minute backstop; user release and HACS pickup; AUT-06 cancellation/serialization backstop; prohibition and eight-review-disposition judgment. Add disabled-calendar runtime and failure-reason frontend checks to the walkthrough, never substitute passing pytest for a human verdict.
- No source code, existing plans/summaries, verification, roadmap, state or requirements changed during planning. No branch switch, commit, push or tag authorized to this planner; orchestrator commits plans after checker verification. Execution summaries must preserve pending human items and cite supporting evidence, not invent acceptance.
