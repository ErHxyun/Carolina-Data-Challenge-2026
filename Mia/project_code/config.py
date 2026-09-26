"""
Project configuration: paths, years, and the indicator map.

Folder layout expected (same as Desktop/CDC2026):
    CDC2026/
      Graduate_Dataset/all_sources/002_WDI/<indicator>.csv.gz ...
      project_code/   <- this folder

Every data file is long format: country_id, country, iso3, date, value, obs_status.
Override the data location with the environment variable CDC_DATA.
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("CDC_DATA", HERE.parent / "Graduate_Dataset" / "all_sources"))
OUT_DIR = Path(os.environ.get("CDC_OUT", HERE / "outputs"))
FIG_DIR = OUT_DIR / "figures"
for _d in (OUT_DIR, FIG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

YEAR_START, YEAR_END = 1990, 2024
YEARS = list(range(YEAR_START, YEAR_END + 1))
SEED = 2026

GROUPS = ["RW", "UW", "RM", "UM"]          # rural women, urban women, rural men, urban men

# ---------------------------------------------------------------------------
# Indicator map
# ---------------------------------------------------------------------------
# kind:
#   "marg"   : source has total / rural / urban / female / male marginals but no
#              rural x sex cross-tab. Rural-women value is estimated on the
#              log-odds scale:  logit(RW) = logit(R) + logit(F) - logit(T)
#              (validated against the one direct cross-tab in 086_JON, see
#              01_build_panel.py -> outputs/validation_rural_women.csv).
#   "hh"     : household-level rural/urban indicator (water, electricity, ...);
#              identical for women and men in the same area.
#   "direct" : already measured for rural women / urban women.
# scale: "prop" (0-1 share, logit approximation) or "cont" (additive approximation)
# sign:  +1 higher is better, -1 higher is worse (flipped before modelling)
# suffix: how each marginal is named inside that source

SUFFIX = {
    "JON": {"T": "{b}", "R": "{b}.RU", "U": "{b}.UR", "F": "{b}.FE", "M": "{b}.MA"},
    "JONZS": {"T": "{b}.ZS", "R": "{b}.RU.ZS", "U": "{b}.UR.ZS", "F": "{b}.FE.ZS", "M": "{b}.MA.ZS"},
    "FDX": {"T": "{b}", "F": "{b}.1", "M": "{b}.2", "R": "{b}.9", "U": "{b}.10"},
    "ID4": {"T": "{b}", "F": "{b}_1", "M": "{b}_2", "R": "{b}_9", "U": "{b}_10"},
    "ID4B": {"T": "{b}.ZS", "F": "{b}.FE.ZS", "M": "{b}.MA.ZS", "R": "{b}.RU.ZS", "U": "{b}.UR.ZS"},
    "WDIHH": {"T": "{b}.ZS", "R": "{b}.RU.ZS", "U": "{b}.UR.ZS"},
}

INDICATORS = [
    # name, dimension, folder, base id, suffix family, kind, scale, divisor, sign
    ("edu_years",      "Education",      "086_JON", "JI.EDU.17UP",    "JON",   "marg", "cont", 1,   +1),
    ("enrol_6_16",     "Education",      "086_JON", "JI.ENR.0616",    "JONZS", "marg", "prop", 1,   +1),
    ("emp_to_pop",     "Employment",     "086_JON", "JI.EMP.TOTL.SP", "JONZS", "marg", "prop", 1,   +1),
    ("nonag_wage_emp", "Employment",     "086_JON", "JI.EMP.WAGE.NA", "JONZS", "marg", "prop", 1,   +1),
    ("work_contract",  "Employment",     "086_JON", "JI.EMP.CONT",    "JONZS", "marg", "prop", 1,   +1),
    ("informal_job",   "Employment",     "086_JON", "JI.EMP.IFRM",    "JONZS", "marg", "prop", 1,   -1),
    ("social_security","Employment",     "086_JON", "JI.EMP.SSEC",    "JONZS", "marg", "prop", 1,   +1),
    ("account",        "Finance",        "028_FDX", "account.t.d",    "FDX",   "marg", "prop", 100, +1),
    ("fi_account",     "Finance",        "028_FDX", "fiaccount.t.d",  "FDX",   "marg", "prop", 100, +1),
    ("saved_formal",   "Finance",        "028_FDX", "fin17a.17a1.d",  "FDX",   "marg", "prop", 100, +1),
    ("borrow_formal",  "Finance",        "028_FDX", "fin22a.22a1.22g.d","FDX", "marg", "prop", 100, +1),
    ("debit_card",     "Finance",        "028_FDX", "fin2.t.d",       "FDX",   "marg", "prop", 100, +1),
    ("emergency_funds","Resilience",     "028_FDX", "fin24aP",        "FDX",   "marg", "prop", 100, +1),
    ("own_mobile",     "Digital",        "028_FDX", "con1",           "FDX",   "marg", "prop", 100, +1),
    ("digital_account","Digital",        "028_FDX", "dig.acc",        "FDX",   "marg", "prop", 100, +1),
    ("digital_payment","Digital",        "028_FDX", "g20.any",        "FDX",   "marg", "prop", 100, +1),
    ("online_id",      "Digital",        "089_ID4", "has_eid",        "ID4",   "marg", "prop", 100, +1),
    ("id_ownership",   "Digital",        "089_ID4", "ID.OWN.TOTL",    "ID4B",  "marg", "prop", 100, +1),
    ("health_insur",   "Health",         "086_JON", "JI.EMP.HINS",    "JONZS", "marg", "prop", 1,   +1),
    ("basic_water",    "Health",         "002_WDI", "SH.H2O.BASW",    "WDIHH", "hh",   "prop", 100, +1),
    ("basic_sanit",    "Health",         "002_WDI", "SH.STA.BASS",    "WDIHH", "hh",   "prop", 100, +1),
    ("handwashing",    "Health",         "002_WDI", "SH.STA.HYGN",    "WDIHH", "hh",   "prop", 100, +1),
    ("electricity",    "Infrastructure", "002_WDI", "EG.ELC.ACCS",    "WDIHH", "hh",   "prop", 100, +1),
    ("clean_cooking",  "Infrastructure", "002_WDI", "EG.CFT.ACCS",    "WDIHH", "hh",   "prop", 100, +1),
    ("safe_water",     "Infrastructure", "002_WDI", "SH.H2O.SMDW",    "WDIHH", "hh",   "prop", 100, +1),
]

# Direct rural-women / urban-women measurements (women only, no men)
DIRECT = [
    # name, dimension, folder, RW id, UW id, divisor, sign
    ("nonag_emp_women", "Employment", "086_JON", "JI.EMP.NAGR.FE.RU.ZS", "JI.EMP.NAGR.FE.UR.ZS", 1,   +1),
    ("menstrual_private","Health",    "014_GDS", "SG.MHG.PPDP.RU.ZS",   "SG.MHG.PPDP.UR.ZS",   100, +1),
    ("menstrual_materials","Health",  "014_GDS", "SG.MHG.UMDP.RU.ZS",   "SG.MHG.UMDP.UR.ZS",   100, +1),
]

# Anchor indicator per dimension (loading fixed to 1, intercept to 0) -> identifies the latent scale
ANCHOR = {
    "Education": "edu_years", "Employment": "nonag_wage_emp", "Finance": "account",
    "Resilience": "emergency_funds", "Digital": "own_mobile", "Health": "basic_sanit",
    "Infrastructure": "clean_cooking", "Overall": "basic_sanit",
}
DIMENSIONS = ["Education", "Employment", "Finance", "Resilience", "Digital", "Health", "Infrastructure"]
# Dimensions with rural/urban time series deep enough for trajectory metrics
# (Findex / ID4D rural-urban splits exist for 2017-2024 only)
TRAJECTORY_DIMS = ["Education", "Employment", "Health", "Infrastructure"]

# Country-level macro controls (national, not rural/urban)
MACRO = {
    "log_gdppc_ppp": ("002_WDI", "NY.GDP.PCAP.PP.KD"),
    "gdppc_growth": ("002_WDI", "NY.GDP.PCAP.KD.ZG"),
    "agri_va_share": ("002_WDI", "NV.AGR.TOTL.ZS"),
    "agri_emp_share": ("002_WDI", "SL.AGR.EMPL.ZS"),
    "rural_pop_share": ("002_WDI", "SP.RUR.TOTL.ZS"),
    "female_lfp": ("002_WDI", "SL.TLF.CACT.FE.ZS"),
    "female_lower_sec": ("002_WDI", "SE.SEC.CMPT.LO.FE.ZS"),
    "internet_users": ("002_WDI", "IT.NET.USER.ZS"),
    "fertility": ("002_WDI", "SP.DYN.TFRT.IN"),
    "u5_mortality": ("002_WDI", "SH.DYN.MORT"),
    "unemployment": ("002_WDI", "SL.UEM.TOTL.ZS"),
}

# Gender wage ratio (female/male), measured separately in rural and urban areas:
# the only direct sex x location contrast -> used for the Intersectional Penalty
WAGE_RATIO = ("086_JON", "JI.WAG.GNDR.RU", "JI.WAG.GNDR.UR", "JI.WAG.GNDR")

# Minimum urban-rural gap (latent units, Overall index) for a delay to be meaningful.
# High-income countries mostly sit below 0.1; used by the escaper, early-warning and report steps.
MIN_GAP = 0.20

# Gibbs sampler settings for the Bayesian dynamic factor model
MCMC = dict(n_iter=10000, burn=4000, thin=30)
