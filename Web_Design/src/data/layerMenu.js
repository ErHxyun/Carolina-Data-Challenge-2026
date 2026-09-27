// Card menu for the map's "Analysis dimension" picker. Two tabs separate annual time series from
// latest snapshots; groups inside each tab say who is compared or which question is asked.
// Plain-language labels live here; full definitions stay in the layer registry (layers.json).
// `rural:<Dimension>` entries are the existing rural–urban dimensions, unchanged.

export const MENU = [
  {
    id: 'time',
    label: 'Over time',
    hint: 'Annual series with a year slider',
    groups: [
      {
        label: 'Rural vs urban women',
        short: 'Rural vs urban',
        note: 'Urban minus rural women · Bayesian model medians',
        items: [
          { id: 'rural:Overall', label: 'Overall', question: 'How far apart are rural and urban women overall?' },
          { id: 'rural:Education', label: 'Education', question: 'Do rural girls and women lag urban ones in education?' },
          { id: 'rural:Employment', label: 'Employment', question: 'Do rural women lag urban women in paid work?' },
          { id: 'rural:Health', label: 'Health', question: 'Do rural women lag urban women in health?' },
          { id: 'rural:Infrastructure', label: 'Infrastructure', question: 'Do rural women lack services urban women have?' },
        ],
      },
      {
        label: 'Women vs men',
        short: 'Women vs men',
        note: 'Distance from gender parity',
        items: [
          { id: 'education_gap_timeline', label: 'Education', question: 'How far are girls from boys in secondary school?' },
          { id: 'employment_gap_timeline', label: 'Employment', question: 'How far are women from men in the labour force?' },
          { id: 'conversion_gap_timeline', label: 'Education vs employment', question: 'Is school closer to parity than work?' },
          { id: 'female_lfpr_timeline', label: 'Women in the labour force', question: 'What share of women are working or seeking work?' },
          { id: 'female_vulnerable_employment_timeline', label: 'Vulnerable work', question: 'How much of women’s work is insecure?' },
        ],
      },
      {
        label: 'Rural vs urban households',
        short: 'Rural vs urban households',
        note: 'Services that shape daily time burdens',
        items: [
          { id: 'rural_electricity_gap_timeline', label: 'Electricity', question: 'How far does rural electricity access lag?' },
          { id: 'rural_clean_cooking_gap_timeline', label: 'Clean cooking', question: 'How far does rural clean cooking lag?' },
        ],
      },
    ],
  },
  {
    id: 'snapshot',
    label: 'Latest snapshot',
    hint: 'Latest available values; no year slider',
    groups: [
      {
        label: 'Does education turn into work?',
        short: 'Education to work',
        note: 'Signals from the conversion model',
        items: [
          { id: 'education_employment_conversion_gap_z', label: 'Education ahead of work', question: 'Is education more gender-equal than work?' },
          { id: 'conversion_residual', label: 'Better or worse than expected', question: 'Is women’s work above or below what the model expects?' },
          { id: 'conversion_shortfall', label: 'Education improved, work didn’t', question: 'Did education gaps close faster than work gaps?' },
        ],
      },
      {
        label: 'Where is it heading?',
        short: 'Model outlook',
        note: 'Model probabilities, not forecasts',
        items: [
          { id: 'gap_momentum_state', label: 'Direction of change', question: 'Is the gap closing, flat or widening?' },
          { id: 'prob_gap_widening', label: 'Chance of getting worse', question: 'How likely is the gap to be widening?' },
          { id: 'prob_gap_not_halved_within_15y', label: 'Chance the gap persists', question: 'How likely is it not to halve in 15 years?' },
          { id: 'prob_employment_gap_halves_within_10y', label: 'Chance of halving', question: 'How likely is the work gap to halve in 10 years?' },
        ],
      },
      {
        label: 'Everyday barriers',
        short: 'Everyday barriers',
        note: 'Access that shapes whether women can work',
        items: [
          { id: 'finance_gender_gap_pp', label: 'Bank account', question: 'Do women have accounts as often as men?' },
          { id: 'digital_gender_gap_pp', label: 'Internet', question: 'Are women online as often as men?' },
          { id: 'identity_female_pct', label: 'ID', question: 'What share of women have official ID?' },
          { id: 'time_tax_extra_hours_day', label: 'Unpaid care hours', question: 'How many extra unpaid hours do women work each day?' },
          { id: 'maternal_mortality_ratio', label: 'Maternal health', question: 'How severe is maternal-health risk?' },
          { id: 'rural_time_tax_gap_latest_pp', label: 'Rural time burden', question: 'How far do rural households lag in time-saving services?' },
        ],
      },
      {
        label: 'Data gaps',
        short: 'Data gaps',
        note: 'Who is missing from the statistics',
        items: [
          { id: 'core_domains_observed', label: 'Data coverage', question: 'How many core domains have data?' },
          { id: 'core_year_spread', label: 'Years out of sync', question: 'How far apart are the latest data years?' },
          { id: 'observed_education_years', label: 'Observed education years', question: 'In how many years was education actually measured?' },
          { id: 'observed_missing_share', label: 'Missing records', question: 'What share of the record is missing?' },
        ],
      },
    ],
  },
];

const INDEX = new Map(MENU.flatMap((tab) => tab.groups.flatMap((group) => group.items.map((item) => [item.id, { ...item, group, tab }]))));

export const menuItem = (id) => INDEX.get(id) ?? null;
/** "Women vs men · Education" style label used in legends, tooltips and the picker button. */
export const menuLabel = (id, fallback) => {
  const item = INDEX.get(id);
  return item ? `${item.group.short} · ${item.label}` : fallback;
};
export const RURAL_PREFIX = 'rural:';
