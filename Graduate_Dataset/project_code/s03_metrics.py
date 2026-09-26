"""
Step 3 - DISCOVER / COMPARE: the core statistical metrics, each computed on every
posterior draw of the latent opportunity states so uncertainty is carried through.

  1. Opportunity Delay           D_{c,t} = argmin_d sum_k w_k (Z^RW_{t-k} - Z^UW_{t-d-k})^2
  2. Progress Without Convergence  dZ^RW > 0 and dG > 0
  3. Inequality Half-Life        log G_{c,t} = a_c - lambda_c t + e,  lambda_c ~ N(mu_region, tau^2)
  4. Divergence Point            Bayesian change point (broken-stick) on G_t -> P(tau | data)
  5. Progress Leakage            Education -> Employment (hierarchical longitudinal),
                                 Employment / Digital -> Finance, Finance -> Resilience (2024 cross-section)
  6. Intersectional Penalty      from the direct rural / urban gender wage ratios
  7. Historical Escapers         who later closed a decade-long delay (+ DTW analogues)

Outputs go to outputs/metrics/.
"""
import numpy as np
import pandas as pd

import config as C
import latent as L
from common import country_table, hpd_window, region_of

MET = C.OUT_DIR / "metrics"
MET.mkdir(exist_ok=True)
rng = np.random.default_rng(C.SEED)
YEARS = L.years()
HEADLINE_YEAR = 2021          # last year with rural/urban labour & education microdata (JOIN)
K_WINDOW, W_DECAY, D_STEP = 5, 0.85, 0.25


# ---------------------------------------------------------------------------
def eligible(dim, min_years=2):
    """Countries with >= min_years observed years for both rural and urban women.
    For Overall we additionally require women-specific (non household-level) data."""
    p = pd.read_csv(C.OUT_DIR / "panel_long.csv", usecols=["iso", "year", "group", "dimension", "kind"])
    if dim != "Overall":
        p = p[p["dimension"] == dim]
    else:
        p = p[p["kind"] != "hh"]
    n = p[p.group.isin(["RW", "UW"])].groupby(["iso", "group"])["year"].nunique().unstack()
    ok = n[(n.get("RW", 0) >= min_years) & (n.get("UW", 0) >= min_years)].index
    return sorted(ok)



def obs_span(dim, isos):
    """Per country: first/last year observed for BOTH rural and urban women, and distance (years)
    from each year to the nearest year observed for both -> (first, last, dist[N, T])."""
    sr, su = L.support(dim, isos, "RW"), L.support(dim, isos, "UW")
    both = (sr > 0) & (su > 0)
    T = both.shape[1]
    first = np.array([np.argmax(b) if b.any() else T for b in both])
    last = np.array([T - 1 - np.argmax(b[::-1]) if b.any() else -1 for b in both])
    idx = np.arange(T)
    dist = np.full(both.shape, 99.0)
    for c in range(len(isos)):
        o = idx[both[c]]
        if len(o):
            dist[c] = np.abs(idx[:, None] - o[None, :]).min(1)
    return first, last, dist

# ---------------------------------------------------------------------------
# 1. Opportunity Delay
# ---------------------------------------------------------------------------
def opportunity_delay(Zr, Zu, t_from=2000, ext_cap=60.0):
    """Zr, Zu: (draws, N, T).  Returns
      D     (draws, N, T) delay in years; for censored draws a lower bound (= years of history)
      cens  (draws, N, T) True when rural women today are below every urban-women level since
            YEAR_START, or the best match is at the edge of the history (true delay >= D)
      Dext  (draws, N, T) extended delay: censored draws extrapolate the urban path linearly
            before YEAR_START using its first-decade slope (explicit assumption, capped)."""
    Dn, N, T = Zr.shape
    w = W_DECAY ** np.arange(K_WINDOW)
    w = w / w.sum()
    out = np.full((Dn, N, T), np.nan, dtype=np.float32)
    cens = np.zeros((Dn, N, T), dtype=bool)
    ext = np.full((Dn, N, T), np.nan, dtype=np.float32)
    slope0 = (Zu[:, :, 10] - Zu[:, :, 0]) / 10.0
    for t in range(L.yidx(t_from), T):
        dmax = t - (K_WINDOW - 1)
        grid = np.arange(0, dmax + 1e-9, D_STEP)
        tr = Zr[:, :, [t - k for k in range(K_WINDOW)]]                    # (D,N,K)
        pos = t - grid[:, None] - np.arange(K_WINDOW)[None, :]             # (G,K)
        lo = np.floor(pos).astype(int); hi = np.minimum(lo + 1, T - 1); fr = pos - lo
        zu = Zu[:, :, lo] * (1 - fr) + Zu[:, :, hi] * fr                  # (D,N,G,K)
        cost = (w * (tr[:, :, None, :] - zu) ** 2).sum(-1)                 # (D,N,G)
        j = np.nanargmin(np.where(np.isnan(cost), np.inf, cost), axis=-1)
        out[:, :, t] = grid[j]
        # censored: best match at the edge of the urban history, or rural women today are
        # below every level urban women had since YEAR_START (true delay > history length)
        below_all = tr[:, :, 0] < np.nanmin(Zu[:, :, :t + 1], axis=-1)
        cens[:, :, t] = (j == len(grid) - 1) | below_all
        out[:, :, t][below_all] = t          # lower bound = years of history available
        with np.errstate(divide="ignore", invalid="ignore"):
            back = np.where(slope0 > 0.005, (Zu[:, :, 0] - tr[:, :, 0]) / slope0, ext_cap)
        e = np.where(below_all, t + np.clip(back, 0, None), out[:, :, t])
        ext[:, :, t] = np.minimum(e, ext_cap)
        # rural women at or above urban women today -> no delay
        ahead = tr[:, :, 0] >= Zu[:, :, t]
        out[:, :, t][ahead] = 0.0
        ext[:, :, t][ahead] = 0.0
        cens[:, :, t][ahead] = False
    bad = np.isnan(Zr).any(-1) | np.isnan(Zu).any(-1)
    out[bad] = np.nan
    ext[bad] = np.nan
    return out, cens, ext


