"""Shared helpers: loading indicator files, country filtering, transforms."""
import logging
from functools import lru_cache

import numpy as np
import pandas as pd

import config as C

logging.getLogger("country_converter").setLevel(logging.ERROR)
import country_converter as coco  # noqa: E402

_CONTINENTS = {"Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Antarctica"}
EPS = 0.005


def logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


@lru_cache(maxsize=None)
def read_indicator(folder: str, ind_id: str) -> pd.Series:
    """Return a Series indexed by (iso3, year). Empty Series if the file is missing."""
    path = C.DATA_DIR / folder / f"{ind_id}.csv.gz"
    if not path.exists():
        return pd.Series(dtype=float, index=pd.MultiIndex.from_arrays([[], []], names=["iso", "year"]))
    d = pd.read_csv(path, usecols=["country_id", "iso3", "date", "value"], dtype={"iso3": str, "country_id": str})
    d = d.dropna(subset=["value"])
    # WDI-style files: ISO2 in country_id + ISO3 in iso3; JOIN/Findex files: ISO3 in country_id
    d["country_id"] = d["iso3"].where(d["iso3"].notna() & (d["iso3"].str.len() == 3), d["country_id"])
    d = d[d["date"].between(C.YEAR_START, C.YEAR_END)]
    d = d[d["country_id"].isin(country_table().index)]
    s = d.groupby(["country_id", "date"])["value"].mean()
    s.index.names = ["iso", "year"]
    return s.astype(float)


@lru_cache(maxsize=None)
def country_table() -> pd.DataFrame:
    """ISO3 -> name, region (7-continent scheme) for real countries only (drops WB aggregates)."""
    d = pd.read_csv(C.DATA_DIR / "002_WDI" / "SP.POP.TOTL.csv.gz", usecols=["country", "iso3"], dtype=str)
    d = d.dropna(subset=["iso3"]).drop_duplicates("iso3").rename(columns={"iso3": "country_id"})
    d = d[d["country_id"].str.len() == 3]
    cont = coco.convert(d["country_id"].tolist(), src="ISO3", to="Continent_7", not_found=None)
    d["region"] = cont
    d.loc[d["country_id"] == "XKX", "region"] = "Europe"
    d = d[d["region"].isin(_CONTINENTS)]
    return d.rename(columns={"country_id": "iso", "country": "name"}).set_index("iso")


def region_of(isos):
    t = country_table()
    return t.reindex(isos)["region"].fillna("Other").values


def hpd_window(years, probs, width):
    """Most probable contiguous window of `width` years for a discrete posterior."""
    best, best_p = None, -1
    for i in range(len(years) - width + 1):
        p = probs[i:i + width].sum()
        if p > best_p:
            best, best_p = (years[i], years[i + width - 1]), p
    return best, best_p


def summarize(draws, axis=0, q=(0.05, 0.5, 0.95)):
    """Posterior 5 / 50 / 95 percentiles along `axis` (NaN-aware)."""
    return np.nanquantile(draws, q, axis=axis)
