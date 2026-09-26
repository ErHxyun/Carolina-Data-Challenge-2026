"""
Step 2 - MEASURE: latent multidimensional opportunity for RW / UW / RM / UM.

Hierarchical Bayesian Dynamic Factor Model, estimated by Gibbs sampling
(forward-filtering backward-sampling for the latent states):

  measurement   y_{i,c,t}^g ~ N(alpha_i + lambda_i * Z_{c,t}^g, sigma_i^2)
                (alpha_i, lambda_i, sigma_i shared by all groups -> RW and UW on the same scale;
                 anchor indicator per dimension: alpha=0, lambda=1; lambda_i > 0)
  state         Z_{c,t}^g ~ N(rho * Z_{c,t-1}^g + delta_c^g + gamma_t, tau_Z^2)
  pooling       delta_c^g ~ N(mu_{region(c), g}, tau_delta^2)          (partial pooling)
                mu_{r,g} ~ N(0, 0.5^2);  gamma_t sum-to-zero;  rho in [0.8, 1]

Missing years are simply unobserved: the Kalman recursion bridges survey gaps and
widens the posterior where data are thin, so the uncertainty flows into every metric.

A PCA baseline is fitted on the same data for comparison.

Output per dimension (and "Overall" = all indicators): outputs/latent/<dim>.npz
  Z        (draws, series, years)   posterior draws
  Zfilt    (series, years)          filtered mean E[Z_t | data up to t]  (for the early-warning model)
  iso, group, years, n_obs (series, years)
"""
import sys
import time

import numpy as np
import pandas as pd

import config as C
from common import region_of

LAT_DIR = C.OUT_DIR / "latent"
LAT_DIR.mkdir(exist_ok=True)


def _ig(rng, a, b):
    return 1.0 / rng.gamma(a, 1.0 / b)


def _truncnorm_pos(rng, mean, sd, low=1e-3):
    for _ in range(50):
        x = rng.normal(mean, sd)
        if x > low:
            return x
    return low


