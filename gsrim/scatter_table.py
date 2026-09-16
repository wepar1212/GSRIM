"""Universal ZBL scattering tables for fast GPU transport.

Reduced variables (ZBL):
  eps = E_cm * a / (Z1 Z2 e^2)   dimensionless energy
  rho = b / a                    dimensionless impact parameter
  theta = theta(eps, rho)        COM scattering angle (rad)

The table stores theta on a log-log grid. Transport interpolates bilinearly
in (log eps, log rho). Full quadrature remains available for verification.
"""
from functools import lru_cache
import numpy as np
from .scattering import screening_length, phi, COULOMB_EV_ANGSTROM


# Dense enough for transport accuracy; expanded at runtime if needed.
EPS_NODES = 512
RHO_NODES = 512
EPS_MIN, EPS_MAX = 1e-4, 1e8
RHO_MIN, RHO_MAX = 1e-6, 64.0


def _theta_quadrature(eps, rho, order=64):
    """COM angle for reduced (eps, rho) via the same regularized quadrature."""
    # F(r) = 1 - (b/r)^2 - V(r)/E with reduced r_bar=r/a, b_bar=rho,
    # V/E = 1/(eps * r_bar) * phi(r_bar)
    # Turning point of 1 - rho^2/rb^2 - phi(rb)/(eps*rb) = 0
    lo = np.zeros_like(eps)
    # Coulomb-like upper bracket in reduced units: rb_hi ~ (1 + sqrt(1+4 eps rho^2))/(2 eps)
    hi = 0.5 * (1.0 / eps + np.sqrt(1.0 / eps**2 + 4.0 * rho**2))
    for _ in range(56):
        mid = 0.5 * (lo + hi)
        allowed = 1.0 - (rho / mid) ** 2 - phi(mid) / (eps * mid) > 0.0
        hi = np.where(allowed, mid, hi)
        lo = np.where(allowed, lo, mid)
    r0 = 0.5 * (lo + hi)
    nodes, weights = np.polynomial.legendre.leggauss(order)
    integral = np.zeros_like(eps)
    for t, w in zip((nodes + 1) * 0.5, weights * 0.5):
        u = 1.0 - t * t
        f = 1.0 - (rho * u / r0) ** 2 - u * phi(r0 / u) / (eps * r0)
        integral += w * 2.0 * t / np.sqrt(np.maximum(f, 1e-30))
    angle = np.pi - 2.0 * rho / r0 * integral
    angle = np.where(rho == 0.0, np.pi, angle)
    return np.clip(angle, 0.0, np.pi)


def build_universal_table(eps_nodes=EPS_NODES, rho_nodes=RHO_NODES,
                          eps_range=(EPS_MIN, EPS_MAX),
                          rho_range=(RHO_MIN, RHO_MAX),
                          quad_order=48):
    """Build log-grid tables of theta(eps,rho). Vectorized CPU reference."""
    log_eps = np.linspace(np.log(eps_range[0]), np.log(eps_range[1]), eps_nodes)
    log_rho = np.linspace(np.log(rho_range[0]), np.log(rho_range[1]), rho_nodes)
    le, lr = np.meshgrid(log_eps, log_rho, indexing="ij")
    eps = np.exp(le).ravel()
    rho = np.exp(lr).ravel()
    theta = _theta_quadrature(eps, rho, order=quad_order).reshape(eps_nodes, rho_nodes)
    # Head-on column is exactly pi for every eps.
    theta[:, 0] = np.pi
    return {
        "log_eps": log_eps,
        "log_rho": log_rho,
        "theta": theta.astype(np.float64),
        "eps_range": eps_range,
        "rho_range": rho_range,
        "quad_order": quad_order,
    }


def _cache_path(eps_nodes, rho_nodes, eps_range, rho_range, quad_order):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "results" / "tables"
    name = f"zbl_theta_{eps_nodes}x{rho_nodes}_q{quad_order}.npz"
    return root / name


def load_cached_or_build(eps_nodes=EPS_NODES, rho_nodes=RHO_NODES,
                         eps_range=(EPS_MIN, EPS_MAX),
                         rho_range=(RHO_MIN, RHO_MAX),
                         quad_order=40):
    """Disk-cached universal table; rebuild only when parameters change."""
    path = _cache_path(eps_nodes, rho_nodes, eps_range, rho_range, quad_order)
    if path.is_file():
        with np.load(path, allow_pickle=False) as data:
            if (data["log_eps"].shape == (eps_nodes,)
                    and data["log_rho"].shape == (rho_nodes,)
                    and float(data["eps_min"]) == eps_range[0]
                    and float(data["eps_max"]) == eps_range[1]
                    and float(data["rho_min"]) == rho_range[0]
                    and float(data["rho_max"]) == rho_range[1]):
                return {
                    "log_eps": data["log_eps"],
                    "log_rho": data["log_rho"],
                    "theta": data["theta"],
                    "eps_range": eps_range,
                    "rho_range": rho_range,
                    "quad_order": quad_order,
                }
    table = build_universal_table(eps_nodes, rho_nodes, eps_range, rho_range, quad_order)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.npz")
    np.savez_compressed(
        temporary,
        log_eps=table["log_eps"], log_rho=table["log_rho"], theta=table["theta"],
        eps_min=eps_range[0], eps_max=eps_range[1],
        rho_min=rho_range[0], rho_max=rho_range[1],
    )
    temporary.replace(path)
    return table



@lru_cache(maxsize=4)
def load_or_build(cache_key=(EPS_NODES, RHO_NODES, EPS_MIN, EPS_MAX, RHO_MIN, RHO_MAX)):
    return build_universal_table()


def interpolate(theta, log_eps_grid, log_rho_grid, eps, rho):
    """Bilinear interpolation of theta on the log-log grid (CPU reference)."""
    le = np.log(np.clip(eps, EPS_MIN, EPS_MAX))
    lr = np.log(np.clip(rho, RHO_MIN, RHO_MAX))
    # cell indices
    di = (log_eps_grid[1] - log_eps_grid[0])
    dj = (log_rho_grid[1] - log_rho_grid[0])
    fi = (le - log_eps_grid[0]) / di
    fj = (lr - log_rho_grid[0]) / dj
    i0 = np.clip(np.floor(fi).astype(int), 0, len(log_eps_grid) - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, len(log_rho_grid) - 2)
    ti = fi - i0
    tj = fj - j0
    t00 = theta[i0, j0]
    t01 = theta[i0, j0 + 1]
    t10 = theta[i0 + 1, j0]
    t11 = theta[i0 + 1, j0 + 1]
    return ((1 - ti) * (1 - tj) * t00 + (1 - ti) * tj * t01
            + ti * (1 - tj) * t10 + ti * tj * t11)


def lab_transfer(energy_ev, angle, m1, m2):
    return energy_ev * (4.0 * m1 * m2 / (m1 + m2) ** 2) * np.sin(angle / 2.0) ** 2