def run_delay():
    rows, store = [], {}
    for dim in ["Overall"] + C.TRAJECTORY_DIMS:
        isos = eligible(dim)
        G = L.groups(dim, isos)
        Dd, cens, Dx = opportunity_delay(G["RW"], G["UW"])
        store[dim] = dict(iso=np.array(isos), D=Dd, cens=cens, Dext=Dx)
        _, _, dist = obs_span(dim, isos)
        q = np.nanquantile(Dd, [0.05, 0.5, 0.95], axis=0)
        qx = np.nanquantile(Dx, [0.05, 0.5, 0.95], axis=0)
        for i, iso in enumerate(isos):
            for t in range(L.yidx(2000), len(YEARS)):
                pc = cens[:, i, t].mean()
                rows.append(dict(dimension=dim, iso=iso, year=YEARS[t], years_to_nearest_obs=dist[i, t],
                                 delay_q05=q[0, i, t],
                                 delay_median=q[1, i, t], delay_q95=q[2, i, t],
                                 p_censored=pc, delay_is_lower_bound=bool(pc > 0.5),
                                 delay_ext_q05=qx[0, i, t], delay_ext_median=qx[1, i, t], delay_ext_q95=qx[2, i, t],
                                 p_rural_ahead=float((G["RW"][:, i, t] >= G["UW"][:, i, t]).mean())))
    df = pd.DataFrame(rows)
    df.to_csv(MET / "opportunity_delay.csv", index=False)
    np.savez_compressed(MET / "delay_draws_overall.npz", **store["Overall"])
    return df, store


# ---------------------------------------------------------------------------
# 2. Progress Without Convergence
# ---------------------------------------------------------------------------
def run_pwc(windows=((2010, 2020), (2005, 2015), (2000, 2010), (2015, 2021))):
    rows = []
    for dim in ["Overall"] + C.TRAJECTORY_DIMS:
        isos = eligible(dim)
        G = L.groups(dim, isos)
        gap = G["UW"] - G["RW"]
        first, last, _ = obs_span(dim, isos)
        for a, b in windows:
            ia, ib = L.yidx(a), L.yidx(b)
            dzr = G["RW"][:, :, ib] - G["RW"][:, :, ia]
            dzu = G["UW"][:, :, ib] - G["UW"][:, :, ia]
            dg = gap[:, :, ib] - gap[:, :, ia]
            for i, iso in enumerate(isos):
                p_pwc = float(((dzr[:, i] > 0) & (dg[:, i] > 0)).mean())
                p_conv = float(((dzr[:, i] > 0) & (dg[:, i] < 0)).mean())
                p_reg = float((dzr[:, i] <= 0).mean())
                probs = {"Progress Without Convergence": p_pwc, "Converging progress": p_conv, "No rural progress": p_reg}
                supported = first[i] <= ia + 3 and last[i] >= ib - 3
                top = max(probs, key=probs.get)
                parity = abs(np.median(gap[:, i, ia])) < 0.1 and abs(np.median(gap[:, i, ib])) < 0.1
                label = ("Insufficient data" if not supported else "At parity" if parity
                         else top if probs[top] >= 0.6 else "Uncertain")
                rows.append(dict(dimension=dim, iso=iso, window=f"{a}-{b}", data_supported=supported,
                                 dZ_rural_median=np.median(dzr[:, i]), dZ_urban_median=np.median(dzu[:, i]),
                                 dGap_median=np.median(dg[:, i]), gap_start=np.median(gap[:, i, ia]),
                                 gap_end=np.median(gap[:, i, ib]), p_pwc=p_pwc, p_converging=p_conv,
                                 p_no_rural_progress=p_reg, label=label))
    df = pd.DataFrame(rows)
    df.to_csv(MET / "progress_without_convergence.csv", index=False)
    return df


