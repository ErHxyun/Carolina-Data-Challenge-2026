# Map layers

The authoritative layer registry is `data/map/layer_catalog.csv` or its JSON equivalent. It includes the label, analytical question, data type, unit, palette, interpretation direction, source, recommendation status, and caveat for every layer.

## Strong primary layers

| Layer | Why it belongs in the main story |
|---|---|
| `education_employment_conversion_gap_z` | Shows the central education-to-employment disconnect directly. |
| `conversion_residual` | Identifies under- and above-model conversion without using fixed stages. |
| `conversion_shortfall` | Shows historical divergence between educational and employment progress. |
| `gap_momentum_state` | Distinguishes current level from recent direction. |
| `prob_gap_widening` | Preserves uncertainty around the momentum state. |
| `prob_gap_not_halved_within_15y` | Adds a persistence/first-passage perspective. |
| `core_domains_observed` | Makes data visibility part of the story. |
| `core_year_spread` | Reveals temporal comparability problems. |

## Bottleneck layers

- `finance_gender_gap_pp`
- `digital_gender_gap_pp`
- `identity_female_pct`
- `time_tax_extra_hours_day`
- `rural_time_tax_gap_latest_pp`

These variables are contextual dimensions and possible mechanisms. A visual association between a bottleneck and conversion does not establish causality.

## Tooltip minimum

Every tooltip should include:

- country;
- selected value and unit;
- relevant year or modeled period;
- data coverage;
- one short caveat;
- all state probabilities for HMM layers.

## Missing-data behavior

- Use a neutral gray fill.
- Keep the country clickable.
- Say which field is unavailable.
- Show which related fields are available.
- Do not replace missing values with zero, regional averages, or model predictions without an explicit imputation layer.

## Color behavior

- Signed gender gaps and residuals: centered diverging scale.
- Probabilities and burdens: sequential scale.
- Closing/Flat/Widening: categorical colors plus direct state labels.
- Avoid red/green-only semantics; use labels and distinguishable lightness.
