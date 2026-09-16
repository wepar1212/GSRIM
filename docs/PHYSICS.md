# Physical and numerical contract

Units: kinetic energy eV; length angstrom; mass atomic mass units.

## Binary scattering (implemented)

Stationary target. E_cm = E_lab m2/(m1+m2).

V(r) = 14.3996454784255 Z1 Z2 phi(r/a)/r.
a = 0.88534 a0/(Z1^0.23 + Z2^0.23).
phi(x) = sum A_i exp(-B_i x), ZBL coefficients
A=(0.1818,0.5099,0.2802,0.02817), B=(3.2,0.9423,0.4029,0.2016).

Turning point is the positive root of F(r)=1-b^2/r^2-V(r)/E_cm.
COM angle from the classical central-force integral with u=r0/r and u=1-t^2.
Recoil energy E_lab [4 m1 m2/(m1+m2)^2] sin(theta/2)^2.

### Universal table

Reduced variables:
  eps = E_cm * a / (Z1 Z2 e^2), rho = b/a.
Table stores theta(eps, rho) on a log grid (default 512×512, eps in
[1e-4, 1e8], rho in [1e-6, 64]), built by independent quadrature and cached
under `results/tables/`. GPU path uses Catmull–Rom bicubic interpolation.
`physics.scattering = "quadrature"` selects numerical 32-point quadrature,
not an exact analytic solution.

CPU reduced formulation and lab-unit solver agree to ~1e-9. Bicubic table
agreement with quadrature is sub-percent on He/Si development cases; measure
with tests before quoting physics numbers.

## Electronic stopping (device)

Lindhard–Scharff: S_e = k_ls * sqrt(E[eV]) eV/Å,

k_ls = n * C_ls * Z1^{7/6} Z2 / (Z1^{2/3}+Z2^{2/3})^{3/2} / sqrt(m_u)

with

C_ls = 8 pi e^2 a0 * sqrt(2 e / m_p) / v_Bohr ≈ 1.2100,

derived from LS (1961) with CODATA constants (`gsrim/electronic_stopping.py`).
Literature often quotes 1.212; GSRIM uses the derived value.

Non-LS paths use tabulated electronic stopping where available, with BV
analytic fallback. The host builds tau(E)=integral dE/Se(E), a length in
angstrom; the device subtracts flight distance and inverts the same piecewise
linear mapping. NIST mass stopping is converted at actual target density;
elemental IAEA series are density-rescaled and compounds use per-atom Bragg
addition. These models do not replace ion/target-specific validation.

## Transport

- Poisson free flight in a spherical-overlap amorphous geometry,
  radius = impact_scale * (3/(4 pi n))^{1/3}.
- Multilayer planar boundaries; outer surface reflection if normal energy
  is below surface binding; otherwise escape (backscatter/transmit/sputter).
- Recoil stack depth 128; overflow marks the history failed, not silent loss.
- Per-history energy ledger: E0 = electronic + lattice + escape + unresolved
  (to numerical precision). Failed-history contributions are diagnostic only;
  no claim is made that shared histograms exclude them. Dose/CSV use is blocked.

## Validation policy

1. Analytic limits (Rutherford, head-on equal mass) must hold in unit tests.
2. GPU/CPU scattering agreement; table/quadrature transport agreement on
   development cases.
3. Published range targets (NIST PSTAR/ASTAR, ICRU 49 methods) are compared
   **without fitting**. Report measured/reference ratios and cite model limits.
4. Convergence in impact_scale, cutoff, bins, and ions is mandatory before
   quoting a number.
5. Never rescale histograms to hide disagreement with SRIM or experiment.

## Known limits

- No crystal channeling, charge-state dynamics, or sputtering chemistry.
  Tracked recoils do lose electronic energy under the selected stopping model.
- LS electronic stopping under-predicts H stopping near the Bragg peak;
  proton ranges are systematically long. Use user-supplied provenance tables
  and verify the selected model against independent data.
- Revision 2 uses corrected BV fallback grids on the GPU for non-LS models;
  the high-energy domain still requires independent validation.
