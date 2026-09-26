"""Access to the posterior draws saved by s02_latent_model.py."""
from functools import lru_cache

import numpy as np
import pandas as pd

import config as C

LAT_DIR = C.OUT_DIR / "latent"


@lru_cache(maxsize=None)
def load(dim):
    z = np.load(LAT_DIR / f"{dim}.npz", allow_pickle=True)  # files written by s02 (trusted)
    d = {k: z[k] for k in z.files}
    for k in ("iso", "group", "indicators"):
        d[k] = np.asarray(d[k]).astype(str)
    d["index"] = pd.MultiIndex.from_arrays([d["iso"], d["group"]], names=["iso", "group"])
    return d


def years():
    return np.array(C.YEARS)


def yidx(y):
    return int(y) - C.YEAR_START


def groups(dim, isos, which=("RW", "UW"), filtered=False):
    """Return {group: array} with shape (draws, n_iso, T) (or (n_iso, T) if filtered).
    Countries lacking a series get NaN."""
    d = load(dim)
    out = {}
    for g in which:
        pos = d["index"].get_indexer(pd.MultiIndex.from_arrays([list(isos), [g] * len(isos)]))
        src = d["Zfilt"] if filtered else d["Z"]
        if filtered:
            arr = np.full((len(isos), src.shape[1]), np.nan, dtype=np.float32)
            arr[pos >= 0] = src[pos[pos >= 0]]
        else:
            arr = np.full((src.shape[0], len(isos), src.shape[2]), np.nan, dtype=np.float32)
            arr[:, pos >= 0] = src[:, pos[pos >= 0]]
        out[g] = arr
    return out


def support(dim, isos, group="RW"):
    """Observed data points per (country, year) for a series -> (n_iso, T)."""
    d = load(dim)
    pos = d["index"].get_indexer(pd.MultiIndex.from_arrays([list(isos), [group] * len(isos)]))
    arr = np.zeros((len(isos), len(C.YEARS)))
    arr[pos >= 0] = d["n_obs"][pos[pos >= 0]]
    return arr