class DFM:
    def __init__(self, obs, anchor, seed=C.SEED):
        self.rng = np.random.default_rng(seed)
        self.years = np.array(C.YEARS)
        T = len(self.years)
        ser = obs[["iso", "group"]].drop_duplicates().sort_values(["iso", "group"]).reset_index(drop=True)
        self.ser = ser
        sid = pd.MultiIndex.from_frame(ser)
        self.s = sid.get_indexer(pd.MultiIndex.from_frame(obs[["iso", "group"]]))
        self.t = (obs["year"].values - C.YEAR_START).astype(int)
        inds = sorted(obs["indicator"].unique())
        self.inds = inds
        self.i = pd.Index(inds).get_indexer(obs["indicator"])
        self.y = obs["y"].values.astype(float)
        self.S, self.T, self.I = len(ser), T, len(inds)
        self.anchor = inds.index(anchor) if anchor in inds else int(np.bincount(self.i).argmax())
        cells = pd.Series(list(zip(region_of(ser["iso"]), ser["group"])))
        self.cell = pd.factorize(cells)[0]
        self.n_cell = self.cell.max() + 1
        self.n_obs = np.zeros((self.S, self.T))
        np.add.at(self.n_obs, (self.s, self.t), 1)

    # ---- Gibbs blocks -------------------------------------------------------
    def _ffbs(self, alpha, lam, sig2, rho, delta, gamma, tau2):
        S, T = self.S, self.T
        w = lam[self.i] ** 2 / sig2[self.i]
        v = lam[self.i] * (self.y - alpha[self.i]) / sig2[self.i]
        prec = np.zeros((S, T)); info = np.zeros((S, T))
        np.add.at(prec, (self.s, self.t), w)
        np.add.at(info, (self.s, self.t), v)
        m = np.zeros((S, T)); P = np.zeros((S, T)); a = np.zeros((S, T)); R = np.zeros((S, T))
        a[:, 0], R[:, 0] = 0.0, 4.0
        for t in range(T):
            if t > 0:
                a[:, t] = rho * m[:, t - 1] + delta + gamma[t]
                R[:, t] = rho ** 2 * P[:, t - 1] + tau2
            P[:, t] = 1.0 / (1.0 / R[:, t] + prec[:, t])
            m[:, t] = P[:, t] * (a[:, t] / R[:, t] + info[:, t])
        Z = np.zeros((S, T))
        Z[:, -1] = self.rng.normal(m[:, -1], np.sqrt(P[:, -1]))
        for t in range(T - 2, -1, -1):
            J = rho * P[:, t] / R[:, t + 1]
            mean = m[:, t] + J * (Z[:, t + 1] - a[:, t + 1])
            var = np.maximum(P[:, t] - J ** 2 * R[:, t + 1], 1e-10)
            Z[:, t] = self.rng.normal(mean, np.sqrt(var))
        return Z, m

    def _measurement(self, Z, alpha, lam, sig2):
        z = Z[self.s, self.t]
        for k in range(self.I):
            idx = self.i == k
            yk, zk = self.y[idx], z[idx]
            if k == self.anchor:
                alpha[k], lam[k] = 0.0, 1.0
            else:
                # alpha | lambda   (prior N(0, 1))
                pa = 1.0 + idx.sum() / sig2[k]
                alpha[k] = self.rng.normal(((yk - lam[k] * zk).sum() / sig2[k]) / pa, 1 / np.sqrt(pa))
                # lambda | alpha   (prior N(1, 1), truncated > 0)
                pl = 1.0 + (zk ** 2).sum() / sig2[k]
                ml = (1.0 + ((yk - alpha[k]) * zk).sum() / sig2[k]) / pl
                lam[k] = _truncnorm_pos(self.rng, ml, 1 / np.sqrt(pl))
            res = yk - alpha[k] - lam[k] * zk
            sig2[k] = _ig(self.rng, 2.0 + idx.sum() / 2, 0.1 + (res ** 2).sum() / 2)
        return alpha, lam, sig2

    def _state(self, Z, rho, delta, gamma, tau2, mu, taud2):
        rng = self.rng
        Zl, Zc = Z[:, :-1], Z[:, 1:]
        # delta_s
        r = Zc - rho * Zl - gamma[None, 1:]
        n = Zc.shape[1]
        pd_ = n / tau2 + 1 / taud2
        delta = rng.normal((r.sum(1) / tau2 + mu[self.cell] / taud2) / pd_, 1 / np.sqrt(pd_))
        # mu_cell (prior N(0, 0.5^2)) and tau_delta^2
        for c in range(self.n_cell):
            d = delta[self.cell == c]
            pc = 1 / 0.25 + len(d) / taud2
            mu[c] = rng.normal((d.sum() / taud2) / pc, 1 / np.sqrt(pc))
        taud2 = _ig(rng, 2.0 + self.S / 2, 0.01 + ((delta - mu[self.cell]) ** 2).sum() / 2)
        # gamma_t (prior N(0, 0.5^2)), then centred
        u = Zc - rho * Zl - delta[:, None]
        pg = self.S / tau2 + 1 / 0.25
        g = rng.normal((u.sum(0) / tau2) / pg, 1 / np.sqrt(pg))
        gamma = np.concatenate([[0.0], g - g.mean()])
        # rho in [0.8, 1]   (prior N(0.95, 0.1^2))
        e = Zc - delta[:, None] - gamma[None, 1:]
        pr = (Zl ** 2).sum() / tau2 + 1 / 0.01
        mr = ((Zl * e).sum() / tau2 + 0.95 / 0.01) / pr
        for _ in range(100):
            rho_new = rng.normal(mr, 1 / np.sqrt(pr))
            if 0.8 <= rho_new <= 1.0:
                rho = rho_new
                break
        res = Zc - rho * Zl - delta[:, None] - gamma[None, 1:]
        tau2 = _ig(rng, 2.0 + res.size / 2, 0.01 + (res ** 2).sum() / 2)
        return rho, delta, gamma, tau2, mu, taud2

    def fit(self, n_iter, burn, thin, verbose=True):
        I, S, T = self.I, self.S, self.T
        alpha, lam, sig2 = np.zeros(I), np.ones(I), np.full(I, 0.3)
        rho, delta, gamma, tau2 = 0.97, np.zeros(S), np.zeros(T), 0.05
        mu, taud2 = np.zeros(self.n_cell), 0.01
        # initialise Z from the per-series mean of observed values
        Z = np.zeros((S, T))
        tot = np.zeros(S); cnt = np.zeros(S)
        np.add.at(tot, self.s, self.y); np.add.at(cnt, self.s, 1)
        Z[:] = (tot / np.maximum(cnt, 1))[:, None]
        keepZ, keepP, mfilt = [], [], np.zeros((S, T))
        t0 = time.time()
        for it in range(n_iter):
            alpha, lam, sig2 = self._measurement(Z, alpha, lam, sig2)
            rho, delta, gamma, tau2, mu, taud2 = self._state(Z, rho, delta, gamma, tau2, mu, taud2)
            Z, m = self._ffbs(alpha, lam, sig2, rho, delta, gamma, tau2)
            if it >= burn and (it - burn) % thin == 0:
                keepZ.append(Z.astype(np.float32))
                keepP.append(np.concatenate([[rho, tau2, taud2], lam, alpha, sig2]))
                mfilt += m
            if verbose and (it + 1) % 500 == 0:
                print(f"    iter {it + 1}/{n_iter}  rho={rho:.3f} tau={np.sqrt(tau2):.3f}  {time.time() - t0:.0f}s")
        self.Z = np.stack(keepZ)
        self.params = np.stack(keepP)
        self.Zfilt = mfilt / len(keepZ)
        return self

    def rhat(self):
        """Split-R-hat for rho, tau and the loadings (first vs second half of kept draws)."""
        p = self.params
        h = len(p) // 2
        a, b = p[:h], p[h:2 * h]
        W = (a.var(0, ddof=1) + b.var(0, ddof=1)) / 2
        B = h * ((a.mean(0) - b.mean(0)) ** 2) / 2
        var = (h - 1) / h * W + B / h
        return np.sqrt(var / np.maximum(W, 1e-12))


