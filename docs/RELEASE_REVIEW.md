# Source publication review — 2026-09-16

Scope: repository structure, source distribution boundaries, basic sensitive
content screening and regression tests. This is not a complete security,
legal, physics-validation or frozen-executable portability audit.

## Changes

- Added MIT license for project-owned code and third-party notices.
- Excluded environments, binaries, results, private work notes, research
  drafts and downloaded datasets. No existing local artifacts were deleted.
- Added NumPy/SciPy requirements and optional desktop dependencies.
- Replaced machine-specific packaging paths with checkout-relative paths.
- Local build scripts use unique output directories, no recursive deletion,
  no copied virtual environment, no bundled external stopping data.
- Replaced outdated README accuracy/performance claims and obsolete damage
  documentation; clarified analytic fallback without external data.
- Added Windows CPU regression workflow. GPU tests remain a local check.

## Verification

- Existing local environment, non-GPU suite: 69 discovered, 53 passed,
  16 skipped as configured.
- Exported staged source tree, without external datasets, existing local
  Python/CUDA environment: 69 discovered, 65 passed, 4 data-dependent tests
  skipped. GPU transport, scattering and HTTP regression checks passed.
- This source-tree check does not constitute a fresh Python dependency
  installation or a clean-machine portable executable test.
- Checked staged files for common credential/private-key patterns and local
  user identifiers; no embedded credentials identified by these checks.
- Existing dist packages and original SRIM were not repackaged or uploaded.

## Remaining boundaries

Optional data are provider-controlled, not MIT-licensed by this project.
Results without these data may differ from a configured local installation.
Scientific convergence and independent benchmark work are still required.
Experimental binary packaging must be tested and its notices audited before
publishing a binary release. The HTTP server is local-only, not a cloud API.
