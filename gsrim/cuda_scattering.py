"""Fused CUDA implementation of the elementary scattering solver."""
from functools import lru_cache
from pathlib import Path
import numpy as np
from .scattering import backend


@lru_cache(maxsize=8)
def _kernel(device):
    cp = backend("gpu")
    source = (Path(__file__).parent / "kernels/scatter.cu").read_text(encoding="utf-8")
    return cp.RawKernel(source, "binary_scatter", options=("--std=c++11",))


@lru_cache(maxsize=32)
def _quadrature(order, device):
    cp = backend("gpu")
    nodes, weights = np.polynomial.legendre.leggauss(order)
    return cp.asarray((nodes+1)*.5), cp.asarray(weights*.5)


def launch(e, b, *, a, k, m1, m2, order, screened):
    cp = backend("gpu")
    shape = e.shape
    e = cp.ascontiguousarray(e.reshape(-1))
    b = cp.ascontiguousarray(b.reshape(-1))
    if e.size > np.iinfo(np.int32).max:
        raise ValueError("Batch too large; split into bounded batches")
    outputs = [cp.empty_like(e) for _ in range(3)]
    if e.size:
        device = cp.cuda.runtime.getDevice()
        nodes, weights = _quadrature(order, device)
        _kernel(device)(((e.size+127)//128,), (128,),
                        (e, b, nodes, weights, *outputs, np.int32(e.size),
                         np.int32(order), np.float64(a), np.float64(k),
                         np.float64(m1), np.float64(m2), np.int32(screened)))
    return tuple(output.reshape(shape) for output in outputs)
