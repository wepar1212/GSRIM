# GSRIM and SRIM: shared framework, not equivalent implementations

GSRIM independently implements Monte Carlo binary-collision transport.
It does not launch TRIM or distribute SRIM binaries or stopping tables.

Shared concepts include screened scattering, electronic stopping, cascades
and amorphous layers. Collision sampling, numerical methods, data and
outputs are not guaranteed identical.

One CUDA thread computes an incident history and its cascade. Scattering
tables and electronic path primitives reduce per-event work. No current
speedup factor against SRIM has been established under matched conditions.

Electronic stopping uses LS/BV or optional NIST/IAEA data; compounds may use
Bragg addition. The full SRIM stopping and compound correction system is
not reproduced. Without external data the default mode uses analytic fallback.

Recoil stacks have 128 entries in the current kernel. Displacement creation
events are not surviving vacancies. KP/NRT and damage-energy estimates are
disabled. Surface barriers are approximate. Replacement bookkeeping,
annealing and dynamic composition are absent.

Standard TRIM also models amorphous targets: lack of explicit crystal
channeling is not unique to GSRIM.

Report code revision, seed, stopping sources, mode, impact_scale, cutoff,
bins, histories and convergence evidence. Engineering tests alone do not
establish predictive accuracy or SRIM equivalence.
