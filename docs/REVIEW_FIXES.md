# Revision 2 — calculation correctness repair

This revision is not a claim of experimental validation or SRIM equivalence.
Prior numerical agreement and performance figures must be measured again.

## Corrected

- CUDA slowing-down: linear E→tau and linear tau→E are now inverse mappings.
  The regression uses a microscopic foil to expose spurious interpolation loss.
- IAEA elemental stopping uses actual project density. Compound Bragg mixing
  converts pure-element linear stopping to per-atom cross sections before
  applying actual compound atomic density. Missing density/mass is not guessed.
- BV/Bethe fallback restores Z1 squared, total excitation I=Z2 I0, B/eb and
  relativistic beta squared. This remains an analytic model, not a fitted database.
  Equation reference: https://raw.githubusercontent.com/lcpp-org/RustBCA/main/src/material.rs
- Both ends of NIST/IAEA tables use analytic fallback outside the available range;
  no high-energy endpoint plateau. Sources, energy bounds and fallback-node counts
  are included in results. Joins are not calibrated; convergence must still be checked.
- Ion escape spectra use initial ion energy; sputter spectra have a separate
  0–1000 eV axis. CSV exports both axes explicitly.
- Restore checks failure column 16, not sputter-count column 13.
- Failed-history histograms are explicitly diagnostic only (not falsely claimed
  to exclude failures); dose inference and scientific CSV export are disabled.
- Cumulative cascade energy transfer is no longer called damage energy or used
  for KP/NRT. KP/NRT mode and unmeasured per-element escape-energy averages are
  unavailable (null) rather than fabricated. Displacement creation events remain.

## Checkpoint safety

New default checkpoint: `results/revision-2/autosave.npz`.
Original `results/autosave.npz` is untouched. The GUI can inspect a legacy file
when no new checkpoint exists, but cannot resume it under the new physics.
Do not mix old and new histories. Unsupported record/trajectory layouts are
rejected explicitly. JSON carries `engine_revision` and `diagnostic_only`.

Use `GSRIM_RESULTS_DIR` to isolate a run. `python run_tests.py --gpu` automatically
isolates all test autosaves in a temporary directory; this is the preferred test command.

## Scientific limits still open

Verification completed: 69 CPU/GPU/HTTP regression tests pass. A separate local
GUI service completed 256 He histories at 40 keV in Si; parameter summary,
checkpoint restoration and browser CSV download were checked. The original
100,000-history autosave SHA256 remained
`500A3B6B65FB7C73E325825E80572E52C89701B52B2003F7AB50692372747E51`.
The launcher now checks engine identity rather than attaching to an old service.
The new GUI refuses a mismatched backend and shows actual run parameters rather
than a stale editor draft.

- IAEA series still aggregate heterogeneous experiments/isotopes/phases; filtering,
  uncertainty treatment and provenance selection need a separate data-quality review.
- No channeling, annealing, composition evolution, stable-defect inventory or
  validated KP/NRT damage partition. The GUI's disabled options reflect this.
- Impact cutoff, electronic table resolution and scattering lookup convergence
  must be demonstrated on the intended ion/material/energy range.
- GPU unit tests, energy conservation and a working GUI do not by themselves
  establish physical accuracy. Re-run independent reference comparisons after repair.
