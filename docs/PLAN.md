# Repository presentation and reproducibility cleanup

## Scope

Create a concise repository entry point and a complete offline reproduction
path while preserving simulation mathematics, published data and numerical behavior.
No existing implementation plan was present in this checkout.

## Work

- [x] Inspect repository, artifact relationships, and existing verification.
- [x] Separate maintained README from the generated numerical REPORT.
- [x] Document setup, script order, file roles, expected values, and limitations.
- [x] Add an executable published-artifact and deterministic-CSV hash check.
- [x] Capture tested dependency versions and refresh publication manifest.
- [x] Run isolated reproduction, focused checks, and independent review.

## Handoff

Worktree: `rocketpool-minipool-exit-simulation` beneath the shared workspace.
Base: `main`, commit `10ae44d`. Changes are local; no commits or pushes made.
Validation completed on CPython 3.14.7 / macOS arm64:

- Fresh virtual environment installed requirements successfully; pip check passed.
- Full pipeline in a disposable copy exited 0: simulate, verify, CSV comparison,
  report builder, and both figure scripts. 24,492 scenario draws across two seeds.
- Seven regenerated CSVs matched the published hashes exactly.
- All 54 publication-manifest entries passed before regeneration.
- Hash-checker self-checks accepted matching files and rejected changed/missing ones.
- Ruff check passed on both changed/new Python files; no repository lint config exists.
- Local links in README, reproduction guide, and report resolved.
- Report rebuild matched REPORT.md and left README.md and POST.md unchanged.
- Independent Council code review reported no findings. No archived hooks executed.

Unverified: fresh Numbers recalculation, other Python versions and operating systems.
Existing spreadsheet export was checked, not recalculated in an application.
Simulation mathematics and published research artifacts remain unchanged.

Next action: user review of the local changes, then commit/publish if requested.

## Folder organization follow-up

User clarified that visual organization is the primary goal. Group snapshot data,
scripts, figures, reports, generated results, and guides in dedicated folders;
keep only README and dependency manifests at the visible root. Update paths and
links without changing the model. Re-run the pipeline in isolation after moving.

Status: complete. Frozen data, charts, spreadsheets, and generated numerical
artifacts were moved without changing their bytes. Reproducibility record keys
and publication manifest now use repository-relative paths.

Evidence for the reorganized layout:
- Full relocated pipeline executed successfully in an isolated copy; all seven
  regenerated CSVs matched, and numerical checks and both figure builders passed.
- Final report-byte comparison initially caught a malformed generated GitHub URL;
  independent review identified the same issue. Fixed it and reran only the
  report builder: report bytes match and README/post remain unchanged.
- Ruff passed for all scripts after removing unused bindings/imports and splitting
  existing semicolon-separated statements. Simulation algorithms were preserved.
- Local Markdown links resolve; 54 artifact hashes match the updated manifest.
- README rendered in a local HTML preview; GitHub's own rendering was not viewed.
- Existing independent review found only the corrected URL issue.

Worktree remains on main with uncommitted changes; no push. No new Numbers
recalculation or cross-platform testing. Next action: review the folder layout
and README, then commit/publish if requested.

## GitHub publication

User explicitly requested updating the GitHub repository. Remote main matched
the local base before publication (0 commits ahead/behind). Artifact validation
passed for all 54 entries. The cleanup is being delivered in the commit containing
this handoff, titled `chore: organize research artifacts and refresh README`.
Push target: `origin/main`; no force push. Remote commit confirmation is recorded
in the session response. Prior local-only status above describes earlier steps.
Next action: inspect the published GitHub README and folder layout.