def pca_baseline(obs, dfm):
    """PCA on complete (series-year) x indicator rows; correlation with the DFM posterior mean."""
    wide = obs.pivot_table(index=["iso", "group", "year"], columns="indicator", values="y")
    wide = wide.dropna(axis=1, thresh=int(0.3 * len(wide))).dropna()
    if wide.shape[0] < 20 or wide.shape[1] < 2:
        return np.nan, 0
    X = (wide - wide.mean()) / wide.std()
    u, s, vt = np.linalg.svd(X.values, full_matrices=False)
    pc1 = u[:, 0] * s[0]
    zbar = dfm.Z.mean(0)
    sidx = pd.MultiIndex.from_frame(dfm.ser).get_indexer(wide.index.droplevel("year"))
    tidx = wide.index.get_level_values("year").values - C.YEAR_START
    r = np.corrcoef(pc1, zbar[sidx, tidx])[0, 1]
    return abs(r), len(wide)


def main(dims=None):
    panel = pd.read_csv(C.OUT_DIR / "panel_long.csv")
    dims = dims or (C.DIMENSIONS + ["Overall"])
    diag = []
    for dim in dims:
        obs = panel if dim == "Overall" else panel[panel["dimension"] == dim]
        obs = obs[obs["year"].between(C.YEAR_START, C.YEAR_END)]
        print(f"\n[{dim}] obs={len(obs):,} indicators={obs.indicator.nunique()} countries={obs.iso.nunique()}")
        dfm = DFM(obs, C.ANCHOR[dim]).fit(**C.MCMC)
        r_pca, n_pca = pca_baseline(obs, dfm)
        rh = dfm.rhat()
        np.savez_compressed(
            LAT_DIR / f"{dim}.npz", Z=dfm.Z, Zfilt=dfm.Zfilt.astype(np.float32),
            iso=np.asarray(dfm.ser["iso"].tolist(), dtype="U8"), group=np.asarray(dfm.ser["group"].tolist(), dtype="U4"),
            years=dfm.years, n_obs=dfm.n_obs, params=dfm.params, indicators=np.asarray(dfm.inds, dtype="U40"))
        k = len(dfm.inds)
        lam = dfm.params[:, 3:3 + k].mean(0)
        diag.append(dict(dimension=dim, n_obs=len(obs), n_series=dfm.S, rho=dfm.params[:, 0].mean(),
                         tau=np.sqrt(dfm.params[:, 1]).mean(), max_rhat=np.nanmax(rh),
                         pca_corr=r_pca, pca_rows=n_pca,
                         loadings="; ".join(f"{n}={l:.2f}" for n, l in zip(dfm.inds, lam))))
        print(f"    PCA-vs-DFM |corr|={r_pca:.3f} on {n_pca} complete rows; max split-Rhat={np.nanmax(rh):.3f}")
    pd.DataFrame(diag).to_csv(C.OUT_DIR / "latent_model_diagnostics.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
