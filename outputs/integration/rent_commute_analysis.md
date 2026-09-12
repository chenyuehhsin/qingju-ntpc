# Rent x Commute Analysis

Scope: 8 candidate living-area nodes joined to New Taipei official independent-suite rent benchmarks by district.

Neihu rent baseline: 19,500 NTD/month. This is a reference line only and is not included in Pareto calculations.

## Main Findings

- Lowest rent candidate: 汐止車站 (汐止區), 14,000 NTD/month, 47.2 minutes.
- Shortest commute candidate: 板橋站 (板橋區), 43.2 minutes, 16,000 NTD/month.
- Pareto-efficient candidates: 板橋站 (16,000 NTD, 43.2 min), 汐止車站 (14,000 NTD, 47.2 min).

## Dominated Candidates

- 大坪林站: dominated by 汐止車站.
- 三重站: dominated by 汐止車站.
- 頂溪站: dominated by 汐止車站.
- 蘆洲站: dominated by 三重站; 大坪林站; 板橋站; 汐止車站; 頂溪站.
- 新莊站: dominated by 三重站; 大坪林站; 汐止車站; 頂溪站.
- 景安站: dominated by 三重站; 汐止車站; 頂溪站.

## Interpretation

Rent x commute shows a meaningful but narrow trade-off at the frontier: Banqiao is the fastest option but costs 2,000 NTD/month more than Xizhi, while Xizhi is 4.0 minutes slower and has the lowest rent among these candidates.

The remaining six candidates do not add frontier choices under the current two-objective definition because at least one other candidate is both cheaper and no slower, or cheaper and faster.

These 8 candidates are sufficient to continue a first recommendation-model prototype because the join is complete and the two core numeric dimensions are available. They are not yet sufficient for a robust final model; later steps should add non-rent housing attributes, accessibility beyond Gangqian, and neighborhood-quality variables.

## Inputs And Outputs

- Input housing benchmark: `data/processed/housing/moi_independent_suite_rent_benchmark.csv`
- Input commute table: `data/processed/transport/commute_to_gangqian.csv`
- Integrated table: `data/processed/integration/rent_commute_candidates.csv`
- Scatter plot: `outputs/integration/01_rent_commute_scatter.png`
