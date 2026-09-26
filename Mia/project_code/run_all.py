"""
Run the whole pipeline:  python run_all.py            (about 15 minutes; the MCMC is most of it)
                         python run_all.py --from 3   (skip steps already done)

  1 s01_build_panel       MEASURE  - rural/urban x women/men indicator panel (+ validation)
  2 s02_latent_model      MEASURE  - Bayesian dynamic factor model -> latent opportunity Z
  3 s03_metrics           DISCOVER - Delay, PWC, Half-life, Divergence, Leakage, Intersectional, Escapers
  4 s04_early_warning     PREDICT  - will the delay widen in 3 years?
  5 s05_evidence_prompts  EXPLAIN  - structured LLM evidence-investigation prompts
  6 s06_report            country_summary.csv + figures
  7 s07_export            hand-off package for UI / LLM teammates (outputs/handoff)
"""
import importlib
import sys
import time
import warnings

warnings.filterwarnings("ignore")
STEPS = ["s01_build_panel", "s02_latent_model", "s03_metrics", "s04_early_warning", "s05_evidence_prompts", "s06_report", "s07_export"]

if __name__ == "__main__":
    start = int(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 1
    for k, name in enumerate(STEPS, 1):
        if k < start:
            continue
        t0 = time.time()
        print(f"\n=== [{k}/{len(STEPS)}] {name} ===")
        mod = importlib.import_module(name)
        if name == "s05_evidence_prompts":
            mod.build()
        else:
            mod.main()
        print(f"--- {name} done in {time.time() - t0:.0f}s")
