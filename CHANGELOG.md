# CHANGELOG

<!-- version list -->

## v2.1.0 (2026-08-27)

### Bug Fixes

- **23**: Correct four stale provenance strings and supersede the E2 frameset doc (FIX-06)
  ([`3f867c2`](https://github.com/McGrathLab/AquaCal/commit/3f867c213233677c565b7437f6269d9b8a1fe16a))

- **23-02**: Named --check exclusion contract, plus the always-red-gate finding
  ([`2a5c18d`](https://github.com/McGrathLab/AquaCal/commit/2a5c18d5a6f2286f69e52cad15164d3e89239c8c))

- **23-02**: Resolve E2 real-rig record relative to --out at both call sites
  ([`e89e1fb`](https://github.com/McGrathLab/AquaCal/commit/e89e1fb34d8d7a1d74c3294f3d2b7d3937a83cbe))

- **24**: Close three review warnings on the degeneracy instrumentation
  ([`dfbbfe7`](https://github.com/McGrathLab/AquaCal/commit/dfbbfe7b773a52df5455bd34de32d62494ccfcbb))

- **24**: Collapse E7 degeneracy counts per seed before summing (CR-01)
  ([`bc8cbf7`](https://github.com/McGrathLab/AquaCal/commit/bc8cbf7433f1585f239634f0b790fae99f4a8126))

- **24**: Correct DISCARD_KEYS base count from 15 to 14 in plan 24-01
  ([`e0be0fa`](https://github.com/McGrathLab/AquaCal/commit/e0be0fa57ed9d635454690b2ea4d316a92664dcc))

- **24**: Restore the guarded 'unreliable' wording in DegenerateObservationWarning
  ([`12f8a50`](https://github.com/McGrathLab/AquaCal/commit/12f8a507a79e3c4dc8bad502cd47d8c4994e2a23))

- **24**: Thread discard_stage through E7's two solver calls (CR-02)
  ([`9f42c0e`](https://github.com/McGrathLab/AquaCal/commit/9f42c0ee15b573c1392081d6fb0822e035b5b768))

- **26-12**: Record an absent E2 record instead of crashing on it
  ([`a033726`](https://github.com/McGrathLab/AquaCal/commit/a0337262fbf49952f636747194b92a94d3948548))

- **26-12**: Schedule e3 after the stage that writes the record it reads
  ([`2f76efb`](https://github.com/McGrathLab/AquaCal/commit/2f76efbb34ee2f09feb22e2a9867cfa5a40febea))

- **26-13**: Stamp a seed on E1's and E7's benchmark records
  ([`56e1ae5`](https://github.com/McGrathLab/AquaCal/commit/56e1ae5488bd6156b8633d47b9507c7a07166a5a))

- **27-02**: Make is_stage_complete read the exit-code column (D-22)
  ([`1b8afa3`](https://github.com/McGrathLab/AquaCal/commit/1b8afa3bcca2e1e7cb0d845f98e0825584271a32))

- **27-02**: Make the frameset pre-flight path-kind agnostic (D-10)
  ([`6dddbaa`](https://github.com/McGrathLab/AquaCal/commit/6dddbaabbc705f5cbb1259513a22a2b44f3af89c))

- **27-03**: Retag the three smoke-unwritable artifacts as full-only (D-20 class 1)
  ([`090244e`](https://github.com/McGrathLab/AquaCal/commit/090244ef80991f37df4e75b9c43a5533c67b957a))

- **27-03**: Thread profile into the E4/E5/E6 checkers (D-20 classes 2 and 3)
  ([`cd7c658`](https://github.com/McGrathLab/AquaCal/commit/cd7c65849205a53eac2cbc3f73a7b421bc89e468))

- **27-04**: Resolve real_rig_metrics.json from --out, not a hardcode (D-23)
  ([`131f16a`](https://github.com/McGrathLab/AquaCal/commit/131f16a3b628f92aee5d2d1cee6570c290374cea))

- **27-08**: Neither Windows literal is reachable as a default (D-12, D-29)
  ([`bb5a4ae`](https://github.com/McGrathLab/AquaCal/commit/bb5a4ae77c381bc34290e545a60853f2b77970f6))

- **29**: Repair eight provenance-rail assertions the returned tree exposed
  ([`5799b14`](https://github.com/McGrathLab/AquaCal/commit/5799b145ef7aca2e67c442955c945a19b5a017dc))

- **29**: Revert a false RUN-05 completion written by `phase complete`
  ([`2205eeb`](https://github.com/McGrathLab/AquaCal/commit/2205eeb2c4d3faa3be6d6e12f04fcff5a6bfb54b))

- **29.1**: Stop the E7 overwrite hazard auto-closing as resolved
  ([`8d1576e`](https://github.com/McGrathLab/AquaCal/commit/8d1576e7ce085eb1506602a78523bc82d9088dc9))

- **29.1-01**: Publish E2's guard count on E4's real-rig row and exempt it from gate 1
  ([`290ed75`](https://github.com/McGrathLab/AquaCal/commit/290ed757da22cb9a38c6da2a6fdf887e52b165ca))

- **29.1-02**: Derive the band's scope field from the run, and close the three E1 todos
  ([`424c1e4`](https://github.com/McGrathLab/AquaCal/commit/424c1e453f4410d012279f33125f809856cfbc89))

- **29.1-02**: Enforce the band's no-overwrite policy at the call and branch its log
  ([`c80490e`](https://github.com/McGrathLab/AquaCal/commit/c80490e407a1e430cbe306bc20b1bec47b63f780))

- **29.1-02**: Restore the two axis literals and the Phase 28 fact in E1's docstring
  ([`8698ab2`](https://github.com/McGrathLab/AquaCal/commit/8698ab2a74a56a8ba27e399d0540f48d491a6b28))

- **29.1-02**: Unclaim e1_seed_band_degeneracy_breakdown.json from all three manifests
  ([`fb1e9f7`](https://github.com/McGrathLab/AquaCal/commit/fb1e9f70197c3a94c7e846504cff073e3cadb44f))

- **29.1-03**: Correct 11 unattributed annotations and pin them with a gate
  ([`df8b3c8`](https://github.com/McGrathLab/AquaCal/commit/df8b3c88c99f746d667d8083d493ebb2ca4593f2))

- **29.1-09**: Point the two conditional artifacts at the directory their writer uses
  ([`4e5a37c`](https://github.com/McGrathLab/AquaCal/commit/4e5a37cb06cbfa12018cbb70a47bd5cbd61af623))

- **29.2-02**: Add a .planning/ arm to detect-secrets, and write its cost down
  ([`d9e8f49`](https://github.com/McGrathLab/AquaCal/commit/d9e8f496aef27e8f53a61b01bc3f0dc676e316a7))

- **29.2-02**: Scope both formatting hooks off the byte-sensitive artifacts
  ([`e671074`](https://github.com/McGrathLab/AquaCal/commit/e671074d07d8164c5552f5a4a96858b67fb2b616))

- **29.2-03**: Bound the two drifting D4 assertions in representable steps
  ([`3026813`](https://github.com/McGrathLab/AquaCal/commit/30268135febb0a007d0a77946c75364e7bd3029b))

- **deps**: Pin opencv-python to 4.13.* and name it in reproduction claims
  ([`fa9ec3a`](https://github.com/McGrathLab/AquaCal/commit/fa9ec3a99b3a698079824f55a4c459b5e6693ebd))

- **provenance**: Gate and record editable-install version drift
  ([`25e65c0`](https://github.com/McGrathLab/AquaCal/commit/25e65c070056e02e3386fc3cfe6e03d6c63f497f))

- **state**: Restore status executing after record-session flipped it
  ([`723e9d6`](https://github.com/McGrathLab/AquaCal/commit/723e9d61df61591c8af60074ff8499e717f19d93))

### Chores

- Archive v2.0 Publication Prep milestone
  ([`d550cdc`](https://github.com/McGrathLab/AquaCal/commit/d550cdcfe3debdbd43012e1d7a3a51e1395dead5))

- Drop the pytest pre-push hook, keep the ruff ones
  ([`cc56eea`](https://github.com/McGrathLab/AquaCal/commit/cc56eea2e3778d2db1956e5adab837963c04f527))

- Remove REQUIREMENTS.md at v2.0 milestone close
  ([`5126667`](https://github.com/McGrathLab/AquaCal/commit/51266674f9a9b79becdba32c7fa5ec67298aa78d))

- **24**: Raise executor to opus for phase 24, with revert todo
  ([`4deaa0b`](https://github.com/McGrathLab/AquaCal/commit/4deaa0bf16a0b9946953e0d100082878b6c46e6a))

- **25-05**: Ignore the Huber-knee probe's raw per-arm outputs (D-19)
  ([`011f9b1`](https://github.com/McGrathLab/AquaCal/commit/011f9b135ac557753d71a7f30cb74f911adf7016))

- **26**: Mark phase 26 execution started
  ([`d0bbe09`](https://github.com/McGrathLab/AquaCal/commit/d0bbe09c29fb8da29c7a214f36b10ed8ff312b3e))

- **26**: Record waves 1-6 complete (9/10 plans)
  ([`14ed743`](https://github.com/McGrathLab/AquaCal/commit/14ed7435a47f44bf551fa4eb059e093bc17e6f91))

- **26-01**: Archive every pre-re-run output tree into experiments/pre_rerun_baseline/
  ([`048c14f`](https://github.com/McGrathLab/AquaCal/commit/048c14fdce8b5ebc0492075d448719258b8d038d))

- **28**: Commit the production queue's 18 per-stage logs
  ([`f399615`](https://github.com/McGrathLab/AquaCal/commit/f39961597985e7315c86d6d8d93cc5ef11ca2f88))

- **28**: Extend DATA-01b ignores to the three ungoverned E2 trees
  ([`672be71`](https://github.com/McGrathLab/AquaCal/commit/672be7163f0b08dd7b335c80812753fe44821765))

- **28-01**: Assert environment provenance before the burn (T-28-01)
  ([`79106d8`](https://github.com/McGrathLab/AquaCal/commit/79106d821a42f30f1bf058f6fa2b501b3a321306))

- **28-01**: Build production clone, env and dry-run venue
  ([`baa0523`](https://github.com/McGrathLab/AquaCal/commit/baa05230a323622a0100e7c05ead68418a480f5c))

- **28-01**: Confirm the D4 three-failure state before launch (T-28-04)
  ([`701b257`](https://github.com/McGrathLab/AquaCal/commit/701b257d595c155eedd3d36e539b7f2e5907fba9))

- **28-02**: Run the pre-launch assertion checklist and write the record
  ([`623fca4`](https://github.com/McGrathLab/AquaCal/commit/623fca438f4dfa0f718dcf1d5a37d50fc948a76f))

- **29.1**: Disable worktree isolation for this branch
  ([`a6e7841`](https://github.com/McGrathLab/AquaCal/commit/a6e7841d830ab2b9f822c4bac44cde590f631641))

- **experiments**: Commit E1's 10-seed parameter-level band
  ([`15fd4aa`](https://github.com/McGrathLab/AquaCal/commit/15fd4aada4d48d558a2f74806ce4918fe9a010c8))

- **experiments**: Commit the 32 GB Linux re-run of E4 and E2
  ([`1af0650`](https://github.com/McGrathLab/AquaCal/commit/1af06508db120daacce8618b8387c7a7213b1fbe))

- **experiments**: Confirm the OpenCV attribution with a single-variable control
  ([`27c80e7`](https://github.com/McGrathLab/AquaCal/commit/27c80e77578b833dc99dcfd2791052d5080beadd))

- **experiments**: Emit exp1_parameter_band.csv from E1's band mode
  ([`5ae6683`](https://github.com/McGrathLab/AquaCal/commit/5ae6683868af88353e453c1508e23577c893f7c8))

- **roadmap**: Track Phase 29.2's phase directory
  ([`0a5d095`](https://github.com/McGrathLab/AquaCal/commit/0a5d09514b659f934513aec8f9c65e993faf496f))

- **todos**: Close three verified-complete todos
  ([`d5eba65`](https://github.com/McGrathLab/AquaCal/commit/d5eba65e1211f901940845dbd1885d9898e7fb4e))

- **todos**: Close verify-non-refractive-baseline; its residue has owners
  ([`e0d0f2b`](https://github.com/McGrathLab/AquaCal/commit/e0d0f2bec24e1849bdecab50e3859af049d75664))

- **todos**: Re-scope pre/post-submission directives for the full re-run
  ([`3ffcc01`](https://github.com/McGrathLab/AquaCal/commit/3ffcc01d38835231d3bce1cef76a001a4b4a9c03))

- **todos**: Restructure the fix-milestone backlog and reconcile it
  ([`7cd34c2`](https://github.com/McGrathLab/AquaCal/commit/7cd34c2504861d397160efdcbedf5f10e2a43849))

### Continuous Integration

- **29.2**: Give CI's test job the tags and psutil its manifest tests assert on
  ([`edfaa5a`](https://github.com/McGrathLab/AquaCal/commit/edfaa5a27cf886718758f7266a6de760e768bc7e))

- **29.2-01**: Pin the release toolchain to a verified-working PSR/GitPython pair
  ([`7ab969e`](https://github.com/McGrathLab/AquaCal/commit/7ab969e2cc5479cb300630697244b534fd06357a))

### Documentation

- Add todo to parallelize the test suite before the next phase
  ([`1f02ed9`](https://github.com/McGrathLab/AquaCal/commit/1f02ed9c70b25da557e7fb1c5aa8022e332c5508))

- Correct four Phase 23 roadmap findings from pre-planning recon
  ([`870151c`](https://github.com/McGrathLab/AquaCal/commit/870151c635380fc93452f39573b488055061e61a))

- Create milestone v2.1 roadmap (8 phases)
  ([`a0e1fb5`](https://github.com/McGrathLab/AquaCal/commit/a0e1fb5978930e25c18e3d8c8ea9c336c4465006))

- Define milestone v2.1 requirements
  ([`fe864c1`](https://github.com/McGrathLab/AquaCal/commit/fe864c1d7394db9e16f019a4f8f35c47accb0aea))

- Fold optimality probe results into DEGEN-05, Phases 25/29, knowledge base
  ([`419f363`](https://github.com/McGrathLab/AquaCal/commit/419f363fbc9e325b086e7f18029e999e88519945))

- Incorporate external roadmap review into v2.1 (Zenodo pulled pre-submission, three new gates)
  ([`76ca847`](https://github.com/McGrathLab/AquaCal/commit/76ca84769d67b9e2d32df9e8d267d148295cdb8f))

- Mark HANDOFF.json milestone-complete for v2.0
  ([`519037f`](https://github.com/McGrathLab/AquaCal/commit/519037f178da2ae38a53e629627525ee9a1ceb12))

- Start milestone v2.1 Clean Experimental Suite
  ([`38a6f78`](https://github.com/McGrathLab/AquaCal/commit/38a6f78bfe04db3a494af4590c11e295bab27734))

- Sync todo counts after closing three at milestone close
  ([`46614b3`](https://github.com/McGrathLab/AquaCal/commit/46614b33b2f53c0ca7f240b74292a94f15346e9b))

- Tag 16 pending todos with resolves_phase after milestone v2.1 roadmap
  ([`941b9f6`](https://github.com/McGrathLab/AquaCal/commit/941b9f68c31102e1d8c71294e36b06a64bc8ba29))

- Write the next milestone's scope boundary before planning starts
  ([`56ecdb8`](https://github.com/McGrathLab/AquaCal/commit/56ecdb808e290ce1cee2aaa22dba6e375889a49f))

- **21**: Close phase 21 -- roadmap, state and handoff
  ([`f7dd4c1`](https://github.com/McGrathLab/AquaCal/commit/f7dd4c123e9082147137ad769ddf68a742c124f4))

- **21**: Record the CI matrix green
  ([`7ccae5a`](https://github.com/McGrathLab/AquaCal/commit/7ccae5ad64f1a217219a5ec108965ab0ed1a2f66))

- **21**: Summaries for plans 09, 10 and 11
  ([`6213be6`](https://github.com/McGrathLab/AquaCal/commit/6213be6eb304980a36d216f75e82f860d32dfca7))

- **23**: Add validation strategy and D-02 probe research
  ([`d16fe60`](https://github.com/McGrathLab/AquaCal/commit/d16fe604cb02c7e5d3decd26e688fa32e11a9327))

- **23**: Capture phase context
  ([`6a0b772`](https://github.com/McGrathLab/AquaCal/commit/6a0b772ac5d27e173ed8364956b4b6d1837d3a9f))

- **23**: Correct the falsified optimality mechanism in four phase artifacts
  ([`02fe224`](https://github.com/McGrathLab/AquaCal/commit/02fe224ea596811b9467383ca15fa465440118e3))

- **23**: Create phase plan -- 4 plans in 1 wave
  ([`f02ec0d`](https://github.com/McGrathLab/AquaCal/commit/f02ec0d9c7d2658ae056ef05c769dccee818507e))

- **23**: Mark phase 23 execution started
  ([`a720c56`](https://github.com/McGrathLab/AquaCal/commit/a720c565279bbecff2d1fd6b78de6c21f6d01448))

- **23-01**: Record plan 23-01 SUMMARY (Tasks 1-2 complete, Tasks 3-4 outstanding)
  ([`292b6d6`](https://github.com/McGrathLab/AquaCal/commit/292b6d6441154d78e628e717d801a86683c81e95))

- **23-01**: Record Task 3/4 evidence in 23-01-SUMMARY.md
  ([`4128cf4`](https://github.com/McGrathLab/AquaCal/commit/4128cf4e73a2b96e3f1739bd8f91c4c3467baaa4))

- **23-02**: Complete E4 --out-relative resolution and --check exclusion plan
  ([`4dc9ec3`](https://github.com/McGrathLab/AquaCal/commit/4dc9ec385aea71adf500132387d42d00a27de177))

- **23-03**: Confirm test_e7_band_mode.py verification completed clean
  ([`7d467a6`](https://github.com/McGrathLab/AquaCal/commit/7d467a61b5f445c00995175ee2f4ece2fa8587e2))

- **23-03**: Record reproducible derivation of MF-12's four quantities
  ([`0d9d457`](https://github.com/McGrathLab/AquaCal/commit/0d9d4571bdf1c2d7f6ea2622a5eef083df58705b))

- **23-04**: Add plan summary for FIX-06 stale provenance strings
  ([`defc75a`](https://github.com/McGrathLab/AquaCal/commit/defc75a63f908aeedba78fcb9d21ad5a17229e83))

- **23-04**: Append self-check results to plan summary
  ([`a88a397`](https://github.com/McGrathLab/AquaCal/commit/a88a397917938055f93f516dd4dcc746eceafb91))

- **24**: Add code review report with resolution log
  ([`8187ebf`](https://github.com/McGrathLab/AquaCal/commit/8187ebffda957bacd29c1a52096113c7e6399fad))

- **24**: Add phase verification report and track the seven open review warnings
  ([`68a79bb`](https://github.com/McGrathLab/AquaCal/commit/68a79bbbca89883afac131a8efed26343ef79264))

- **24**: Apply plan-checker fixes and record planning completion
  ([`8add0aa`](https://github.com/McGrathLab/AquaCal/commit/8add0aa1edf08b495a942e3dd47bcafae759933c))

- **24**: Capture phase context
  ([`df5a352`](https://github.com/McGrathLab/AquaCal/commit/df5a352755c6a90d9a06e5e07300f79a9f7f39f3))

- **24**: Correct roadmap's 24-01 description after the D-06 reversal
  ([`09cd079`](https://github.com/McGrathLab/AquaCal/commit/09cd0790d8e31e95ee6b864f31e877a0285c8000))

- **24**: Create phase plans for degeneracy instrumentation
  ([`3300b6d`](https://github.com/McGrathLab/AquaCal/commit/3300b6d671003a3a0c4f28eda48af8565da29ad7))

- **24**: Finalize verification with first-hand real-solve test evidence
  ([`05bf985`](https://github.com/McGrathLab/AquaCal/commit/05bf9853887bd7ca2e336a8b7ffe06f7d2b27ae5))

- **24**: Mark phase 24 execution start in STATE
  ([`a25fae2`](https://github.com/McGrathLab/AquaCal/commit/a25fae2a4e445341853becd6a3174fd50fde939a))

- **24**: Reconcile phase context with the 2026-08-17 optimality probes
  ([`909a723`](https://github.com/McGrathLab/AquaCal/commit/909a7239f12ae05683a5fa43c09b25fa6264532d))

- **24**: Revise D-09 to two axes, reword D-20, flag stale PATTERNS passages
  ([`9d86282`](https://github.com/McGrathLab/AquaCal/commit/9d86282b3509b863f8265a67202d60a7a38f70e2))

- **24**: Revise plan 24-01 to plumb the NaN reason out of the projector
  ([`a01ff16`](https://github.com/McGrathLab/AquaCal/commit/a01ff167f5a52fb514dc3fdde04670823ddb66c2))

- **24**: Revise plans for D-09 two-axis CSV, D-20 rewording, and line-scoped reads
  ([`b03cbec`](https://github.com/McGrathLab/AquaCal/commit/b03cbece088f656542daec7aa3d9b13c428e858f))

- **24-01**: Complete the degeneracy instrumentation core plan
  ([`577887b`](https://github.com/McGrathLab/AquaCal/commit/577887bef48286aaed6c0d96f26952e71633aaf0))

- **24-02**: Complete degeneracy artifact persistence plan
  ([`4fde653`](https://github.com/McGrathLab/AquaCal/commit/4fde653e40281f8a52a6968d4536a55d2f93d2de))

- **25**: Add summaries for the two orchestrator-run plans (25-06, 25-08)
  ([`0f5b17e`](https://github.com/McGrathLab/AquaCal/commit/0f5b17ee7518db4558e326ebabfdd1b8b36e33bd))

- **25**: Add validation strategy
  ([`0ce962b`](https://github.com/McGrathLab/AquaCal/commit/0ce962bfcbbbed6eaeaeb6403be1d545a6d22f35))

- **25**: Capture phase context
  ([`f3ccbad`](https://github.com/McGrathLab/AquaCal/commit/f3ccbadd57a7e6fe02fd449438bed058610bdc02))

- **25**: Carry D-21 rescope into ROADMAP criterion 3 and the validation strategy
  ([`a7714e6`](https://github.com/McGrathLab/AquaCal/commit/a7714e613cc8ee15cd84a2fdff69084789575b61))

- **25**: Close phase 25 — 8/8 plans, full gate green
  ([`5569fbf`](https://github.com/McGrathLab/AquaCal/commit/5569fbf6ad6c98b42a584a390d490d36899b0734))

- **25**: Close plan-checker warnings (open questions, deps, validation sign-off)
  ([`e89804f`](https://github.com/McGrathLab/AquaCal/commit/e89804fddf71643228bcc983a1b14a704b8bd4b3))

- **25**: Close the Huber-knee objection by measurement
  ([`2a6aed2`](https://github.com/McGrathLab/AquaCal/commit/2a6aed2f68ece53a00734ee0c2d7c1c7a95a5af6))

- **25**: Correct 25-04 prose still attributing the 7 h band to plan 25-08
  ([`4d2be36`](https://github.com/McGrathLab/AquaCal/commit/4d2be36c4c5792d97aecfbb5fc5b3a6c1b4278a7))

- **25**: Create phase plan
  ([`19e74f2`](https://github.com/McGrathLab/AquaCal/commit/19e74f2da1be64891c1e3531063b2cf7209d2ae3))

- **25**: Map patterns and correct two test routings
  ([`549e6e5`](https://github.com/McGrathLab/AquaCal/commit/549e6e5bf88c9f7a2e3ba2a68e8be2d92104ddc0))

- **25**: Record D-21 — E1 noise axis is a probe here, band of record is Phase 28
  ([`edaa0b6`](https://github.com/McGrathLab/AquaCal/commit/edaa0b68c0160645c5b0a88cc5c200540baa7710))

- **25**: Record planning completion and annotate roadmap waves
  ([`c4d6088`](https://github.com/McGrathLab/AquaCal/commit/c4d60882050d93c6bf5f5558dde84a637cf41dfb))

- **25**: Rescope 25-08's noise run to a two-seed probe (D-21)
  ([`785e639`](https://github.com/McGrathLab/AquaCal/commit/785e6398b7bff3a3eb8eefa843ef7e5649656656))

- **25**: Research phase domain
  ([`86b9fdb`](https://github.com/McGrathLab/AquaCal/commit/86b9fdb2542fc388aa10d022a2dab8d5bb4be8cd))

- **25**: Verification passed — 4/4 success criteria
  ([`724a81e`](https://github.com/McGrathLab/AquaCal/commit/724a81e2615f70a3296d83b5ad54c3028e0b5c02))

- **25-01**: Complete per-observation degeneracy detail sinks plan
  ([`839e44f`](https://github.com/McGrathLab/AquaCal/commit/839e44fb09cb113ecef8010f02cafe03291bb354))

- **25-02**: Complete the config flag and degeneracy sidecar plan
  ([`0da1b5a`](https://github.com/McGrathLab/AquaCal/commit/0da1b5a1d99872b4d9442ac2f934e63dfb2fb57a))

- **25-03**: Complete the offline classifier plan (DEGEN-04)
  ([`0d46e6b`](https://github.com/McGrathLab/AquaCal/commit/0d46e6ba4c6fd0565d348d24bc2c9b33d6f070a5))

- **25-04**: Complete E1 noise_std band axis plan (BAND-01)
  ([`a551357`](https://github.com/McGrathLab/AquaCal/commit/a5513573bcfe173548083ec830e60328a3449947))

- **25-04**: Record the 46-test verification result and self-check
  ([`c90dbc9`](https://github.com/McGrathLab/AquaCal/commit/c90dbc9bb03a945d5fd660897d70f27a4ce2dd0f))

- **25-04**: State E1's accuracy-claim domain beside the demotion note (D-14)
  ([`dd794fb`](https://github.com/McGrathLab/AquaCal/commit/dd794fb4cca3253cf8b6fedaaa2947c2b5d1a062))

- **25-05**: Complete the optimality-caveat and DEGEN-05-verdict plan
  ([`cf26d2b`](https://github.com/McGrathLab/AquaCal/commit/cf26d2bbe3bf1d45471f8bddeb874f368940de69))

- **25-05**: Label optimality where the number ships (D-17)
  ([`ad21137`](https://github.com/McGrathLab/AquaCal/commit/ad211377d312558078907f9e8034a0d0225375fe))

- **25-05**: Record MF-21 -- the optimality caveat and the DEGEN-05 verdict
  ([`8a1d447`](https://github.com/McGrathLab/AquaCal/commit/8a1d4472481c7c66c1b7c62f232ccfeca32b1f3c))

- **25-06**: Add the instrumented config copy as committed provenance (DEGEN-04)
  ([`7118e0b`](https://github.com/McGrathLab/AquaCal/commit/7118e0bcef20a53701f31778f045694c540787a4))

- **25-06**: Classify the 198 unprojectable observations (DEGEN-04)
  ([`42d9efb`](https://github.com/McGrathLab/AquaCal/commit/42d9efb78ec9bcc812db9230811b47a5aad65f8a))

- **25-07**: Carry the gate-scope rationale onto both harness guards and resolve the todo (DEGEN-04)
  ([`54d8586`](https://github.com/McGrathLab/AquaCal/commit/54d858617719af913ffbe904753ea405106746c9))

- **25-07**: Complete the degeneracy-gate scope plan (DEGEN-04)
  ([`61d45f6`](https://github.com/McGrathLab/AquaCal/commit/61d45f60fe45761a254b426fd886d12af4c70516))

- **25-07**: Record the synthetic-only gate-scope rationale beside the degeneracy vocabularies
  (DEGEN-04)
  ([`5925bb3`](https://github.com/McGrathLab/AquaCal/commit/5925bb3daef4359025e7797346ac5591901da000))

- **25-08**: Measure the noise axis with a two-seed probe and record MF-22 (BAND-01)
  ([`7c94281`](https://github.com/McGrathLab/AquaCal/commit/7c94281161477b68ed76134e81f0297553909e33))

- **25-08**: Register Phase 25's artifact expectations and the Phase 28 band shape
  ([`211214c`](https://github.com/McGrathLab/AquaCal/commit/211214ce7640b33b6631a8ee964c8664fb64f6ad))

- **26**: Add gap-closure plan 26-11 — driver reduced-scale path
  ([`6cab6c4`](https://github.com/McGrathLab/AquaCal/commit/6cab6c41111e0c9faca31fd3495d64f9e99e4d83))

- **26**: Add gap-closure plans 26-12 and 26-13 with their summaries
  ([`00b8d41`](https://github.com/McGrathLab/AquaCal/commit/00b8d41429aa6b323410530137b013c9ef265eae))

- **26**: Add validation strategy
  ([`08a17fd`](https://github.com/McGrathLab/AquaCal/commit/08a17fd6f3b3a328aab5f417089fd4a8ffead0cd))

- **26**: Amend context with measured runtime, grid cuts, and de-scoping
  ([`45b19dc`](https://github.com/McGrathLab/AquaCal/commit/45b19dcfe23543ce15e7cfd368ad52d8e90c0bf8))

- **26**: Capture phase context
  ([`15d3060`](https://github.com/McGrathLab/AquaCal/commit/15d3060eb8a13530a3cad14aa8db460da95907ea))

- **26**: Close phase 26 -- driver proven at reduced scale, three gaps closed
  ([`80a2a34`](https://github.com/McGrathLab/AquaCal/commit/80a2a343e4c6b828be516bb7274c7a7e74780586))

- **26**: Concurrency probe — correct the runtime estimate and adopt selective parallelism
  ([`529f404`](https://github.com/McGrathLab/AquaCal/commit/529f40484e2113dd3790d7c5509850593daf106f))

- **26**: Create phase 26 plans — full-suite driver and handoff readiness
  ([`0a3e8a9`](https://github.com/McGrathLab/AquaCal/commit/0a3e8a9ea6e510a790393616b8bddf600f270d57))

- **26**: E7_band stays an acknowledged uncertainty, not a scheduled probe
  ([`e1a202a`](https://github.com/McGrathLab/AquaCal/commit/e1a202a76fdb43efc74539ebafd640f5447e4fde))

- **26**: Research the full-suite driver, gates, and output trees
  ([`af85b40`](https://github.com/McGrathLab/AquaCal/commit/af85b4064575806f92ace221acf577815233af75))

- **26**: Revise plans after checker — wave graph, ordering test, decision coverage
  ([`92da9af`](https://github.com/McGrathLab/AquaCal/commit/92da9affb8495c44bb74b53e4054af8b580d8721))

- **26-01**: Summarize the archive-aside, test repair, and gate probe
  ([`13bb3ce`](https://github.com/McGrathLab/AquaCal/commit/13bb3ce3a04e91ee1d2c9ae9a27575e2520c2caf))

- **26-02**: Complete the run-manifest and Gate 3 extension plan
  ([`fcba392`](https://github.com/McGrathLab/AquaCal/commit/fcba39291700f8cc5e1aa9592722cba4f6e8e906))

- **26-03**: Complete the expectation manifest and completeness gate plan
  ([`aee8ee8`](https://github.com/McGrathLab/AquaCal/commit/aee8ee8cbdb88a6ee6476262d5e97e9e2ebcf383))

- **26-04**: Complete --baseline-dir and missing-baseline N/A guard plan
  ([`fdd2fc0`](https://github.com/McGrathLab/AquaCal/commit/fdd2fc00f63f5490ac673575111d6d1c9e59773e))

- **26-05**: Complete the E6 --axes selector plan
  ([`ca92c7e`](https://github.com/McGrathLab/AquaCal/commit/ca92c7ee105bfe2a5e13757e210e45ceb152599a))

- **26-06**: Complete E2 invocation-config and check-verdict plan
  ([`0aa06bd`](https://github.com/McGrathLab/AquaCal/commit/0aa06bd3b524c99afb45d84eeb2c9fe43c9fc329))

- **26-07**: Complete the one-driver plan
  ([`d0de5e3`](https://github.com/McGrathLab/AquaCal/commit/d0de5e3e3a3640b8ecfdd8efd29dce1dc4bc9ac2))

- **26-08**: Complete the driver safety-rails and concurrency plan
  ([`40e7400`](https://github.com/McGrathLab/AquaCal/commit/40e74003feb211634217848a6a62fd38b5714d95))

- **26-09**: Complete handoff-documentation plan
  ([`a7130c3`](https://github.com/McGrathLab/AquaCal/commit/a7130c340bc5f4f96544877e7c9ff809356300e3))

- **26-09**: Record MF-23 and archive the two superseded drivers (DRIVER-04)
  ([`bd055e1`](https://github.com/McGrathLab/AquaCal/commit/bd055e1dc2812181ddb6c5dcef7db0867df3e4c8))

- **26-09**: Rewrite experiments/README.md to one row per invocation
  ([`df3ed29`](https://github.com/McGrathLab/AquaCal/commit/df3ed29eec2d3b92e192824198bfdc40d6e6192c))

- **26-11**: Complete the driver reduced-scale path plan
  ([`46d4ae1`](https://github.com/McGrathLab/AquaCal/commit/46d4ae14e6b0eb58cd262ddd7b9818bebf63e0df))

- **260813-clj**: Quick task plan, summary and state
  ([`f55dd51`](https://github.com/McGrathLab/AquaCal/commit/f55dd516c375932d6916fa7292df51f0f66df281))

- **27**: Capture phase context
  ([`78b4599`](https://github.com/McGrathLab/AquaCal/commit/78b45991359e177e15d9c2cfe1aec40080389ab4))

- **27**: Close Phase 27 -- freeze verified on target, production run launched
  ([`d49a837`](https://github.com/McGrathLab/AquaCal/commit/d49a83757b58fa483432a9bb0b86d7aa01be5ffc))

- **27**: Correct the dry-run seam name inherited from phase 26
  ([`3d781c4`](https://github.com/McGrathLab/AquaCal/commit/3d781c4d34388e12200a17d3b60553c7492ce0b9))

- **27**: Fix context inconsistencies and de-scope three overengineered decisions
  ([`d37001f`](https://github.com/McGrathLab/AquaCal/commit/d37001fe94d1c48a40004c44174a01965b0553a1))

- **27**: Plan the frozen single-sha handoff package -- 13 plans in 6 waves
  ([`80c8e19`](https://github.com/McGrathLab/AquaCal/commit/80c8e19e8aa6ec63939912eed7b2f43daad03618))

- **27**: Record planning completion and close phase 26 bookkeeping
  ([`c618e7f`](https://github.com/McGrathLab/AquaCal/commit/c618e7f5f100ff700aa25d758bd088c7a360128e))

- **27**: Record target access and three findings that bind wave 5
  ([`4f6e1f5`](https://github.com/McGrathLab/AquaCal/commit/4f6e1f5e42bf93616e6b359ce90ff83bd4a52490))

- **27**: Record the post-discussion review in the discussion log
  ([`fc083d9`](https://github.com/McGrathLab/AquaCal/commit/fc083d9d370be26dfaa43d49ae2372555f1aef01))

- **27**: Record waves 1-2 merged and the post-merge gate result
  ([`9ac6a6d`](https://github.com/McGrathLab/AquaCal/commit/9ac6a6dc6b95c9dc649c6386abc447242d761966))

- **27**: Supersede D-12's GATE_PYTHON rung and require an interpreter record
  ([`fdd0f3c`](https://github.com/McGrathLab/AquaCal/commit/fdd0f3c8ecedf1d04131a2c02dc1a22f501327aa))

- **27-01**: Complete target-measurement plan
  ([`6dc29b9`](https://github.com/McGrathLab/AquaCal/commit/6dc29b969258c0daedef2a1804c008b9a9774cc2))

- **27-01**: Measure the Linux run machine before the freeze
  ([`7f04941`](https://github.com/McGrathLab/AquaCal/commit/7f0494148cab1bc67e66dadc960e4b210b155c98))

- **27-02**: Summarise the D-10 and D-22 driver fixes
  ([`b00da51`](https://github.com/McGrathLab/AquaCal/commit/b00da51632dd2d76d6640b07bfa1158e47d912af))

- **27-03**: Record the smoke-profile truthfulness plan and D-24 finding
  ([`d680bae`](https://github.com/McGrathLab/AquaCal/commit/d680baef2889a4ab03893d9e0b0bbaa7b2741977))

- **27-04**: Complete the --out-relative real_rig_metrics resolution plan
  ([`2182fbf`](https://github.com/McGrathLab/AquaCal/commit/2182fbf0d9139ec84b1647e37f06df59690383b5))

- **27-05**: Complete the environment-provenance plan
  ([`acf7e13`](https://github.com/McGrathLab/AquaCal/commit/acf7e13678a1662d16ac89cc2770b3aee7156beb))

- **27-06**: Apply the author's three rulings and 27-07's sha finding
  ([`20db9ac`](https://github.com/McGrathLab/AquaCal/commit/20db9acfc617917cd4f90470558c6b5939d99522))

- **27-06**: Record the emitter-coverage walk and its checkpoint
  ([`9270ea8`](https://github.com/McGrathLab/AquaCal/commit/9270ea83f36eeb0eb86321bdad592d2d824f7e17))

- **27-06**: Record the gate as approved and close the plan
  ([`6024c9e`](https://github.com/McGrathLab/AquaCal/commit/6024c9e5ac2a2121ee787ec089d38ddaf4604e59))

- **27-06**: Walk all 27 ledger artifacts to their emitters
  ([`c1f3af2`](https://github.com/McGrathLab/AquaCal/commit/c1f3af21bd228315d417efc1af102d51a5c54855))

- **27-07**: Add RL-guard-frac to the by-construction group (author ruling)
  ([`4c9a37f`](https://github.com/McGrathLab/AquaCal/commit/4c9a37fe0491fa59b823f9eb79576f5bfd619ac7))

- **27-07**: Classify every ledger row this run will not regenerate
  ([`c5646da`](https://github.com/McGrathLab/AquaCal/commit/c5646daf6576f2cdf03bd012b038e9edf09a6506))

- **27-07**: Complete the frozen-ledger-rows classification plan
  ([`464e0c9`](https://github.com/McGrathLab/AquaCal/commit/464e0c9ddf6e04330ae91b256246520f01cc2b7c))

- **27-07**: Record the RL-guard-frac addition and the 22 -> 23 total
  ([`c92cafc`](https://github.com/McGrathLab/AquaCal/commit/c92cafc0a6a98268339d9d5384593377c64c3873))

- **27-08**: Complete the driver-portability plan
  ([`d0dd8c6`](https://github.com/McGrathLab/AquaCal/commit/d0dd8c653785ee02a9b04861bd651fb5136f7fab))

- **27-09**: Complete the frozen handoff note plan
  ([`5e752fe`](https://github.com/McGrathLab/AquaCal/commit/5e752fe2cb8c529099173819a71be61b94fa4d9b))

- **27-09**: Correct three stale or misleading points in the handoff note
  ([`3ab9c13`](https://github.com/McGrathLab/AquaCal/commit/3ab9c13723202a58bb50e351b0b6bc0c0ffcd59c))

- **27-09**: Document the dry run and the thread cap in the handoff note
  ([`e2b2377`](https://github.com/McGrathLab/AquaCal/commit/e2b2377efbaa024ee7ccc2f9c842eeb5919cdf78))

- **27-09**: Write the handoff note's environment requirements (criterion 3)
  ([`900d835`](https://github.com/McGrathLab/AquaCal/commit/900d835aec6123c1203f3e36e9881c35e9286b27))

- **27-09**: Write the run procedure and the declared gaps (D-21)
  ([`801eb81`](https://github.com/McGrathLab/AquaCal/commit/801eb818a5c04786215ae4304195203f9990a697))

- **27-10**: Record the smoke acceptance pass and the pre-push audit
  ([`6d47d4f`](https://github.com/McGrathLab/AquaCal/commit/6d47d4f13b366fc215cc5977579242fc8407758d))

- **27-11**: Cut the freeze at 3ab9c13, tagged rerun-freeze-01
  ([`4b5e8ce`](https://github.com/McGrathLab/AquaCal/commit/4b5e8ce036dc4c01cc0055a51e4bce5e015746c2))

- **27-12**: Correct the baseline-archive size before it fails a clone check
  ([`a77e3c7`](https://github.com/McGrathLab/AquaCal/commit/a77e3c7ad28a27f30ed3528dbe31199267fe3e27))

- **28**: Add phase context and repoint state at the rerun
  ([`687f969`](https://github.com/McGrathLab/AquaCal/commit/687f969d7b9ff6f3bc4637434eb72f55ac2b1cab))

- **28**: Add read_first to the launch authorisation gate; deduplicate threat ids
  ([`f1ecae9`](https://github.com/McGrathLab/AquaCal/commit/f1ecae9519e2698c56a4d39f3df1bd592bcaa842))

- **28**: Close phase 28 in project state
  ([`8d26b5b`](https://github.com/McGrathLab/AquaCal/commit/8d26b5bb34be15b9718e8005f3324e0ab01f227c))

- **28**: Close phase-28 planning -- gates, wave annotations, state
  ([`a7efb3b`](https://github.com/McGrathLab/AquaCal/commit/a7efb3b97100c85ef75b8edeb13d7a3865c6bf8f))

- **28**: Create phase plan — 5 plans, 5 waves, tracer-led production runbook
  ([`c3596f2`](https://github.com/McGrathLab/AquaCal/commit/c3596f26f1303183192eb9b11ec974bc89199ddd))

- **28**: File the four defects the production run surfaced
  ([`8c9243c`](https://github.com/McGrathLab/AquaCal/commit/8c9243c61ff3e56b700e4b0a6ca96d0da05da374))

- **28**: Freeze02 run evidence and run record
  ([`1140dd5`](https://github.com/McGrathLab/AquaCal/commit/1140dd58fb2c29ff67f369cdf1c4a6cec1d98e51))

- **28**: Mark RESEARCH.md's open questions resolved
  ([`b001904`](https://github.com/McGrathLab/AquaCal/commit/b001904f9052733944c44b01c33d2d59fbdaab1e))

- **28**: Research phase domain
  ([`b0fcef1`](https://github.com/McGrathLab/AquaCal/commit/b0fcef10f43ee2f8931f50e62339ada485ddb88b))

- **28**: Run verdict, gate output, and environment capture
  ([`97135a2`](https://github.com/McGrathLab/AquaCal/commit/97135a232e44d55ea7f4ab5d3241315ab383470e))

- **28-01**: Complete production-venue plan
  ([`99c2c4c`](https://github.com/McGrathLab/AquaCal/commit/99c2c4c34e92921bc3523892d7384b0d4dc420c1))

- **28-01**: Record self-check result
  ([`be34637`](https://github.com/McGrathLab/AquaCal/commit/be346378741c2ff2e13b7a564a65128a52553bf8))

- **28-01**: Summarise the production venue build
  ([`055225c`](https://github.com/McGrathLab/AquaCal/commit/055225c8f6dacfaf28ceb3368050ef46271df20a))

- **28-02**: Complete pre-flight and launch authorisation plan
  ([`1eabd29`](https://github.com/McGrathLab/AquaCal/commit/1eabd29e868ae3c9c4d9e923f501bd67ab39ba15))

- **29**: Add ORCID and remove a placeholder from Record A's description
  ([`cd83a99`](https://github.com/McGrathLab/AquaCal/commit/cd83a990cecfc515ac4a4e76a5cb61a64a36ba4b))

- **29**: Add the missing action block to the sandbox-confirmation checkpoint
  ([`7dc2bcd`](https://github.com/McGrathLab/AquaCal/commit/7dc2bcdb0afb789824522f5791a2a885d8fdb2db))

- **29**: Capture phase context from discussion
  ([`c19ecec`](https://github.com/McGrathLab/AquaCal/commit/c19ececaafa40ca8d6e248a125f12af987017cf4))

- **29**: Correct two stale requirements-completed claims in SUMMARY frontmatter
  ([`899095a`](https://github.com/McGrathLab/AquaCal/commit/899095a4a933ffb4bd98d5de4a6415cb53d78078))

- **29**: Create phase plan
  ([`9c0ed09`](https://github.com/McGrathLab/AquaCal/commit/9c0ed09a4cc73fea055fe349905b055dffb25876))

- **29**: Create phase plan
  ([`da0f02f`](https://github.com/McGrathLab/AquaCal/commit/da0f02ffac464c3ff206835f16555bee55352dde))

- **29**: Move the Zenodo upload work to the Linux box
  ([`149d89b`](https://github.com/McGrathLab/AquaCal/commit/149d89b07a2377f6df1367c544181a66867aac29))

- **29**: Re-scope RUN-05 from a date to the submission event
  ([`60ea40d`](https://github.com/McGrathLab/AquaCal/commit/60ea40ded9167e1edc07dd6fb16ad1e7cf0a4b76))

- **29**: Research the gate, the commit set, and the Zenodo API
  ([`99db4cd`](https://github.com/McGrathLab/AquaCal/commit/99db4cdad7cc565514aa90011400adf3df3a0607))

- **29**: Return handoff -- preserve, verify, and commit the freeze-01 run on the Linux box
  ([`a33e21c`](https://github.com/McGrathLab/AquaCal/commit/a33e21c0eb8c97c6f0f92b1b5779af04e0ef3982))

- **29**: Set Record B's version to 2.1.0 per author ruling
  ([`9fdd884`](https://github.com/McGrathLab/AquaCal/commit/9fdd884e3968e5f4130ea37fb32e40adf4e79904))

- **29-01**: Complete zenodo-tooling-and-sandbox-rehearsal plan
  ([`9559ea8`](https://github.com/McGrathLab/AquaCal/commit/9559ea80f531e303b7ee0c190e953ab98bbcd413))

- **29-01**: Record the author's sandbox approval and three findings
  ([`0b56022`](https://github.com/McGrathLab/AquaCal/commit/0b56022e2fa2d6bbe30322894c0b67c336401771))

- **29-01**: Record the Zenodo credential gate as satisfied
  ([`75a33cb`](https://github.com/McGrathLab/AquaCal/commit/75a33cb1d2daed4c93b58c8ba59747dda67d3054))

- **29-01**: Rule the Record A / Record B payload split
  ([`a96da07`](https://github.com/McGrathLab/AquaCal/commit/a96da0772cb9f082ec3963cc4b798be095a6f754))

- **29-01**: Update state and roadmap for the zenodo tooling plan
  ([`51ebbcc`](https://github.com/McGrathLab/AquaCal/commit/51ebbcccfe200db6e5316e2cc2f418151be7b5aa))

- **29-02**: Complete land-and-grade-the-returned-run plan
  ([`e290f63`](https://github.com/McGrathLab/AquaCal/commit/e290f632ce455985f4130f3a54ad158aa2103794))

- **29-02**: Grade the returned run with the frozen gate
  ([`224c229`](https://github.com/McGrathLab/AquaCal/commit/224c2297fe857fd2db7357e28db7c3fc65017129))

- **29-02**: Inventory the 227 files the ignore rules admit
  ([`7632402`](https://github.com/McGrathLab/AquaCal/commit/7632402b893ab3b79c6738e3a4c9ff2e8da44c14))

- **29-03**: Complete e2-control-and-e7-before-after plan
  ([`fa9ed24`](https://github.com/McGrathLab/AquaCal/commit/fa9ed24ecfbd5b647194fb1997be531788e32209))

- **29-03**: Complete e2-control-and-e7-before-after plan
  ([`1b540d5`](https://github.com/McGrathLab/AquaCal/commit/1b540d58e686f35cdcfed083a451fc3f6ee8c90a))

- **29-04**: Build Record A's input-only archive and record its digest
  ([`f15f1ba`](https://github.com/McGrathLab/AquaCal/commit/f15f1ba06c1f50953299b81af1b7b02a9913f54e))

- **29-04**: Complete record-a-build-and-production-draft plan
  ([`b95762f`](https://github.com/McGrathLab/AquaCal/commit/b95762fb0468bbd5fa17b716cc34ec0e04425d62))

- **29-04**: Complete record-a-build-and-production-draft plan
  ([`886bbda`](https://github.com/McGrathLab/AquaCal/commit/886bbda78facd385320e41b47ca81e7fa686c6ee))

- **29-04**: Create Record A's production draft and record its handles
  ([`b71ffe5`](https://github.com/McGrathLab/AquaCal/commit/b71ffe5dfd69cef6e77166219d1611ef5dd6be2b))

- **29-05**: Complete commit-the-returned-run plan
  ([`088b876`](https://github.com/McGrathLab/AquaCal/commit/088b8761b92097b9525b516dc3214b9936030ed9))

- **29-05**: Record the post-commit gate re-run and byte anchors
  ([`da86892`](https://github.com/McGrathLab/AquaCal/commit/da86892f134c3fa6e0d92539dbf6da010479202b))

- **29-06**: Complete repair-the-provenance-rails plan
  ([`dc2de72`](https://github.com/McGrathLab/AquaCal/commit/dc2de72523d4185e026938ed948cd303dc67d8cc))

- **29-06**: Measure the D1 provenance rails against the committed tree
  ([`4256e82`](https://github.com/McGrathLab/AquaCal/commit/4256e8247df5d004bedeb959956e93270c00f853))

- **29-07**: Append the summary self-check result
  ([`b75a066`](https://github.com/McGrathLab/AquaCal/commit/b75a066f7336a3f1579f48d6a5fd00b872eda4b1))

- **29-07**: Complete record-b-build-and-production-draft plan
  ([`ec06b7e`](https://github.com/McGrathLab/AquaCal/commit/ec06b7edd26f2b0532aa100897256d1887999c24))

- **29-07**: Record Record B's draft handles before any payload byte moves
  ([`ca3f044`](https://github.com/McGrathLab/AquaCal/commit/ca3f0449972572caf195d3e0f91e78fea7522051))

- **29-07**: Record the A<->B linkage options and Record A's live draft state
  ([`67d0b9b`](https://github.com/McGrathLab/AquaCal/commit/67d0b9bc786f2ed12a4aa2914e7f2b1559c2e2e2))

- **29-07**: Record the sequential linkage ruling and Record A's minted DOIs
  ([`cc08fa5`](https://github.com/McGrathLab/AquaCal/commit/cc08fa506bd612618a8f4b542e3365b629445470))

- **29-07**: Summarise Record B's build and production draft
  ([`c227048`](https://github.com/McGrathLab/AquaCal/commit/c227048cbb5e799fcdb8af19a654f442d6d5a42a))

- **29-08**: Append the self-check result
  ([`862eb99`](https://github.com/McGrathLab/AquaCal/commit/862eb998cbdb0da6f8bc7f140b7760096f48ee2f))

- **29-08**: Complete the phase-close plan
  ([`66c70fb`](https://github.com/McGrathLab/AquaCal/commit/66c70fbc815e745e568c029241cf5c8ddc495d28))

- **29-08**: File the forward-carried items with their blast radius attached
  ([`9ea932e`](https://github.com/McGrathLab/AquaCal/commit/9ea932e4f4938c247d941cd322c5b835f00c66e0))

- **29-08**: Record the author's `defer` ruling and make the handoff unmissable
  ([`da8312c`](https://github.com/McGrathLab/AquaCal/commit/da8312c748be61b78cd2a945ada7d5d66be431f2))

- **29-08**: Summarise the phase-close plan
  ([`cbf56a3`](https://github.com/McGrathLab/AquaCal/commit/cbf56a3df84769b657ff3c8d7bd2d49c17d18bb4))

- **29-08**: Write the phase record — six criteria, measured values, named evidence
  ([`0bcf13d`](https://github.com/McGrathLab/AquaCal/commit/0bcf13d641b469149403d1f89efe3e4f0d24c6f4))

- **29.1**: Capture phase context
  ([`cfba57f`](https://github.com/McGrathLab/AquaCal/commit/cfba57f694a0def0162be85d6cceee074371433d))

- **29.1**: Correct the SC-3 mechanism and record the 198 evidence table
  ([`e399056`](https://github.com/McGrathLab/AquaCal/commit/e3990566b4057a96864a90430bdac099b6d0c813))

- **29.1**: Create phase plans -- 8 plans, 6 waves, tracer-first
  ([`153eb48`](https://github.com/McGrathLab/AquaCal/commit/153eb485fd501bcd6b6d5598f422caaab9c70a1b))

- **29.1**: Fold SC-7 in as plan 09, cite the 198 evidence table, correct the SC-3 mechanism
  ([`c629a65`](https://github.com/McGrathLab/AquaCal/commit/c629a65b8060f29bc9f7872aa93776592c16d78c))

- **29.1**: Fold the conditional-artifact mis-scoring in as criterion 7
  ([`b077ef0`](https://github.com/McGrathLab/AquaCal/commit/b077ef063f81183bf259f0eacf9d596a9ea1d0bf))

- **29.1**: Insert Post-Run Fixes & Re-Freeze between Phases 29 and 30
  ([`6209f70`](https://github.com/McGrathLab/AquaCal/commit/6209f705a5bd793672610d31c3340bc18b14b1e9))

- **29.1**: Record that the 198 are settled -- above-water board corners
  ([`84b6550`](https://github.com/McGrathLab/AquaCal/commit/84b655060afab4986eb8545a8783dd22cb4d1f9c))

- **29.1-01**: Close the real-rig guard-count todo with its resolution
  ([`3ab2a65`](https://github.com/McGrathLab/AquaCal/commit/3ab2a65edfe11e2a54758ea3781bea2e7fdcfbb4))

- **29.1-01**: Complete E4 real-rig guard count plan
  ([`85f7bcf`](https://github.com/McGrathLab/AquaCal/commit/85f7bcf624b48db50f7a79e25ee49814c48525e0))

- **29.1-01**: Complete E4 real-rig guard count plan
  ([`54f3699`](https://github.com/McGrathLab/AquaCal/commit/54f3699f58e49b7df10c63a7478071ceab2aeabc))

- **29.1-01**: Log 8 pre-existing provenance-test failures as a deferred item
  ([`4e5cf4e`](https://github.com/McGrathLab/AquaCal/commit/4e5cf4e8babde086e39984ee4bf480fc9779ecef))

- **29.1-01**: Replace the stale D-26 rationale and make the pipeline exemption explicit
  ([`85ec38c`](https://github.com/McGrathLab/AquaCal/commit/85ec38c16cca6f2712f41014776000e568d240fd))

- **29.1-02**: Append self-check result to the plan summary
  ([`ad1a99f`](https://github.com/McGrathLab/AquaCal/commit/ad1a99f192bc31c25c07cc0e21cc0dbf117a7cbd))

- **29.1-02**: Complete E1 band defects plan
  ([`65252f7`](https://github.com/McGrathLab/AquaCal/commit/65252f7163b7f1a67f042b25d68e856979e1ae5e))

- **29.1-02**: Record plan 02 completion in project state
  ([`3157bcb`](https://github.com/McGrathLab/AquaCal/commit/3157bcb0b4f0102c5e49f72ea971753db6b61db6))

- **29.1-03**: Annotate three todos with what the bounded pass covered
  ([`82bb0bc`](https://github.com/McGrathLab/AquaCal/commit/82bb0bc8975dd1a964e2ed424d4b67886df26585))

- **29.1-03**: Complete bounded stale-string sweep plan
  ([`bd4019c`](https://github.com/McGrathLab/AquaCal/commit/bd4019cc7dd573ec2abc6c2933084fbdd89d5fbb))

- **29.1-03**: Enumerate and classify the bounded stale-string sweep
  ([`f983d21`](https://github.com/McGrathLab/AquaCal/commit/f983d21edaebe824af7f11633a900eaa37d66c50))

- **29.1-03**: Record the bounded stale-string sweep summary
  ([`0612725`](https://github.com/McGrathLab/AquaCal/commit/06127254c7937d69f93739dd965519845ac4f0b0))

- **29.1-03**: Record the summary self-check result
  ([`4480138`](https://github.com/McGrathLab/AquaCal/commit/44801384f56e3a457e01b617d3f79d80398065e9))

- **29.1-04**: Complete the install-instruction correction plan
  ([`bbdb3bc`](https://github.com/McGrathLab/AquaCal/commit/bbdb3bc8ce1df37db270e5d6d1b0055b18d92669))

- **29.1-04**: Correct HANDOFF §1.2 install command and rule on every install site
  ([`4633009`](https://github.com/McGrathLab/AquaCal/commit/46330099d11d56678d758c35dedfa8acd1568304))

- **29.1-04**: Prove the corrected install by building an environment from it
  ([`5debda6`](https://github.com/McGrathLab/AquaCal/commit/5debda6976f720a3fd744b9aca558bac463c93b9))

- **29.1-04**: Record plan 04 completion in project state
  ([`51b3d08`](https://github.com/McGrathLab/AquaCal/commit/51b3d08f8870dff1a43b88aa2d8011b9649def7e))

- **29.1-05**: Complete the folded-todo discharge plan
  ([`bafc005`](https://github.com/McGrathLab/AquaCal/commit/bafc005ed7cd076d83b4a117c461b75f0914ab7f))

- **29.1-05**: Confirm the E4 aggregator path defect is fixed, then close it
  ([`dd92fbd`](https://github.com/McGrathLab/AquaCal/commit/dd92fbd5a08f5cb6f1d9a64ef17cec693296f6c0))

- **29.1-05**: Record plan 05 completion in project state
  ([`ffbe1a4`](https://github.com/McGrathLab/AquaCal/commit/ffbe1a41571b35095e5f9b031af2cf7d5c1f12ba))

- **29.1-05**: Settle the 198 unprojectable observations as above-water board corners
  ([`65294c5`](https://github.com/McGrathLab/AquaCal/commit/65294c5a85774906624008ca67ca2492a0f250d1))

- **29.1-06**: Complete the archive-aside plan
  ([`a833a15`](https://github.com/McGrathLab/AquaCal/commit/a833a1553b8fa004c7bffeff89b01c3e93a7c7af))

- **29.1-06**: Reconcile every reference to the moved output tree
  ([`63d3cb5`](https://github.com/McGrathLab/AquaCal/commit/63d3cb5882ce22a691ee5528b05e9b81ae9289b8))

- **29.1-06**: Record the archive-aside plan's completion
  ([`646cf08`](https://github.com/McGrathLab/AquaCal/commit/646cf08dceece0054c864ddb8ede400d6cba78ea))

- **29.1-06**: Record the gate before/after while the tree is still at the default path
  ([`b1adb3f`](https://github.com/McGrathLab/AquaCal/commit/b1adb3f3ec66ee91149207da38a955d862d7d9cf))

- **29.1-06**: Record the summary self-check result
  ([`ad5ba1c`](https://github.com/McGrathLab/AquaCal/commit/ad5ba1ca0156212506af1ef4b8af0f55f761be0c))

- **29.1-07**: Record attempt 1's verification bar re-run, including the three failures it found
  ([`98c942b`](https://github.com/McGrathLab/AquaCal/commit/98c942b1e3e8767a55b40817b598e2762b2c334a))

- **29.1-07**: Record the summary self-check result
  ([`3719d30`](https://github.com/McGrathLab/AquaCal/commit/3719d303e40f785dbd5e95dbdf705f1e64a205a1))

- **29.1-07**: Record the verification-bar plan's completion
  ([`4cc85b0`](https://github.com/McGrathLab/AquaCal/commit/4cc85b047e9ff572ba5b70d04ba2e6eb6e5a2f6f))

- **29.1-07**: Record verification-bar completion in project state
  ([`7005a27`](https://github.com/McGrathLab/AquaCal/commit/7005a2771aa115e4f4c1284cec7e145739586a4a))

- **29.1-08**: Append attempt 2 to the numbered freeze attempt log
  ([`e7448a9`](https://github.com/McGrathLab/AquaCal/commit/e7448a96df6705fb8582bc8070ca6912596b9d3e))

- **29.1-08**: Close out D4, D5 and D6 in the deferred-items ledger
  ([`3fd92bf`](https://github.com/McGrathLab/AquaCal/commit/3fd92bf9eddf75efa7f1d1704779cf9c9f4e2f71))

- **29.1-08**: Close the plan -- rerun-freeze-02 pushed, phase 29.1 done
  ([`92901ac`](https://github.com/McGrathLab/AquaCal/commit/92901ac57d6d5d863e58548c81039b428669952b))

- **29.1-08**: Complete the rerun-freeze-02 freeze plan up to the push gate
  ([`ffbd647`](https://github.com/McGrathLab/AquaCal/commit/ffbd64731709ec54c8539dac629c57bb31a4a90a))

- **29.1-08**: Correct a stale PENDING reference in the summary
  ([`0898c53`](https://github.com/McGrathLab/AquaCal/commit/0898c53a2fdaf757593cf7ebb6eb184b897ae135))

- **29.1-08**: Record the approved push and the post-push assertions
  ([`fff7f2e`](https://github.com/McGrathLab/AquaCal/commit/fff7f2e1f4c86fa1372cf335d905ee063d8febda))

- **29.1-08**: Record the pre-push exposure audit and the D4 ruling
  ([`54542c6`](https://github.com/McGrathLab/AquaCal/commit/54542c6e01860b72a999be50ef407e0feec78849))

- **29.1-08**: Record the rerun-freeze-02 freeze
  ([`ea11a81`](https://github.com/McGrathLab/AquaCal/commit/ea11a812f03eeb73b63101ff93aa9a1895067f43))

- **29.1-08**: Record the summary self-check result
  ([`59fa146`](https://github.com/McGrathLab/AquaCal/commit/59fa1468f09709c82cd96e83e8529a62c74eb89a))

- **29.1-08**: Register the three D4 anchor failures in the windows ledger
  ([`03333d7`](https://github.com/McGrathLab/AquaCal/commit/03333d7082ee1f2913b46067b1efa656997a6b7f))

- **29.1-08**: Summarise the rerun-freeze-02 freeze plan
  ([`01ee83d`](https://github.com/McGrathLab/AquaCal/commit/01ee83d9abad54652217099e38cc733e8c685367))

- **29.1-09**: Record plan 09 completion in project state
  ([`7f1d91f`](https://github.com/McGrathLab/AquaCal/commit/7f1d91f8093e2c2ee20782690eb946240b72c1a1))

- **29.1-09**: Record the conditional-artifact gate summary
  ([`3d0c598`](https://github.com/McGrathLab/AquaCal/commit/3d0c5989c7f84d60d2542bc45b67de05a9e9d880))

- **29.1-09**: Record the summary self-check result
  ([`37a8b14`](https://github.com/McGrathLab/AquaCal/commit/37a8b145cbabd02837474aaebe04bbe2b3dc6f7e))

- **29.1-09**: Surface the predicate in the sheet and record the mechanism chosen
  ([`911cb94`](https://github.com/McGrathLab/AquaCal/commit/911cb9483276a0eb13a82522870232815762ce14))

- **29.2**: Capture phase context
  ([`45efc98`](https://github.com/McGrathLab/AquaCal/commit/45efc98bd70e6d78c8cd8553b805efcdf995122b))

- **29.2**: Correct CONTEXT decisions research invalidated
  ([`bb4083a`](https://github.com/McGrathLab/AquaCal/commit/bb4083a2612b30651b0afd5f056c834cc042550d))

- **29.2**: Create phase plan
  ([`7b6f1f2`](https://github.com/McGrathLab/AquaCal/commit/7b6f1f2e2e78eb438c9b9b3f5d766b2b25fe2beb))

- **29.2**: Research phase domain
  ([`beeaf92`](https://github.com/McGrathLab/AquaCal/commit/beeaf9294ce4f0f45e786b616dc341736bcfda8d))

- **29.2-01**: Assert the 2.1.0 sdist's member list, record the size series
  ([`55f3bcc`](https://github.com/McGrathLab/AquaCal/commit/55f3bcc3d6066ab9e5aaf0b956d53480ba376204))

- **29.2-01**: Complete the release-rehearsal tracer plan
  ([`fe9c433`](https://github.com/McGrathLab/AquaCal/commit/fe9c433137491a556b6d974782959d1cc2bba580))

- **29.2-01**: Rehearse the whole v2.1.0 release end to end in a throwaway clone
  ([`efcc7bc`](https://github.com/McGrathLab/AquaCal/commit/efcc7bc2384180b98d9924e6630f17ca3239a249))

- **29.2-02**: Complete the pre-commit hook repair plan
  ([`80ae46e`](https://github.com/McGrathLab/AquaCal/commit/80ae46ec7a1785da3753c313e2435d25979f8974))

- **29.2-03**: Amend the D4 todo to the two members it still owns
  ([`ae90117`](https://github.com/McGrathLab/AquaCal/commit/ae90117db1fe7b288b465033889be64d1b674308))

- **29.2-03**: Complete the D4 step-bound and CI pre-measurement plan
  ([`dc3d1f7`](https://github.com/McGrathLab/AquaCal/commit/dc3d1f703cd789875776bb229dafae82322c8e69))

- **29.2-03**: File this plan's two deviations in the windows ledger
  ([`12291c6`](https://github.com/McGrathLab/AquaCal/commit/12291c695a65b91ae2563361f8cfa0759536b9d5))

- **29.2-03**: Record both suite counts and all seven smoke invocations
  ([`3c831b1`](https://github.com/McGrathLab/AquaCal/commit/3c831b12affa802a0c21db2b78156fb5a9616c3a))

- **29.2-04**: Complete the hook-proof, pull-request and check-board plan
  ([`d561021`](https://github.com/McGrathLab/AquaCal/commit/d56102172e929da0980991a4478d53fe5d490598))

- **29.2-04**: Fix the four docutils faults that fail CI's build-docs job
  ([`3ffebe3`](https://github.com/McGrathLab/AquaCal/commit/3ffebe39279a2c2d9064c05793a939ba5711123f))

- **29.2-04**: Open PR #3 into main and record it, unmerged
  ([`f5b9e10`](https://github.com/McGrathLab/AquaCal/commit/f5b9e1085befc31cee13f7724465d4f37b9f73bc))

- **29.2-04**: Prove CI's whole-tree hook sweep moves not a byte
  ([`ff9d5d1`](https://github.com/McGrathLab/AquaCal/commit/ff9d5d1667ab2d09a3e69c87cd893a671e1b315c))

- **29.2-04**: Record the credential-scope gate blocking the pull request
  ([`cf14d0e`](https://github.com/McGrathLab/AquaCal/commit/cf14d0e6fb9b79167c57930455817a1a42985ca6))

- **29.2-04**: Record the seventh board row, the build-docs failure, and the re-proof
  ([`f300c55`](https://github.com/McGrathLab/AquaCal/commit/f300c55d8cf261db4ef95365d71a8131966e7a21))

- **29.2-04**: Rule the check board NOT GREEN, with all seven rows behind it
  ([`64f83aa`](https://github.com/McGrathLab/AquaCal/commit/64f83aa3d9b28972e73d52ede5574dc66d28f887))

- **29.2-04**: Summarise the hook proof, PR #3, and the not-green board
  ([`6046665`](https://github.com/McGrathLab/AquaCal/commit/6046665c3206d286761ab3d2a0d08061472d9d04))

- **experiments**: Distinguish results_linux32gb/ and file the E4 aggregator defect
  ([`3eb1f4a`](https://github.com/McGrathLab/AquaCal/commit/3eb1f4a7ede0ffca3d1ffb44cb0a5651b3a78c26))

- **findings**: Correct MF-08's determinism figure from 8/308 to 16/308
  ([`ae8479b`](https://github.com/McGrathLab/AquaCal/commit/ae8479bf1b16d3bcaff64a97c6ba176d99dd594a))

- **phase-23**: Complete phase execution
  ([`a7f0f25`](https://github.com/McGrathLab/AquaCal/commit/a7f0f25a4a571d906d3de127fe0bbe4b6ba941ae))

- **phase-23**: Update tracking after wave 1
  ([`7ff7265`](https://github.com/McGrathLab/AquaCal/commit/7ff7265ef3fc5edfd5df7b3d907b880d65a7ae7f))

- **phase-24**: Auto-close 3 todo(s) resolved by this phase
  ([`8772122`](https://github.com/McGrathLab/AquaCal/commit/877212206b2c10ea7a274e85eebd5e6165ce2a2b))

- **phase-24**: Complete phase execution
  ([`d25e896`](https://github.com/McGrathLab/AquaCal/commit/d25e896e8be34250396efd2fa61ea9211b010650))

- **phase-24**: Evolve PROJECT.md after phase completion
  ([`01bead1`](https://github.com/McGrathLab/AquaCal/commit/01bead1718179d8641cc209f2d3d15628f28ff61))

- **phase-24**: Update requirements traceability
  ([`ee36e23`](https://github.com/McGrathLab/AquaCal/commit/ee36e23fdd3677c8aabf0c0835219572d33ff446))

- **phase-24**: Update tracking after wave 2
  ([`faaaf8a`](https://github.com/McGrathLab/AquaCal/commit/faaaf8aa9f721bfc06f6fa50cad687f42fa7364e))

- **phase-28**: Add validation strategy
  ([`4672f4a`](https://github.com/McGrathLab/AquaCal/commit/4672f4a376007fec1036ca0e43a6efc4f3e53388))

- **phase-29**: Add validation strategy
  ([`34e268b`](https://github.com/McGrathLab/AquaCal/commit/34e268b1af69f4b8b57dac25f97bb8a4475f95eb))

- **phase-29.1**: Begin phase execution tracking
  ([`4543a29`](https://github.com/McGrathLab/AquaCal/commit/4543a290a16369797efcdf6e8e4648e2548bf1b2))

- **phase-29.1**: Complete phase execution
  ([`7edda2e`](https://github.com/McGrathLab/AquaCal/commit/7edda2e07f5d62a498bd163716e467b40804dc32))

- **phase-29.2**: Add validation strategy
  ([`8d9f819`](https://github.com/McGrathLab/AquaCal/commit/8d9f819beeaab5b4f46c62fcf628cb3d92788f67))

- **roadmap**: Add DEGEN-05 per-block optimality decomposition to Phase 24
  ([`30f5486`](https://github.com/McGrathLab/AquaCal/commit/30f548600e287a8465f769892b352740b6e0fcb1))

- **roadmap**: Insert Phase 29.2 — Merge, Release, and Publish
  ([`fd78d77`](https://github.com/McGrathLab/AquaCal/commit/fd78d77443176e730321eb091814abc8a9ffe8ea))

- **state**: Record phase 23 context session
  ([`7da1194`](https://github.com/McGrathLab/AquaCal/commit/7da1194e28a5997ad0dfc61ed63f59166367612c))

- **state**: Record phase 24 context session
  ([`6276792`](https://github.com/McGrathLab/AquaCal/commit/6276792b5f751b5bfc2b06e77584e1c645148c28))

- **state**: Record phase 25 context session
  ([`054d753`](https://github.com/McGrathLab/AquaCal/commit/054d7539582c27096b7868298e136a5f2c02951b))

- **state**: Record phase 26 context session
  ([`c214d09`](https://github.com/McGrathLab/AquaCal/commit/c214d0982a419f02b96e77d3d0450a70c974626b))

- **state**: Record phase 27 context session
  ([`9889e37`](https://github.com/McGrathLab/AquaCal/commit/9889e376b65facc359937f047fc5f641fbcc8f32))

- **state**: Record phase 29.1 context session
  ([`6f515e5`](https://github.com/McGrathLab/AquaCal/commit/6f515e5fa14bc59397acbf2ccfe65564d8e5ef55))

- **state**: Record phase 29.1 planning completion
  ([`89c2092`](https://github.com/McGrathLab/AquaCal/commit/89c20923e098ec3f521a1d4e31272ebe24ae56ea))

- **state**: Record phase 29.2 context session
  ([`1baa971`](https://github.com/McGrathLab/AquaCal/commit/1baa9712f1a34b9bf44d17f863691a16d1a48d92))

- **state**: Record phase 29.2 planning session
  ([`c61500b`](https://github.com/McGrathLab/AquaCal/commit/c61500b82bc2589c374837f1edc2957d820749c5))

- **state**: Rename the work branch to results/rerun-freeze-02
  ([`1e2550c`](https://github.com/McGrathLab/AquaCal/commit/1e2550c89a602bcef20d7765c07fde42abd55fb0))

- **state**: Repair frontmatter and advance position to phase 27
  ([`c25bcef`](https://github.com/McGrathLab/AquaCal/commit/c25bcef60e54514dc57efa8bb6a5cc1382876bfa))

- **todo**: Capture pytest-xdist suite parallelization
  ([`3761044`](https://github.com/McGrathLab/AquaCal/commit/376104464dfbb4264428437de4b54dbfc3b7e0f0))

- **todo**: File the decision-coverage gate's dotted-phase blindness
  ([`a7a3d41`](https://github.com/McGrathLab/AquaCal/commit/a7a3d41a8987280fdb3fc786b1b621e4ff059c00))

- **todo**: Record the first pytest-xdist attempt failing at collection
  ([`10f7c4e`](https://github.com/McGrathLab/AquaCal/commit/10f7c4e7bc884cc3e4bf7e423b75f7600721738f))

### Features

- **23-01**: E1 and E7 solve with the interface normal free (FIX-02)
  ([`57ac430`](https://github.com/McGrathLab/AquaCal/commit/57ac430dad6e6e55843ca80a7cda9515a9ec0585))

- **23-01**: Pin water_z in E1 non-refractive arm via bounds override (FIX-01)
  ([`fb33db4`](https://github.com/McGrathLab/AquaCal/commit/fb33db48d63de8bd6d1fc9fa0dc39880c234020e))

- **23-03**: FIX-03 -- E6 signed/gauge-corrected Z error plus per-camera decomposition
  ([`bbcdbde`](https://github.com/McGrathLab/AquaCal/commit/bbcdbdedb3cb1b5182a109b392197cbd78c4418f))

- **23-03**: FIX-04 -- label E7's fixed rows vacuous-by-construction
  ([`0633ff3`](https://github.com/McGrathLab/AquaCal/commit/0633ff3e9c69980099c7a4e445490e387bf8d966))

- **24-01**: Add the bound-hit detector, pinned vs traveled (D-16)
  ([`25d1dad`](https://github.com/McGrathLab/AquaCal/commit/25d1dad815c612511f2c294aeeda5b76509f9e1b))

- **24-01**: Decompose optimality by parameter block (DEGEN-05)
  ([`ba59f84`](https://github.com/McGrathLab/AquaCal/commit/ba59f8491cf8bb020747e06f1ae1bd9d8b3e154b))

- **24-01**: Narrow the degenerate-observation warning by cause and fraction (DEGEN-03)
  ([`d6b55ed`](https://github.com/McGrathLab/AquaCal/commit/d6b55edb491c74b578e3e7e1f11ed267fbf6dd8b))

- **24-01**: Plumb the NaN reason out of the batch projector (DEGEN-02)
  ([`220a403`](https://github.com/McGrathLab/AquaCal/commit/220a403fb220f099678ca0f3f4045b300e45faf3))

- **24-01**: Split the degeneracy counter on cause and fate axes (DEGEN-02)
  ([`d48e669`](https://github.com/McGrathLab/AquaCal/commit/d48e6690a79d446cf455716dab275ed36e2ebecc))

- **24-01**: Thread discard_stage through both solver entry points (DEGEN-02)
  ([`21e398a`](https://github.com/McGrathLab/AquaCal/commit/21e398aa16ef574b5f7e8418abe697dfc8131c3e))

- **24-02**: Carry the whole discard_stats dict into benchmark.json (DEGEN-01)
  ([`6c76986`](https://github.com/McGrathLab/AquaCal/commit/6c76986ded1b4830719139755dcc969f46891c24))

- **24-02**: Publish both degeneracy axes in E1/E5/E7 plus a JSON sidecar
  ([`a55c6f1`](https://github.com/McGrathLab/AquaCal/commit/a55c6f134d2e8234cc256dca1d264e9c2db1afc7))

- **24-02**: Teach the re-run gate the split and hand Phase 26 the inventory
  ([`a381453`](https://github.com/McGrathLab/AquaCal/commit/a3814539061ee4c973a39c1d1346e6117f853f15))

- **25-01**: Add per-observation degeneracy detail sinks to compute_residuals
  ([`a1ca422`](https://github.com/McGrathLab/AquaCal/commit/a1ca4227b17c6e0b66268ac9c6f8a5f122d6d99b))

- **25-01**: Thread the detail sinks through both post-solve call sites (DEGEN-04)
  ([`34b4354`](https://github.com/McGrathLab/AquaCal/commit/34b4354066989f6c7c301f1c0c713f5572a34c7f))

- **25-02**: Add log_all_observation_depths config flag (D-09)
  ([`fdb78a6`](https://github.com/McGrathLab/AquaCal/commit/fdb78a65a5f76e768a19bf189e261a64335f1471))

- **25-02**: Thread the per-observation sinks through both stage-3 calls
  ([`ab62613`](https://github.com/McGrathLab/AquaCal/commit/ab62613f00d40769d4b8795c01002475a18732f0))

- **25-02**: Write the degenerate_observations.csv sidecar (D-08)
  ([`a212d5a`](https://github.com/McGrathLab/AquaCal/commit/a212d5a4cb4a86e53de974c75a2d02d5e9dd3163))

- **25-03**: Add the offline bucket vocabulary and classifier (DEGEN-04)
  ([`56bfbfe`](https://github.com/McGrathLab/AquaCal/commit/56bfbfeb2e21ab29ca1d376f0a6860f21a5bdace))

- **25-03**: Write the classification table with its in-body provenance stamp (DEGEN-04)
  ([`2f07dab`](https://github.com/McGrathLab/AquaCal/commit/2f07dabdc7016bf5c5d5a2d49599779c0da34ede))

- **25-04**: Nest E1's noise_std band axis and correct both band key lists
  ([`cc088b1`](https://github.com/McGrathLab/AquaCal/commit/cc088b11e7fee04d90e3d09496019297d6acc11d))

- **26-02**: Emit one suite-level run manifest at pre-flight (DRIVER-02)
  ([`24e547a`](https://github.com/McGrathLab/AquaCal/commit/24e547a876d0aed14c17aa7b80598d11f2bae627))

- **26-02**: Extend Gate 3 over the run manifest, all hard FAIL (D-21)
  ([`c8444fc`](https://github.com/McGrathLab/AquaCal/commit/c8444fc82e4bd4e18921d377ec8aff92e8206b86))

- **26-03**: Author suite_expectations.json, the single expectation manifest
  ([`8d00c69`](https://github.com/McGrathLab/AquaCal/commit/8d00c69dbd7ae5a866aa47178c15cc4c00ca4f23))

- **26-03**: Implement the completeness gate and its optional CLI selector
  ([`8c0c538`](https://github.com/McGrathLab/AquaCal/commit/8c0c538b2891fc8bb3d40797319199b9e7004ac5))

- **26-04**: Add --baseline-dir helpers and the missing-baseline N/A guard
  ([`375f895`](https://github.com/McGrathLab/AquaCal/commit/375f89501734d4c1a4cd3c30a87b2e9a7a28f688))

- **26-04**: Thread --baseline-dir through E3's --check
  ([`18f448a`](https://github.com/McGrathLab/AquaCal/commit/18f448afa034ad80024101c0c7a7ab031421ce34))

- **26-05**: Add an --axes selector to E6 so D-40 can drop the scale axis
  ([`02a4c82`](https://github.com/McGrathLab/AquaCal/commit/02a4c821981e63b99ec07113514ae1447c2da509))

- **26-06**: Emit E2's classification/timing/memory invocation configs (D-15/D-16)
  ([`64f0dc6`](https://github.com/McGrathLab/AquaCal/commit/64f0dc63ae2f196b4fd28aab0a50f53ece04f322))

- **26-07**: Populate the full stage list — every invocation in the suite
  ([`a9b12b4`](https://github.com/McGrathLab/AquaCal/commit/a9b12b4bcfb3a3ed150cd2530603fe2b68b5ae3e))

- **26-08**: Pre-flight refusals, the sticky exit and D-52's concurrency pool
  ([`edf6f49`](https://github.com/McGrathLab/AquaCal/commit/edf6f49d7835732712a0d0494f0e692f3a9d6c18))

- **26-09**: Render experiments/EXPECTATIONS.md from the manifest (D-05/D-08)
  ([`5497d4e`](https://github.com/McGrathLab/AquaCal/commit/5497d4edeec0c34933f28b051a3354cc19558480))

- **26-11**: Add the driver's reduced-scale (--smoke) path
  ([`5c0faee`](https://github.com/McGrathLab/AquaCal/commit/5c0faee956fbdf7e900dc96a4c2a0fe780d1a32f))

- **27-05**: Emit the environment lockfile as a run artifact (D-13)
  ([`bc2cc25`](https://github.com/McGrathLab/AquaCal/commit/bc2cc25fdb1343339f19122f8acdeee2ecfd83c1))

- **27-05**: Record both BLAS thread regimes in the run manifest (D-14)
  ([`cd958c9`](https://github.com/McGrathLab/AquaCal/commit/cd958c939d294b7fadd831d79f6abe47d9e46d05))

- **27-08**: Commit E2's exact release inputs inside the frozen sha (D-11)
  ([`ce9154a`](https://github.com/McGrathLab/AquaCal/commit/ce9154afd8b79bc93b43d74227f1668bedb78bd7))

- **27-08**: Record both interpreters in the run manifest (D-30)
  ([`fdd1ce4`](https://github.com/McGrathLab/AquaCal/commit/fdd1ce4cebb121e522fae5c6412a65dc42f81e86))

- **27-08**: Two-regime BLAS pin, the lockfile call site, and the re-derived byte floor (D-14, D-13,
  D-10)
  ([`d2b026b`](https://github.com/McGrathLab/AquaCal/commit/d2b026b276aac94a02a59c05773d562531ecc804))

- **29-01**: Zenodo upload tooling, rehearsed end to end on sandbox
  ([`240ed00`](https://github.com/McGrathLab/AquaCal/commit/240ed007b612c19010cd4da91166fe01519f02a1))

- **29-03**: E2 same-seed control script and evidence
  ([`8e34c6b`](https://github.com/McGrathLab/AquaCal/commit/8e34c6b23c4ea1b4d2eeb7e749359fe16893d6f0))

- **29-03**: E7 before/after sign test script and evidence
  ([`9b94f51`](https://github.com/McGrathLab/AquaCal/commit/9b94f51946ddee8aa74144d6394118a63d14bae4))

- **29-04**: Stream Record A into its production bucket, byte-verified
  ([`b6bec8d`](https://github.com/McGrathLab/AquaCal/commit/b6bec8db44e6e1cd5d1ac1947308729fa610675d))

- **29-07**: Build Record B's payload from this run's own fresh outputs
  ([`00db4ac`](https://github.com/McGrathLab/AquaCal/commit/00db4ac587b76d3bdf14e90c537c7d3a6925ceec))

- **29-07**: Finalise Record B's metadata with the ruled linkage
  ([`edd9f1b`](https://github.com/McGrathLab/AquaCal/commit/edd9f1b5da81f2324bf107dcebf817b8c9c6a819))

- **29-07**: Stream Record B into the draft and prove the round trip
  ([`37717eb`](https://github.com/McGrathLab/AquaCal/commit/37717eb695bf824d701984290bee680550098adb))

- **29.1-06**: Archive the 2026-08-20 run output aside so the new tag ships an empty output tree
  ([`24bf414`](https://github.com/McGrathLab/AquaCal/commit/24bf414282a62800d378093d73c2f964d51f75da))

- **29.1-09**: Evaluate the condition instead of excusing the absence
  ([`f22e853`](https://github.com/McGrathLab/AquaCal/commit/f22e8536701f5d172bb00d9cfcff7fdb410b1536))

### Refactoring

- **26-07**: Git mv rerun_19_3.sh -> run_experiment_suite.sh (D-25)
  ([`0402960`](https://github.com/McGrathLab/AquaCal/commit/0402960b37dd246eacef29979157133bbaed07af))

- **26-07**: Lift 19.5's machinery and write the one-driver header
  ([`bdd9dcc`](https://github.com/McGrathLab/AquaCal/commit/bdd9dcc329e0f2ab405808756004dd220481af75))

### Testing

- **24-02**: Add failing tests for the benchmark.json discard_stats block
  ([`9102b7c`](https://github.com/McGrathLab/AquaCal/commit/9102b7c65c12f0cfea8c0d0510cd39c4260715bb))

- **25-04**: Pin the 640/960 band shape, key uniqueness and the fixed contracts
  ([`ab1539a`](https://github.com/McGrathLab/AquaCal/commit/ab1539ad0f5eeacb08c2da42a225c5d82ca0bb09))

- **25-07**: Pin the gate-scope rationale and the count > 0 predicate (DEGEN-04)
  ([`dee5b64`](https://github.com/McGrathLab/AquaCal/commit/dee5b646fa0fd3171925c9c5294bf30da54a53e2))

- **26-01**: Repoint the committed-baseline reads at the pre-re-run archive
  ([`e3a7bf3`](https://github.com/McGrathLab/AquaCal/commit/e3a7bf35d4dce37ec0d340864da4e390228ef15d))

- **26-02**: Add failing TestRunManifestGate for Gate 3's manifest check
  ([`2dc19ef`](https://github.com/McGrathLab/AquaCal/commit/2dc19efb15a119007d33afbb33663adc7feddfd7))

- **26-02**: Add failing tests for the suite run-manifest emitter
  ([`1674883`](https://github.com/McGrathLab/AquaCal/commit/16748831df206b19119f6ef4b14e5bbfcbc57cee))

- **26-03**: Add failing tests for the completeness gate
  ([`872754f`](https://github.com/McGrathLab/AquaCal/commit/872754f6a566b441dfe74309be34e4084aa727aa))

- **26-03**: Add the forbidden-row-literal tripwire and the manifest couplings
  ([`db9f0ba`](https://github.com/McGrathLab/AquaCal/commit/db9f0bac12feae40e908fb462270c74517c44c98))

- **26-04**: Add failing E3 --baseline-dir plumbing tests
  ([`7f0fe8a`](https://github.com/McGrathLab/AquaCal/commit/7f0fe8a63e5cbc8708d1718af5fc02d3ffc795a4))

- **26-04**: Add failing TestBaselineDir for --baseline-dir helpers
  ([`7bd9905`](https://github.com/McGrathLab/AquaCal/commit/7bd9905b81b3824c9f93ae9b14f654751b1ac146))

- **26-05**: Add failing tests for E6's --axes selector (D-40)
  ([`59d6249`](https://github.com/McGrathLab/AquaCal/commit/59d62492778abd7d9836e7a219c680ef8ffef551))

- **26-06**: Add failing tests for E2 invocation configs and --check N/A guard
  ([`d1bc006`](https://github.com/McGrathLab/AquaCal/commit/d1bc006f7732ce9d0eae17c2fd75e00e689d6a0f))

- **26-07**: Couple the driver's stage list to the expectation manifest
  ([`35de34f`](https://github.com/McGrathLab/AquaCal/commit/35de34f2e5bafaaaa4cdf4aa7c659566d41ed80b))

- **26-08**: The suite driver's first automated test, ever
  ([`7fcc413`](https://github.com/McGrathLab/AquaCal/commit/7fcc4138b0d487205939a4ea6a0811f9dad3bc54))

- **26-09**: Failing freshness test for the expectation sheet (D-08)
  ([`adee237`](https://github.com/McGrathLab/AquaCal/commit/adee237d370311b1a8e58654f861b0665c483631))

- **26-11**: Cover the reduced-scale path and freeze the full-scale one
  ([`cc3c28d`](https://github.com/McGrathLab/AquaCal/commit/cc3c28d3302c3b6f4e605965ecacd48c380d8f90))

- **26-14**: Re-aim the baseline rails at the tree the frozen run writes
  ([`88512b7`](https://github.com/McGrathLab/AquaCal/commit/88512b78d38d3b4c5d05aa3f5175a8ca28e1da34))

- **27-02**: Add a failing resume test for a stage that completed non-zero (D-22)
  ([`03ee55b`](https://github.com/McGrathLab/AquaCal/commit/03ee55b94204e58f7b43568fd2ca88ea66cedd26))

- **27-02**: Add failing pre-flight tests for a directory frameset (D-09)
  ([`61d9a86`](https://github.com/McGrathLab/AquaCal/commit/61d9a86b33a85e3beb3fc1836a520989492e2a7f))

- **27-03**: Add failing tests for profile-aware E4/E5/E6 checkers (D-20)
  ([`2582ec7`](https://github.com/McGrathLab/AquaCal/commit/2582ec75748fbfed230389d9dc90c83f40cf45cb))

- **27-04**: Add failing tests for --out-relative real_rig_metrics resolution
  ([`f4ea3ff`](https://github.com/McGrathLab/AquaCal/commit/f4ea3ffb9a3f6c2e6a17e165fee0eacd3820b477))

- **27-05**: Add failing tests for the environment lockfile emitter (D-13)
  ([`2c25829`](https://github.com/McGrathLab/AquaCal/commit/2c25829525caf5d8d70ca2cabe931b6323721218))

- **27-05**: Add failing tests for the two-regime thread record (D-14)
  ([`38c0560`](https://github.com/McGrathLab/AquaCal/commit/38c0560cd6c91eec8b73d3e0f573556704e42dd7))

- **29.1-01**: Pin both halves of the real-rig guard-count fix
  ([`5fa6bd2`](https://github.com/McGrathLab/AquaCal/commit/5fa6bd22f615bf85588e604115060d5182f18de2))

- **29.1-02**: Add failing tests for the band's benchmark write policy
  ([`b14bd9d`](https://github.com/McGrathLab/AquaCal/commit/b14bd9dd107ec6e7eb7cf8b93f20fe734435163f))

- **29.1-09**: Failing tests for the conditional predicate and the misplacement search
  ([`dc7e6a2`](https://github.com/McGrathLab/AquaCal/commit/dc7e6a2d23b77c954823c5ce363e5744670e387c))

- **benchmark**: Guard the psutil peak-wset assertion on psutil being installed
  ([`d27bda7`](https://github.com/McGrathLab/AquaCal/commit/d27bda76fe7c765b3c975b2052ca1f8f7b286068))


## v2.0.1 (2026-08-11)

### Bug Fixes

- **tests**: Compare frozen anchors with a tolerance, not exact equality
  ([`eea0a83`](https://github.com/McGrathLab/AquaCal/commit/eea0a833201771505a332dd49998712281597077))


## v2.0.0 (2026-08-11)

### Bug Fixes

- **17-05**: Thread shared_interface through compute_residuals
  ([`575bdc8`](https://github.com/McGrathLab/AquaCal/commit/575bdc8203731525ae9ac56dab0aef3e70955f6a))

- **18**: Repair run_calibration_from_config docstring RST after wave 2
  ([`34497f9`](https://github.com/McGrathLab/AquaCal/commit/34497f9ce60f2d27579ebdcd733c76fc739d939a))

- **19**: Close verification gap and code-review findings
  ([`5e246b1`](https://github.com/McGrathLab/AquaCal/commit/5e246b183b95cf2412b7fc1f3ad87b91cbbc324a))

- **19.1-04**: Correct load_config import in explicit-config path
  ([`144b731`](https://github.com/McGrathLab/AquaCal/commit/144b7311181ebd3402dc4524f6c4a9b8b3fccef5))

- **19.1-04**: Distinguish pooled RMS from mean per-camera reprojection
  ([`eefeaa6`](https://github.com/McGrathLab/AquaCal/commit/eefeaa610e49f8eaebcedcbb546eedaf84c1a4de))

- **19.1-05**: Thread refraction-aware kwargs into Stage 2 extrinsics estimate
  ([`f984397`](https://github.com/McGrathLab/AquaCal/commit/f9843972a879d95b87cbff66f06cc37c54e522c3))

- **19.2-01**: Forward scenario.n_air/n_water to synthetic detection generation
  ([`03546b9`](https://github.com/McGrathLab/AquaCal/commit/03546b96eacf746a2a5a0301aa712168e401e72f))

- **19.2-09**: Compare_experiment_csv crashes when a status_reason column round-trips through CSV
  ([`ee8af31`](https://github.com/McGrathLab/AquaCal/commit/ee8af313f685e436b575c1dd2b7b3313dd76184d))

- **19.2-12**: Normalize mixed NaN/empty-string columns in compare_experiment_csv
  ([`ac75e35`](https://github.com/McGrathLab/AquaCal/commit/ac75e35a45fa919a87bce9980f1a401bb031e119))

- **19.2-13**: Implement E5 --check against the production baseline
  ([`9ff27be`](https://github.com/McGrathLab/AquaCal/commit/9ff27be4878215fad5c85ada1c214b72401fc7fb))

- **19.2-17**: Lossless E4 resume and defensive aggregation (CR-01, CR-03)
  ([`ac92033`](https://github.com/McGrathLab/AquaCal/commit/ac92033855785a4c0ac6361ed3770dd594d38ce9))

- **19.2-19**: Anchor the noise-floor path and guard --check's baseline (WR-06, WR-12)
  ([`383e19a`](https://github.com/McGrathLab/AquaCal/commit/383e19a191be0c164245db198e186c26df98d9d9))

- **19.2-24**: Anchor the e3 Newton-header test to a literal, not the live CSV
  ([`90e40ab`](https://github.com/McGrathLab/AquaCal/commit/90e40abf70159564ba5fa8ebf3cb121a610da409))

- **19.2-27**: Capture E6's environment once per sweep, not per configuration
  ([`48e3311`](https://github.com/McGrathLab/AquaCal/commit/48e3311686732edf7e9e7557366a0999e345c272))

- **19.2-27**: Restrict E6's WR-03 identity guard to scenario-determining fields
  ([`7b9493e`](https://github.com/McGrathLab/AquaCal/commit/7b9493e81e792c9e6530592422dc69078154484d))

- **19.3**: Repair E1's smoke depth and record two orchestrator findings
  ([`5b54b16`](https://github.com/McGrathLab/AquaCal/commit/5b54b16f663addc9d26e4ef030fb243d2c739583))

- **19.3-01**: Update in-repo callers for the required board parameter
  ([`95aed75`](https://github.com/McGrathLab/AquaCal/commit/95aed7576a489aa509286d8a2dc0f3de7f29f0ea))

- **19.3-02**: Correct DegenerateObservationWarning's backwards convergence advice
  ([`1e94d3c`](https://github.com/McGrathLab/AquaCal/commit/1e94d3ce77248202b892a716e1ce4b0057ba74ea))

- **19.3-05**: Update E3's and E5's hardcoded depth_range=(1.1, 2.0) call sites
  ([`5235d1b`](https://github.com/McGrathLab/AquaCal/commit/5235d1b71d40b39c3b46179be3b073228482cf6c))

- **19.3-06**: Anchor E6 scale axis at the derived clearance floor
  ([`af892c3`](https://github.com/McGrathLab/AquaCal/commit/af892c39f498ec4f8865af112dfac16555c8da0e))

- **19.4**: Make the inertness gate honour its own contract
  ([`0e40cae`](https://github.com/McGrathLab/AquaCal/commit/0e40cae0019f9d82e37c47c8d12b320c03d87781))

- **19.4-02**: Relocate generate_camera_array jitter from water_z to C_z
  ([`091e97d`](https://github.com/McGrathLab/AquaCal/commit/091e97dbbda2a3d07a9eadc2fb55ae329430aad5))

- **19.4-02**: Stop the anchor generator destroying its own provenance chain
  ([`10fe32e`](https://github.com/McGrathLab/AquaCal/commit/10fe32e55bb4caee14f32cec96b371a9fc46b2c9))

- **19.4-03**: Correct coverage matrix YES/PARTIAL arithmetic (10/2, not 11/1)
  ([`999fbc2`](https://github.com/McGrathLab/AquaCal/commit/999fbc2ac6049337ed1dfbd4a75ffc7ef97cc1ed))

- **19.5-09**: ARCHIVES_PRESENT reports N/A when it can prove its premise absent
  ([`98930bf`](https://github.com/McGrathLab/AquaCal/commit/98930bf59f8136cf3fd4b2a5b4441f00836d8a02))

- **19.5-09**: Defer legality_probe's aquacal imports to call time
  ([`4885568`](https://github.com/McGrathLab/AquaCal/commit/48855683e1002c2a0781a8f775b00882e739282b))

- **19.5-09**: Queue's own probe reads the seed list; un-ignore the queue log
  ([`2a2f0fa`](https://github.com/McGrathLab/AquaCal/commit/2a2f0faccef4eca243d027023e44e047041a4a1c))

- **19.5-09**: Six-seed bands, single-source seed list, dry-run state isolation
  ([`ac0928d`](https://github.com/McGrathLab/AquaCal/commit/ac0928d2f95bf1847fa0a149df51781a94d6e704))

- **19.5-10**: The seed-band gates expected five seeds, the run produced six
  ([`8093547`](https://github.com/McGrathLab/AquaCal/commit/8093547623123fad47017ec050d53c8c69f0d3d9))

- **21**: Add blank line before bullet list in generate_board_trajectory docstring
  ([`83b59e5`](https://github.com/McGrathLab/AquaCal/commit/83b59e507eb7c678264f2ce195f03c9fb308bd18))

- **21-01**: Add --per-camera mode so intrinsic extraction is not truncated
  ([`aeaa29d`](https://github.com/McGrathLab/AquaCal/commit/aeaa29dbfd58b1261a9ad605b72959fe39217f53))

- **21-01**: Write frames at maximum PNG compression
  ([`2132854`](https://github.com/McGrathLab/AquaCal/commit/2132854ba6a16a84ec46ce68eed3907f106e1328))

- **21-02**: Retag trace CSV fence to avoid Pygments highlighting failure
  ([`0040484`](https://github.com/McGrathLab/AquaCal/commit/0040484b9db67e703573511270a22920c0638a7e))

- **21-08**: Correct aquacal compare output filenames in the CLI walkthrough
  ([`57976b9`](https://github.com/McGrathLab/AquaCal/commit/57976b90348a4e3f3fd679d59e95b927f0e3f472))

- **21-08**: Resolve both pre-publish blockers -- MF-19 and reference_outputs
  ([`2a8a8ce`](https://github.com/McGrathLab/AquaCal/commit/2a8a8ce9a3a22abe7279313be9fb10e25b875f53))

- **calibration**: Keep a gradient where the refractive model cannot project
  ([`7e0cb90`](https://github.com/McGrathLab/AquaCal/commit/7e0cb9072028b3247b6745498328d1a19fb0350a))

- **cli**: Make --output-dir actually apply to the calibration run
  ([`1b1b4c2`](https://github.com/McGrathLab/AquaCal/commit/1b1b4c2b0369a75a7a9979fcd2b056ad3397c891))

- **config**: Default interface.normal_fixed to false and drop initial_distances
  ([`cee18f6`](https://github.com/McGrathLab/AquaCal/commit/cee18f6400fb1a5d85662b0943002dc5b08fe28e))

- **deps**: Pin opencv-python below 5.0
  ([`eb6dd96`](https://github.com/McGrathLab/AquaCal/commit/eb6dd96fe2b856ad9f44994dd8915bed86be6b22))

- **e4**: Measure whether a cell fits instead of predicting it
  ([`a17331e`](https://github.com/McGrathLab/AquaCal/commit/a17331e22e6a94fe6cbdeff12dea65081ef5ec94))

- **e4**: Remove the per-cell timeout whose derivation no longer holds
  ([`c511429`](https://github.com/McGrathLab/AquaCal/commit/c511429e3fcd6b4e052a1362f44965d1c12f7f33))

### Build System

- Require Python >=3.11 and correct release metadata for 2.0.0
  ([`d19b3af`](https://github.com/McGrathLab/AquaCal/commit/d19b3afebbfafffc6b165a0c7fdce6028564a340))

### Chores

- **19.1**: Disable auto_advance so the chain stops before execute
  ([`556206c`](https://github.com/McGrathLab/AquaCal/commit/556206c6160861701d9ab7376d54b35e2d899593))

- **19.2**: Add the D-36 seed sweep driver and its paired analysis
  ([`5721314`](https://github.com/McGrathLab/AquaCal/commit/5721314b2daed5ea31f81809eed0f93bcdea7560))

- **19.2**: Correct STATE's stopped_at before wave 6 dispatch
  ([`5b49ffd`](https://github.com/McGrathLab/AquaCal/commit/5b49ffd277a48e728594dc27b011a14d5085ddd7))

- **19.2-06**: Refresh E2's section-3 record on guarded code
  ([`faa05b3`](https://github.com/McGrathLab/AquaCal/commit/faa05b38b65a2652266d6916c9f3784de713abcd))

- **19.4-09**: Commit regenerated experiment artifacts from the production queue
  ([`0ffbe15`](https://github.com/McGrathLab/AquaCal/commit/0ffbe15b4ade4398645fe162ca9afe12b3489af8))

- **19.5-10**: Commit E2/E4 band evidence, ignore the regenerable bulk
  ([`20ba83d`](https://github.com/McGrathLab/AquaCal/commit/20ba83dd9f80d508877d79e27a37977d339f7901))

- **19.5-10**: Commit the production queue's artifacts under one frozen sha
  ([`d007de7`](https://github.com/McGrathLab/AquaCal/commit/d007de73340466dbe13f18145a8fbaebe5da19e7))

- **260807-dcv**: E7's band sidecar -- gate4_band category now fully closed
  ([`f8a2bbd`](https://github.com/McGrathLab/AquaCal/commit/f8a2bbd74085c73a914019c55254ea4d70121ba9))

- **260807-dcv**: Regenerate E1's band with z_rmse_mm and its own sidecar
  ([`fea64a9`](https://github.com/McGrathLab/AquaCal/commit/fea64a9dda0e5d437d55f2df950e1ecf0ab0b3e1))

- **e2**: Archive the pre-PnP-guard Section-3 baseline
  ([`117bad7`](https://github.com/McGrathLab/AquaCal/commit/117bad7410b9476dde61211f1109dbeeb425078a))

### Documentation

- Add MF-02 (E4 memory curve does not bound real deployments) and MF-01 provenance caveat
  ([`3ed4e37`](https://github.com/McGrathLab/AquaCal/commit/3ed4e371df1fd379ff2028866beb8e15ac986374))

- Add three todos raised while monitoring the 19.4 queue
  ([`d9d057a`](https://github.com/McGrathLab/AquaCal/commit/d9d057a93db305cccbb60911c0b3068bca61fd4f))

- Correct guide, tutorial and experiment claims against the code
  ([`f45d278`](https://github.com/McGrathLab/AquaCal/commit/f45d27883f116b3ef1d908ce958b1fbc46ec70d1))

- Correct stale 100px-penalty claims and record the root-cause session
  ([`0cb8e56`](https://github.com/McGrathLab/AquaCal/commit/0cb8e56aeef2dbeb5110c8689a45e0cf7b7a5539))

- Create milestone v1.9 roadmap (7 phases)
  ([`a12d6a7`](https://github.com/McGrathLab/AquaCal/commit/a12d6a7cf751e2b80e3da0df4107f41027a157ee))

- Cross-AI review for phase 19.2
  ([`5454cfe`](https://github.com/McGrathLab/AquaCal/commit/5454cfe0036bec995206c4991a360dcc108e0671))

- Define milestone v1.9 requirements
  ([`71db341`](https://github.com/McGrathLab/AquaCal/commit/71db3416b9c02da308544a8c3f6b6f834591753a))

- Fold Zenodo dataset refresh into Post-Review Updates milestone
  ([`10eed6b`](https://github.com/McGrathLab/AquaCal/commit/10eed6b762b6612158ff540c25a168a45d7e5503))

- Insert Phase 19.4 for the grid-family clearance floor fix
  ([`c83bd0d`](https://github.com/McGrathLab/AquaCal/commit/c83bd0d1e87597d7934299415f275094ad9b43ef))

- Keep DOCS-01 in the docs phase
  ([`04a1256`](https://github.com/McGrathLab/AquaCal/commit/04a1256cc9004cf84fefaebc0b30b2943ed5d46a))

- Reconcile todo backlog after v1.6-v1.8 drift
  ([`f2503d0`](https://github.com/McGrathLab/AquaCal/commit/f2503d081ea686b033fd10c7f9d07e2132e81317))

- Record the backgrounded-executor stall and the untracked-.claude finding
  ([`abf7cdf`](https://github.com/McGrathLab/AquaCal/commit/abf7cdf541ee5df011972c94ab54723abfef2cd7))

- Record the executor-stall root cause and move full-suite runs to the post-merge gate
  ([`d01b36b`](https://github.com/McGrathLab/AquaCal/commit/d01b36bab9399615bd7b9570907fa31c0f374413))

- Record the per-camera water surface defect before context clear
  ([`bae8b2b`](https://github.com/McGrathLab/AquaCal/commit/bae8b2b59bd63d7966d81b419c53c08f09b0fc3b))

- Record Zenodo dataset findings and correct severity
  ([`89a4b5a`](https://github.com/McGrathLab/AquaCal/commit/89a4b5afd709e47b705644c0f23704020a73283c))

- Refresh milestone handoff, retire stale phase-18 continue-here
  ([`f3a32e6`](https://github.com/McGrathLab/AquaCal/commit/f3a32e634b1626f5493ce5b9f065a389e31f6e1e))

- Replace PERF-01's unmeasured 3.6 GB estimate with the measured 10.26 GiB peak
  ([`82d7935`](https://github.com/McGrathLab/AquaCal/commit/82d79353c88b5d6ac4696c029a23795d6efd4120))

- Start milestone v1.9 Publication Prep
  ([`c003689`](https://github.com/McGrathLab/AquaCal/commit/c003689a20ce4e453cfedd1a3fa96aee791ec781))

- **16**: Add phase research with conditioning-route addendum
  ([`3a4e88d`](https://github.com/McGrathLab/AquaCal/commit/3a4e88dcaddd127c48adda09d6bc094976fea479))

- **16**: Capture phase context
  ([`5577aa4`](https://github.com/McGrathLab/AquaCal/commit/5577aa4cf251a3caf154a45b04c19392584ebbfa))

- **16**: Create phase plan
  ([`2759dd5`](https://github.com/McGrathLab/AquaCal/commit/2759dd534da1cd0643c2f651f27949ff80226115))

- **16-01**: Complete conditioning diagnostics plan
  ([`bca3d04`](https://github.com/McGrathLab/AquaCal/commit/bca3d042b15a1572c83084045bf2aabd6da9d708))

- **16-02**: Complete synthetic sweep-axis support plan
  ([`238a65b`](https://github.com/McGrathLab/AquaCal/commit/238a65b352172664cee1f4293a40db09f5597ffc))

- **16-03**: Complete observability config foundation plan
  ([`e62294e`](https://github.com/McGrathLab/AquaCal/commit/e62294e256d207127acd95250300ec1c3952f477))

- **16-04**: Complete optimizer observability trace plan
  ([`e3dfc5b`](https://github.com/McGrathLab/AquaCal/commit/e3dfc5bfa051d6a090d4f963f779469ee7c65ab5))

- **16-05**: Complete wire-conditioning-into-pipeline plan
  ([`ede0e84`](https://github.com/McGrathLab/AquaCal/commit/ede0e840d2f119e893489d84fcf047c875391bb1))

- **16-06**: Complete seed threading & recording plan
  ([`a0bf953`](https://github.com/McGrathLab/AquaCal/commit/a0bf9531a960559d08b513001972733a49c085ce))

- **16-07**: Complete standalone held-out evaluation plan
  ([`7a984ec`](https://github.com/McGrathLab/AquaCal/commit/7a984ecdf549a6f47aa8335010e86c467bc4e3a3))

- **17**: Capture phase context
  ([`362ab3b`](https://github.com/McGrathLab/AquaCal/commit/362ab3b4f376ab2065d2eb095172ea621d863aa9))

- **17**: Create phase plan
  ([`3740a05`](https://github.com/McGrathLab/AquaCal/commit/3740a055d084a7830ee48b1f6ad55178a9521f7c))

- **17**: Revise plans per checker feedback (IFACE-04 loader gate)
  ([`2353563`](https://github.com/McGrathLab/AquaCal/commit/23535633c848529c62fcae2c31e5db72cab7f0eb))

- **17-01**: Complete per-camera water_z packing layer plan
  ([`6284ff2`](https://github.com/McGrathLab/AquaCal/commit/6284ff2ed9c7acc89d873cd910c4811eae37e345))

- **17-02**: Complete shared_interface config surface plan
  ([`07cea1c`](https://github.com/McGrathLab/AquaCal/commit/07cea1cdb52d82807a5397b44c57b4a9b80033d5))

- **17-03**: Complete optimizer + pipeline integration plan
  ([`b75e6e4`](https://github.com/McGrathLab/AquaCal/commit/b75e6e4c73601402fb870af6ca544d1b6997cbef))

- **17-04**: Complete seed resolver + spread report plan
  ([`4fe5a5d`](https://github.com/McGrathLab/AquaCal/commit/4fe5a5dcf6da3e884da86edbf6decade43d88858))

- **17-05**: Complete IFACE-05 correctness safety net plan
  ([`7c82ee1`](https://github.com/McGrathLab/AquaCal/commit/7c82ee1b262d11ae9297c170dbd4730bc3a3283e))

- **18**: Address code-review findings and correct a false summary claim
  ([`a5d1657`](https://github.com/McGrathLab/AquaCal/commit/a5d1657b97ab5130e51ff85a5e2629cc9a76b6fe))

- **18**: Capture phase context
  ([`102acad`](https://github.com/McGrathLab/AquaCal/commit/102acad6828749ba004a7496607705659b8ad9e9))

- **18**: Clear stale wording from re-check warnings
  ([`5f24d71`](https://github.com/McGrathLab/AquaCal/commit/5f24d719f23f93ca2e60329587ca257d5fbd30f6))

- **18**: Create phase plan
  ([`313be21`](https://github.com/McGrathLab/AquaCal/commit/313be2129c9405bde0be20f5e144c384783d5510))

- **18**: Create phase plan
  ([`3296cd3`](https://github.com/McGrathLab/AquaCal/commit/3296cd3e67092512edca57ce90c98126aeb0a9a0))

- **18**: Port the located supplement figure generator into plan 18-04
  ([`387208f`](https://github.com/McGrathLab/AquaCal/commit/387208fb355825f8a3ad083e8bcd89b24d29154f))

- **18**: Propagate D-05 and D-23 wording across plans 06-08
  ([`408a72c`](https://github.com/McGrathLab/AquaCal/commit/408a72c4d6c84df5c993df50cd5318c43c5260fe))

- **18**: Reconcile phase plans with the live manuscript source
  ([`ec467c7`](https://github.com/McGrathLab/AquaCal/commit/ec467c7d523eeec2755e01fcfa8572b9359d092c))

- **18**: Research phase domain - re-derive DOCS-01 numbers, surface manuscript BFS/stage-vocabulary
  contradiction
  ([`c5bcf0b`](https://github.com/McGrathLab/AquaCal/commit/c5bcf0b83d19f9f4029f773d31628170135bdb51))

- **18-01**: Add plan summary
  ([`81f93d4`](https://github.com/McGrathLab/AquaCal/commit/81f93d47b9f27dfa72ee4f749e233cb633c7ecbe))

- **18-01**: Append self-check results to summary
  ([`cd4c5ba`](https://github.com/McGrathLab/AquaCal/commit/cd4c5ba286ba9e860f08e5f5b5ebb5708bb6890d))

- **18-01**: Correct four numeric errors in sparse-Jacobian section
  ([`f1fbfb9`](https://github.com/McGrathLab/AquaCal/commit/f1fbfb95b4c6dd85a65c964d3106b6f499f576cc))

- **18-02**: Record confirmed stage/traversal vocabulary contract
  ([`08879fb`](https://github.com/McGrathLab/AquaCal/commit/08879fb0611e69dbcef65cfac10d2124a0d43ad7))

- **18-03**: Complete configuration reference plan
  ([`967602e`](https://github.com/McGrathLab/AquaCal/commit/967602e00e327709b220a75108168b29df36d12b))

- **18-03**: Create docs/guide/configuration.md reference page
  ([`6c94edf`](https://github.com/McGrathLab/AquaCal/commit/6c94edfe2fa62e4bacc5bf0cc8ed0c8a6d539fb1))

- **18-03**: Cross-link troubleshooting to the configuration reference
  ([`1dd5b95`](https://github.com/McGrathLab/AquaCal/commit/1dd5b9513f3b0748075d98fffcd24e48130f5de6))

- **18-03**: Register configuration.md in guide index toctree
  ([`07818ce`](https://github.com/McGrathLab/AquaCal/commit/07818cebc14186d7b38488418de2338888e431ec))

- **18-04**: Add partial summary — checkpoint pending at Task 3
  ([`1505d2b`](https://github.com/McGrathLab/AquaCal/commit/1505d2b8d797d1291c5c3019e20dbfe3add02802))

- **18-04**: Cut over to the regenerated pose_graph.png and fix glossary
  ([`9ae1f55`](https://github.com/McGrathLab/AquaCal/commit/9ae1f55094f7bb2ce31a1e6bdf1f9db1bd0aefef))

- **18-04**: Finalize summary — Task 3 checkpoint approved
  ([`d7e2e58`](https://github.com/McGrathLab/AquaCal/commit/d7e2e58ab81ef4e394ab564628449776db0437aa))

- **18-04**: Preserve discovery direction through to the drawn arrows
  ([`0be6b78`](https://github.com/McGrathLab/AquaCal/commit/0be6b78ffe1f40d687e79af0f9dfe0a90a44ffcd))

- **18-04**: Replace hardcoded BFS pose-graph generator with heap replay
  ([`f93e0e8`](https://github.com/McGrathLab/AquaCal/commit/f93e0e839dd964b11d0170ee4bb87fec0c3af202))

- **18-04**: Update partial summary with checkpoint round 1 findings
  ([`fd1b856`](https://github.com/McGrathLab/AquaCal/commit/fd1b856affec5b581ab01077e7f7f525de6757ff))

- **18-05**: Add plan 05 execution summary
  ([`d9c6640`](https://github.com/McGrathLab/AquaCal/commit/d9c6640ef8decf37d0e910939ec654718ea86304))

- **18-05**: Correct BFS terminology to best-first in estimate_extrinsics
  ([`bfee0ad`](https://github.com/McGrathLab/AquaCal/commit/bfee0ada979a7d8a97e158ab8c39e781aed03538))

- **18-05**: Fix misleading neighbour-scoring comments, document invariant
  ([`4d33261`](https://github.com/McGrathLab/AquaCal/commit/4d33261d275b556cb2d00e7c53eaafb1d5414f09))

- **18-06**: Complete pipeline stage-model rename plan
  ([`cffd653`](https://github.com/McGrathLab/AquaCal/commit/cffd65314cb0ec87a24fa295cc1f2fb9320859a8))

- **18-07**: Add plan summary
  ([`cf27941`](https://github.com/McGrathLab/AquaCal/commit/cf27941a2d331caf567830b54fe64f4518817660))

- **18-07**: Correct remaining module and stage-tag docstrings
  ([`6d6fdbc`](https://github.com/McGrathLab/AquaCal/commit/6d6fdbc83f47bf1e39286345b74b9c90108d07e9))

- **18-07**: Correct user-facing config surfaces to three-stage model
  ([`8ef1556`](https://github.com/McGrathLab/AquaCal/commit/8ef1556a494e2e679412a163a736e6892e78307a))

- **18-07**: Fix stray Stage 3/4 comment in intrinsics.py
  ([`050a547`](https://github.com/McGrathLab/AquaCal/commit/050a547f881aa7cf4243d5cca54f3e777e015dc7))

- **18-08**: Add plan summary
  ([`16468b1`](https://github.com/McGrathLab/AquaCal/commit/16468b130bf7460e9bb300e6a030abc15dd985af))

- **18-08**: Collapse troubleshooting.md's Stage 3/4 phrasings to Stage 3
  ([`6376553`](https://github.com/McGrathLab/AquaCal/commit/6376553726dcaa460287a3879b07eb8f30a81475))

- **18-08**: Record self-check result in plan summary
  ([`79c6ab9`](https://github.com/McGrathLab/AquaCal/commit/79c6ab93465c51501b329a80c965336f63962209))

- **18-08**: Rewrite optimizer.md to the three-stage model and fix the loss formula
  ([`55d07fd`](https://github.com/McGrathLab/AquaCal/commit/55d07fd2562c1f56ade08e76fbd23eb5d137587c))

- **18-08**: Sweep remaining doc pages, API reference, and README to three-stage/best-first
  ([`8971c61`](https://github.com/McGrathLab/AquaCal/commit/8971c6113e1f6737d90ef04bec92ad5d6670fc1f))

- **19**: Add BENCH-06 explicit solver tolerance requirement
  ([`13d28dd`](https://github.com/McGrathLab/AquaCal/commit/13d28dd062ae1f27e2a11e80a6d7c938f05b7735))

- **19**: Capture phase context
  ([`9eeff71`](https://github.com/McGrathLab/AquaCal/commit/9eeff714fa073a89622635f6f76ad026c6f2be83))

- **19**: Correct njev research claim and add D-18 per-stage memory
  ([`eef4667`](https://github.com/McGrathLab/AquaCal/commit/eef4667ad39a0254ec387fe32c1ca2d8867f065b))

- **19**: Create phase plan
  ([`9bae88c`](https://github.com/McGrathLab/AquaCal/commit/9bae88c581c713e12d4283f5856486ca8866aa85))

- **19**: Research benchmark instrumentation phase
  ([`b4a26f1`](https://github.com/McGrathLab/AquaCal/commit/b4a26f1ed4ef9c27aac6b2bae387ef1747827912))

- **19**: Research phase 19 and revise D-02 after findings
  ([`e95219c`](https://github.com/McGrathLab/AquaCal/commit/e95219ca1c65317deb8ffbbc63c7a7d38688dae1))

- **19**: Revise plan set for plan-check blockers (D-18, njev correction)
  ([`f1e4468`](https://github.com/McGrathLab/AquaCal/commit/f1e44680168e7d9b82aff336f84c8be931595ad9))

- **19-01**: Complete solver diagnostics contract plan
  ([`5715fef`](https://github.com/McGrathLab/AquaCal/commit/5715fef6829a9be482706c659a42d075c825696e))

- **19-02**: Add plan 02 summary
  ([`001acfc`](https://github.com/McGrathLab/AquaCal/commit/001acfc5a4a25df207073aaa8b6449a658ddf39f))

- **19-03**: Add plan 03 summary
  ([`6cf0b97`](https://github.com/McGrathLab/AquaCal/commit/6cf0b975b052427b4f333b52608eef2d567f773f))

- **19-04**: Add plan 04 summary
  ([`a3cb96f`](https://github.com/McGrathLab/AquaCal/commit/a3cb96f12b441c1ae2ae351a0aa1b34a9f7fd531))

- **19-05**: Add plan 05 execution summary
  ([`bf15f6d`](https://github.com/McGrathLab/AquaCal/commit/bf15f6dbb051a3bc0655f57c1a83134403d1e8e1))

- **19-06**: Add plan 06 execution summary
  ([`7e35b3a`](https://github.com/McGrathLab/AquaCal/commit/7e35b3a89d0d9b024792209f995a91fc20b66939))

- **19-06**: Warn when a table mixes memory.mode values
  ([`c9cb238`](https://github.com/McGrathLab/AquaCal/commit/c9cb238c1a3b3849a42c4bbf0ad31fa79a529516))

- **19.1**: Add DATA-01b -- move large artifacts into the Zenodo archive
  ([`2b24add`](https://github.com/McGrathLab/AquaCal/commit/2b24adda2253a1a05d8039caee9b30e48b37d67b))

- **19.1**: Add research and validation strategy
  ([`93cb1f3`](https://github.com/McGrathLab/AquaCal/commit/93cb1f37339091fd137c9e79b222b1c4c48c6131))

- **19.1**: Apply reviewed amendments to plans 01 and 06
  ([`bbebaa0`](https://github.com/McGrathLab/AquaCal/commit/bbebaa015236f607c8936e6af77ad3162270742a))

- **19.1**: Begin phase execution
  ([`42bc1c5`](https://github.com/McGrathLab/AquaCal/commit/42bc1c59b5e884fe7d70ed5c684ae3472e7b4bab))

- **19.1**: Capture phase context
  ([`eac37df`](https://github.com/McGrathLab/AquaCal/commit/eac37dfc1f4369b7b981f67c1397896fe67f8d17))

- **19.1**: Create phase plan
  ([`411b16e`](https://github.com/McGrathLab/AquaCal/commit/411b16e313c2f14616938d33a48f6273c52f3ac4))

- **19.1**: Create phase plan
  ([`1c8212f`](https://github.com/McGrathLab/AquaCal/commit/1c8212ffff0a5801e9158a584d2e83a73c8d551a))

- **19.1**: Record user review of the five flagged decisions
  ([`787df9b`](https://github.com/McGrathLab/AquaCal/commit/787df9b89d9e7632ad67c7c8c4c8d0aa45db2292))

- **19.1**: Track Zenodo frameset regeneration as DATA-01a publication blocker
  ([`3f37308`](https://github.com/McGrathLab/AquaCal/commit/3f37308dfdcc1e5376b7ba47dab64c958a544b01))

- **19.1-01**: Complete plan 01 summary
  ([`d964a84`](https://github.com/McGrathLab/AquaCal/commit/d964a848070b568b63a69ee69224880e4447ed4f))

- **19.1-02**: Append self-check result to plan summary
  ([`daeada7`](https://github.com/McGrathLab/AquaCal/commit/daeada74849c7d4f703dc42acdc77fe2b5d98bb3))

- **19.1-02**: Complete experiment suite package relocation plan
  ([`7fe0250`](https://github.com/McGrathLab/AquaCal/commit/7fe02508ce38f8c847b92b60bab850bc644c1822))

- **19.1-03**: Add plan 03 summary
  ([`495f757`](https://github.com/McGrathLab/AquaCal/commit/495f757ab6c29db0003079b6e0083be8ca284070))

- **19.1-04**: Complete E2 real-rig plan summary
  ([`5843162`](https://github.com/McGrathLab/AquaCal/commit/584316209356354ff011a4e248681646b1096580))

- **19.1-04**: Establish E2 frameset provenance, correct delta-table conclusion
  ([`b816398`](https://github.com/McGrathLab/AquaCal/commit/b8163984b2ce946b90e6d086676fb0aa4ea80a8c))

- **19.1-04**: Rebuild E2 delta table as a like-for-like comparison
  ([`609c91c`](https://github.com/McGrathLab/AquaCal/commit/609c91c03d4fee7a0bbd317fe38493a647f9ccf4))

- **19.1-04**: Record archive-vs-manuscript options and sequencing
  ([`026ffd0`](https://github.com/McGrathLab/AquaCal/commit/026ffd07448740def5be022f2a83bde50eb4711f))

- **19.1-04**: Resolve A3 -- E2 dataset findings and spatial_measurements.csv verdict
  ([`517b90f`](https://github.com/McGrathLab/AquaCal/commit/517b90f337887fdf1ff73d52ee636baee6f8a266))

- **19.1-05**: Complete E7 interface ablation summary
  ([`bb695cb`](https://github.com/McGrathLab/AquaCal/commit/bb695cb08149fef8cbae906c072c37da113cd270))

- **19.1-06**: Add plan 06 summary
  ([`4e02ded`](https://github.com/McGrathLab/AquaCal/commit/4e02dedef2cd7bb59248c6efe6892b3cf2d30594))

- **19.1-06**: Record user clearance of the E1 deletion gate
  ([`f193d60`](https://github.com/McGrathLab/AquaCal/commit/f193d60bd13bd61eb51b1b86a9fb632951ca9940))

- **19.1-06**: Seed committed E1 baseline CSVs from DissertationFigures
  ([`867ae2c`](https://github.com/McGrathLab/AquaCal/commit/867ae2cdb8cb875e9f2d4e7923e0e1fa86a4b8de))

- **19.1-06**: Write E1 reproduce-or-explain record -- no escalation
  ([`3d23ddd`](https://github.com/McGrathLab/AquaCal/commit/3d23ddd757d474e974d10d96bccd506d7b564f78))

- **19.1-07**: Add plan 07 summary
  ([`8daa93c`](https://github.com/McGrathLab/AquaCal/commit/8daa93ce6fbe77bbe7868c22b24857416ddf952e))

- **19.1-07**: Delete notebook export cells, sweep stale experiments/ paths
  ([`d65dac6`](https://github.com/McGrathLab/AquaCal/commit/d65dac6a6253539af4e134d6b44fee7a12bee95d))

- **19.1-07**: Write experiments/README.md and add the experiments-smoke CI job
  ([`3d88670`](https://github.com/McGrathLab/AquaCal/commit/3d88670021e76c5fe65c451b61a37ebfb31aeb7d))

- **19.1-08**: Record user response to the E2 blocking gate
  ([`785e8fd`](https://github.com/McGrathLab/AquaCal/commit/785e8fdc22bcbf60196e8259da1d8bdcbd9f4544))

- **19.1-08**: Resolve the section-3 provenance caveat against the live manuscript
  ([`ec881be`](https://github.com/McGrathLab/AquaCal/commit/ec881be648f250bf6befaa814169fddaa6485897))

- **19.2**: Add code review report
  ([`d02b296`](https://github.com/McGrathLab/AquaCal/commit/d02b296928a96eb0cf58ffcd447a1e752f6e4d10))

- **19.2**: Add D-24/D-25 from pattern mapping; fix test-file path
  ([`5762d6d`](https://github.com/McGrathLab/AquaCal/commit/5762d6d3372fd3b26bf1d98e4ef7e4f41cbe739d))

- **19.2**: Add D-33 OOM guard requirements to gap context
  ([`79f1c47`](https://github.com/McGrathLab/AquaCal/commit/79f1c4785929a7189626c3e71b0c20ec607db3a8))

- **19.2**: Add gap wave map, D-26 reconciliation, and E5 re-run correction
  ([`e46a370`](https://github.com/McGrathLab/AquaCal/commit/e46a37060c9a108af683c268cf214ac64e347ab0))

- **19.2**: Add phase verification report (gaps_found, 5/7)
  ([`3fea569`](https://github.com/McGrathLab/AquaCal/commit/3fea56936bd78b84bf577c4f6b31c4e463fb06ad))

- **19.2**: Amend context after research -- D-03/D-11 anchor, D-23 n_true wiring
  ([`2502469`](https://github.com/McGrathLab/AquaCal/commit/250246914fde9318b667ea70a3739d0003ba0084))

- **19.2**: Amend D-14/D-15 -- accuracy block not copyable, n_residuals absent
  ([`973ecbb`](https://github.com/McGrathLab/AquaCal/commit/973ecbbd5baa93cc55e040aca677c99e1bffe2ab))

- **19.2**: Amend D-36 to the paired criterion and queue seeds 47-51
  ([`3d0aa3e`](https://github.com/McGrathLab/AquaCal/commit/3d0aa3e4a7e61f0d3fb34b5fdd52a629a625f813))

- **19.2**: Amend plans 06/22/23/24 under D-35 without loosening a gate
  ([`afbe063`](https://github.com/McGrathLab/AquaCal/commit/afbe063c99c7703d2c50e11cca01c57552016dd9))

- **19.2**: Answer the open question — the fix is a trade, not a free win
  ([`55735d6`](https://github.com/McGrathLab/AquaCal/commit/55735d6d1433cef08f07fafc98fca7e7871ddafc))

- **19.2**: Capture phase context
  ([`f71981e`](https://github.com/McGrathLab/AquaCal/commit/f71981e450953ed59d5afc2e8dcf64cac5794b77))

- **19.2**: Correct STATE.md to gap wave 3 (plan 19.2-21) before dispatch
  ([`35d76a6`](https://github.com/McGrathLab/AquaCal/commit/35d76a6828550a5a81d47e7eb820f9e34cdb2fe3))

- **19.2**: Correct the regression claim — the deltas are seed noise
  ([`46cb4cb`](https://github.com/McGrathLab/AquaCal/commit/46cb4cbd49258ad6560b6f82ea73955a2cb097ae))

- **19.2**: Correct validation sign-off -- four guards, approved
  ([`f52c819`](https://github.com/McGrathLab/AquaCal/commit/f52c819f3c74305c82f93c49d7323ace7ce86418))

- **19.2**: Create phase plan
  ([`632ee54`](https://github.com/McGrathLab/AquaCal/commit/632ee5417acb9a750d8d53aa69cd3626db4d35d8))

- **19.2**: Create phase plan -- 12 plans in 5 waves
  ([`8330740`](https://github.com/McGrathLab/AquaCal/commit/8330740f508297d2a1b92372748d2bea9e555a75))

- **19.2**: D-32 resolved — instrument the batch Newton path (option c)
  ([`130fa28`](https://github.com/McGrathLab/AquaCal/commit/130fa288f161e81658d263617684738d1f51c691))

- **19.2**: E7 delta is noise too — but its refined arms swing 10mm across seeds
  ([`f6b389d`](https://github.com/McGrathLab/AquaCal/commit/f6b389d61415b670bd51e226ad9fd97453aea2ec))

- **19.2**: Fix a contradiction and add next actions to the handoff
  ([`e4bce72`](https://github.com/McGrathLab/AquaCal/commit/e4bce724b16f8ea555b9244ebf1be8580d50a28f))

- **19.2**: Gap-closure context — D-27..D-32 geometry redesign and provenance backfill
  ([`e94e2d6`](https://github.com/McGrathLab/AquaCal/commit/e94e2d689657de87c7bb4219d6755253126e9d22))

- **19.2**: Gap-closure plans 15-25 across six waves
  ([`294fb8d`](https://github.com/McGrathLab/AquaCal/commit/294fb8d2c4ed2c218c36ce0919ed14eac047c8c7))

- **19.2**: Make threat IDs globally unique, mark RESEARCH open questions resolved
  ([`61ae310`](https://github.com/McGrathLab/AquaCal/commit/61ae31085f1eca1294da78537b607bb7dd4dff10))

- **19.2**: Mark phase execution start
  ([`e1d6548`](https://github.com/McGrathLab/AquaCal/commit/e1d6548dbe807eb0abc0d0e8f8c1f9c0065d7477))

- **19.2**: Mark the handoff complete and redirect it to phase 19.3
  ([`0193959`](https://github.com/McGrathLab/AquaCal/commit/0193959be51df901b62e4a9b7704305eb49a0e1c))

- **19.2**: Overnight handoff — fixes, blast radius, and the completed grid
  ([`4c407fb`](https://github.com/McGrathLab/AquaCal/commit/4c407fb24bb377f71b0ab12f95008551745e4c03))

- **19.2**: Plan gap closure — 11 plans (19.2-15..25) across 6 waves
  ([`bb6757a`](https://github.com/McGrathLab/AquaCal/commit/bb6757a8c61fabd8dabdc74861a4213d2aa38d45))

- **19.2**: Plan the close-out of all four disclosed defects
  ([`68e097d`](https://github.com/McGrathLab/AquaCal/commit/68e097dc7c12593c8fdef4059ca0a93922a4562f))

- **19.2**: Re-verify after waves 8-9 -- 7/7 truths hold, new finding needs human decision
  ([`80ac3f7`](https://github.com/McGrathLab/AquaCal/commit/80ac3f7654f2113298ec366996913e0b799a12c7))

- **19.2**: Re-verify phase 19.2 — both prior gaps closed, status verified
  ([`b53c6a9`](https://github.com/McGrathLab/AquaCal/commit/b53c6a9baaa5f58be72a00817574e2caff92f047))

- **19.2**: Record D-26 -- all src changes precede any publishable experiment
  ([`8c70d34`](https://github.com/McGrathLab/AquaCal/commit/8c70d34c15f8bb323b398090ae446996c91adba3))

- **19.2**: Record decisions D-34/D-35/D-36 in the handoff
  ([`07ab4da`](https://github.com/McGrathLab/AquaCal/commit/07ab4daed5da67ace860e8528cb8f8828b7d4497))

- **19.2**: Record MF-01 -- supplement understates Newton iteration tail
  ([`dd0d97b`](https://github.com/McGrathLab/AquaCal/commit/dd0d97b9daa556a0327dfe6b374eee7c7b90a2e4))

- **19.2**: Record MF-02..MF-06 and refresh the handoff to the sweep result
  ([`3d5c3e6`](https://github.com/McGrathLab/AquaCal/commit/3d5c3e61bce15bd8e4daaecaccb8802a3c1675e0))

- **19.2**: Record the E6 convergence finding where readers actually look
  ([`6b71bfe`](https://github.com/McGrathLab/AquaCal/commit/6b71bfe77472d596105f6d8d3f7e98657d99d582))

- **19.2**: Record the one red test left by plan 23's regeneration
  ([`8d412a5`](https://github.com/McGrathLab/AquaCal/commit/8d412a50013a651f3516c960cd918b55a61fc001))

- **19.2**: Record wave 3 as superseded and the fix blast radius
  ([`ff320f1`](https://github.com/McGrathLab/AquaCal/commit/ff320f1fc5ef936132990567919f421503450461))

- **19.2**: Replan for D-26 -- 14 plans in 8 waves, src changes precede all results
  ([`1f35388`](https://github.com/McGrathLab/AquaCal/commit/1f353885266378d2506c1dac40b66c9184a4bc56))

- **19.2**: Replan from cross-AI review -- 13 plans in 7 waves
  ([`3b3024c`](https://github.com/McGrathLab/AquaCal/commit/3b3024cc6eecbbf66705ba1841aecf8e409c293f))

- **19.2**: Update roadmap tally to 0/14 planned
  ([`b83f8ea`](https://github.com/McGrathLab/AquaCal/commit/b83f8eae2a38023885ffbf34d20ee4679392e3bb))

- **19.2-01**: Complete calibrate_synthetic memory/index/tilt threading plan
  ([`a3b0001`](https://github.com/McGrathLab/AquaCal/commit/a3b0001e230056e5eb6907a9a43394d2acca91f7))

- **19.2-02**: Add plan 02 execution summary
  ([`38872d2`](https://github.com/McGrathLab/AquaCal/commit/38872d2fb747024eabeed8409325be606c878462))

- **19.2-03**: Add plan summary for Newton-iteration diagnostic
  ([`96fe8d4`](https://github.com/McGrathLab/AquaCal/commit/96fe8d477832abeef8395c941a223a9c31db1121))

- **19.2-04**: Add plan summary
  ([`8a27c63`](https://github.com/McGrathLab/AquaCal/commit/8a27c637566fc9871a2c20d020f3a0d600ea7a49))

- **19.2-04**: Append self-check results to summary
  ([`099129f`](https://github.com/McGrathLab/AquaCal/commit/099129fa0cc918cb11324016bf136946e441a560))

- **19.2-05**: Complete E3 derived quantities plan
  ([`339d224`](https://github.com/McGrathLab/AquaCal/commit/339d22416573f4c843ceb7691f51be697b51365d))

- **19.2-06**: Add quiescence check and duplicate-run prevention (review H4)
  ([`eb898fb`](https://github.com/McGrathLab/AquaCal/commit/eb898fbb27acf5b5e3ec4796c93e24a656fbef7a))

- **19.2-06**: Complete E2 real-rig re-run plan
  ([`fe92862`](https://github.com/McGrathLab/AquaCal/commit/fe928621f7673e42435ca9c7eedd1a98f670d9d2))

- **19.2-07**: Complete E4 direct-call synthetic benchmark grid plan
  ([`1ad59c6`](https://github.com/McGrathLab/AquaCal/commit/1ad59c67f8b509e1a30101001e7074a312b244e2))

- **19.2-08**: Add E5 index-sensitivity plan summary
  ([`a569146`](https://github.com/McGrathLab/AquaCal/commit/a5691461e82e10f2ac6d440239cdb52347ec16de))

- **19.2-09**: Add plan 09 execution summary
  ([`c43f8ff`](https://github.com/McGrathLab/AquaCal/commit/c43f8ffe85abd976ce112a88403732aaa65d7529))

- **19.2-09**: Two-stage M8 probe, pre-authorize 16x200 OOM
  ([`f379d4b`](https://github.com/McGrathLab/AquaCal/commit/f379d4b9e0d149afc71684adbdff1d2de491d4cd))

- **19.2-10**: Complete E6 generalization sweep plan
  ([`33da302`](https://github.com/McGrathLab/AquaCal/commit/33da30253d9e0f5d244208074aef7956def88ccd))

- **19.2-11**: Add E6 generalization sweep summary
  ([`6f66b75`](https://github.com/McGrathLab/AquaCal/commit/6f66b75ef7522b84e8b2906f217b03a3f3895041))

- **19.2-12**: Add EXP-11 provenance close-out summary
  ([`3b83f59`](https://github.com/McGrathLab/AquaCal/commit/3b83f59f0cf716766af75faaf6c9ea6149f2bb63))

- **19.2-12**: Complete the provenance table and wire E3-E6 into CI smoke
  ([`fd91178`](https://github.com/McGrathLab/AquaCal/commit/fd911784c2d570dbf53cdaf4f434b87d926f749a))

- **19.2-13**: Summarize E5 production index-sensitivity band
  ([`1a3b8da`](https://github.com/McGrathLab/AquaCal/commit/1a3b8dab429abbc2036215f52106b59f53262fe4))

- **19.2-14**: Add plan summary
  ([`4c8b00d`](https://github.com/McGrathLab/AquaCal/commit/4c8b00db1e9be2d36a9046f9acaeccbdfd646496))

- **19.2-15**: Add plan summary for total compare_experiment_csv
  ([`e7edd7e`](https://github.com/McGrathLab/AquaCal/commit/e7edd7e26ee23fd60b5e522f89ff79b9bf65029b))

- **19.2-16**: Add plan summary
  ([`516b362`](https://github.com/McGrathLab/AquaCal/commit/516b362133e08f19ca3fc071b40cf7005ff5471e))

- **19.2-16**: Append self-check results to summary
  ([`442d054`](https://github.com/McGrathLab/AquaCal/commit/442d054c8d787d504b027490b359b354382b09e2))

- **19.2-17**: Add plan summary
  ([`90ee70d`](https://github.com/McGrathLab/AquaCal/commit/90ee70dca1ae878ea46412982fa56d21a5fcfd16))

- **19.2-17**: Record the near-ceiling coverage follow-up in the plan summary
  ([`7ae7ff6`](https://github.com/McGrathLab/AquaCal/commit/7ae7ff640ea9ce561a540992d311a13556b4a190))

- **19.2-18**: Grid-family geometry redesign summary
  ([`7e90c20`](https://github.com/McGrathLab/AquaCal/commit/7e90c20e1db395865fc9b751e7809425d2bdee5f))

- **19.2-19**: Add plan summary for E5 provenance sidecar + cwd-anchoring
  ([`8b978af`](https://github.com/McGrathLab/AquaCal/commit/8b978aff7c54b8fca3b12fc62d8936300cbe3bea))

- **19.2-20**: Add plan 20 summary — batch Newton diagnostic and E3 tier 2 rewire
  ([`db25e09`](https://github.com/McGrathLab/AquaCal/commit/db25e09dd603f35083f68f581642faaa7db072e8))

- **19.2-21**: Add plan summary for the E4 grid re-run
  ([`bd767fb`](https://github.com/McGrathLab/AquaCal/commit/bd767fb6cf678e6633eea8db67cd47887cd3a104))

- **19.2-22**: Correct the --check section -- it is cheap, and permanently red
  ([`54c51e8`](https://github.com/McGrathLab/AquaCal/commit/54c51e86b7f1fb94e7373e3db5cda92cb831605a))

- **19.2-23**: Adjudicate the overnight queue; E7's unanimity broke at 10 seeds
  ([`6f55ff7`](https://github.com/McGrathLab/AquaCal/commit/6f55ff79da03152753d15c3692b1d266de2470a4))

- **19.2-24**: Amend for the ten-seed D-36 result and adopt the orphaned test
  ([`e29f332`](https://github.com/McGrathLab/AquaCal/commit/e29f3323d400233b0e600d3167b0bf1914156414))

- **19.2-24**: Complete EXP-11 gate hardening plan
  ([`1bb38d3`](https://github.com/McGrathLab/AquaCal/commit/1bb38d3b940583ab65588212e6ac2c8bce53dc0f))

- **19.2-25**: Add plan summary
  ([`9a7312c`](https://github.com/McGrathLab/AquaCal/commit/9a7312c931f666e5be3c895d4af9d2314f0e227f))

- **19.2-25**: Close the requirements ledger and resolve MF-01/MF-02
  ([`a090a05`](https://github.com/McGrathLab/AquaCal/commit/a090a0585f4525408a4066eaf79b842bd1da1966))

- **19.2-25**: Make README's provenance claim true and its runtimes current
  ([`183a65d`](https://github.com/McGrathLab/AquaCal/commit/183a65dbaad8850b52e525c679776cea6144b3de))

- **19.2-26**: Add the plan and summary for the discard counters
  ([`4d3ba8d`](https://github.com/McGrathLab/AquaCal/commit/4d3ba8d06687c2736154eb5e4a65a3cb586c4b9f))

- **19.2-27**: Summarize the four disclosed-defect fixes and their proofs
  ([`1b0ad75`](https://github.com/McGrathLab/AquaCal/commit/1b0ad75b045bc4b054a647b503f31e34b7f53ef9))

- **19.2-28**: Record the decisive determinism probe
  ([`8100e21`](https://github.com/McGrathLab/AquaCal/commit/8100e21f932b046384124df05df1dc8628988bea))

- **19.2-29**: Replace the bit-identity gate with attribution, per plan 28
  ([`a6da3fa`](https://github.com/McGrathLab/AquaCal/commit/a6da3fa6d1805b89dad54bebe00e887996d0e73d))

- **19.3**: Add GEOM-01..06 requirements and sync state for planning
  ([`0d1d07c`](https://github.com/McGrathLab/AquaCal/commit/0d1d07cc0b3f28fafaf95650166bee905d666118))

- **19.3**: Add phase 19.3 to the roadmap and retire 19.2's handoff
  ([`14041c8`](https://github.com/McGrathLab/AquaCal/commit/14041c813ca76acb62a971233587d89db3d7aa4c))

- **19.3**: Add phase verification report
  ([`e5ef93f`](https://github.com/McGrathLab/AquaCal/commit/e5ef93f4790ce58213a26ad376240d0a11484197))

- **19.3**: Add validation strategy
  ([`9d448f4`](https://github.com/McGrathLab/AquaCal/commit/9d448f43e123df2974cdcb1da10b8dbbe76f7501))

- **19.3**: Amend plans 07-10 -- E3 joins the re-run set, smoke carve-out for the guard gate
  ([`a1f3871`](https://github.com/McGrathLab/AquaCal/commit/a1f3871fedfd650daebe0a5cc6ce5c665f9f92b5))

- **19.3**: Begin phase execution
  ([`78befe6`](https://github.com/McGrathLab/AquaCal/commit/78befe6aa19344f4ca83b8334d8d8f5ac04c6596))

- **19.3**: Capture phase context
  ([`980b333`](https://github.com/McGrathLab/AquaCal/commit/980b333f5aaedae5a7fd6afda28e50d98e9da2e1))

- **19.3**: Correct the clearance derivation and re-centre board poses (D-19.3-19)
  ([`f447b99`](https://github.com/McGrathLab/AquaCal/commit/f447b99dfdecbd1e207efaaee698e8e97b18ca1b))

- **19.3**: Create phase plan
  ([`ab7938c`](https://github.com/McGrathLab/AquaCal/commit/ab7938c9aa5554bd6bfa754d967cc98e7b44c28c))

- **19.3**: Create phase plan — 10 plans in 7 waves
  ([`23f4c60`](https://github.com/McGrathLab/AquaCal/commit/23f4c60e1ecf080eeee140e0a0703db64fd329e4))

- **19.3**: Diagnose the E6 clearance-floor defect and map findings to the manuscript
  ([`416ffa8`](https://github.com/McGrathLab/AquaCal/commit/416ffa81f42c84846cad9262e566ac8dded3408f))

- **19.3**: Foreground the E6 seed failures in the handoff
  ([`9e745c4`](https://github.com/McGrathLab/AquaCal/commit/9e745c43fdcaf32f86e5c2838f4adc12a9c94367))

- **19.3**: Pause at the code/run boundary with a pre-launch handoff
  ([`d094751`](https://github.com/McGrathLab/AquaCal/commit/d094751faa601191b11e28cf22df04af60e9d61d))

- **19.3**: Persist the trace findings and rewrite the handoff before context clear
  ([`6e4e999`](https://github.com/McGrathLab/AquaCal/commit/6e4e999884b9543ce9f0045568282587fa856938))

- **19.3**: Point the handoff at the correct HEAD
  ([`29f06d8`](https://github.com/McGrathLab/AquaCal/commit/29f06d8048ce7e1135e8de1ee4ab9667081472c4))

- **19.3**: Preserve the session evidence before the context is cleared
  ([`1c91eae`](https://github.com/McGrathLab/AquaCal/commit/1c91eae3dc1487e9b4669a1688bad06a31ee1ad8))

- **19.3**: Record the session transcript path as a handoff fallback
  ([`d0341d1`](https://github.com/McGrathLab/AquaCal/commit/d0341d1f2bb6793c129711c0d5724dc6a0b23198))

- **19.3**: Seed the scenario-geometry phase before the context is lost
  ([`aa4c92e`](https://github.com/McGrathLab/AquaCal/commit/aa4c92e4f063c75493c1d4c64cfde555636270be))

- **19.3**: Stop the handoff citing a SHA it can never get right
  ([`a0c7a41`](https://github.com/McGrathLab/AquaCal/commit/a0c7a41652fde98e9a4f40459041406eb4dda982))

- **19.3**: Sync RESEARCH.md's GEOM-05 scope to six experiments
  ([`f2a9082`](https://github.com/McGrathLab/AquaCal/commit/f2a9082f1de1d3785b77040317a73d80239997f8))

- **19.3**: Update tracking after phase close
  ([`4570855`](https://github.com/McGrathLab/AquaCal/commit/4570855b2bb63ef18d241e22bac5e8af4f36c3ce))

- **19.3**: Update tracking after wave 1
  ([`87304f2`](https://github.com/McGrathLab/AquaCal/commit/87304f249e9e8f858dbab0fd3d114be8f6927d0c))

- **19.3**: Update tracking after wave 2
  ([`493f611`](https://github.com/McGrathLab/AquaCal/commit/493f6112cbb5fd4bfc9d806a16d72a8b6f7c378c))

- **19.3**: Update tracking after wave 3
  ([`21ef9dc`](https://github.com/McGrathLab/AquaCal/commit/21ef9dc76af33518c69c578e1e4e98bbdefd1b89))

- **19.3**: Update tracking after wave 4
  ([`51c4cb5`](https://github.com/McGrathLab/AquaCal/commit/51c4cb5da2a8af433700e40c36fbb9cddec8fc86))

- **19.3**: Update tracking after wave 5
  ([`b65be01`](https://github.com/McGrathLab/AquaCal/commit/b65be014ae68e0c50104977cd27f4a87abb0ff3f))

- **19.3-01**: Add plan SUMMARY
  ([`a42fe2a`](https://github.com/McGrathLab/AquaCal/commit/a42fe2ab5a2aed3c9da85ba46e8fcd3042b8dbb1))

- **19.3-02**: Add plan summary -- guard count recorded, warning corrected, inertness proven
  ([`8379f23`](https://github.com/McGrathLab/AquaCal/commit/8379f2386c648be954a3fdd288a6281b0af4db79))

- **19.3-03**: Add the archive index and cross-link it from experiments/README.md
  ([`8f926c0`](https://github.com/McGrathLab/AquaCal/commit/8f926c01232da0026e68c528e4aac47267880e52))

- **19.3-03**: Append self-check result to summary
  ([`d48d9d5`](https://github.com/McGrathLab/AquaCal/commit/d48d9d54beefac55b36df80c79b03b931a246f54))

- **19.3-03**: Archive the five experiments' pre-depth-fix artifacts
  ([`8a90ea3`](https://github.com/McGrathLab/AquaCal/commit/8a90ea3438c9a15d3723738e23b4fb300d161ad0))

- **19.3-03**: Complete pre-depth-fix experiment archive plan
  ([`2013f74`](https://github.com/McGrathLab/AquaCal/commit/2013f74734bf5fdef21fab3335ce106a4dab6e04))

- **19.3-04**: Add plan summary
  ([`f65b4c3`](https://github.com/McGrathLab/AquaCal/commit/f65b4c3e032ee125995d48dc5a47974644478a71))

- **19.3-04**: Repair the tutorial notebook's latent standoff mismatch
  ([`3f42921`](https://github.com/McGrathLab/AquaCal/commit/3f42921d98d2786606949b86ae1fa9bf78311bb7))

- **19.3-05**: Add plan summary
  ([`7e1d3d5`](https://github.com/McGrathLab/AquaCal/commit/7e1d3d5974bee7123d97cce5ac9923cf44dbafcb))

- **19.3-06**: Add plan 06 execution summary
  ([`0e06a33`](https://github.com/McGrathLab/AquaCal/commit/0e06a33db2d84d8acab9af8832e0ba1167d43152))

- **19.3-07**: Add plan summary (written by orchestrator)
  ([`3860869`](https://github.com/McGrathLab/AquaCal/commit/3860869fe9ef1ca7dac1c7ccd4ee5f7e08e9e2f2))

- **19.3-08**: Add plan summary
  ([`f357d56`](https://github.com/McGrathLab/AquaCal/commit/f357d563c770f2d02ba45902fb3bf87080898718))

- **19.3-10**: Band the synthetic claims and retract a noise-based attribution
  ([`aebc098`](https://github.com/McGrathLab/AquaCal/commit/aebc098b4ea86a1ee189a8c2cb876157f99e14da))

- **19.3-10**: Correct MF-08 E4/E6 against the clearance-floor diagnosis
  ([`0054cd9`](https://github.com/McGrathLab/AquaCal/commit/0054cd952047911f334db1ed704dcda0c81fa552))

- **19.3-10**: Decompose the 135x->128x change and verify both optimality columns
  ([`a8f1fdf`](https://github.com/McGrathLab/AquaCal/commit/a8f1fdfc20ff29fe17054c60135b6409287a7fab))

- **19.3-10**: E6 is seed-locked to 42 -- measured, not predicted
  ([`d86cf3f`](https://github.com/McGrathLab/AquaCal/commit/d86cf3f9bd42a0f9ee2e7b622370de33c58b1368))

- **19.3-10**: Re-resolve MF-01 and write MF-08
  ([`b2aa4dc`](https://github.com/McGrathLab/AquaCal/commit/b2aa4dca48a9465a536492f69a0936177b01859a))

- **19.4**: Add E6 seed 43 to verification; correct two factual errors
  ([`ded5277`](https://github.com/McGrathLab/AquaCal/commit/ded527710c1ca7087dc84acc118eb3434ab51743))

- **19.4**: Add phase context and research
  ([`c999a1e`](https://github.com/McGrathLab/AquaCal/commit/c999a1ea896428bf3409275be8fb325cb704c499))

- **19.4**: Correct D-19.4-03 against the committed checkpoints
  ([`92cd8e7`](https://github.com/McGrathLab/AquaCal/commit/92cd8e76fe1b921f38b5b059434c5b0c3069e4bf))

- **19.4**: Create phase plans -- 7 plans, 6 waves, GRID-01..05 proposed
  ([`aa9ad7f`](https://github.com/McGrathLab/AquaCal/commit/aa9ad7fc20925cda9690d19833e55a785a4d75d1))

- **19.4**: Draft re-scope proposal -- single flat interface
  ([`e420dd6`](https://github.com/McGrathLab/AquaCal/commit/e420dd6738c9758c9d1c6ff7d6061a0e1f554d89))

- **19.4**: Fold --seeds into E1/E7; verify E6 seed-locking is cured
  ([`81a03b3`](https://github.com/McGrathLab/AquaCal/commit/81a03b39070cec9794fd4ce135d45d8b75fac36f))

- **19.4**: Headline the end state and gate the queue on a pre-run intent audit
  ([`bcd3702`](https://github.com/McGrathLab/AquaCal/commit/bcd3702608b3f192858af8cd80a18567e0fc4802))

- **19.4**: Mark phase executing
  ([`0c0d321`](https://github.com/McGrathLab/AquaCal/commit/0c0d3211772803232f1f13fb308b6cbd89741d55))

- **19.4**: Plan Single Flat Interface as 10 plans across 6 waves
  ([`54c79d6`](https://github.com/McGrathLab/AquaCal/commit/54c79d68ac2476d2671e60c0636f91ca214da5b0))

- **19.4**: Re-research for Single Flat Interface; correct E7 to the inert set
  ([`30c3d01`](https://github.com/McGrathLab/AquaCal/commit/30c3d0123b395b18f697f0fbeaf76534cabb68bc))

- **19.4**: Re-scope to Single Flat Interface; delete superseded plans
  ([`1ecb9d8`](https://github.com/McGrathLab/AquaCal/commit/1ecb9d8c4d6ba319ea526d500e444dad99e5e39b))

- **19.4**: Record planning completion and resolve research open questions
  ([`e235df6`](https://github.com/McGrathLab/AquaCal/commit/e235df64f9b04f066d4011d27b44ddb8ffef5669))

- **19.4**: Research phase domain
  ([`fcc9ebb`](https://github.com/McGrathLab/AquaCal/commit/fcc9ebb3fc411e701ca613ad7ec63541189cf681))

- **19.4**: Run the verification queue risk-first with a pre-committed abort protocol
  ([`b60f6e2`](https://github.com/McGrathLab/AquaCal/commit/b60f6e255638d388822774403d1852479a41e24c))

- **19.4**: Update tracking after wave 1
  ([`a36a300`](https://github.com/McGrathLab/AquaCal/commit/a36a30058a4e4e9d2003f6ecc61a663dffb3c4fa))

- **19.4-01**: Archive E4 pre-interface-fix artifacts
  ([`81fbcf5`](https://github.com/McGrathLab/AquaCal/commit/81fbcf54bcee54843958e02dec6507ccc680c619))

- **19.4-01**: Archive E6 pre-interface-fix artifacts
  ([`25414b1`](https://github.com/McGrathLab/AquaCal/commit/25414b1b76d67a92d9e33e7db6ca5ae42387c68f))

- **19.4-01**: Complete archive pre-interface-fix artifacts plan
  ([`7ec9f83`](https://github.com/McGrathLab/AquaCal/commit/7ec9f83cbf7bd7ac764a1c379cb98be80d761884))

- **19.4-01**: Index the E4/E6 pre-interface-fix archive generations
  ([`58bd225`](https://github.com/McGrathLab/AquaCal/commit/58bd2252fc64e85e2dfd709655e5faf91abb67ba))

- **19.4-02**: Add plan summary for the water_z-to-C_z jitter relocation
  ([`9f4f527`](https://github.com/McGrathLab/AquaCal/commit/9f4f52758e5924a8df8a955744d4415da120687a))

- **19.4-03**: Produce pre-run reviewer-intent coverage matrix (D-19.4-17)
  ([`73ed131`](https://github.com/McGrathLab/AquaCal/commit/73ed1314abfd33d823800f22e4c0457fef034ba1))

- **19.4-03**: Record approved CONFIRMED verdict and complete plan 03
  ([`e99a852`](https://github.com/McGrathLab/AquaCal/commit/e99a852eef267a0f1cc04ca2bd88ef12ae223bb5))

- **19.4-04**: Complete GRID_DEPTH_RANGE re-derivation and inertness proof plan
  ([`b992082`](https://github.com/McGrathLab/AquaCal/commit/b992082abe1d20b100982d25d4bd46d278b33a56))

- **19.4-05**: Add plan summary for shared seed-band mechanism + E7 --seeds
  ([`904c0c9`](https://github.com/McGrathLab/AquaCal/commit/904c0c91a45bd57a4f3121bfb212b637cd852a98))

- **19.4-06**: Add plan 06 summary
  ([`1deb69b`](https://github.com/McGrathLab/AquaCal/commit/1deb69b6dd4fca86743d17d229b3ef4b61303b90))

- **19.4-06**: Append self-check results to summary
  ([`14c52f0`](https://github.com/McGrathLab/AquaCal/commit/14c52f039bd7975be39e4f4dfd1c77ae5bf5e2a4))

- **19.4-06**: Document E4/E6 seed-band extension path in run_seed_band
  ([`fb4cafc`](https://github.com/McGrathLab/AquaCal/commit/fb4cafcc9a935ab32aacea3dc5e0eda85de38547))

- **19.4-07**: Add plan summary for E4/E6 fail-fast
  ([`0240e50`](https://github.com/McGrathLab/AquaCal/commit/0240e50125d93038b1f50879c56ce3d063b3a4f2))

- **19.4-10**: Close phase 19.4 — inertness verdict, MF updates, traceability
  ([`6532000`](https://github.com/McGrathLab/AquaCal/commit/65320000d7bba96140664a158a1872b16a783f4e))

- **19.5**: Add research and validation strategy
  ([`563952f`](https://github.com/McGrathLab/AquaCal/commit/563952fecf88677283c1c8e4d44c048a3f503dde))

- **19.5**: Begin phase execution
  ([`4576489`](https://github.com/McGrathLab/AquaCal/commit/457648911022065b7a8c2b967af9686fe0a1262c))

- **19.5**: Correct handoff log path and expected gate verdicts
  ([`1bdb3ad`](https://github.com/McGrathLab/AquaCal/commit/1bdb3adc18e944321ea9855a53ebc723fbdde6a6))

- **19.5**: Handoff before the production queue launch
  ([`cd284ea`](https://github.com/McGrathLab/AquaCal/commit/cd284ea0485145dc19d7268aa20c45328b58fb8f))

- **19.5**: Insert phase, define COV-01..09, record scoping context
  ([`81f1e87`](https://github.com/McGrathLab/AquaCal/commit/81f1e87bd9e22f7f0cf8d877bac51128536b891f))

- **19.5**: Plan phase -- 11 plans in 5 waves, checker passed
  ([`2d64e4e`](https://github.com/McGrathLab/AquaCal/commit/2d64e4e6dc0c63e5d5e9ba6577e40fd9cac5df13))

- **19.5**: Plan phase 19.5 -- 11 plans, 5 waves, one 26h queue
  ([`686979a`](https://github.com/McGrathLab/AquaCal/commit/686979a97562a072fe36744769208b9045034f56))

- **19.5-01**: Add plan 01 SUMMARY (COV-01 structural scaling sweep)
  ([`165c5f5`](https://github.com/McGrathLab/AquaCal/commit/165c5f57c5ff00c19173b73271ce0d48084e351f))

- **19.5-02**: Add plan 02 SUMMARY -- FD Jacobian accuracy (COV-02)
  ([`15233a1`](https://github.com/McGrathLab/AquaCal/commit/15233a181a61490b39e8040d70bf8c25314caf6b))

- **19.5-03**: Complete E7 focal/standoff re-analysis plan
  ([`c747900`](https://github.com/McGrathLab/AquaCal/commit/c74790057741a03e17a8758bbb77d5d880730e94))

- **19.5-04**: Add plan 04 SUMMARY -- COV-08 bootstrap CI
  ([`fa19517`](https://github.com/McGrathLab/AquaCal/commit/fa19517abac75eef0114177944cbfc7be4440040))

- **19.5-05**: Add plan summary — E5 seed band CLI complete
  ([`233826d`](https://github.com/McGrathLab/AquaCal/commit/233826d210a8b128769026ddc6cd3df17fb0795f))

- **19.5-06**: Complete E6 seed band and camera-count axis plan
  ([`5918d0b`](https://github.com/McGrathLab/AquaCal/commit/5918d0b6f5dec0ededb345fc5fc09d13f054bfce))

- **19.5-07**: Add SUMMARY for COV-07 E2 seed-variant config generator
  ([`6a04b61`](https://github.com/McGrathLab/AquaCal/commit/6a04b61a3f6e14a76f08e5e942f6cfcf7991b70d))

- **19.5-08**: Add plan 08 SUMMARY -- COV-06 splice helper and CLI
  ([`6cda985`](https://github.com/McGrathLab/AquaCal/commit/6cda985bd7deb5cc6517dac7649b5be491843c0c))

- **19.5-09**: Add plan SUMMARY
  ([`cb8266d`](https://github.com/McGrathLab/AquaCal/commit/cb8266dd0ec1b73923a64d5ed7aecd41a602c2cf))

- **19.5-09**: Append self-check block to SUMMARY
  ([`b77f8df`](https://github.com/McGrathLab/AquaCal/commit/b77f8dfc91ffe06e89ecb2ba97591c7d9b93f7cd))

- **19.5-10**: Correct the SUMMARY's reading of E1's guard-count FAIL
  ([`1933647`](https://github.com/McGrathLab/AquaCal/commit/1933647b72bdddbca39278cfee9e1941feaff2f0))

- **19.5-10**: SUMMARY for the production queue run
  ([`66188a3`](https://github.com/McGrathLab/AquaCal/commit/66188a33018aff47ea7b2404ecaf2be1541db48b))

- **19.5-11**: MF-11..MF-17, COV discharge, and phase 19.5 closure
  ([`55f75ce`](https://github.com/McGrathLab/AquaCal/commit/55f75cefe12d9ae6ec7d5ac23aea3e06dceb30db))

- **21**: Capture phase context
  ([`ca96c0a`](https://github.com/McGrathLab/AquaCal/commit/ca96c0abca59fe0c2e1990d7ed37dde787b7e8a2))

- **21**: Create phase plan -- 12 plans in 7 waves
  ([`156f70d`](https://github.com/McGrathLab/AquaCal/commit/156f70d5a31bb4edccb53b96a260ff6e6f277087))

- **21**: Pattern map and planning-complete state
  ([`caede4d`](https://github.com/McGrathLab/AquaCal/commit/caede4df86557f6e8e6f25d7f428d128aa12d6cf))

- **21**: Revise plans per checker -- 21-07 non-autonomous, conda-env notes
  ([`f118fa7`](https://github.com/McGrathLab/AquaCal/commit/f118fa7fbf337e3814a97eb60726e7ea75f0cd22))

- **21-01**: Complete frame-extraction-tool plan
  ([`19186b2`](https://github.com/McGrathLab/AquaCal/commit/19186b26ba8f0d282dea40aa6ad7a98072dab95a))

- **21-02**: Add benchmarking.md schema reference
  ([`b8a222d`](https://github.com/McGrathLab/AquaCal/commit/b8a222d18275b7af8dba20d0a333d5b844547b8c))

- **21-02**: Add plan 02 execution summary
  ([`fce9180`](https://github.com/McGrathLab/AquaCal/commit/fce91809ec6d31e358db12be722c8eeeae34affe))

- **21-02**: Forward-link internals rows to benchmarking.md
  ([`38bef02`](https://github.com/McGrathLab/AquaCal/commit/38bef02dde20b8c1c8675ea8811b2e676653fcc3))

- **21-02**: Register benchmarking.md in guide nav
  ([`3a7e4a7`](https://github.com/McGrathLab/AquaCal/commit/3a7e4a7087c955867c61f9f475460e40e048714b))

- **21-03**: Add end-to-end CLI walkthrough tutorial over real-rig archive
  ([`f62f40b`](https://github.com/McGrathLab/AquaCal/commit/f62f40b0c39d3f6b0673aaf0d6695560a7f35cd4))

- **21-03**: Add plan summary
  ([`73433f5`](https://github.com/McGrathLab/AquaCal/commit/73433f588d8dfb97b994ce2cb023b45b1ef91cc2))

- **21-03**: Register CLI walkthrough in tutorials nav, fix cross-worktree link
  ([`ea9acd0`](https://github.com/McGrathLab/AquaCal/commit/ea9acd0fac02df01cbf265b13ba5233065bce00c))

- **21-03**: Restore benchmarking.md links after cross-worktree merge
  ([`ce73ce5`](https://github.com/McGrathLab/AquaCal/commit/ce73ce58a9c18d270e12a3a9774cef5574ca1b92))

- **21-04**: Complete notebook refresh plan
  ([`b0f4348`](https://github.com/McGrathLab/AquaCal/commit/b0f43482bff6e9d85b8860c75249251835ec933c))

- **21-05**: Complete requirements reconciliation & OpenCV pin audit plan
  ([`6a3a780`](https://github.com/McGrathLab/AquaCal/commit/6a3a780b868edd12c67903834703ebec939b88bb))

- **21-05**: Reword DOCS-05/DATA-02/DATA-03 with dated amendment notes
  ([`de35d4a`](https://github.com/McGrathLab/AquaCal/commit/de35d4a3d8b944402e9b1c4dd470f0c206be4b73))

- **21-06**: Complete production frame extraction plan
  ([`16b63fe`](https://github.com/McGrathLab/AquaCal/commit/16b63fe390acc72781f11196d9a8f01c0d7a2a87))

- **21-07**: Archive manifest with D-15 gates 2 and 4 evidence
  ([`84ff0b5`](https://github.com/McGrathLab/AquaCal/commit/84ff0b55374d3475007d9f80977c0591c86e036b))

- **21-07**: Complete archive assembly plan
  ([`4de9673`](https://github.com/McGrathLab/AquaCal/commit/4de9673f525802ce147344c4ccdf47161f5c8935))

- **21-08**: Archive verified faithful; gate 1 blocked on a manuscript decision
  ([`e6a3348`](https://github.com/McGrathLab/AquaCal/commit/e6a3348246da21f92a2fe109ff6e2e9fb65ced85))

- **21-08**: HALT - D-15 gate 1 FAILED, archive does not reproduce Section 3
  ([`93923cf`](https://github.com/McGrathLab/AquaCal/commit/93923cf4eee11e427ce2ef5eeedcb7f97fcda2d1))

- **21-08**: MF-19 -- Section 3's numbers predate the current library
  ([`8fc4942`](https://github.com/McGrathLab/AquaCal/commit/8fc4942e026cc17d0cf050277bd704fdc5b3414b))

- **21-08**: Summary -- gates 1/3 blocked on a manuscript decision
  ([`67f4004`](https://github.com/McGrathLab/AquaCal/commit/67f40043634e3b04b4808bdb6ad4a8eca50a474c))

- **21-08**: The rig figure is a manuscript item, not an archive gate
  ([`c8defb9`](https://github.com/McGrathLab/AquaCal/commit/c8defb935a2d71fcde324fa4f87f54f8b7ce31e6))

- **21-12**: Add plan SUMMARY
  ([`63ea7da`](https://github.com/McGrathLab/AquaCal/commit/63ea7da649ad0a116143405c0f878df147a99150))

- **21-12**: Append self-check to SUMMARY
  ([`1b7be11`](https://github.com/McGrathLab/AquaCal/commit/1b7be1145cc76fba9ec64096364866442e83ed53))

- **21-12**: MF-18 -- n=1 baseline is converged; route through MF-09
  ([`e6b5e35`](https://github.com/McGrathLab/AquaCal/commit/e6b5e35c22b3c2db8a4faee94c4e510fd69c2945))

- **260807-dcv**: Pre-dispatch plan for E1/E7 band provenance
  ([`58d2f7d`](https://github.com/McGrathLab/AquaCal/commit/58d2f7d1c8c9b7b9eafd63aa14eee48519091350))

- **260807-dcv**: SUMMARY and STATE row for the E1/E7 band provenance task
  ([`b13a3e0`](https://github.com/McGrathLab/AquaCal/commit/b13a3e038f29594085acb262b174c050d97ec8dd))

- **datasets**: Freeze WATER_Z as a design constant, not a calibrated value
  ([`98b17cb`](https://github.com/McGrathLab/AquaCal/commit/98b17cbb604b743ec120e5bc585dd72aafac9d42))

- **phase-16**: Complete phase execution
  ([`98b3f82`](https://github.com/McGrathLab/AquaCal/commit/98b3f82e84d0c6927181c8c14d0990c1e2834a86))

- **phase-17**: Complete phase execution
  ([`b2aea44`](https://github.com/McGrathLab/AquaCal/commit/b2aea44622b56efbdba7d4896ee2d599306e4194))

- **phase-18**: Add validation strategy
  ([`612d08f`](https://github.com/McGrathLab/AquaCal/commit/612d08f6b586456697f642609f406479e9a6d986))

- **phase-18**: Complete phase execution
  ([`7fcdb18`](https://github.com/McGrathLab/AquaCal/commit/7fcdb18267a0296359a01acd5193027cb51ef40c))

- **phase-18**: Mark phase 18 execution started
  ([`3e85ec4`](https://github.com/McGrathLab/AquaCal/commit/3e85ec469042053d29463fd21e1be99a251625e5))

- **phase-18**: Update tracking after 18-04 checkpoint approval
  ([`a41361d`](https://github.com/McGrathLab/AquaCal/commit/a41361d4cc9c7f577217a260fa68acda0e54791b))

- **phase-18**: Update tracking after wave 1
  ([`ffccec2`](https://github.com/McGrathLab/AquaCal/commit/ffccec2ae269c8219780aca118407c5ccd69e1c6))

- **phase-18**: Update tracking after wave 2 (18-04 pending checkpoint)
  ([`cf36c87`](https://github.com/McGrathLab/AquaCal/commit/cf36c870c6666ffdb951d875424732f9ca14c737))

- **phase-18**: Update tracking after wave 3
  ([`34d95a1`](https://github.com/McGrathLab/AquaCal/commit/34d95a1327a771ebf6774beff277782640cc3362))

- **phase-19**: Add validation strategy
  ([`1e2ac73`](https://github.com/McGrathLab/AquaCal/commit/1e2ac731cc01c59db2888cda823793f734854d51))

- **phase-19**: Complete phase execution
  ([`ade7921`](https://github.com/McGrathLab/AquaCal/commit/ade79215bd062e532f4b9fd49fef776ee78a9847))

- **phase-19**: Mark phase 19 execution started
  ([`8fdb652`](https://github.com/McGrathLab/AquaCal/commit/8fdb652942d59f75fd56a1784a2f0f7ea0ee8d6e))

- **phase-19**: Update tracking after wave 3
  ([`cfb6dcf`](https://github.com/McGrathLab/AquaCal/commit/cfb6dcfc44bbdd3c9b5373500d5aa3f7e2077eee))

- **phase-19**: Update tracking after wave 4
  ([`ef68bbd`](https://github.com/McGrathLab/AquaCal/commit/ef68bbd1e40f53ed22ae93041905935a2e1f7c61))

- **phase-19**: Update tracking after waves 1-2
  ([`3007a23`](https://github.com/McGrathLab/AquaCal/commit/3007a234216d3d3b167fd045e56d4e3956047519))

- **phase-19.1**: Complete phase execution
  ([`78dbfed`](https://github.com/McGrathLab/AquaCal/commit/78dbfede701e5e201a7c354166ae7d47da463f11))

- **phase-19.1**: Update tracking after wave 1
  ([`77f4f43`](https://github.com/McGrathLab/AquaCal/commit/77f4f43e74f36a5d2d3efcc0792903b3825dcf97))

- **phase-19.1**: Update tracking after wave 2
  ([`c6af7b2`](https://github.com/McGrathLab/AquaCal/commit/c6af7b25752478fb80fa3b1828cdbe72ab026e3d))

- **phase-19.1**: Update tracking after wave 3
  ([`ae8c807`](https://github.com/McGrathLab/AquaCal/commit/ae8c807b8d46d74fa4d895052f5d0a2fd96269a3))

- **phase-19.1**: Update tracking after wave 4
  ([`4970e71`](https://github.com/McGrathLab/AquaCal/commit/4970e7120d6dd23079179541dbca2670d70e8698))

- **phase-19.1**: Update tracking after wave 5
  ([`9c86aac`](https://github.com/McGrathLab/AquaCal/commit/9c86aac9d8bb4cc065b7a34ae8989daf23d28c4c))

- **phase-19.1**: Update tracking after wave 6
  ([`29c276d`](https://github.com/McGrathLab/AquaCal/commit/29c276deb18ad69969572563d41c14de89b2fcc6))

- **phase-19.2**: Add validation strategy
  ([`dc56ae7`](https://github.com/McGrathLab/AquaCal/commit/dc56ae7cc87b3d366f3dca5b2ac0ce510113f4ec))

- **phase-19.2**: Correct stale stopped_at in STATE.md
  ([`1fce0ce`](https://github.com/McGrathLab/AquaCal/commit/1fce0ce404b80d62f30e94645dc5954f5c762c31))

- **phase-19.2**: Correct STATE position after wave 2
  ([`fad4d33`](https://github.com/McGrathLab/AquaCal/commit/fad4d3381a3709b95ca4f2844efb35d108a5b853))

- **phase-19.2**: Sync stale STATE counters after wave 3
  ([`dbfb1c1`](https://github.com/McGrathLab/AquaCal/commit/dbfb1c131828367c5b684870326f624bd36aea62))

- **phase-19.2**: Update tracking after wave 1
  ([`77a1026`](https://github.com/McGrathLab/AquaCal/commit/77a1026adae2e7e3f6857f424c829ed762628975))

- **phase-19.2**: Update tracking after wave 1 gap closure
  ([`177b5f4`](https://github.com/McGrathLab/AquaCal/commit/177b5f49d95e2269071dfddd5714225e60477728))

- **phase-19.2**: Update tracking after wave 2 gap closure
  ([`e550e18`](https://github.com/McGrathLab/AquaCal/commit/e550e18bb7f660de9bf59459085d155311e0d83f))

- **phase-19.2**: Update tracking after wave 3
  ([`5e1b94d`](https://github.com/McGrathLab/AquaCal/commit/5e1b94dfb5543f25e0a47b4595fd7d9b2540d0e0))

- **phase-19.2**: Update tracking after wave 4
  ([`124594a`](https://github.com/McGrathLab/AquaCal/commit/124594a9c2cfa5e6753ac3c0cb33b83fc5d37743))

- **phase-19.2**: Update tracking after wave 5
  ([`4e361b2`](https://github.com/McGrathLab/AquaCal/commit/4e361b2dd7736791b570134e8d0761e8ba8a6d43))

- **phase-19.2**: Update tracking after wave 6
  ([`3f2e1f4`](https://github.com/McGrathLab/AquaCal/commit/3f2e1f43eed8726533c53bdb5ab19ebc8e61d539))

- **phase-19.2**: Update tracking after wave 6
  ([`a5dabd7`](https://github.com/McGrathLab/AquaCal/commit/a5dabd7ab3fc0c6a2eda822b2632c6a5396a7c9b))

- **phase-19.2**: Update tracking after wave 7
  ([`74e75a7`](https://github.com/McGrathLab/AquaCal/commit/74e75a7b33d4d9be1467f5806e76d1e77604e047))

- **phase-19.2**: Update tracking after wave 7
  ([`b5bda37`](https://github.com/McGrathLab/AquaCal/commit/b5bda373ef5cbf7af53c08390913a148b857d4ef))

- **phase-19.2**: Update tracking after wave 8
  ([`727ba8d`](https://github.com/McGrathLab/AquaCal/commit/727ba8dd0807d207c498aefc14616f62ad718051))

- **phase-19.2**: Update tracking after wave 9 — phase complete
  ([`6247c1f`](https://github.com/McGrathLab/AquaCal/commit/6247c1f05a67bb6f64bcc77c0e40e5a423198b99))

- **phase-19.5**: Update tracking after wave 1
  ([`c1696f2`](https://github.com/McGrathLab/AquaCal/commit/c1696f280c32aae62e716944f41ef81800b53edf))

- **phase-19.5**: Update tracking after wave 2
  ([`147f2e1`](https://github.com/McGrathLab/AquaCal/commit/147f2e13cfe86f21778cc63f836b2ad0517f5b86))

- **phase-19.5**: Update tracking after wave 3
  ([`b517cd3`](https://github.com/McGrathLab/AquaCal/commit/b517cd3a252e398a656022c510cd0e1e0fd3c0cb))

- **phase-21**: Update tracking after wave 1
  ([`02867f0`](https://github.com/McGrathLab/AquaCal/commit/02867f0f81c4d39aff144e608c9093a4ebef6ae0))

- **phase-21**: Update tracking after wave 2
  ([`029076b`](https://github.com/McGrathLab/AquaCal/commit/029076b8c6294612d1e649a46f270fe0f3d01a34))

- **phase-21**: Update tracking after wave 3
  ([`71d1145`](https://github.com/McGrathLab/AquaCal/commit/71d1145795013034405445cff046d657f14e6847))

- **planning**: Migrate STATE.md command references to GSD 1.42 namespace
  ([`e1be9e4`](https://github.com/McGrathLab/AquaCal/commit/e1be9e45ae13af91cc8b2eb4edbd5f98ee819a9f))

- **planning**: Reconcile STATE.md and ROADMAP.md with phases 16-17 complete
  ([`9561b8f`](https://github.com/McGrathLab/AquaCal/commit/9561b8fa6594afca2f533e4df48beee528f033dc))

- **quick-260811-e7s**: Read-only pre-2.0.0 release audit
  ([`57eca21`](https://github.com/McGrathLab/AquaCal/commit/57eca217211a74f1868b597b6983e8058a6b82c6))

- **quick-260811-f81**: Record the pre-2.0.0 fix task
  ([`6ac4569`](https://github.com/McGrathLab/AquaCal/commit/6ac45698b399c6fd766583c8acda8a2d0c3d2aa6))

- **quick-3**: Complete structural column grouping task
  ([`1f4a115`](https://github.com/McGrathLab/AquaCal/commit/1f4a115516efb83f4ece044c0fc5fc963082977d))

- **roadmap**: Insert phases 19.1 and 19.2 with EXP-01..11
  ([`292e973`](https://github.com/McGrathLab/AquaCal/commit/292e9731867f451b55ad40fa91dfc81dc20fcf65))

- **state**: Record phase 16 context session
  ([`87972b7`](https://github.com/McGrathLab/AquaCal/commit/87972b7ebe8c64486dfc3daecba330b716016c70))

- **state**: Record phase 16 planning session
  ([`e7cef25`](https://github.com/McGrathLab/AquaCal/commit/e7cef258599d59cd9d42d7c47969f1f9db991d80))

- **state**: Record phase 18 context session
  ([`84814b5`](https://github.com/McGrathLab/AquaCal/commit/84814b58944c43f3819b9d536d3eb633e5e1ed6d))

- **state**: Record phase 19.1 context session
  ([`6492abf`](https://github.com/McGrathLab/AquaCal/commit/6492abf1d06ef6f7ee7353dffae3e06ad5b2af76))

- **state**: Record phase 19.1 decision review session
  ([`a5e47b9`](https://github.com/McGrathLab/AquaCal/commit/a5e47b96b568fbf78fe016c3be5594bcd23c8197))

- **state**: Record phase 19.2 context session
  ([`e564742`](https://github.com/McGrathLab/AquaCal/commit/e56474270915add37ec8dc5c31e4c939d230ecbe))

- **state**: Record phase 19.2 position before context clear
  ([`3bad87d`](https://github.com/McGrathLab/AquaCal/commit/3bad87df648ba3369835a2f04fb8977be41fa351))

- **state**: Record phase 19.2 replan (13 plans)
  ([`345cc4b`](https://github.com/McGrathLab/AquaCal/commit/345cc4b509293cdbdb6cddd58a344098cddefaae))

- **state**: Record phase 19.3 context session
  ([`8f4da33`](https://github.com/McGrathLab/AquaCal/commit/8f4da330cab3b7fc45acb1c26e1df5bf546dd1e9))

- **state**: Record phase 21 context session
  ([`e25af2c`](https://github.com/McGrathLab/AquaCal/commit/e25af2c655ad7639df7c820fc432f139109468ff))

- **state**: Record replan-required position
  ([`1ef72e9`](https://github.com/McGrathLab/AquaCal/commit/1ef72e95860900359379d44f81d30526c80bfc47))

- **tutorials**: Name the config that reproduces Section 3
  ([`3ccb852`](https://github.com/McGrathLab/AquaCal/commit/3ccb85295c9a6dc1ccedf95c940df87d74973f11))

### Features

- Close Phase 19.3 -- scenario geometry corrected, six experiments re-measured
  ([`d406001`](https://github.com/McGrathLab/AquaCal/commit/d406001cec568e4f3f32da1e642eeef3c419d42b))

- **16-01**: Add JSON/NPZ conditioning report writer and public exports
  ([`67f38b9`](https://github.com/McGrathLab/AquaCal/commit/67f38b9908766475b2d84233a0a7d9ee908b5469))

- **16-01**: Implement compute_conditioning via blocked tall-skinny QR
  ([`cd5dd00`](https://github.com/McGrathLab/AquaCal/commit/cd5dd002d9b6291020ed8fa4cc10df8e9ba419c1))

- **16-02**: Plumb refractive index through synthetic detection generation
  ([`85e60c2`](https://github.com/McGrathLab/AquaCal/commit/85e60c270f9168afc819fc6fe950a2a2dab934fb))

- **16-03**: Add internals/ artifact directory helper
  ([`afe54e8`](https://github.com/McGrathLab/AquaCal/commit/afe54e884d676a820c1b4a0f1a57aa0614dc9e11))

- **16-03**: Add observability config fields and internals: YAML section
  ([`bb523a7`](https://github.com/McGrathLab/AquaCal/commit/bb523a7e227ed9eb105d8482fdd48ff1f2bd2948))

- **16-03**: Dump each bundle-adjustment stage's intermediate calibration
  ([`ce94111`](https://github.com/McGrathLab/AquaCal/commit/ce941110465c7d9dd39e0f94e68552d557237215))

- **16-04**: Accept optional OptimizerObserver in the two BA entry points
  ([`9928deb`](https://github.com/McGrathLab/AquaCal/commit/9928debc5832771e823ee8dd70d5cef4113f82fb))

- **16-04**: Add OptimizerObserver and bump scipy floor to >=1.16
  ([`048f8ba`](https://github.com/McGrathLab/AquaCal/commit/048f8bad44d25c42e480f5ea99630e22656c2b46))

- **16-04**: Wire per-stage OptimizerObserver trace files into the pipeline
  ([`29201f3`](https://github.com/McGrathLab/AquaCal/commit/29201f328b73801b5bf9ea5feb751c69d5987bb7))

- **16-05**: Compute labelled conditioning inside OptimizerObserver.on_solution
  ([`ccc61ac`](https://github.com/McGrathLab/AquaCal/commit/ccc61ace23ea082be32fd7c4d807b4d7c875c617))

- **16-05**: Enable conditioning on the final reported stage and write it once
  ([`f5ea190`](https://github.com/McGrathLab/AquaCal/commit/f5ea19029bf45e0e23e599b6d551e2f3f178a0dc))

- **16-06**: Record the seed used in every saved calibration artifact
  ([`f4f0249`](https://github.com/McGrathLab/AquaCal/commit/f4f0249bd52b4e21efe181978e6ffab27236674b))

- **16-06**: Thread config.seed into the pipeline holdout split
  ([`e92a01d`](https://github.com/McGrathLab/AquaCal/commit/e92a01d6e6d8a14770ada5ec7c8f266caa525d84))

- **16-07**: Add standalone evaluate_calibration, move _estimate_validation_poses
  ([`c5c8218`](https://github.com/McGrathLab/AquaCal/commit/c5c8218fa8ad154576727cc8e71d82ebb2ab65cf))

- **17-01**: Per-camera water_z columns in sparsity, grouping, labels
  ([`07de913`](https://github.com/McGrathLab/AquaCal/commit/07de913b13bf1facd9b80f8fe9801dbba94a9e08))

- **17-01**: Per-camera water_z in pack/unpack/bounds
  ([`82ab1d3`](https://github.com/McGrathLab/AquaCal/commit/82ab1d3282edd41cdeaeb644d6dd0459c3f7d875))

- **17-02**: Add shared_interface field to CalibrationConfig
  ([`3231c1c`](https://github.com/McGrathLab/AquaCal/commit/3231c1ce2f2b13f00c7546b026a6c09fa011b054))

- **17-02**: Loader pass-through + conditional coverage gate + init line
  ([`f24585c`](https://github.com/McGrathLab/AquaCal/commit/f24585c029b3fd2faa99746d182a60f010d83590))

- **17-03**: Pipeline wiring + single ablation WARNING
  ([`1a8ce3a`](https://github.com/McGrathLab/AquaCal/commit/1a8ce3a47df2a44312b5d3485cc9abebf0720a34))

- **17-03**: Thread shared_interface through joint_refinement (Stage 4)
  ([`e6c6f5f`](https://github.com/McGrathLab/AquaCal/commit/e6c6f5f262b23b39e45187e669e3363382c3ba0d))

- **17-03**: Thread shared_interface through optimize_interface (Stage 3)
  ([`b3320d2`](https://github.com/McGrathLab/AquaCal/commit/b3320d211df7c0dcad46b56d1a4eb04eab5894bc))

- **17-04**: Per-camera seed resolver + water_z spread report
  ([`8fdfc08`](https://github.com/McGrathLab/AquaCal/commit/8fdfc08c3784b2d8e2e5f062913cf154154afb34))

- **19-01**: Add SolverDiagnostics dataclass contract
  ([`ff43bc1`](https://github.com/McGrathLab/AquaCal/commit/ff43bc1b015094628697b4ebe3e184dd99ec426a))

- **19-01**: Implement capture_solver_diagnostics() and test it
  ([`8400c33`](https://github.com/McGrathLab/AquaCal/commit/8400c33223e2c3d2c331e7c35f3c2eaf5004e670))

- **19-02**: Add diagnostics capture to register_auxiliary_camera
  ([`510ecbf`](https://github.com/McGrathLab/AquaCal/commit/510ecbfd50176b0e103724007eae0943d596dcac))

- **19-02**: Add explicit tolerances and diagnostics capture to optimize_interface
  ([`4a7d46e`](https://github.com/McGrathLab/AquaCal/commit/4a7d46e04c3817f799cbbb9fcf1af7e3f62bcf82))

- **19-03**: Add RefinementResult.solver_diagnostics, wire refine_calibration
  ([`3dece3e`](https://github.com/McGrathLab/AquaCal/commit/3dece3e1cd00b50a202a4e726d0a31e8a7cc4a82))

- **19-03**: Capture solver diagnostics in joint_refinement
  ([`7829607`](https://github.com/McGrathLab/AquaCal/commit/782960796645fffe6ad89728320fc9ae3fa208bd))

- **19-04**: Add capture_environment and capture_peak_memory
  ([`c637b86`](https://github.com/McGrathLab/AquaCal/commit/c637b868443411ad0a020a1b1a5c02dac5b6f8c0))

- **19-05**: Add assemble_benchmark_record()/write_benchmark_json()
  ([`ec798e2`](https://github.com/McGrathLab/AquaCal/commit/ec798e28c57293edbfdc5d9e960a5bdd48f4b704))

- **19-05**: Thread diagnostics_out and per-stage memory reads through pipeline
  ([`cbd4e4f`](https://github.com/McGrathLab/AquaCal/commit/cbd4e4fe7b206ad3d9d1e735bf0e2e1034303799))

- **19-05**: Write benchmark.json from run_calibration_from_config
  ([`1036b0b`](https://github.com/McGrathLab/AquaCal/commit/1036b0b53346e7d7f27b7a84648690652c63df08))

- **19-06**: Benchmarks/aggregate.py CSV aggregation with schema_version refusal
  ([`728818f`](https://github.com/McGrathLab/AquaCal/commit/728818f1789aee6399700ce16b0452dc7ce1549c))

- **19-06**: LaTeX fragment emission + sweep_runner.py grid skeleton
  ([`1e29995`](https://github.com/McGrathLab/AquaCal/commit/1e29995792626c183b3258f725ea31832ac8d052))

- **19.1-01**: Promote calibrate_synthetic/evaluate_reconstruction/compute_per_camera_errors
  ([`92bc11b`](https://github.com/McGrathLab/AquaCal/commit/92bc11baa5c4cb66563a9454d4dafedc27f1951f))

- **19.1-01**: Widen datasets barrel, shim experiment_helpers, promote build_interface_spread_report
  ([`9ae159d`](https://github.com/McGrathLab/AquaCal/commit/9ae159d32c6d1b035768f3dc69bdad32bfde24fa))

- **19.1-02**: Relocate benchmarks/ into experiments/ package
  ([`afe93ea`](https://github.com/McGrathLab/AquaCal/commit/afe93eab95daecb7e2b548f81218a9e32336f948))

- **19.1-03**: Add experiments/_io.py shared I/O layer
  ([`8496c47`](https://github.com/McGrathLab/AquaCal/commit/8496c47a7e35a6a3b9e373a1d61c022a9e36f71d))

- **19.1-04**: E2 full-frameset artifacts reproducing section-3 exactly
  ([`7c5917e`](https://github.com/McGrathLab/AquaCal/commit/7c5917ea45df3e463e345a1ab45ec6578d2e2196))

- **19.1-04**: E2 real-rig run artifacts and nine-row delta table
  ([`46ce4ee`](https://github.com/McGrathLab/AquaCal/commit/46ce4ee577d936c9c7196caefe121b4b394fbe4a))

- **19.1-04**: Port notebook 01's export cell to experiments/e2_real_rig.py
  ([`21e41cf`](https://github.com/McGrathLab/AquaCal/commit/21e41cffa8bd01800f0e96af79d418bacd6d6cf9))

- **19.1-05**: E7 four-arm ablation outputs (shared arm NON-CONVERGED, see SUMMARY)
  ([`258fda5`](https://github.com/McGrathLab/AquaCal/commit/258fda50c9144d981fffff1e6d10382da4755bcc))

- **19.1-05**: E7 four-arm ablation results (post Stage-2 fix)
  ([`ca421a7`](https://github.com/McGrathLab/AquaCal/commit/ca421a7ce061420815e7c04ac845d454087b6329))

- **19.1-05**: Emit ablation CSV, conditioning report, traces, benchmarks
  ([`ce3ce6c`](https://github.com/McGrathLab/AquaCal/commit/ce3ce6c9119694b8ae5b096593a86287e6194342))

- **19.1-05**: Four-arm interface ablation harness
  ([`8e8a640`](https://github.com/McGrathLab/AquaCal/commit/8e8a640b5c6d712d7d68dc731f720e0e27ded427))

- **19.1-06**: Port E1 refractive vs non-refractive comparison to experiments/
  ([`7dfcb2e`](https://github.com/McGrathLab/AquaCal/commit/7dfcb2e5ee46f7fd311199907c3a2e37b0676f2d))

- **19.1-06**: Replace committed exp{1,2,3} CSVs with E1's fresh run output
  ([`d9539cc`](https://github.com/McGrathLab/AquaCal/commit/d9539ccbe49a04ca1b5c2f24f5c3f5b735295cd9))

- **19.1-07**: Delete tests/synthetic/experiments.py and compare_refractive.py
  ([`706faf4`](https://github.com/McGrathLab/AquaCal/commit/706faf4b39c586f13c3d76e37165788b1e3b2118))

- **19.2-01**: Add memory_out and normal_fixed passthrough to calibrate_synthetic
  ([`686022d`](https://github.com/McGrathLab/AquaCal/commit/686022d4ca7ae82b5660584275be7ddd77b33fa1))

- **19.2-02**: Add n_residuals to SolverDiagnostics (EXP-08)
  ([`c2f9cc9`](https://github.com/McGrathLab/AquaCal/commit/c2f9cc92d80269fd5c5baed8a9b4cad74a14593c))

- **19.2-02**: Thread memory_readings and seed through write_direct_call_benchmark (D-24, review H5)
  ([`37de23a`](https://github.com/McGrathLab/AquaCal/commit/37de23aa0245cb4fc56ed319267ac3dd90ac7b22))

- **19.2-03**: Add public Newton-iteration diagnostic for refractive projection
  ([`39da216`](https://github.com/McGrathLab/AquaCal/commit/39da216098dd000453b70204b0bc672bf4603ad2))

- **19.2-05**: E3 skeleton, five-flag CLI, tier 1 rendering, sidecar
  ([`636e99e`](https://github.com/McGrathLab/AquaCal/commit/636e99ebc475d4d17ae70f97e8618681f0c31833))

- **19.2-05**: E3 tier 2 -- Newton iteration distribution over real rig
  ([`f4c56e9`](https://github.com/McGrathLab/AquaCal/commit/f4c56e9b83ec254c90d0565c16622b742eef9bac))

- **19.2-05**: GREEN -- E3 tier 3 CPR grouping, LaTeX fragments, committed artifacts
  ([`636673f`](https://github.com/McGrathLab/AquaCal/commit/636673fad0bef56e39ff3d2079db958f2cf2f43f))

- **19.2-06**: Re-run E2 with benchmark_memory to add stage-attributed memory (D-07)
  ([`427738f`](https://github.com/McGrathLab/AquaCal/commit/427738f37de23708361066a0500ed993c8432490))

- **19.2-07**: Rewrite E4 as direct-call synthetic benchmark grid
  ([`849daa4`](https://github.com/McGrathLab/AquaCal/commit/849daa4225b9a9e32a05fc286f6efd4a9a4279eb))

- **19.2-08**: Add E5 index-sensitivity sweep module (EXP-09)
  ([`344479d`](https://github.com/McGrathLab/AquaCal/commit/344479d69ce3897ccfb7ccbf1da0dc2ee91eadbd))

- **19.2-09**: Commit the ten-row E4 benchmark grid and LaTeX fragment
  ([`49b2428`](https://github.com/McGrathLab/AquaCal/commit/49b2428df4264e323fad2294d380a5d8e87677ed))

- **19.2-09**: Run E4 nine-cell synthetic benchmark grid
  ([`54f1d68`](https://github.com/McGrathLab/AquaCal/commit/54f1d68ba1a7622435c043841f2cacd0adb9ed14))

- **19.2-10**: Add E6 generalization sweep axes and per-configuration runner
  ([`d8c52bf`](https://github.com/McGrathLab/AquaCal/commit/d8c52bf7366578fc571b825f230cb648df0d9d4a))

- **19.2-11**: Run E6 three-axis generalization sweep (EXP-10)
  ([`3949e29`](https://github.com/McGrathLab/AquaCal/commit/3949e299b1b59f6c1a64d9d52b1f443176b65908))

- **19.2-13**: Run E5 production index-sensitivity band (EXP-09)
  ([`0a735b5`](https://github.com/McGrathLab/AquaCal/commit/0a735b53ce81ba7fa893baf666b40c31a53f21ab))

- **19.2-14**: Add seed to pipeline solver_config provenance
  ([`877634a`](https://github.com/McGrathLab/AquaCal/commit/877634ac94b9998268c196ad98311459ad6ec7ef))

- **19.2-15**: Coerce worst-cell loop to tolerate non-numeric cells in float-classified columns
  ([`4eb2bc5`](https://github.com/McGrathLab/AquaCal/commit/4eb2bc5bc601a88cf91f327cdfa49344b6dbeeb9))

- **19.2-15**: Make compare_experiment_csv total for row-count/key-set/duplicate-key inputs
  ([`c4678ac`](https://github.com/McGrathLab/AquaCal/commit/c4678aca156842177afcd2e29d55202a270a9481))

- **19.2-16**: E6 resume returns cached outcomes and gains four-field provenance
  ([`d1f79d9`](https://github.com/McGrathLab/AquaCal/commit/d1f79d99650b91af7571396c602a5225a1f4f732))

- **19.2-17**: Bound every E4 cell, observe a real death, guard paging (D-33)
  ([`20ac731`](https://github.com/McGrathLab/AquaCal/commit/20ac73196dc5691e14c5511f8536f8dce278c01b))

- **19.2-17**: Record commit/virtual memory beside the resident peak
  ([`179df0e`](https://github.com/McGrathLab/AquaCal/commit/179df0ea13b6a570b6bf425afb349c477389e9f3))

- **19.2-18**: D-27 -- centroid-default board trajectory with mechanical containment gate
  ([`d5d9dde`](https://github.com/McGrathLab/AquaCal/commit/d5d9dde1d8dad1cb20bcefe135a4a7031f4cdc3e))

- **19.2-18**: D-28/D-29 -- representative grid geometry, matching holdout, rescaled E6 axis
  ([`a2b244d`](https://github.com/McGrathLab/AquaCal/commit/a2b244dcf505eee0b640d9fd10e94ecf445a8783))

- **19.2-19**: Emit an E5 provenance sidecar carrying environment and run configuration
  ([`a349a2c`](https://github.com/McGrathLab/AquaCal/commit/a349a2c330ab161c0b21b81378018555728a6185))

- **19.2-20**: Instrument the batch Newton path production actually runs (D-32/CR-05)
  ([`20b0dfc`](https://github.com/McGrathLab/AquaCal/commit/20b0dfc250261bb59b43c31ab3d00e3d008843bb))

- **19.2-20**: Rewire E3 tier 2 to measure the production Newton loop (D-32/CR-05)
  ([`5b8ec1d`](https://github.com/McGrathLab/AquaCal/commit/5b8ec1d5f63bc29e9d183aeaccd016b82efbf843))

- **19.2-21**: Re-measure E4's nine-cell grid on fixed code
  ([`5b17cd4`](https://github.com/McGrathLab/AquaCal/commit/5b17cd464c704f204a3f927a306302c03edd6137))

- **19.2-22**: Re-measure E6's three-axis sweep on the redesigned geometry
  ([`242cb30`](https://github.com/McGrathLab/AquaCal/commit/242cb3089b1f1cde69c160ff7c1f78c0987cca52))

- **19.2-23**: Regenerate E5's band and E3's tiers with provenance sidecars
  ([`38fdbc7`](https://github.com/McGrathLab/AquaCal/commit/38fdbc7432664451b9588ef6d652235d289e06ac))

- **19.2-26**: Count every silent discard in the calibration path
  ([`6c7f930`](https://github.com/McGrathLab/AquaCal/commit/6c7f930bb56b019067b8eb7ac1f2c84d37be645e))

- **19.2-27**: Emit discard_stats from E5 for plan 23's attribution gate
  ([`914516c`](https://github.com/McGrathLab/AquaCal/commit/914516c0217f1a3caee3a504eafc08678a6b6d82))

- **19.2-27**: Record E6 solver optimality per configuration (WR-02)
  ([`7340534`](https://github.com/McGrathLab/AquaCal/commit/73405347e6a26b22f35aa67a677391ef5abec6f1))

- **19.2-28**: Re-run E6 with optimality capture -- three cells did not converge
  ([`9efc2da`](https://github.com/McGrathLab/AquaCal/commit/9efc2dad080032394b7b91066bc18d2660c34990))

- **19.2-29**: Re-run E5 for discard_stats -- bit-identical reproduction
  ([`04bb319`](https://github.com/McGrathLab/AquaCal/commit/04bb3198708ea952c81f73ebf1f8a6c5e32af91f))

- **19.3-02**: Record the final-solution degeneracy guard count in discard_stats
  ([`f9fac98`](https://github.com/McGrathLab/AquaCal/commit/f9fac98d380818085b1eed6fc3ba6fed1d07621f))

- **19.3-04**: Finish the real-rig standoff into the library default and presets
  ([`b8e057a`](https://github.com/McGrathLab/AquaCal/commit/b8e057ab49b53845bb91c50e588f6ac0f00cdbff))

- **19.3-05**: Derive GRID_DEPTH_RANGE from board_clearance_floor and thread board through
  build_grid_scenario
  ([`09b2a26`](https://github.com/McGrathLab/AquaCal/commit/09b2a261040520433057d428a59430ca10876837))

- **19.3-07**: Gate E4/E6 per-cell status on the final-solution guard count
  ([`c930112`](https://github.com/McGrathLab/AquaCal/commit/c930112e7bebb13108cbb4cfa73ad3f97467983f))

- **19.3-07**: Record the final-solution guard count in E1, E5 and E7
  ([`c79aff4`](https://github.com/McGrathLab/AquaCal/commit/c79aff4af5d929bfd00e4fb8919f66a43ad06566))

- **19.3-08**: Add machine-checkable gates for the re-run queue
  ([`04e6c97`](https://github.com/McGrathLab/AquaCal/commit/04e6c97a1f21b50304b80df40330ee59ab17f34d))

- **19.3-08**: Add the chained detached re-run queue with stage-level recovery
  ([`29b06a5`](https://github.com/McGrathLab/AquaCal/commit/29b06a570192a9a902bb184f8345fb3eaec2b95b))

- **19.3-09**: Add the scripted pre-launch abort gate and archive E3
  ([`22e75ef`](https://github.com/McGrathLab/AquaCal/commit/22e75ef2b424c9b0234502e5229345a9f5912b11))

- **19.3-09**: Re-measure all six experiments on the corrected geometry
  ([`ae91625`](https://github.com/McGrathLab/AquaCal/commit/ae91625fd90e69cbe18b2ffe9684c8b7c51866e5))

- **19.3-10**: Report the post-fix cell reproduction statistic
  ([`f1d4800`](https://github.com/McGrathLab/AquaCal/commit/f1d4800d2452cdb42b651c2628753ff634df7dde))

- **19.4-04**: Re-derive GRID_DEPTH_RANGE through a water_zs-parameterized helper
  ([`f6e8b0e`](https://github.com/McGrathLab/AquaCal/commit/f6e8b0ec0fee17d02baa87da54daf0ee51682037))

- **19.4-05**: Add parse_seed_list and run_seed_band shared band mechanism
  ([`c44b1f7`](https://github.com/McGrathLab/AquaCal/commit/c44b1f7816966c77b8de12acd6662f9deaba72c5))

- **19.4-05**: Wire --seeds band mode into E7 (D-19.4-14, SC-5a)
  ([`736e0a6`](https://github.com/McGrathLab/AquaCal/commit/736e0a66fd8b74101fc312c34c4d3eed1ba26fb3))

- **19.4-06**: Wire --seeds into E1 emitting exp1_band.csv
  ([`ee79645`](https://github.com/McGrathLab/AquaCal/commit/ee79645381f3f7c036cbac2b6b61fd5190a19ac6))

- **19.4-07**: Single-layer fail-fast in E6 with --no-fail-fast opt-out
  ([`c16f926`](https://github.com/McGrathLab/AquaCal/commit/c16f9266ec7b6316e0f8424361f5531a734fbe9d))

- **19.4-07**: Two-layer fail-fast in E4 with --no-fail-fast opt-out
  ([`aff546d`](https://github.com/McGrathLab/AquaCal/commit/aff546d02534847bd1e0eaf7114008a3bc665c35))

- **19.4-08**: Risk-first production queue, band gates, narrowed prelaunch gate
  ([`2a623f9`](https://github.com/McGrathLab/AquaCal/commit/2a623f9d09bc77bbbb1cfbd3188075bc8b8b4395))

- **19.5-01**: Add closed-form Jacobian shape predictor for COV-01
  ([`8b587f6`](https://github.com/McGrathLab/AquaCal/commit/8b587f6044eda3d04ad9dc91f675eae44a83b4c9))

- **19.5-01**: Add structural scaling sweep and committed artifact for COV-01
  ([`58d7798`](https://github.com/McGrathLab/AquaCal/commit/58d779825e03200aa82cd61b67f23d4993c3c3a3))

- **19.5-02**: CLI, step sweep, and committed FD-accuracy artifact
  ([`9f185a1`](https://github.com/McGrathLab/AquaCal/commit/9f185a1713516878c8973626e4b94963cd57f149))

- **19.5-02**: Pure FD-Jacobian accuracy functions + Wave 0 tests
  ([`225a92d`](https://github.com/McGrathLab/AquaCal/commit/225a92dd8c2f3509db4d6306bab3d13844b28a8c))

- **19.5-03**: CLI + committed e7_focal_standoff.csv artifact
  ([`3ae527c`](https://github.com/McGrathLab/AquaCal/commit/3ae527c5bc404541c8eb44680f27bd9214a4948c))

- **19.5-04**: Add frame-clustered bootstrap for reconstruction errors
  ([`72dbc36`](https://github.com/McGrathLab/AquaCal/commit/72dbc36fa49ea23a8f6e9788557e72b2f562d152))

- **19.5-04**: Write COV-08 bootstrap CI over reconstruction_errors.csv
  ([`abf87b1`](https://github.com/McGrathLab/AquaCal/commit/abf87b16d0948dcf5653c2662565bbbc52ad116f))

- **19.5-05**: Add --seeds band mode to E5 index sensitivity
  ([`5843691`](https://github.com/McGrathLab/AquaCal/commit/5843691ddc8785ffb3e7cd31931cf7e598fe8b80))

- **19.5-06**: Add E6 --seeds band mode with per-seed isolation (COV-03)
  ([`27750ba`](https://github.com/McGrathLab/AquaCal/commit/27750bad1d26e1cf8eb2cf864894222dca786fbe))

- **19.5-06**: Add opt-in n_cameras axis to E6 (COV-04)
  ([`d97dfad`](https://github.com/McGrathLab/AquaCal/commit/d97dfad166804c75338fa70993b10b0a6ec1db63))

- **19.5-07**: Add COV-07 seed-variant config generator + band CLI for E2
  ([`cbdf3a1`](https://github.com/McGrathLab/AquaCal/commit/cbdf3a1186c0fa3e96e815c576e311cd6edba9ee))

- **19.5-08**: COV-06 E4 repeat splice helper and --splice-repeat CLI
  ([`c11ac3d`](https://github.com/McGrathLab/AquaCal/commit/c11ac3d78d90b5ac41f4452e13faac73939710ab))

- **19.5-09**: Legality probe and four new band gates (D-19.5-04, COV-03..07)
  ([`b3442bc`](https://github.com/McGrathLab/AquaCal/commit/b3442bcc511485eb4a8a1ec2301a7191405a0502))

- **19.5-09**: Rerun_19_5.sh -- the risk-first production queue
  ([`1de567a`](https://github.com/McGrathLab/AquaCal/commit/1de567adf9df1e49afca3db1e25a44019c7911ed))

- **21-01**: Add scripts/extract_frames.py AVI-to-PNG extractor
  ([`35cd5ae`](https://github.com/McGrathLab/AquaCal/commit/35cd5ae5d97c52280e3f9aaed7d2dbea8f20e195))

- **21-04**: Delete Zenodo path from notebook 01, full editorial pass
  ([`f062a43`](https://github.com/McGrathLab/AquaCal/commit/f062a4379a61e717d5a7c20c9268ed55a8646e06))

- **21-04**: Demote notebook 02 default RIG_SIZE to small
  ([`143b7c9`](https://github.com/McGrathLab/AquaCal/commit/143b7c9874114a030d800b967345af7dc99a853a))

- **21-04**: Re-execute both tutorial notebooks with fresh outputs
  ([`c3a22cc`](https://github.com/McGrathLab/AquaCal/commit/c3a22cc90f3df59ce8d479d6681e456a3b1e1106))

- **260807-dcv**: E1 band emits z_rmse_mm; E1/E7 gain band-owned sidecars
  ([`cda9d0e`](https://github.com/McGrathLab/AquaCal/commit/cda9d0e453108cb25a72bf41b7f48cad3c44395b))

- **datasets**: Point real-rig at the published v2.0.0 Zenodo archive
  ([`25655f7`](https://github.com/McGrathLab/AquaCal/commit/25655f79f370f038362714bcf658d526e562dcf7))

### Performance Improvements

- **quick-3**: Use structural FD column grouping for board-observation Jacobian
  ([`3c8685c`](https://github.com/McGrathLab/AquaCal/commit/3c8685c05f9c030674014ad5ce3482d6fdc80de4))

### Refactoring

- Remove deprecated public API ahead of the 2.0.0 cut
  ([`0d82b82`](https://github.com/McGrathLab/AquaCal/commit/0d82b82d1d4af86a4d334b70803e52ba83cd814f))

- **16-07**: Pipeline calls evaluate_calibration for held-out validation
  ([`c27c747`](https://github.com/McGrathLab/AquaCal/commit/c27c747c7b782e3d72b4662a8057730ddaa69140))

- **18-06**: Bring pipeline.py console output and prose onto the three-stage model
  ([`e301ae9`](https://github.com/McGrathLab/AquaCal/commit/e301ae95b206fefee7cff42f6085a02a453f2ca5))

- **18-06**: Rename ex-Stage-4 machine surfaces to stage3_intrinsic_pass
  ([`8afddfc`](https://github.com/McGrathLab/AquaCal/commit/8afddfc19047a539cfb16a7910ad4d7de9354fbf))

- **19.2-08**: Extract compute_scale_bias into E1's one-origin formula
  ([`62cc60a`](https://github.com/McGrathLab/AquaCal/commit/62cc60aff5de62fcffea0b6aa266194a21f0a77c))

- **datasets**: Drop the dead min_cameras_per_frame parameter
  ([`0efbf2b`](https://github.com/McGrathLab/AquaCal/commit/0efbf2b2f0a1674fdd3d55f853207b313d113612))

- **experiments**: Move the three large E2 artifacts to the Zenodo archive
  ([`e0ef765`](https://github.com/McGrathLab/AquaCal/commit/e0ef765804a2d1f78aaa4748136077131dd05c90))

### Testing

- **16-02**: Add executable WP5 sweep-axis audit
  ([`25cf08a`](https://github.com/McGrathLab/AquaCal/commit/25cf08aa452906c7e15a835eeb9b0bb23e8cbd2f))

- **16-07**: Add evaluate_calibration tests incl. legacy-equivalence regression
  ([`f04a093`](https://github.com/McGrathLab/AquaCal/commit/f04a09358c52233730c2ade8265b4967b5c00811))

- **16-07**: Update pipeline mocks for shared evaluate_calibration, add refactor guards
  ([`375e1a1`](https://github.com/McGrathLab/AquaCal/commit/375e1a1fa36f32d5f7bd11f8d35c1686bbdc792d))

- **17-01**: Per-camera water_z packing, sparsity, grouping, labels
  ([`2f4cde5`](https://github.com/McGrathLab/AquaCal/commit/2f4cde595b64a5301bdcafc7a64e81bcc143a42f))

- **17-02**: Docs stub + shared_interface loader tests
  ([`fe5e70b`](https://github.com/McGrathLab/AquaCal/commit/fe5e70ba13a6c1f2c390153771b34d265ac0f48f))

- **17-04**: Seed resolver edge cases + spread report math
  ([`386defa`](https://github.com/McGrathLab/AquaCal/commit/386defafe3af38b5ca7548d5513e7ec27093969b))

- **17-05**: IFACE-05 bit-identity + equal-seed recovery safety net
  ([`2bb5ba6`](https://github.com/McGrathLab/AquaCal/commit/2bb5ba6b0fcd3df22136693953f1ff2a4362a963))

- **18-01**: Pin DOCS-01 grouping numbers to live derivation
  ([`70d6382`](https://github.com/McGrathLab/AquaCal/commit/70d63825287648c34dfe714dcc0c0ca0f9c2f943))

- **19-04**: Add failing tests for capture_environment and capture_peak_memory
  ([`1b11f94`](https://github.com/McGrathLab/AquaCal/commit/1b11f947e2590c805f130c41cc43b471a1e4f942))

- **19.1-01**: Zero-numerical-change and export-surface tests for pipelines.py
  ([`f367798`](https://github.com/McGrathLab/AquaCal/commit/f3677987930608f841e6e430f9e97e046eedf6cb))

- **19.1-02**: Relocate aggregator tests, drop sys.path hack
  ([`9a0ec16`](https://github.com/McGrathLab/AquaCal/commit/9a0ec1641ff77df9b9fd1ebd8f87675030a7cd0c))

- **19.1-03**: Add tests/unit/test_experiments_io.py
  ([`f4516eb`](https://github.com/McGrathLab/AquaCal/commit/f4516eb8023098b1753f3238a5f6d1903f014ccc))

- **19.2-01**: Add exact-equality guards for memory_out, n_air/n_water, and normal_fixed
  ([`d20e2e0`](https://github.com/McGrathLab/AquaCal/commit/d20e2e0f23683e3c5fd1793edf1badf7eedeb900))

- **19.2-03**: Add bit-exactness guard and behavior tests for Newton diagnostic
  ([`a44f05b`](https://github.com/McGrathLab/AquaCal/commit/a44f05b91de332dd32cad1f7d852abda553f9e83))

- **19.2-04**: Declare E3 tier 1 code-constants table asserted against live values (D-18)
  ([`a016924`](https://github.com/McGrathLab/AquaCal/commit/a01692449662e14ff6fc43ceb48db471d54f3cfb))

- **19.2-04**: Validate the P formula against live pack_params length (D-22)
  ([`682b7f8`](https://github.com/McGrathLab/AquaCal/commit/682b7f86dbaddd44e4a136a5fc8e87c0091c5379))

- **19.2-05**: RED -- E3 tier 3 CPR grouping and LaTeX fragment behaviors
  ([`1ae80e6`](https://github.com/McGrathLab/AquaCal/commit/1ae80e6377507368ed2d9f424d19817fe5a723fc))

- **19.2-07**: CLI wiring, smoke mode, and unit tests for the E4 grid
  ([`4d121d8`](https://github.com/McGrathLab/AquaCal/commit/4d121d83778dcf64e7e95f9db75b80c468431592))

- **19.2-10**: Add E6 schema, CLI, and smoke-mode tests
  ([`058cf38`](https://github.com/McGrathLab/AquaCal/commit/058cf381c29c62cd2c13c7a4dcecd81158eccbfc))

- **19.2-12**: Assert provenance mechanically over every committed result
  ([`896962d`](https://github.com/McGrathLab/AquaCal/commit/896962d469cb26af516b7b642b2ca8536914b251))

- **19.2-14**: Prove the solver_config seed addition is inert
  ([`85cc8e3`](https://github.com/McGrathLab/AquaCal/commit/85cc8e3660cfc8520ee9916ef05fbd12e48737ee))

- **19.2-14**: Regenerate the ideal-preset anchor invalidated by D-27
  ([`4ed8259`](https://github.com/McGrathLab/AquaCal/commit/4ed825927fc9aa399df01724f4dd42a0c03f767f))

- **19.2-15**: Add failing regression test for worst-cell loop non-numeric coercion crash
  ([`d490f1f`](https://github.com/McGrathLab/AquaCal/commit/d490f1f3dc7195d62a0feedf353481f77cd7c652))

- **19.2-15**: Add failing regression tests for CR-04 row-count/key-set/duplicate-key crashes
  ([`dc51631`](https://github.com/McGrathLab/AquaCal/commit/dc51631ac314d4b9d6e9be6c87521f4cc986c4bc))

- **19.2-16**: Add failing tests for E6 resume path + provenance (CR-02, WR-08, D-31)
  ([`b4a8dcd`](https://github.com/McGrathLab/AquaCal/commit/b4a8dcd3131e7dd72a14f4eb66427e7a5d9efe13))

- **19.2-17**: Cover the near-ceiling branch of _classify_memory_pressure
  ([`012c7f2`](https://github.com/McGrathLab/AquaCal/commit/012c7f21ac9b0b01b77fc2d4fb63b5126c87187c))

- **19.2-24**: Widen EXP-11 gate to four fields per artifact, per file
  ([`d2fc7d6`](https://github.com/McGrathLab/AquaCal/commit/d2fc7d662c4b19f0b71a9a841529f440ee3ea960))

- **19.2-26**: Capture the pre-instrumentation numerical anchor
  ([`4aa296d`](https://github.com/McGrathLab/AquaCal/commit/4aa296d2ae49019ad98980750063fd007b4459cc))

- **19.2-27**: Prove diagnostics_out/discard_stats_out are numerically inert
  ([`a0322a0`](https://github.com/McGrathLab/AquaCal/commit/a0322a0fafe09ea39d6e7dd41f549b4505a62eed))

- **19.3**: Add the overnight seed-sweep harness for E1 and E6 noise floors
  ([`f6ee934`](https://github.com/McGrathLab/AquaCal/commit/f6ee934baee9a0348b06b658006ba9cdce43707e))

- **19.3-02**: Prove the degeneracy-guard-count sink is inert by exact equality
  ([`0a4119b`](https://github.com/McGrathLab/AquaCal/commit/0a4119bcbaa6b9f861a6dbc23936a3aa67bae604))

- **19.3-04**: Regenerate the two frozen anchors 19.3-04's own standoff change moved
  ([`f59637b`](https://github.com/McGrathLab/AquaCal/commit/f59637b30b54c3ee5ed7c9959c86d1c690445fb2))

- **19.3-06**: Prove every E6 axis value is legal, correct scale-axis prose
  ([`e840375`](https://github.com/McGrathLab/AquaCal/commit/e840375694c903bc556e3efa8b2d03cfbbf7cd41))

- **19.3-10**: Retire a time-bound guard and narrow a glob to its stated scope
  ([`8b6d725`](https://github.com/McGrathLab/AquaCal/commit/8b6d72572eceda33fb85e9be7abb6e555a02f688))

- **19.4-02**: Add scenario-invariant single-water_z and h_c preservation proof
  ([`12fa9e6`](https://github.com/McGrathLab/AquaCal/commit/12fa9e6354acea532d4f091b44e20e6dfbfede80))

- **19.4-02**: Repair fallout from the water_z-to-C_z jitter relocation
  ([`03e6656`](https://github.com/McGrathLab/AquaCal/commit/03e665683119d6cc1a687ae91ca01b1b54f23914))

- **19.4-04**: Exact-value and seed/camera-count-invariance for the derived floor
  ([`9f93e5b`](https://github.com/McGrathLab/AquaCal/commit/9f93e5b26443a07fca1a8f52b062e2fc1e993c8d))

- **19.4-04**: Prove E1/E3/E5/E7 inert at the source level post-fix
  ([`22c06a1`](https://github.com/McGrathLab/AquaCal/commit/22c06a1c3f280528b837bfc0f560dbac6acb4384))

- **19.5**: Register the two seed bands and gate band seed coverage
  ([`9444f96`](https://github.com/McGrathLab/AquaCal/commit/9444f96978a59867ada37ffbdf8ff045bffa29e6))

- **19.5**: Register wave 1's three new CSVs in CSV_TO_RECORD
  ([`bbc5791`](https://github.com/McGrathLab/AquaCal/commit/bbc5791e93980ad1f0f6b3f144cad9a92dea5ff1))

- **19.5**: Route solve-spinning experiment tests out of the fast CI lane
  ([`2fc9266`](https://github.com/McGrathLab/AquaCal/commit/2fc92665a9f4334ff2c9d5f57293710b303dc353))

- **19.5-03**: Paired focal/standoff association functions and tests
  ([`c1efbef`](https://github.com/McGrathLab/AquaCal/commit/c1efbeff7d7381b8b44449a28b48940a2573da2f))

- **19.5-05**: Add E5 band-mode CLI, band, and distinguishability coverage
  ([`c59901d`](https://github.com/McGrathLab/AquaCal/commit/c59901d45c81407c1adfbb6a078d3abcf64e54e3))

- **19.5-10**: Carry the six-seed band through test_rerun_gates fixtures
  ([`fbf89d5`](https://github.com/McGrathLab/AquaCal/commit/fbf89d5adb5a76e53f4cc3c90def669eef9a741d))

- **21-01**: Unit tests for scripts/extract_frames.py
  ([`ec2ce56`](https://github.com/McGrathLab/AquaCal/commit/ec2ce5612461909c53fd393fcac8187e9161541b))

- **21-12**: Pin n_water=1.0 pinhole-equals-refractive identity
  ([`2751021`](https://github.com/McGrathLab/AquaCal/commit/2751021ceb8b2e46d7974ea8ef5a8a4122e0c9f0))

- **quick-3**: Cover structural column grouping validity and equivalence
  ([`a0df1c7`](https://github.com/McGrathLab/AquaCal/commit/a0df1c7d83ca281afa3a5b5da5554d0e64155702))

### Breaking Changes

- Python 3.10 is no longer supported. Requires Python >=3.11.


## v1.8.0 (2026-07-20)

### Documentation

- Refresh commit hash references after rebase onto v1.7.1
  ([`0fbcbb2`](https://github.com/McGrathLab/AquaCal/commit/0fbcbb28b6e8576cfa9f5a713c7799bf5847ccac))

- **debug**: Close out callibration071626 and rig-tilt debug sessions
  ([`2dd0cff`](https://github.com/McGrathLab/AquaCal/commit/2dd0cff5c17d7e443fd388bcbd8c00da0f522cf7))

- **quick-2**: Complete reject_outlier_frames config discoverability task
  ([`00dc76a`](https://github.com/McGrathLab/AquaCal/commit/00dc76a0b7a62ac4976a01839aae826d319b7d3f))

- **quick-2**: Record quick task 2 in STATE.md
  ([`0ebbe28`](https://github.com/McGrathLab/AquaCal/commit/0ebbe28977e3149278a3261f0040d532c4b69696))

### Features

- **config**: Emit reject_outlier_frames as an active line in generated configs
  ([`8b6eb0d`](https://github.com/McGrathLab/AquaCal/commit/8b6eb0d46a782e65204610b0cc10a90cf44de480))

- **intrinsics**: Seed calibration and warn on fronto-parallel board views
  ([`16fd84f`](https://github.com/McGrathLab/AquaCal/commit/16fd84f111f8c0aba8fe4a67894e7401aeed69d2))

### Testing

- **cli**: Assert generated config exposes reject_outlier_frames as True
  ([`5222a57`](https://github.com/McGrathLab/AquaCal/commit/5222a5790d410e867b8c16f1da4bffac9825266b))


## v1.7.1 (2026-07-16)

### Bug Fixes

- **metadata**: Correct stale package metadata, URLs, and version references
  ([`0ba9f96`](https://github.com/McGrathLab/AquaCal/commit/0ba9f968ed07daf4c0acdf8c3337389230829947))


## v1.7.0 (2026-07-15)

### Documentation

- **planning**: Add rig-tilt debug session and inbox notes
  ([`a87f28f`](https://github.com/McGrathLab/AquaCal/commit/a87f28f17d9caea7364fbd6f9a13b99076d88ede))

- **troubleshooting**: Explain weakly-observable camera layout
  ([`ed500c2`](https://github.com/McGrathLab/AquaCal/commit/ed500c2bd1ba688adcb7647dc65de3eb6b2967ea))

### Features

- Add outlier-frame rejection and detection.stop_frame
  ([`e4be63a`](https://github.com/McGrathLab/AquaCal/commit/e4be63a971cb185ee8c2ec1efd786889fe6c548c))

- **detection**: Add detection.start_frame to skip leading extrinsic frames
  ([`9f3ccf5`](https://github.com/McGrathLab/AquaCal/commit/9f3ccf51f53795dbe888a3f3c7e059faf68686b1))


## v1.6.0 (2026-05-05)

### Continuous Integration

- Exclude tutorial notebooks from detect-secrets
  ([`ae6f769`](https://github.com/tlancaster6/AquaCal/commit/ae6f7695c8ee4b2636bf6108b2f9be1c4d3af230))

- **docs**: Add ipython to [docs] extra for nbsphinx lexer
  ([`c60acaf`](https://github.com/tlancaster6/AquaCal/commit/c60acaf8866770ed760b9ff86079bb2bf16117ce))

- **docs**: Install docs extras in workflow
  ([`61825d3`](https://github.com/tlancaster6/AquaCal/commit/61825d36764e5f8150823dcfe40e191f70ce6d54))

- **docs**: Install pandoc for nbsphinx
  ([`09b58dc`](https://github.com/tlancaster6/AquaCal/commit/09b58dcd4611ddd2872257cdf03ac91dec8e33c8))

### Documentation

- Add validation + refinement features to README, mark refinement beta
  ([`efe8588`](https://github.com/tlancaster6/AquaCal/commit/efe8588946fbc552de3841bfc16d0971030c2455))

- Remove WIP status warning from README
  ([`5ee0a51`](https://github.com/tlancaster6/AquaCal/commit/5ee0a51824233b80836427121a3412189a47accb))

### Features

- Persist per-stage calibration timings to diagnostics.json
  ([`e3cf40d`](https://github.com/tlancaster6/AquaCal/commit/e3cf40d1432a4a86d964784c156f8633855bef40))


## v1.5.0 (2026-03-09)

### Bug Fixes

- Variable name typo fix
  ([`72eff64`](https://github.com/tlancaster6/AquaCal/commit/72eff64564c7e9040ddbe6e36b6f2a71518f6f11))

- Variable name typo fix
  ([`0010db2`](https://github.com/tlancaster6/AquaCal/commit/0010db25738fbb86cb13f780f0627e643ae6eb11))

### Chores

- Complete v1.6 Refinement API milestone
  ([`1af31b8`](https://github.com/tlancaster6/AquaCal/commit/1af31b801e5ab8c0c171b93a602937e6f1f8f4e2))

### Documentation

- Capture todo - Add active calibration refinement API for downstream consumers
  ([`3931863`](https://github.com/tlancaster6/AquaCal/commit/393186343b2ebb5e9a19d2b4a11af21c75be6782))

- Capture todo - Upload new Zenodo dataset with image-based inputs
  ([`cc777a1`](https://github.com/tlancaster6/AquaCal/commit/cc777a188475b574b5403476435e985638501454))

- Create milestone v1.6 roadmap (3 phases)
  ([`6c5c8a4`](https://github.com/tlancaster6/AquaCal/commit/6c5c8a48babd52ec09b40e8d0ebf224a29548f14))

- Define milestone v1.6 requirements
  ([`bd1054d`](https://github.com/tlancaster6/AquaCal/commit/bd1054d63de366dc075c90bb6c2ca978f49eb491))

- Enhance tutorial notebooks with new visualizations, data export, and Colab support
  ([`70df96d`](https://github.com/tlancaster6/AquaCal/commit/70df96d01b271635d72182b74746887f1db98f2b))

- Start milestone v1.6 Refinement API
  ([`81ba39f`](https://github.com/tlancaster6/AquaCal/commit/81ba39f0712597ffe81d1026fc6eb1d76abc9789))

- Update tutorials with per-camera diagnostics, data export, and technique report
  ([`92a120c`](https://github.com/tlancaster6/AquaCal/commit/92a120c8e6d6bb3431390d6426e09ed1e2dedaae))

- **13**: Capture phase context
  ([`de67db9`](https://github.com/tlancaster6/AquaCal/commit/de67db91f0141cfb0f8d0c4c5e0973e21fa6740c))

- **13**: Create phase plan
  ([`4fb5240`](https://github.com/tlancaster6/AquaCal/commit/4fb52400959d58a55c5dfdfff24c68bd50cb3102))

- **13-01**: Complete core refinement API plan
  ([`05e498d`](https://github.com/tlancaster6/AquaCal/commit/05e498d8cd7bf7aea0f1df72c0158a3bf1e6f546))

- **13-02**: Complete point refinement tests plan
  ([`56af3aa`](https://github.com/tlancaster6/AquaCal/commit/56af3aa0c56489035ea45e8b9e38e80fb2528e05))

- **14**: Capture phase context
  ([`ef73dff`](https://github.com/tlancaster6/AquaCal/commit/ef73dff5ec94ef92f04fddd6b046c2ac4f689f85))

- **14**: Create phase plan for optimization extensions
  ([`d3a0fa8`](https://github.com/tlancaster6/AquaCal/commit/d3a0fa8f9ece6beb0a0f7f9d39354801b8e1a875))

- **14-01**: Complete plan execution summary
  ([`b0b4cf0`](https://github.com/tlancaster6/AquaCal/commit/b0b4cf040efc25cbafc70cdf7d1605be4fb4ae62))

- **14-02**: Complete plan execution summary
  ([`c6f22b2`](https://github.com/tlancaster6/AquaCal/commit/c6f22b2f3d526cd5951f7d52d86332e7719f3a5a))

- **15**: Add edge case note for holdout split minimum
  ([`fa44671`](https://github.com/tlancaster6/AquaCal/commit/fa4467139ae636f091dd579143c055234f70e5d8))

- **15**: Capture phase context
  ([`574ce9e`](https://github.com/tlancaster6/AquaCal/commit/574ce9edf2c993358ee8219d267631b5e98ae908))

- **15**: Create phase plans for validation and result contract
  ([`6a3727d`](https://github.com/tlancaster6/AquaCal/commit/6a3727d7a2b97cd20e664f7364f338d0cd7b5de6))

- **phase-13**: Complete phase execution
  ([`3f05d21`](https://github.com/tlancaster6/AquaCal/commit/3f05d213d94368f2fd4c3af936e45b590a7156c8))

- **phase-14**: Complete phase execution
  ([`c6fc987`](https://github.com/tlancaster6/AquaCal/commit/c6fc987925de48196d65ef973414090f2dccd0c8))

- **phase-15**: Complete phase execution
  ([`e246a9a`](https://github.com/tlancaster6/AquaCal/commit/e246a9ae0b3af7950133d3dc7616d0e65303a118))

- **quick-1**: Add calibration-file-based synthetic rig to 02_synthetic_validation
  ([`eac1132`](https://github.com/tlancaster6/AquaCal/commit/eac1132644a7c7861f6b2b0fc04f102220efd356))

- **quick-1**: Complete add-calibration-file-based-synthetic-rig plan
  ([`a24c8d6`](https://github.com/tlancaster6/AquaCal/commit/a24c8d62ee5788ae1b59ceaafc39132949eac169))

### Features

- Batch projection in residuals, per-camera labels in diagnostics
  ([`4c586d6`](https://github.com/tlancaster6/AquaCal/commit/4c586d614d1e3467455a44b1a9f569b385d8c6b2))

- **13-01**: Add PointCorrespondence dataclass and export from public API
  ([`52c0ceb`](https://github.com/tlancaster6/AquaCal/commit/52c0cebd44f5fa74e9bc0b7e3b9b51e00e886a70))

- **13-01**: Implement refine_calibration() with point correspondence bundle adjustment
  ([`929d64c`](https://github.com/tlancaster6/AquaCal/commit/929d64c3b4d0fe816d4475aea16d1fb24e5ff964))

- **13-01**: Wire refine_calibration into public API and calibration package
  ([`3832637`](https://github.com/tlancaster6/AquaCal/commit/38326371b7e3742833c8eb6f7c45e42464f7b8fa))

- **14-01**: Extend refine_calibration with intrinsics, loss, and tilt
  ([`6f98e17`](https://github.com/tlancaster6/AquaCal/commit/6f98e1741f6a678880b075ca16ceefee88d96503))

- **15-01**: Add CameraDrift, ValidationReport, RefinementResult dataclasses
  ([`dc6361d`](https://github.com/tlancaster6/AquaCal/commit/dc6361d3f2636dc566826585a585c17229b2331d))

- **15-01**: Add validation module with holdout, triangulation, drift checks
  ([`85a6bf7`](https://github.com/tlancaster6/AquaCal/commit/85a6bf771859eb235e4081dfd4696f7ebd16b100))

- **15-01**: Export RefinementResult, ValidationReport, CameraDrift from aquacal
  ([`081fa43`](https://github.com/tlancaster6/AquaCal/commit/081fa43a80538e1034d6b8987d9bee28abb36ef0))

- **15-01**: Update refine_calibration to return RefinementResult with validation
  ([`cf73c9a`](https://github.com/tlancaster6/AquaCal/commit/cf73c9a0d2c914ec5028b5bfb74667fab34c906f))

- **quick-1**: Add calibration file support to synthetic validation notebook
  ([`e849bca`](https://github.com/tlancaster6/AquaCal/commit/e849bca59e9992379eceb6a7ac1dfdb2438dc4c9))

- **quick-1**: Add rig_from_calibration() to datasets API
  ([`8743756`](https://github.com/tlancaster6/AquaCal/commit/8743756d30bbd5689a0d3e3ead6fcdfe38793c20))

### Refactoring

- Simplify datasets module — rename generate_synthetic_rig to create_scenario, remove bundled small
  dataset
  ([`38047a2`](https://github.com/tlancaster6/AquaCal/commit/38047a28642b50347a0a0d1fc4892522bd09ed84))

### Testing

- Update synthetic tests and pipeline tests for new datasets API and batch projection
  ([`2ef1c5f`](https://github.com/tlancaster6/AquaCal/commit/2ef1c5fbd401838be29b0ff728cb80e9a8e6ea69))

- **13-02**: Add synthetic data fixtures for point refinement tests
  ([`cf30c61`](https://github.com/tlancaster6/AquaCal/commit/cf30c61885553f2b849d8acfa560b21259613a88))

- **14-02**: Add tests for intrinsics refinement, robust loss, and tilt
  ([`0d846ff`](https://github.com/tlancaster6/AquaCal/commit/0d846ffee2a8288be66113786f51e16d84947a23))

- **15**: Complete UAT - 7 passed, 0 issues
  ([`1719101`](https://github.com/tlancaster6/AquaCal/commit/17191010be0cee15a0f28e39240b46bcf7f0e732))

- **15-02**: Add unit tests for validation module
  ([`a4a0bff`](https://github.com/tlancaster6/AquaCal/commit/a4a0bfff65e322fdffb2dcac97dafb8290cbf937))

- **15-02**: Update test_point_refinement for RefinementResult return type
  ([`e32bb0a`](https://github.com/tlancaster6/AquaCal/commit/e32bb0a00669183d2669746180a6bc5c910b3b82))


## v1.4.2 (2026-02-19)

### Bug Fixes

- Variable name typo fix
  ([`0b6643c`](https://github.com/tlancaster6/AquaCal/commit/0b6643c0bec1122f9872fa189094c1e49e1fd2da))

- Variable name typo fix
  ([`b77b863`](https://github.com/tlancaster6/AquaCal/commit/b77b863b774325192427bdb9a9ab2513fe919dcd))

### Chores

- Complete v1.4 QA & Polish milestone
  ([`a0087ef`](https://github.com/tlancaster6/AquaCal/commit/a0087ef0b64fa00dc5ee2f06dd729820612579df))

### Documentation

- Create milestone v1.5 roadmap (5 phases)
  ([`c8ca625`](https://github.com/tlancaster6/AquaCal/commit/c8ca625f353f4c02711db3525337cc536b518d70))

- Define milestone v1.5 requirements
  ([`2595922`](https://github.com/tlancaster6/AquaCal/commit/25959226eb4e5f41dd96112e904bc3ce98dcc1d5))

- Start milestone v1.5 AquaKit Integration
  ([`e8cb0c3`](https://github.com/tlancaster6/AquaCal/commit/e8cb0c3270ae07e7744fd147d20daa984fadc102))


## v1.4.1 (2026-02-19)

### Bug Fixes

- **docs**: Resolve Sphinx build warnings and RTD pandoc requirement
  ([`9e1b285`](https://github.com/tlancaster6/AquaCal/commit/9e1b2854672b4c21bc4e03731adf88fa09cc83f5))

### Documentation

- Capture todo - Check version field in JSON output reads local version properly
  ([`9409e66`](https://github.com/tlancaster6/AquaCal/commit/9409e664a96af5c5ea1da2fde721766ccda69704))

- Dropping readme image and refining tutorial notebooks
  ([`a338969`](https://github.com/tlancaster6/AquaCal/commit/a338969f0a51c012603e8496dc7cc84f230558c2))


## v1.4.0 (2026-02-18)

### Bug Fixes

- **11-02**: Simplify Mermaid pipeline, revert hero image to original
  ([`9a192ee`](https://github.com/tlancaster6/AquaCal/commit/9a192ee361d1a0f14edb20ab1d833650e0a10497))

- **12**: Remove redundant _temp_result in tutorial 01
  ([`d419203`](https://github.com/tlancaster6/AquaCal/commit/d4192034250e28f8fa05ff6afc3842fcf00ecdeb))

- **12**: Rename tutorial 01 data sources to synthetic-1/synthetic-2/zenodo
  ([`f3e262b`](https://github.com/tlancaster6/AquaCal/commit/f3e262b637c10b76cfa1ac8f6936d7772f8f154d))

- **12**: Revise plan 02 based on checker feedback
  ([`01c8995`](https://github.com/tlancaster6/AquaCal/commit/01c8995a487c300b13868cf2e77aaf4eb1adf894))

- **12**: Rewrite tutorial 01 to support both synthetic and real data
  ([`57cd904`](https://github.com/tlancaster6/AquaCal/commit/57cd904d4afd1ba318afd38e108d1dee6d37d96a))

### Documentation

- **11**: Capture phase context
  ([`d813dc4`](https://github.com/tlancaster6/AquaCal/commit/d813dc48b4419feb78287da165ba0261a2d40248))

- **11**: Create phase plan
  ([`94cfabe`](https://github.com/tlancaster6/AquaCal/commit/94cfabebb8f49dd05a252b4e21f5ceefac481544))

- **11-01**: Complete visual foundation plan
  ([`24b39ce`](https://github.com/tlancaster6/AquaCal/commit/24b39ced52dfd8d8d5913a532ef76fb2291304b1))

- **11-02**: Complete visual aids plan with user approval
  ([`c367394`](https://github.com/tlancaster6/AquaCal/commit/c367394e9d9320898f7abda9fb4e31a6caeee845))

- **12**: Capture phase context
  ([`9f679ab`](https://github.com/tlancaster6/AquaCal/commit/9f679ab38a52032f8104cedd43e8d9c25ded5ea3))

- **12**: Create tutorial verification phase plan
  ([`2f34784`](https://github.com/tlancaster6/AquaCal/commit/2f34784325fd4f7d444687cd8a378a04a7747c1b))

- **12-01**: Add self-check results to summary
  ([`1b98218`](https://github.com/tlancaster6/AquaCal/commit/1b98218fa001337ae2d41e1e6751301db9d6de54))

- **12-01**: Complete tutorial restructure plan
  ([`7a2cd1a`](https://github.com/tlancaster6/AquaCal/commit/7a2cd1ab8d1de831b71e6df39c362d95e68d6b57))

- **12-02**: Complete tutorial rewrite and execution plan
  ([`041b338`](https://github.com/tlancaster6/AquaCal/commit/041b338da54c77827a665dd4c025fb17d85449eb))

- **phase-11**: Complete phase execution
  ([`b39cc76`](https://github.com/tlancaster6/AquaCal/commit/b39cc76901e191e6abf72416bc65a457d6993283))

### Features

- **11-01**: Create color palette, style guide, and hero image
  ([`d77ff6b`](https://github.com/tlancaster6/AquaCal/commit/d77ff6bcf5b8a20067ce7a2d91dde60a1282ebde))

- **11-01**: Update existing diagrams to use shared palette
  ([`2f8575e`](https://github.com/tlancaster6/AquaCal/commit/2f8575e50590352bcb6cf906c4676bb6a99193a0))

- **11-02**: Add color styling to Mermaid pipeline diagram
  ([`23f55d9`](https://github.com/tlancaster6/AquaCal/commit/23f55d9ac383a7e1fb27f3a04410ec22cee3155d))

- **11-02**: Add Mermaid pipeline, sparsity pattern, and BFS pose graph diagrams
  ([`298167d`](https://github.com/tlancaster6/AquaCal/commit/298167d46f991d0c320cf355cbd39affc89a7d7e))

- **12**: Add calibrate_from_detections API and simplify tutorials
  ([`08fb65c`](https://github.com/tlancaster6/AquaCal/commit/08fb65c8310ecf2aa01c1ab1ebbd059554a92d09))

- **12-01**: Merge diagnostics into tutorial 01, restructure to 2 tutorials
  ([`f00d437`](https://github.com/tlancaster6/AquaCal/commit/f00d43781e8071ae5d683af5c9fe4c55bace2cb8))

- **12-01**: Update tutorial index for 2-tutorial structure
  ([`7f0439a`](https://github.com/tlancaster6/AquaCal/commit/7f0439ab6748b03be1f2a09a6e7fcf4240b23887))

- **12-02**: Execute tutorials and fix API bugs
  ([`10791a6`](https://github.com/tlancaster6/AquaCal/commit/10791a67025714474efed86da72417c78b909412))

- **12-02**: Rewrite tutorial 02 with three progressive experiments
  ([`5047cf4`](https://github.com/tlancaster6/AquaCal/commit/5047cf499e0b1a0affbad53c1bb1d61092dfa02a))


## v1.3.2 (2026-02-17)

### Bug Fixes

- **tests**: Rename initial_distances to initial_water_z in test code
  ([`db78ffd`](https://github.com/tlancaster6/AquaCal/commit/db78ffdc706973691d8561210dcb8e623901ee08))

### Chores

- Add pre-push hooks and detect-secrets scanning
  ([`f5b3de9`](https://github.com/tlancaster6/AquaCal/commit/f5b3de96fee20a23efb4c0b710204337797e7d7b))

- Move pre-push hook scripts from scripts/ to .hooks/
  ([`a129cc8`](https://github.com/tlancaster6/AquaCal/commit/a129cc8c407e05aaf9849089cc6ded430a7853a1))

- Remove docs-build from pre-push hooks to speed up push
  ([`45c32bd`](https://github.com/tlancaster6/AquaCal/commit/45c32bd56e28f8f6d56be7e28abc0ff8fdcba084))

- Updating readme with a repo status message
  ([`2723536`](https://github.com/tlancaster6/AquaCal/commit/2723536b7af9df2e00dca8a00ed667430dd89f7f))

### Documentation

- Adding a note in CONTRIBUTING.md about building docs locally if they have been modified
  ([`0dc26ce`](https://github.com/tlancaster6/AquaCal/commit/0dc26ce4fa8f10c36867a2dbb8f5fafa540f703b))

### Testing

- Small assertion fix
  ([`a498021`](https://github.com/tlancaster6/AquaCal/commit/a4980215b93bd0d3d20fa2da5a60ed5aaf2abeb8))


## v1.3.1 (2026-02-17)

### Bug Fixes

- Cleaning up missed initial_distance to initial_water_z parameter name changes and elevating the
  associated DeprecationWarning to a UserWarning so that users see it when running from the CLI
  ([`a49fef1`](https://github.com/tlancaster6/AquaCal/commit/a49fef1406f8444e52593dacc3fb577c2ef37134))

- **cli**: Improve init config generation, dry-run output, and error messages
  ([`0220c44`](https://github.com/tlancaster6/AquaCal/commit/0220c4406cacb015b2a9408b0e41837a0ea205ff))

- **intrinsics**: Auto-simplify distortion model when roundtrip validation fails
  ([`0863fae`](https://github.com/tlancaster6/AquaCal/commit/0863fae1e2e88a3e6376fb74a23442f5ec045828))

### Chores

- Fixing DOI badge placeholder
  ([`a8d07c3`](https://github.com/tlancaster6/AquaCal/commit/a8d07c34cff1b547c9b7deca2aeb960aa6b7d7aa))

- Plan updates
  ([`57496f8`](https://github.com/tlancaster6/AquaCal/commit/57496f8ec5f4ba3c687a386f56c5b6a154e28bb0))

### Documentation

- Create milestone v1.4 roadmap (7 phases)
  ([`e4a25f3`](https://github.com/tlancaster6/AquaCal/commit/e4a25f3a2db635f9ca6c7fc7b69bbfa53865692f))

- Define milestone v1.4 requirements
  ([`d8b32a2`](https://github.com/tlancaster6/AquaCal/commit/d8b32a29e5d30bca87b61d96abcbfa4f9d5baacd))

- Fix milestone version to v1.4 (v1.3 already released)
  ([`d43c61e`](https://github.com/tlancaster6/AquaCal/commit/d43c61e6551c2b561eb8d7f5bab112a9a1bf4a68))

- Start milestone v1.3 QA & Polish
  ([`54047d8`](https://github.com/tlancaster6/AquaCal/commit/54047d8ede17cb6c414a288777ba6dd8c1b24e0a))

- **07**: Create infrastructure check phase plan
  ([`d98e5a1`](https://github.com/tlancaster6/AquaCal/commit/d98e5a10ad92763d9d01da3a2b02fd61332855ad))

- **07-01**: Complete infrastructure check plan
  ([`a3f54bb`](https://github.com/tlancaster6/AquaCal/commit/a3f54bb535550e820f95b207832f51f85c94eb0e))

- **08-cli-qa-execution**: Create phase plan
  ([`8c63789`](https://github.com/tlancaster6/AquaCal/commit/8c63789bed9e83045a8695a525712ba9c98e75c5))

- **10**: Capture phase context
  ([`fd6346c`](https://github.com/tlancaster6/AquaCal/commit/fd6346c7a1b0ea9e5b5c7dc45ea231f02f809c99))

- **10**: Create phase plan
  ([`4176560`](https://github.com/tlancaster6/AquaCal/commit/4176560afb0323d761bf4a079bf8fac1e647c27d))

- **10-01**: Audit docstrings, README, and terminology
  ([`5d7c228`](https://github.com/tlancaster6/AquaCal/commit/5d7c2283aa5c6c39e5ab6015b8767b5f4ce1c53e))

- **10-01**: Complete documentation audit plan
  ([`275885d`](https://github.com/tlancaster6/AquaCal/commit/275885d703381d75e43c8b46c96e3600e7b1486e))

- **10-01**: Complete Sphinx documentation audit
  ([`04b5951`](https://github.com/tlancaster6/AquaCal/commit/04b5951e7aec2ae08328068ebdb87ad14d5bbc29))

- **10-02**: Complete interface_distance rename plan
  ([`b774102`](https://github.com/tlancaster6/AquaCal/commit/b77410231dcf23faa871440fa8bc1b593cae8f49))

- **10-03**: Complete documentation audit phase
  ([`ddcbc7f`](https://github.com/tlancaster6/AquaCal/commit/ddcbc7fa692f48043dc41ae270d375559858d465))

- **10-03**: Create new documentation sections and apply audit fixes
  ([`afdbbca`](https://github.com/tlancaster6/AquaCal/commit/afdbbcaf04f381518623abb5c2155b5fb940d77a))

- **phase-07**: Complete infrastructure check verification
  ([`1b0eff5`](https://github.com/tlancaster6/AquaCal/commit/1b0eff597598fd684b2c5653f82ce2f79b94fa33))

- **phase-07**: Mark phase complete, remove Phase 13 from roadmap
  ([`7327ab2`](https://github.com/tlancaster6/AquaCal/commit/7327ab273a39a0eff1df2a9abeeb51e5e8e0e8f0))

- **phase-08**: Complete CLI QA execution, all workflows verified
  ([`9e8bc85`](https://github.com/tlancaster6/AquaCal/commit/9e8bc8549bb7d91f1e4a5930b08124fa0f43e21f))

- **phase-09**: Skip bug triage, all bugs resolved in Phase 8
  ([`d5e4038`](https://github.com/tlancaster6/AquaCal/commit/d5e403824281b77cb90e72981462a6675fb25284))

- **phase-10**: Complete phase execution
  ([`8784858`](https://github.com/tlancaster6/AquaCal/commit/87848581009fec49bba1921a03ade2649e7cfed7))

- **state**: Record phase 10 context session
  ([`b213c59`](https://github.com/tlancaster6/AquaCal/commit/b213c59ed9464eb409d1d5cb45d2a5dac0a42bf3))

### Refactoring

- **10-02**: Rename interface_distance to water_z in docs and tests
  ([`5b172e9`](https://github.com/tlancaster6/AquaCal/commit/5b172e9194e65c218c96c4fea9d9704b972012e1))

- **10-02**: Rename interface_distance to water_z in source code
  ([`4487b84`](https://github.com/tlancaster6/AquaCal/commit/4487b840a2321ff7921b7d677d0e47c828a7c666))


## v1.3.0 (2026-02-15)

### Bug Fixes

- **06**: Revise plans based on checker feedback
  ([`1657f49`](https://github.com/tlancaster6/AquaCal/commit/1657f49b7714eab71ce0009258581eac4d0ac8cb))

### Chores

- Complete v1.0 milestone
  ([`7c4fa2c`](https://github.com/tlancaster6/AquaCal/commit/7c4fa2c112cbc56684543a640382f26a490974bd))

- Remove unused .zenodo.json and one-off preset generator
  ([`fb4b86d`](https://github.com/tlancaster6/AquaCal/commit/fb4b86df828b323e4d5e3929ab314c71e3381a31))

- Small gitignore fix
  ([`cc64179`](https://github.com/tlancaster6/AquaCal/commit/cc641793d5644cea9334d06ee9bb5b7106a5df91))

### Documentation

- Capture todo - Design better hero image for README
  ([`fe546a6`](https://github.com/tlancaster6/AquaCal/commit/fe546a618db2fc5b6a08c10bc323ee462cfcd8ff))

- Fix milestone version references from v1.0 to v1.2
  ([`5bbb796`](https://github.com/tlancaster6/AquaCal/commit/5bbb7969cf150fef3191b243c44bc26b1189419d))

- **06**: Capture phase context
  ([`d589f8e`](https://github.com/tlancaster6/AquaCal/commit/d589f8e72f0438ef02d9dde7000f0ac5357fd1f1))

- **06**: Create phase plan
  ([`5cd7be8`](https://github.com/tlancaster6/AquaCal/commit/5cd7be80e632762ad40f08572a2397f263bef34d))

- **06**: Research phase domain
  ([`f24cc85`](https://github.com/tlancaster6/AquaCal/commit/f24cc85d9726d0b9e9dfedcbe4dddf4736d09d2c))

- **06-01**: Complete FrameSet + ImageSet plan
  ([`5ff20ca`](https://github.com/tlancaster6/AquaCal/commit/5ff20ca0ceb106d5c63c5c1c9ccd19a46532ae41))

- **06-02**: Complete nbsphinx setup and README overhaul plan
  ([`1afe78c`](https://github.com/tlancaster6/AquaCal/commit/1afe78c348b257c4f8ba57101a15b5e7e39342bb))

- **06-03**: Complete full pipeline tutorial plan
  ([`7cfc60f`](https://github.com/tlancaster6/AquaCal/commit/7cfc60fb978dc879704a43f1239c2e07c916bf03))

- **06-04**: Complete diagnostics and validation plan
  ([`af1f7e0`](https://github.com/tlancaster6/AquaCal/commit/af1f7e05364a4270828f3b364d0730992991c10f))

- **phase-05**: Complete phase execution and verification
  ([`2ef2939`](https://github.com/tlancaster6/AquaCal/commit/2ef2939381b59ac884974042f73914f360ec879d))

- **phase-06**: Complete phase execution and verification
  ([`f4ec8c7`](https://github.com/tlancaster6/AquaCal/commit/f4ec8c763455c00d4599d9520dfc603fe31cdfae))

### Features

- **06-01**: Implement FrameSet protocol, ImageSet, and auto-detection
  ([`c73aa71`](https://github.com/tlancaster6/AquaCal/commit/c73aa71883be5ad0f7eb4ecb6920fcf49ea445c0))

- **06-02**: Overhaul README and update tutorial index
  ([`e66fb30`](https://github.com/tlancaster6/AquaCal/commit/e66fb306e58562be6cf93fabc61539fbd45cb63f))

- **06-03**: Create full pipeline tutorial notebook
  ([`c6aecf0`](https://github.com/tlancaster6/AquaCal/commit/c6aecf02da359a7975d974da7302daf2e8645ff2))

- **06-04**: Create diagnostics and visualization notebook
  ([`41d6cb2`](https://github.com/tlancaster6/AquaCal/commit/41d6cb2af61d8d269637050f5a7ff0ae28cdd01f))

- **06-04**: Create synthetic validation notebook
  ([`9d429c6`](https://github.com/tlancaster6/AquaCal/commit/9d429c6a828c95ce8d0a4e31c8d8630d52c41fd3))

### Testing

- **06-01**: Add failing tests for ImageSet and auto-detection
  ([`d1ce779`](https://github.com/tlancaster6/AquaCal/commit/d1ce77916fb4a16a8237dba0eeaa61387ec5d465))


## v1.2.0 (2026-02-15)

### Bug Fixes

- **05**: Split plan 05-03 task 2 into 2a/2b per checker feedback
  ([`8ffba8a`](https://github.com/tlancaster6/AquaCal/commit/8ffba8a449cc9cdb8274740e97339c5f67651383))

- **05-01**: Remove opencv from intersphinx mapping
  ([`e8511a4`](https://github.com/tlancaster6/AquaCal/commit/e8511a427f694423ce2fc157883e5fbee4f07abc))

### Documentation

- **05**: Add Furo theme decision to phase context
  ([`c47c455`](https://github.com/tlancaster6/AquaCal/commit/c47c45517172fd5f89520585a79d29b15abe455c))

- **05**: Capture phase context
  ([`06e0bc9`](https://github.com/tlancaster6/AquaCal/commit/06e0bc981155accc28bf6ca073a494c5e05fd078))

- **05**: Create phase plan
  ([`c814df8`](https://github.com/tlancaster6/AquaCal/commit/c814df81553358e81a2dca1bb0599cf70fe6d9a8))

- **05**: Research Sphinx documentation site implementation
  ([`a67b55d`](https://github.com/tlancaster6/AquaCal/commit/a67b55d8ff6b004f9764057e5724275d307f47c3))

- **05-01**: Complete Sphinx infrastructure plan
  ([`a6e0f53`](https://github.com/tlancaster6/AquaCal/commit/a6e0f53fcde8018aa945a9bd6567df4aab3a369f))

- **05-02**: Complete theory pages plan summary
  ([`5149364`](https://github.com/tlancaster6/AquaCal/commit/5149364bf1b6b189ed450abfb862615c704c54f0))

- **05-03**: Complete API reference and docstrings plan
  ([`bb847df`](https://github.com/tlancaster6/AquaCal/commit/bb847df1284736d65a46a7e62e32b5cf08f940e7))

- **05-04**: Complete ray trace diagram library integration plan
  ([`6afec89`](https://github.com/tlancaster6/AquaCal/commit/6afec899ce8cf17bed286ef2e499bb940bb5a520))

### Features

- **05-01**: Add landing page, overview, and site skeleton
  ([`1b17015`](https://github.com/tlancaster6/AquaCal/commit/1b17015aee05f3ff78757dd2c70a9662f875d510))

- **05-01**: Add Sphinx configuration, docs dependencies, and RTD config
  ([`c51597c`](https://github.com/tlancaster6/AquaCal/commit/c51597ce3da5011867905e100ff2ce2fb4dc4893))

- **05-02**: Create coordinate conventions and optimizer pipeline theory pages
  ([`05b1104`](https://github.com/tlancaster6/AquaCal/commit/05b1104c4cca5c3ac832794fdd981fddd8359456))

- **05-02**: Create diagram generators and refractive geometry theory page
  ([`96d3e04`](https://github.com/tlancaster6/AquaCal/commit/96d3e04ab711d289d9e6d6b40244df57ff6d1e03))

- **05-03**: Create API reference pages with autodoc directives
  ([`71f7282`](https://github.com/tlancaster6/AquaCal/commit/71f728207f1c47b2e25baae8691a1e7243f63e25))

- **05-03**: Improve docstrings for core and calibration modules
  ([`cd4e8e7`](https://github.com/tlancaster6/AquaCal/commit/cd4e8e7e3817a1f1f39b5b269a99002170256f3d))

- **05-03**: Improve docstrings for io, validation, and other modules
  ([`65045fe`](https://github.com/tlancaster6/AquaCal/commit/65045fe91c673348869072f4121271c5d7ff98df))

### Refactoring

- **05-04**: Use AquaCal library functions in ray trace diagram
  ([`d980d8f`](https://github.com/tlancaster6/AquaCal/commit/d980d8f8a6260feb461116975e0c172771e1378c))


## v1.1.0 (2026-02-15)

### Bug Fixes

- **04**: Add missing re-exports in ground_truth.py
  ([`6f9c870`](https://github.com/tlancaster6/AquaCal/commit/6f9c8701629efb3c624f5d4ba98bad75c110df66))

### Documentation

- **04-01**: Complete synthetic data API plan
  ([`b9a688b`](https://github.com/tlancaster6/AquaCal/commit/b9a688b02b54cbb8272532db6a3cf9aa84877905))

- **04-02**: Complete dataset loading and download plan
  ([`9a8f582`](https://github.com/tlancaster6/AquaCal/commit/9a8f5826803236ffa3a1be2a7c0341528bf5cc22))

- **04-03**: Complete real dataset integration plan
  ([`40a7d25`](https://github.com/tlancaster6/AquaCal/commit/40a7d25313cf9822aeecbf615caae57c8a688fe5))

- **06**: Add image directory input support to phase 6 scope
  ([`47c809a`](https://github.com/tlancaster6/AquaCal/commit/47c809aa19bf0f7ce6457fc0e9355887de8a3977))

- **phase-04**: Mark phase 4 complete, verified
  ([`999652a`](https://github.com/tlancaster6/AquaCal/commit/999652a0b185beb67227976bcbc0a391bfaca033))

### Features

- **04-01**: Add aquacal.datasets module with synthetic rig generation
  ([`63a9260`](https://github.com/tlancaster6/AquaCal/commit/63a92609e29415b6d98385fbcffeedbe764ce53e))

- **04-01**: Refactor tests to use public datasets API
  ([`ea815e8`](https://github.com/tlancaster6/AquaCal/commit/ea815e8b605395d0a41e1767bd19c0e5c720d8a2))

- **04-02**: Add dataset loading, download, and caching infrastructure
  ([`dbdcfb9`](https://github.com/tlancaster6/AquaCal/commit/dbdcfb9223bac5e86e977957c356ba071d8c8f37))

- **04-03**: Add real-rig dataset to manifest and support MD5 checksums
  ([`5eba1d8`](https://github.com/tlancaster6/AquaCal/commit/5eba1d8fff745838ad2c9b94086e835f2a40d0a9))

### Testing

- **04-02**: Add comprehensive loader and cache tests
  ([`fa5e58c`](https://github.com/tlancaster6/AquaCal/commit/fa5e58c7134727def9b6bf56f60c01d55c125be4))


## v1.0.3 (2026-02-15)

### Bug Fixes

- **ci**: Exclude .planning/ from trailing-whitespace pre-commit hook
  ([`f85611b`](https://github.com/tlancaster6/AquaCal/commit/f85611b66da284b33e57e5df6682976423f82117))

### Documentation

- **04**: Capture phase context
  ([`c436916`](https://github.com/tlancaster6/AquaCal/commit/c4369160004cef9da8c5fdc5625a0835b3ac0622))

- **04**: Create phase plan
  ([`8aa6ec1`](https://github.com/tlancaster6/AquaCal/commit/8aa6ec1bcf9b4d0ad366e2918f85c5618fa5f4b7))

- **phase-03**: Mark phase 3 complete, verified
  ([`b9f3a93`](https://github.com/tlancaster6/AquaCal/commit/b9f3a93bc27b526d1faf491c12d463750e95faf0))


## v1.0.2 (2026-02-14)

### Bug Fixes

- **ci**: Use RELEASE_TOKEN in release workflow to trigger publish
  ([`f6ef716`](https://github.com/tlancaster6/AquaCal/commit/f6ef716bb90a19471fb99c4ea08de786fa3bb2b6))


## v1.0.1 (2026-02-14)

### Bug Fixes

- Pass all pre-commit checks (ruff lint, format, trailing whitespace)
  ([`5deb852`](https://github.com/tlancaster6/AquaCal/commit/5deb85229d20e8eab10d1d341f420f096a65222c))


## v1.0.0 (2026-02-14)

- Initial Release