# ---------------------------------------------------------------------------
# 3. Bayesian Inequality Half-Life  (cut posterior: the Gibbs chain for the
#    hierarchical regression is fed a fresh posterior draw of G at each step)
# ---------------------------------------------------------------------------
def run_half_life(dim="Overall", y0=2000, y1=None, sweeps_per_draw=5, warm=300):
    y1 = y1 or (HEADLINE_YEAR if dim in ("Education", "Employment") else C.YEAR_END)
    isos = eligible(dim)
    G = L.groups(dim, isos)
    gap = (G["UW"] - G["RW"])[:, :, L.yidx(y0):L.yidx(y1) + 1]
    Dn, N, T = gap.shape
    first, last, _ = obs_span(dim, isos)
    span = np.zeros(gap.shape[1:], bool)                       # years inside each country's data span
    for c in range(N):
        a0, b0 = max(first[c] - L.yidx(y0), 0), min(last[c] - L.yidx(y0), T - 1)
        span[c, a0:b0 + 1] = True
    keep = ((np.median(gap, 0) > 0) | ~span).all(1) & (span.sum(1) >= 8)   # positive gap, >= 8 supported years
    isos = np.array(isos)[keep]; gap = gap[:, keep]; span = span[keep]; N = len(isos)
    x = -(np.arange(T) - T / 2.0)                              # coefficient on x is lambda
    reg = pd.factorize(region_of(isos))[0]; R = reg.max() + 1
    a, lam = np.zeros(N), np.zeros(N)
    mu, tau2, sig2 = np.zeros(R), 0.01, 0.05
    lam_draws = []

    def sweep(ly, mask):
        nonlocal a, lam, mu, tau2, sig2
        n = mask.sum(1); sx = (mask * x).sum(1); sxx = (mask * x ** 2).sum(1)
        sy = (mask * ly).sum(1); sxy = (mask * x * ly).sum(1)
        for c in range(N):
            P = np.array([[n[c], sx[c]], [sx[c], sxx[c]]]) / sig2 + np.diag([1 / 100.0, 1 / tau2])
            b = np.array([sy[c], sxy[c]]) / sig2 + np.array([0.0, mu[reg[c]] / tau2])
            cov = np.linalg.inv(P)
            a[c], lam[c] = rng.multivariate_normal(cov @ b, cov)
        for r in range(R):
            l_r = lam[reg == r]
            pr = 1 / 0.01 + len(l_r) / tau2
            mu[r] = rng.normal((l_r.sum() / tau2) / pr, 1 / np.sqrt(pr))
        tau2 = 1 / rng.gamma(2 + N / 2, 1 / (1e-4 + ((lam - mu[reg]) ** 2).sum() / 2))
        res = mask * (ly - a[:, None] - lam[:, None] * x[None, :])
        sig2 = 1 / rng.gamma(2 + mask.sum() / 2, 1 / (0.01 + (res ** 2).sum() / 2))

    for s in range(Dn):
        g = gap[s]
        mask = ((g > 0.02) & span).astype(float)
        ly = np.log(np.maximum(g, 0.02))
        for _ in range(warm if s == 0 else sweeps_per_draw):
            sweep(ly, mask)
        lam_draws.append(lam.copy())
    lam_draws = np.array(lam_draws)
    rows = []
    for c, iso in enumerate(isos):
        l = lam_draws[:, c]
        p = float((l > 0).mean())
        hl = np.where(l > 0, np.log(2) / np.where(l > 0, l, 1), np.inf)
        q = np.quantile(hl, [0.05, 0.5, 0.95])
        rows.append(dict(dimension=dim, iso=iso, lambda_median=np.median(l), p_convergence=p,
                         half_life_median=q[1] if p >= 0.8 else np.nan,
                         half_life_q05=q[0] if p >= 0.8 else np.nan,
                         half_life_q95=q[2] if p >= 0.8 else np.nan,
                         verdict=("Converging" if p >= 0.8 else
                                  "Diverging" if p <= 0.2 else "No strong evidence of convergence")))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Divergence Point  (broken-stick change point; Jeffreys prior -> closed-form
#    marginal likelihood; averaged over posterior draws of the gap)
# ---------------------------------------------------------------------------
def run_divergence(dim="Overall", y0=2000, y1=None, min_seg=4, width=4):
    """Change point in the *speed* of the gap: dG_t = G_t - G_{t-1} ~ N(mu_1, s^2) before tau and
    N(mu_2, s^2) from tau on.  Under the state model the yearly innovations are independent, so this
    is the correctly specified test (a broken line on the smooth level G would always find a kink).
    Per posterior draw of G:
      (a) BIC weight of a step change vs no change -> P(change point exists)
      (b) P(tau | data) with a Jeffreys prior (closed form), averaged over draws
      mu_2 > mu_1 -> divergence (gap began widening faster / closing slower)."""
    y1 = y1 or (HEADLINE_YEAR if dim in ("Education", "Employment") else C.YEAR_END)
    isos = eligible(dim)
    G = L.groups(dim, isos)
    gap = (G["UW"] - G["RW"])[:, :, L.yidx(y0) - 1:L.yidx(y1) + 1].astype(float)
    dG = np.diff(gap, axis=-1)                                     # (D, N, n) for years y0..y1
    Dn, N, n = dG.shape
    yrs = np.arange(y0, y1 + 1)
    taus = yrs[min_seg:n - min_seg + 1]
    rows, post_all = [], []
    for c, iso in enumerate(isos):
        y = dG[:, c, :]
        rss0 = ((y - y.mean(1, keepdims=True)) ** 2).sum(1)
        rss, dmu = [], []
        for tau in taus:
            k = tau - y0
            a, b = y[:, :k], y[:, k:]
            rss.append(((a - a.mean(1, keepdims=True)) ** 2).sum(1) + ((b - b.mean(1, keepdims=True)) ** 2).sum(1))
            dmu.append(b.mean(1) - a.mean(1))
        rss, dmu = np.array(rss).T, np.array(dmu).T                 # (D, taus)
        ks = taus - y0
        logml = -0.5 * np.log(ks * (n - ks)) - (n - 2) / 2 * np.log(rss)
        post = np.exp(logml - logml.max(1, keepdims=True)); post /= post.sum(1, keepdims=True)
        p_tau = post.mean(0)
        bic1 = n * np.log(rss.min(1) / n) + 3 * np.log(n)
        bic0 = n * np.log(rss0 / n) + 1 * np.log(n)
        p_cp = float((1 / (1 + np.exp(np.clip((bic1 - bic0) / 2, -50, 50)))).mean())
        p_widen = float((post * (dmu > 0)).sum(1).mean())
        win, p_win = hpd_window(taus, p_tau, width)
        j = p_tau.argmax()
        kind = ("No clear change point" if p_cp < 0.5 else
                "Divergence (gap began widening faster)" if p_widen >= 0.5 else
                "Convergence break (gap began closing faster)")
        rows.append(dict(dimension=dim, iso=iso, p_change_point=p_cp, tau_mode=taus[j],
                         window_start=win[0], window_end=win[1], p_window=p_win, p_speed_increase=p_widen,
                         gap_speed_before=float(np.median(y[:, :ks[j]].mean(1))),
                         gap_speed_after=float(np.median(y[:, ks[j]:].mean(1))), type=kind))
        post_all.append(p_tau)
    pd.DataFrame(np.array(post_all), index=isos, columns=taus).to_csv(MET / f"divergence_posterior_{dim}.csv")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 5. Progress Leakage
# ---------------------------------------------------------------------------
def _macro():
    m = pd.read_csv(C.OUT_DIR / "macro_panel.csv").set_index(["iso", "year"])
    return m


def leakage_edu_to_emp(h=3, sweeps_per_draw=3, warm=200):
    """Employment^g_{c,t+h} = a_{c,g} + gamma_t + beta_{c,g} Edu^g_{c,t} + b * logGDP_{c,t} + e
    beta_{c,g} ~ N(mu_g, tau^2).  Lambda = mu_UW - mu_RW, and per-country beta_{c,UW} - beta_{c,RW}.
    Rows are restricted to years inside the observed span of each series (no pure extrapolation)."""
    isos = sorted(set(eligible("Education")) & set(eligible("Employment")))
    E = L.groups("Education", isos); J = L.groups("Employment", isos)
    mac = _macro()["log_gdppc_ppp"]
    rows = []
    for g in ("RW", "UW"):
        se, sj = L.support("Education", isos, g), L.support("Employment", isos, g)
        for c, iso in enumerate(isos):
            obs_e = np.where(se[c] > 0)[0]; obs_j = np.where(sj[c] > 0)[0]
            if len(obs_e) < 2 or len(obs_j) < 2:
                continue
            lo, hi = max(obs_e.min(), obs_j.min() - h), min(obs_e.max(), obs_j.max() - h)
            for t in range(lo, hi + 1):
                gdp = mac.get((iso, YEARS[t]), np.nan)
                if not np.isnan(gdp):
                    rows.append((c, g, t, gdp))
    R = pd.DataFrame(rows, columns=["c", "g", "t", "gdp"])
    R["series"] = pd.factorize(R.c.astype(str) + "_" + R.g)[0]
    S = R.series.max() + 1
    grp = (R.groupby("series").g.first() == "UW").astype(int).values   # 0 RW, 1 UW
    tf = pd.factorize(R.t)[0]; nT = tf.max() + 1
    cc, tt, ss = R.c.values, R.t.values, R.series.values
    beta, mu, tau2, sig2 = np.zeros(S), np.zeros(2), 0.1, 0.1
    gam, bg = np.zeros(nT), 0.0
    out_mu, out_beta = [], []

    def demean(v):
        m = np.bincount(ss, v, S) / np.bincount(ss, None, S)
        return v - m[ss]

    Dn = E["RW"].shape[0]
    for d in range(Dn):
        x = np.where(R.g == "RW", E["RW"][d, cc, tt], E["UW"][d, cc, tt]).astype(float)
        y = np.where(R.g == "RW", J["RW"][d, cc, tt + h], J["UW"][d, cc, tt + h]).astype(float)
        xd, yd, gd = demean(x), demean(y), demean(R.gdp.values)
        for _ in range(warm if d == 0 else sweeps_per_draw):
            # series slopes
            r = yd - gam[tf] - bg * gd
            sxx = np.bincount(ss, xd * xd, S); sxy = np.bincount(ss, xd * r, S)
            P = sxx / sig2 + 1 / tau2
            beta = rng.normal((sxy / sig2 + mu[grp] / tau2) / P, 1 / np.sqrt(P))
            # year effects + gdp (ridge prior)
            r2 = yd - beta[ss] * xd
            X = np.column_stack([np.eye(nT)[tf], gd])
            Pm = X.T @ X / sig2 + np.eye(nT + 1) / 0.25
            cov = np.linalg.inv(Pm)
            coef = rng.multivariate_normal(cov @ (X.T @ r2) / sig2, cov)
            gam, bg = coef[:nT], coef[nT]
            # group means, tau, sigma
            for k in (0, 1):
                b_k = beta[grp == k]
                pk = 1 / 1.0 + len(b_k) / tau2
                mu[k] = rng.normal((b_k.sum() / tau2) / pk, 1 / np.sqrt(pk))
            tau2 = 1 / rng.gamma(2 + S / 2, 1 / (0.01 + ((beta - mu[grp]) ** 2).sum() / 2))
            res = yd - gam[tf] - bg * gd - beta[ss] * xd
            sig2 = 1 / rng.gamma(2 + len(res) / 2, 1 / (0.01 + (res ** 2).sum() / 2))
        out_mu.append(mu.copy()); out_beta.append(beta.copy())
    out_mu, out_beta = np.array(out_mu), np.array(out_beta)
    Lam = out_mu[:, 1] - out_mu[:, 0]
    summary = dict(link="Education -> Employment (t+3), longitudinal", n_rows=len(R), n_countries=R.c.nunique(),
                   beta_UW=np.median(out_mu[:, 1]), beta_RW=np.median(out_mu[:, 0]),
                   Lambda_median=np.median(Lam), Lambda_q05=np.quantile(Lam, .05), Lambda_q95=np.quantile(Lam, .95),
                   p_Lambda_gt_0=float((Lam > 0).mean()))
    # country-level leakage
    ser = R.groupby("series")[["c", "g"]].first()
    crow = []
    for c in ser.c.unique():
        su = ser.index[(ser.c == c) & (ser.g == "UW")]; sr = ser.index[(ser.c == c) & (ser.g == "RW")]
        if len(su) and len(sr):
            lc = out_beta[:, su[0]] - out_beta[:, sr[0]]
            crow.append(dict(iso=isos[c], beta_UW=np.median(out_beta[:, su[0]]), beta_RW=np.median(out_beta[:, sr[0]]),
                             Lambda_median=np.median(lc), p_Lambda_gt_0=float((lc > 0).mean())))
    return summary, pd.DataFrame(crow)


def leakage_cross_section(x_dim, y_dim, x_year, y_year=2024, label=None):
    """Y^g_c = a_region + a_g + beta_g X^g_c + b logGDP_c + e over countries (2024 snapshot).
    Conjugate Bayesian regression sampled once per posterior draw of the latent states."""
    isos = sorted(set(L.load(x_dim)["iso"]) & set(L.load(y_dim)["iso"]))
    sx, sy = L.support(x_dim, isos, "RW"), L.support(y_dim, isos, "RW")
    ok = (sx[:, L.yidx(x_year) - 3:L.yidx(x_year) + 1].sum(1) > 0) & (sy[:, L.yidx(y_year)] > 0)
    isos = list(np.array(isos)[ok])
    gdp = _macro()["log_gdppc_ppp"].unstack().reindex(isos)
    gdp = gdp.loc[:, 2015:2024].mean(axis=1).values
    keep = ~np.isnan(gdp); isos = list(np.array(isos)[keep]); gdp = gdp[keep]
    X_ = L.groups(x_dim, isos); Y_ = L.groups(y_dim, isos)
    fin = np.ones(len(isos), bool)
    for A, yr in ((X_, x_year), (Y_, y_year)):
        for g in ("RW", "UW"):
            fin &= np.isfinite(A[g][:, :, L.yidx(yr)]).all(0)
    isos = list(np.array(isos)[fin]); gdp = gdp[fin]
    X_ = {g: v[:, fin] for g, v in X_.items()}; Y_ = {g: v[:, fin] for g, v in Y_.items()}
    reg = pd.get_dummies(region_of(isos), drop_first=True).values.astype(float)
    n = len(isos)
    lam = []
    for d in range(X_["RW"].shape[0]):
        xr, xu = X_["RW"][d, :, L.yidx(x_year)], X_["UW"][d, :, L.yidx(x_year)]
        yr, yu = Y_["RW"][d, :, L.yidx(y_year)], Y_["UW"][d, :, L.yidx(y_year)]
        y = np.concatenate([yr, yu]).astype(float)
        u = np.r_[np.zeros(n), np.ones(n)]
        X = np.column_stack([np.ones(2 * n), u, np.r_[xr, np.zeros(n)], np.r_[np.zeros(n), xu],
                             np.r_[gdp, gdp], np.vstack([reg, reg])])
        XtX = X.T @ X + 1e-3 * np.eye(X.shape[1])
        bhat = np.linalg.solve(XtX, X.T @ y)
        res = y - X @ bhat
        s2 = (res @ res) / rng.chisquare(len(y) - X.shape[1])
        b = rng.multivariate_normal(bhat, s2 * np.linalg.inv(XtX))
        lam.append((b[3] - b[2], b[2], b[3]))
    lam = np.array(lam)
    return dict(link=label or f"{x_dim} ({x_year}) -> {y_dim} ({y_year}), cross-country", n_rows=2 * n, n_countries=n,
                beta_UW=np.median(lam[:, 2]), beta_RW=np.median(lam[:, 1]),
                Lambda_median=np.median(lam[:, 0]), Lambda_q05=np.quantile(lam[:, 0], .05),
                Lambda_q95=np.quantile(lam[:, 0], .95), p_Lambda_gt_0=float((lam[:, 0] > 0).mean()))


def run_leakage():
    s1, per_country = leakage_edu_to_emp()
    links = [s1,
             leakage_cross_section("Employment", "Finance", HEADLINE_YEAR),
             leakage_cross_section("Digital", "Finance", 2024),
             leakage_cross_section("Finance", "Resilience", 2024)]
    df = pd.DataFrame(links)
    df["reading"] = [
        f"P = {p:.0%} that gains in {l.split(' ->')[0].split(' (')[0].lower()} convert less strongly for rural women than for urban women"
        for l, p in zip(df.link, df.p_Lambda_gt_0)]
    df.to_csv(MET / "progress_leakage.csv", index=False)
    per_country.to_csv(MET / "leakage_edu_emp_by_country.csv", index=False)
    return df, per_country


# ---------------------------------------------------------------------------
# 6. Intersectional Penalty (direct rural / urban gender wage ratios)
#    G^F - G^M = log(w_UW/w_UM) - log(w_RW/w_RM) = log ratio_urban - log ratio_rural
# ---------------------------------------------------------------------------
def run_intersectional(n_iter=4000, burn=1000):
    w = pd.read_csv(C.OUT_DIR / "wage_ratio_panel.csv").dropna(subset=["rural", "urban"])
    w = w[w.rural.between(0.05, 3) & w.urban.between(0.05, 3)]
    w["I"] = np.log(w.urban) - np.log(w.rural)
    isos = sorted(w.iso.unique())
    ci = pd.Index(isos).get_indexer(w.iso)
    reg = pd.factorize(region_of(isos))[0]; R = reg.max() + 1
    N = len(isos)
    th, mu, mu0, tau2, sig2, taur2 = np.zeros(N), np.zeros(R), 0.0, 0.01, 0.01, 0.01
    I = w.I.values
    n_c = np.bincount(ci, None, N); s_c = np.bincount(ci, I, N)
    keep_th, keep_mu0, keep_mu = [], [], []
    for it in range(n_iter):
        P = n_c / sig2 + 1 / tau2
        th = rng.normal((s_c / sig2 + mu[reg] / tau2) / P, 1 / np.sqrt(P))
        for r in range(R):
            t_r = th[reg == r]
            pr = 1 / taur2 + len(t_r) / tau2
            mu[r] = rng.normal((mu0 / taur2 + t_r.sum() / tau2) / pr, 1 / np.sqrt(pr))
        p0 = 1 / 0.25 + R / taur2
        mu0 = rng.normal((mu.sum() / taur2) / p0, 1 / np.sqrt(p0))
        taur2 = 1 / rng.gamma(2 + R / 2, 1 / (0.001 + ((mu - mu0) ** 2).sum() / 2))
        tau2 = 1 / rng.gamma(2 + N / 2, 1 / (0.001 + ((th - mu[reg]) ** 2).sum() / 2))
        sig2 = 1 / rng.gamma(2 + len(I) / 2, 1 / (0.001 + ((I - th[ci]) ** 2).sum() / 2))
        if it >= burn:
            keep_th.append(th.copy()); keep_mu0.append(mu0); keep_mu.append(mu.copy())
    th, mu0, mu = np.array(keep_th), np.array(keep_mu0), np.array(keep_mu)
    rows = [dict(iso=iso, n_surveys=int(n_c[c]), I_median=np.median(th[:, c]),
                 I_q05=np.quantile(th[:, c], .05), I_q95=np.quantile(th[:, c], .95),
                 p_I_gt_0=float((th[:, c] > 0).mean())) for c, iso in enumerate(isos)]
    df = pd.DataFrame(rows)
    regions = pd.factorize(region_of(isos))[1]
    glob = pd.DataFrame([dict(scope="Global", I_median=np.median(mu0), I_q05=np.quantile(mu0, .05),
                              I_q95=np.quantile(mu0, .95), p_I_gt_0=float((mu0 > 0).mean()))] +
                        [dict(scope=r, I_median=np.median(mu[:, k]), I_q05=np.quantile(mu[:, k], .05),
                              I_q95=np.quantile(mu[:, k], .95), p_I_gt_0=float((mu[:, k] > 0).mean()))
                         for k, r in enumerate(regions)])
    df.to_csv(MET / "intersectional_penalty_by_country.csv", index=False)
    glob.to_csv(MET / "intersectional_penalty_summary.csv", index=False)
    return df, glob


# ---------------------------------------------------------------------------
# 7. Historical Escapers
# ---------------------------------------------------------------------------
def classify_ratio(r):
    return np.select([r < 0.5, r < 0.8, r <= 1.2], ["Escaper", "Partial improvement", "Stagnator"], "Fall behind")


def run_escapers(store, horizon=10, min_delay=2.0):
    D, cens, isos = store["Dext"], store["cens"], store["iso"]
    G = L.groups("Overall", list(isos))
    gap = np.nanmedian(G["UW"] - G["RW"], 0)
    rows = []
    for c, iso in enumerate(isos):
        for t in range(L.yidx(2000), L.yidx(C.YEAR_END - horizon) + 1):
            d0, d1 = D[:, c, t], D[:, c, t + horizon]
            if np.isnan(d0).all() or np.median(d0) < min_delay or cens[:, c, t].mean() > 0.5:
                continue
            if gap[c, t] < C.MIN_GAP:            # near parity: a "delay" is noise
                continue
            ratio = d1 / np.maximum(d0, 0.25)
            cls = classify_ratio(ratio)
            probs = {k: float((cls == k).mean()) for k in ["Escaper", "Partial improvement", "Stagnator", "Fall behind"]}
            rows.append(dict(iso=iso, base_year=YEARS[t], delay_base=np.median(d0), delay_after=np.median(d1),
                             ratio_median=np.median(ratio), outcome=max(probs, key=probs.get),
                             **{f"p_{k.lower().replace(' ', '_')}": v for k, v in probs.items()}))
    df = pd.DataFrame(rows)
    df.to_csv(MET / "historical_escapers.csv", index=False)
    return df


def dtw_analogues(store, K=8, top=5, horizon=10):
    """For each country today, find the historically most similar (Z^RW, Z^UW) trajectories
    (other countries, ending <= YEAR_END - horizon) with Dynamic Time Warping, and report
    what happened to those analogues over the next `horizon` years."""
    isos = list(store["iso"])
    G = L.groups("Overall", isos)
    zr, zu = np.nanmedian(G["RW"], 0), np.nanmedian(G["UW"], 0)
    Dm = np.nanmedian(store["Dext"], 0)
    esc = pd.read_csv(MET / "historical_escapers.csv") if (MET / "historical_escapers.csv").exists() else None
    cand = []                                              # (country, end year)
    for c in range(len(isos)):
        for e in range(L.yidx(2000) + K, L.yidx(C.YEAR_END - horizon) + 1):
            if zu[c, e] - zr[c, e] >= C.MIN_GAP and Dm[c, e] >= 2:
                cand.append((c, e))
    cand = np.array(cand)
    seq = lambda c, e: np.stack([zr[c, e - K + 1:e + 1], zu[c, e - K + 1:e + 1]], -1)
    candseq = np.stack([seq(c, e) for c, e in cand])       # (M, K, 2)
    rows = []
    e_now = L.yidx(HEADLINE_YEAR)
    gapm = zu - zr
    for c, iso in enumerate(isos):
        if np.isnan(Dm[c, e_now]) or Dm[c, e_now] < 2 or gapm[c, e_now] < C.MIN_GAP:
            continue
        q = seq(c, e_now)
        cost = np.full((len(cand), K + 1, K + 1), np.inf); cost[:, 0, 0] = 0
        for i in range(1, K + 1):
            for j in range(1, K + 1):
                d = np.sqrt(((candseq[:, j - 1] - q[i - 1]) ** 2).sum(-1))
                cost[:, i, j] = d + np.minimum(np.minimum(cost[:, i - 1, j], cost[:, i, j - 1]), cost[:, i - 1, j - 1])
        dist = cost[:, K, K]
        dist[cand[:, 0] == c] = np.inf
        # one analogue per country (its best-matching period)
        order = np.argsort(dist); seen, picks = set(), []
        for m in order:
            if cand[m, 0] not in seen and np.isfinite(dist[m]):
                seen.add(cand[m, 0]); picks.append(m)
            if len(picks) == top:
                break
        outs = []
        for m in picks:
            ca, ea = cand[m]
            d0, d1 = Dm[ca, ea], Dm[ca, ea + horizon]
            outs.append(f"{isos[ca]}@{YEARS[ea]}:{classify_ratio(np.array([d1 / max(d0, 0.25)]))[0]}")
        n_esc = sum("Escaper" in o for o in outs)
        rows.append(dict(iso=iso, year=HEADLINE_YEAR, delay_now=Dm[c, e_now], analogues="; ".join(outs),
                         share_analogues_escaped=n_esc / max(len(outs), 1)))
    df = pd.DataFrame(rows)
    df.to_csv(MET / "dtw_analogues.csv", index=False)
    return df


def escaper_characteristics(esc):
    """Which characteristics (at the base year) distinguished later Escapers among
    historically delayed settings?  L2 logistic regression with region effects,
    evaluated with country-grouped CV; plus LightGBM + SHAP. Associational, not causal."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold, cross_val_predict
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    import lightgbm as lgb

    feats = base_features(esc[["iso", "base_year"]].rename(columns={"base_year": "year"}), filtered=False)
    X = feats.drop(columns=["iso", "year"])
    y = (esc["outcome"] == "Escaper").astype(int).values
    if y.sum() < 5 or (1 - y).sum() < 5:
        return None
    X = X.fillna(X.median())
    Xs = pd.DataFrame(StandardScaler().fit_transform(X), columns=X.columns)
    reg = pd.get_dummies(region_of(esc.iso.values), prefix="reg", drop_first=True).astype(float)
    Xr = pd.concat([Xs, reg.reset_index(drop=True)], axis=1)
    groups = esc.iso.values
    lr = LogisticRegression(C=0.5, max_iter=2000)
    cv = GroupKFold(n_splits=min(5, len(set(groups))))
    p_lr = cross_val_predict(lr, Xr, y, cv=cv, groups=groups, method="predict_proba")[:, 1]
    lr.fit(Xr, y)
    coef = pd.Series(lr.coef_[0], index=Xr.columns)
    gbm = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=8, min_child_samples=10,
                             subsample=0.8, colsample_bytree=0.8, verbose=-1, random_state=C.SEED)
    p_gb = cross_val_predict(gbm, X, y, cv=cv, groups=groups, method="predict_proba")[:, 1]
    gbm.fit(X, y)
    try:
        import shap
        sv = shap.TreeExplainer(gbm).shap_values(X)
        sv = sv[1] if isinstance(sv, list) else sv
        shap_imp = pd.Series(np.abs(sv).mean(0), index=X.columns)
        shap_dir = pd.Series([np.corrcoef(X[c], sv[:, i])[0, 1] if X[c].std() > 0 else 0
                              for i, c in enumerate(X.columns)], index=X.columns)
    except Exception:
        shap_imp = pd.Series(gbm.feature_importances_, index=X.columns, dtype=float); shap_dir = shap_imp * np.nan
    out = pd.DataFrame({"logit_coef_std": coef.reindex(X.columns), "shap_mean_abs": shap_imp,
                        "shap_direction": shap_dir}).sort_values("shap_mean_abs", ascending=False)
    out.attrs["auc_logit"] = roc_auc_score(y, p_lr); out.attrs["auc_gbm"] = roc_auc_score(y, p_gb)
    out.to_csv(MET / "escaper_characteristics.csv")
    with open(MET / "escaper_characteristics_cv.txt", "w") as f:
        f.write(f"rows={len(y)} escapers={y.sum()} countries={len(set(groups))}\n"
                f"grouped-CV AUC logistic={out.attrs['auc_logit']:.3f}  lightgbm={out.attrs['auc_gbm']:.3f}\n")
    return out


# ---------------------------------------------------------------------------
# Shared feature builder (also used by the early-warning model)
# ---------------------------------------------------------------------------
def base_features(keys, filtered=True):
    """keys: DataFrame with iso, year.  Latent features use the *filtered* means
    (information available at time t) when filtered=True."""
    isos = sorted(keys.iso.unique())
    feats = keys.copy()
    for dim in C.TRAJECTORY_DIMS + ["Overall"]:
        G = L.groups(dim, isos, filtered=filtered)
        zr, zu = (G["RW"], G["UW"]) if filtered else (np.nanmedian(G["RW"], 0), np.nanmedian(G["UW"], 0))
        ci = pd.Index(isos).get_indexer(feats.iso); ti = feats.year.values - C.YEAR_START
        gap = zu - zr
        feats[f"gap_{dim}"] = gap[ci, ti]
        feats[f"rural_level_{dim}"] = zr[ci, ti]
        feats[f"dgap3_{dim}"] = gap[ci, ti] - gap[ci, np.maximum(ti - 3, 0)]
        feats[f"drural3_{dim}"] = zr[ci, ti] - zr[ci, np.maximum(ti - 3, 0)]
    # rolling Education->Employment conversion gap (8-year window, info up to t)
    E = L.groups("Education", isos, filtered=filtered); J = L.groups("Employment", isos, filtered=filtered)
    if not filtered:
        E = {k: np.nanmedian(v, 0) for k, v in E.items()}; J = {k: np.nanmedian(v, 0) for k, v in J.items()}
    ci = pd.Index(isos).get_indexer(feats.iso); ti = feats.year.values - C.YEAR_START
    conv = {}
    for g in ("RW", "UW"):
        vals = np.full(len(feats), np.nan)
        for n, (c, t) in enumerate(zip(ci, ti)):
            a = max(t - 7, 0)
            x, y = E[g][c, a:t + 1], J[g][c, a:t + 1]
            if np.isfinite(x).all() and np.isfinite(y).all() and np.std(x) > 1e-6 and len(x) >= 4:
                vals[n] = np.polyfit(x, y, 1)[0]
        conv[g] = vals
    feats["edu_emp_conversion_gap"] = conv["UW"] - conv["RW"]
    mac = _macro()
    feats = feats.join(mac, on=["iso", "year"])
    return feats


# ---------------------------------------------------------------------------
def main(start=1):
    """python s03_metrics.py [start_step]  -- rerun from a given step (1-7)."""
    if start <= 1:
        print("1. Opportunity Delay ..."); run_delay()
    store = dict(np.load(MET / "delay_draws_overall.npz"))
    if start <= 2:
        print("2. Progress Without Convergence ..."); run_pwc()
    if start <= 3:
        print("3. Inequality Half-Life ...")
        hl = pd.concat([run_half_life(d) for d in ["Overall"] + C.TRAJECTORY_DIMS], ignore_index=True)
        hl.to_csv(MET / "inequality_half_life.csv", index=False)
    if start <= 4:
        print("4. Divergence Point ...")
        # annual dimensions only: change points on sparse survey series are not meaningful
        dv = pd.concat([run_divergence(d) for d in ["Overall", "Health", "Infrastructure"]], ignore_index=True)
        dv.to_csv(MET / "divergence_point.csv", index=False)
    if start <= 5:
        print("5. Progress Leakage ..."); leak, _ = run_leakage(); print(leak.drop(columns="reading").round(3).to_string(index=False))
    if start <= 6:
        print("6. Intersectional Penalty ..."); _, ip = run_intersectional(); print(ip.round(3).to_string(index=False))
    print("7. Historical Escapers ..."); esc = run_escapers(store); print(esc.outcome.value_counts().to_string())
    dtw_analogues(store)
    ch = escaper_characteristics(esc)
    if ch is not None:
        print(ch.head(10).round(3).to_string()); print(open(MET / "escaper_characteristics_cv.txt").read())


if __name__ == "__main__":
    import sys
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
