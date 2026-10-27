"""Batched classical two-body scattering, eV / angstrom / atomic-mass units.

No SRIM code or material database is embedded. NumPy is a test reference;
the GPU path must be selected explicitly and never falls back to the CPU.
"""

import numpy as np

COULOMB_EV_ANGSTROM = 14.3996454784255
BOHR_ANGSTROM = 0.529177210903


def backend(name):
    if name == "cpu":
        return np
    if name != "gpu":
        raise ValueError("backend must be cpu or gpu")
    try:
        from .gpu_environment import configure
        configure()
        import cupy as cp
        if cp.cuda.runtime.getDeviceCount() < 1:
            raise RuntimeError("No CUDA device")
        return cp
    except (ImportError, RuntimeError) as exc:
        raise RuntimeError("GPU backend unavailable; CPU fallback is disabled") from exc


def screening_length(z1, z2):
    if not (np.isfinite(z1) and np.isfinite(z2) and 1 <= z1 <= 118 and 1 <= z2 <= 118):
        raise ValueError("Atomic numbers must lie in [1, 118]")
    return 0.88534 * BOHR_ANGSTROM / (z1**0.23 + z2**0.23)


def phi(x, xp=np):
    return (0.1818*xp.exp(-3.2*x) + 0.5099*xp.exp(-0.9423*x)
            + 0.2802*xp.exp(-0.4029*x) + 0.02817*xp.exp(-0.2016*x))


def scatter(energy_ev, impact_a, *, z1, z2, m1, m2,
            engine="cpu", order=128, screened=True):
    """Return COM angle (rad), target recoil energy (eV), closest approach (A).

    Stationary target; energy_ev is projectile LAB kinetic energy.
    screened=False is an unscreened Coulomb analytic-validation mode.
    Returns backend arrays, leaving GPU outputs resident on device.
    Inputs are validated on host; this public API is not yet a transport kernel.
    """
    if not (np.isfinite(m1) and np.isfinite(m2) and m1 > 0 and m2 > 0):
        raise ValueError("Masses must be finite and positive")
    if not isinstance(order, int) or order < 16 or order > 512:
        raise ValueError("Quadrature order must be an integer in [16, 512]")
    a = screening_length(z1, z2)
    e, b = np.broadcast_arrays(np.asarray(energy_ev, dtype=float),
                               np.asarray(impact_a, dtype=float))
    if not (np.all(np.isfinite(e)) and np.all(e > 0)
            and np.all(np.isfinite(b)) and np.all(b >= 0)):
        raise ValueError("Energy must be positive, impact nonnegative, both finite")
    xp = backend(engine)
    e, b = xp.asarray(e), xp.asarray(b)
    k = COULOMB_EV_ANGSTROM*z1*z2
    if engine == "gpu":
        from .cuda_scattering import launch
        return launch(e, b, a=a, k=k, m1=m1, m2=m2,
                      order=order, screened=screened)
    relative_e = e*m2/(m1+m2)

    def potential(r):
        return k/r * (phi(r/a, xp) if screened else 1.0)

    # Coulomb turning point is a guaranteed upper bracket for screened ZBL.
    # Rounded ZBL coefficients sum to 1.00007, slightly above one.
    # The upper bracket must dominate phi(0), including very small r/a.
    c = k/relative_e * (float(phi(0.0)) if screened else 1.0)
    lo = xp.zeros_like(e)
    hi = 0.5*(c + xp.sqrt(c*c + 4*b*b))
    for _ in range(64):
        mid = 0.5*(lo+hi)
        allowed = 1.0-(b/mid)**2-potential(mid)/relative_e > 0
        hi = xp.where(allowed, mid, hi)
        lo = xp.where(allowed, lo, mid)
    r0 = 0.5*(lo+hi)

    # u=r0/r, then u=1-t^2 removes the square-root endpoint singularity.
    # theta=pi-2*(b/r0)* integral_0^1 [2t/sqrt(F(1-t^2))] dt.
    nodes, weights = np.polynomial.legendre.leggauss(order)
    integral = xp.zeros_like(e)
    for t, w in zip((nodes+1)*0.5, weights*0.5):
        u = 1.0-t*t
        f = 1.0-(b*u/r0)**2-potential(r0/u)/relative_e
        integral += w*2*t/xp.sqrt(xp.maximum(f, 1e-30))
    angle = xp.pi - 2*b/r0*integral
    angle = xp.where(b == 0, xp.pi, angle)
    # Do not clip numerical failures into apparently valid scattering results.
    transfer = e * (4*m1*m2/(m1+m2)**2) * xp.sin(angle/2)**2
    return angle, transfer, r0
