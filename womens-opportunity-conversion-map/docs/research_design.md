# Research design

## Primary question

Why does women’s educational progress translate into employment opportunity in some countries but stall in others?

## Analytical logic

The project separates three tasks:

1. **Description:** measure gender differences in education, employment, finance, digital access, identity, health, and unpaid-care time.
2. **Statistical discovery:** identify under-conversion, above-model conversion, divergence, momentum, and persistence patterns.
3. **Evidence retrieval:** search authoritative sources for plausible context and contradictory evidence.

These stages must remain separate. Statistical discovery determines where to investigate; external sources may contextualize the signal; neither stage by itself identifies causality.

## Primary statistical signals

### Education ahead of employment

```text
education–employment conversion gap
  = education gender advantage z-score
  − employment gender advantage z-score
```

A high value means education outcomes are more gender-equal than employment outcomes. It does not follow the same people through school and work.

### Conversion residual

```text
conversion residual
  = observed employment-opportunity score
  − cross-validated expected employment-opportunity score
```

Expected outcomes are modeled from education, finance, digital access, and macro conditions. Negative residuals identify potential under-conversion; positive residuals identify above-model performance. Residuals may also reflect omitted variables, measurement error, or mismatched years.

### Education progress without employment progress

```text
conversion shortfall
  = improvement in education gender gap
  − improvement in employment gender gap
```

This is an endpoint comparison where coverage permits. It is sensitive to starting and ending years.

### Momentum state

A Hidden Markov Model describes the latest latent state as Closing, Flat, or Widening. The interface should display all three posterior/state probabilities, not only the most likely label.

### First-passage analysis

The first-passage model estimates the probability of reaching half the current employment gap within a specified horizon, conditional on fitted historical dynamics. It is not a deterministic forecast.

## Dimensions for the country profile

- education;
- employment access;
- employment quality;
- financial inclusion;
- digital inclusion;
- identification;
- health;
- unpaid-care time;
- rural infrastructure;
- advancement and leadership when data permit.

## Main limitations

- Observation years vary across countries and domains.
- National averages conceal rural, income, disability, age, ethnicity, and other intersectional differences.
- Female labor-force participation may include unpaid family work or vulnerable self-employment.
- Some outcomes have sparse gender-disaggregated coverage.
- Cross-country prediction is not causal identification.
