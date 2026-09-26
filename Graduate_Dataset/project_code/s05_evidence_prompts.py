"""
Step 5 - EXPLAIN: LLM evidence investigation.

The statistics say WHEN and WHERE; the LLM is asked to investigate WHY, with a fixed
structure so it does evidence review instead of storytelling:

  Statistical Finding -> Possible Mechanism -> Supporting Evidence -> Contradicting Evidence -> Confidence

This script writes one prompt per finding to outputs/evidence/prompts.jsonl.
With --run and an ANTHROPIC_API_KEY in the environment it also sends them to Claude
with the web-search tool (sources restricted to World Bank, ILO, UN Women, WHO, UNICEF,
FAO, IFAD, UNDP by default) and saves the answers to outputs/evidence/responses.jsonl.

  python s05_evidence_prompts.py            # prompts only
  python s05_evidence_prompts.py --run 10   # also query the first 10 prompts
"""
import json
import os
import sys

import pandas as pd

import config as C
from common import country_table

EVD = C.OUT_DIR / "evidence"
EVD.mkdir(exist_ok=True)
MET = C.OUT_DIR / "metrics"
DOMAINS = ["worldbank.org", "ilo.org", "unwomen.org", "who.int", "unicef.org", "fao.org", "ifad.org", "undp.org",
           "data.unicef.org", "washdata.org"]

TEMPLATE = """You are assisting a statistical study of how unevenly development reaches rural versus urban women.
The statistical model has already produced the finding below. Your job is NOT to accept it or to invent a story:
investigate what may explain it, using documented evidence only.

STATISTICAL FINDING
{finding}

CONTEXT FROM THE MODEL
{context}

Search authoritative sources (World Bank, ILO, UN Women, WHO/UNICEF JMP, FAO, IFAD, UNDP, national statistics offices)
for policies, programmes, shocks or structural changes in {country} around {period} that could plausibly relate to it.

Answer in exactly this structure:
1. Statistical Finding - restate it in one sentence, including the uncertainty.
2. Possible Mechanisms - up to 3, each one sentence.
3. Supporting Evidence - for each mechanism: what the source says, with source name, year and URL.
4. Contradicting or Complicating Evidence - anything that cuts against each mechanism, with sources.
5. Confidence - High / Medium / Low for each mechanism, with one sentence on why.
Do not claim causality. If you find no relevant evidence, say so rather than speculating."""


def _name(iso):
    t = country_table()
    return t.loc[iso, "name"] if iso in t.index else iso


def build():
    prompts = []
    delay = pd.read_csv(MET / "opportunity_delay.csv")
    d21 = delay[delay.year == 2021].set_index(["dimension", "iso"])

    def ctx(iso):
        parts = []
        for dim in ["Education", "Employment", "Health", "Infrastructure"]:
            if (dim, iso) in d21.index:
                r = d21.loc[(dim, iso)]
                lb = ">" if r.delay_is_lower_bound else ""
                parts.append(f"{dim} delay 2021: {lb}{r.delay_median:.0f} years (90% CI {r.delay_q05:.0f}-{r.delay_q95:.0f})")
        return "; ".join(parts) or "n/a"

    dv = pd.read_csv(MET / "divergence_point.csv")
    for _, r in dv[dv.type != "No clear change point"].sort_values("p_window", ascending=False).iterrows():
        verb = "began widening faster" if r.type.startswith("Divergence") else "began closing faster"
        f = (f"In {_name(r.iso)}, the rural-urban gap for women in {r.dimension.lower()} {verb} around "
             f"{r.window_start}-{r.window_end} (posterior probability of that window {r.p_window:.0%}; "
             f"probability that a change point exists {r.p_change_point:.0%}). Yearly gap change: "
             f"{r.gap_speed_before:+.3f} before vs {r.gap_speed_after:+.3f} after (latent units).")
        prompts.append(dict(kind="divergence", iso=r.iso, dimension=r.dimension,
                            prompt=TEMPLATE.format(finding=f, context=ctx(r.iso), country=_name(r.iso),
                                                   period=f"{r.window_start - 2}-{r.window_end + 1}")))

    pwc = pd.read_csv(MET / "progress_without_convergence.csv")
    for _, r in pwc[(pwc.window == "2010-2020") & (pwc.label == "Progress Without Convergence")].iterrows():
        f = (f"In {_name(r.iso)} between 2010 and 2020, rural women's {r.dimension.lower()} opportunity improved "
             f"(change {r.dZ_rural_median:+.2f}) but urban women improved faster ({r.dZ_urban_median:+.2f}), so the gap "
             f"widened from {r.gap_start:.2f} to {r.gap_end:.2f} (P(progress without convergence) = {r.p_pwc:.0%}).")
        prompts.append(dict(kind="progress_without_convergence", iso=r.iso, dimension=r.dimension,
                            prompt=TEMPLATE.format(finding=f, context=ctx(r.iso), country=_name(r.iso), period="2010-2020")))

    ewf = sorted((C.OUT_DIR / "early_warning").glob("early_warning_*.csv"))
    if ewf:
        ew = pd.read_csv(ewf[-1]).head(10)
        for _, r in ew.iterrows():
            f = (f"The early-warning model gives {_name(r.iso)} a {r.p_widen:.0%} probability that rural women's "
                 f"opportunity delay relative to urban women will widen between {r.year} and {r.year + 3}.")
            prompts.append(dict(kind="early_warning", iso=r.iso, dimension="Overall",
                                prompt=TEMPLATE.format(finding=f, context=ctx(r.iso), country=_name(r.iso),
                                                       period=f"{r.year - 5}-{r.year}")))
    with open(EVD / "prompts.jsonl", "w") as fh:
        for p in prompts:
            fh.write(json.dumps(p) + "\n")
    print(f"wrote {len(prompts)} prompts -> {EVD / 'prompts.jsonl'}")
    return prompts


def run(prompts, n):
    import anthropic                                   # pip install anthropic
    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
    with open(EVD / "responses.jsonl", "a") as fh:
        for p in prompts[:n]:
            msg = client.messages.create(
                model=model, max_tokens=2500,
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6, "allowed_domains": DOMAINS}],
                messages=[{"role": "user", "content": p["prompt"]}])
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            fh.write(json.dumps({**p, "model": model, "response": text}) + "\n")
            print(f"  {p['kind']} {p['iso']}: {len(text)} chars")


if __name__ == "__main__":
    ps = build()
    if "--run" in sys.argv:
        k = sys.argv.index("--run")
        n = int(sys.argv[k + 1]) if len(sys.argv) > k + 1 else 5
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("Set ANTHROPIC_API_KEY to query the model.")
        run(ps, n)
