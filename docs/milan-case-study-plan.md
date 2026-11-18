# Extra result: why is Milan unaffordable, and why does it stay that way?

A plan for an optional "Milan case study" (notebook `04_milan_case_study.ipynb`,
one page in the Streamlit app, 3–4 slides on presentation day).

## The honest framing

Our data can **describe the mechanism** (who earns what, where prices rose, who gets
pushed out). It cannot **prove causes**: there is no supply data (new homes,
permits), no buyer data (who buys: investors, foreigners, funds) and no tourism data
in MEF/OMI. So the claim on the slide is:

> "The data is consistent with X", not "X is the root cause."

Saying this out loud on presentation day is a strength. It shows you know the difference
between correlation and causation, which economists check for first.

## Part A: what we can show with the data we already have

| # | Question | Data | Output |
|---|----------|------|--------|
| A1 | **Prices and incomes diverged.** How much faster did Milan prices grow than Milan incomes and wages, vs the rest of Italy? | OMI 2014/2024, MEF 2014/2024 | Index chart (2014 = 100): Milan price, Milan income, Milan wage, Italy price, Italy income |
| A2 | **For whom is Milan priced?** Years of income to buy 60 m² for the *median* taxpayer vs a taxpayer in the top bracket (>€75k / >€120k) | MEF brackets + OMI | Bar chart: years to buy, per income bracket |
| A3 | **Inequality.** Milan's Gini and top-income share vs other big cities and Italy, 2014 → 2024 | MEF (functions already in notebook 01) | Small table + dot chart |
| A4 | **Renters lose twice.** Rent rose faster than prices in most of Italy. Rent burden of a 60 m² flat for the average Milan employee, 2014 vs 2024 | OMI rents + MEF wages | Rent as % of wage, 2014 vs 2024 |
| A5 | **Displacement to the hinterland.** Did prices rise faster in the comuni around Milan (Sesto, Cinisello, Rho, Monza...) than in Milan itself, i.e. are people being pushed out? | OMI + ISTAT boundaries (distance from Milan) | Map of the Città metropolitana: price change 2014→2024; scatter: distance vs change |
| A6 | **Inside the city.** Which OMI zones of Milan rose most (Porta Romana / Olympic village, Isola, NoLo...)? | OMI zones 2014 vs 2024 | Bar chart of zone changes. ⚠️ First check that OMI zone codes did not change between 2014 and 2024 |

## Part B: optional external data (only if time allows)

| Topic | Source | Why |
|-------|--------|-----|
| Short-term rentals | Inside Airbnb, Milan (free, CC BY 4.0) | Homes taken off the long-term rental market, per zone |
| New construction | ISTAT, building permits (*permessi di costruire*) | Supply response: are enough homes being built? |
| Population / households | ISTAT demographic data | Demand: Milan keeps attracting young workers and students |

## Part C: "why it is not getting resolved" (discussion, not data)

Talking points for the presentation, each to be checked against a source before use:

- **Most voters are homeowners** (around 70% of Italian households own their home). Rising
  prices make them richer, so there is little political pressure to bring prices down.
- **Demand-side policies push prices up.** Subsidies to buyers (first-home bonuses,
  guarantees for under-36s) add purchasing power when supply is fixed, so part of the
  subsidy ends up in the price.
- **Supply is slow and contested.** New building in Milan depends on complex planning
  rules. In 2024–25 a judicial investigation into city planning permits slowed or
  blocked several building sites.
- **Milan competes globally.** Incomes in Milan are set by the Italian labour market,
  but prices are set partly by international demand: the flat tax for new wealthy
  residents, foreign investors, the 2026 Winter Olympics and tourism. Local wages cannot
  keep up with a global price.

- **Housing is not a normal market.** Demand is inelastic (everyone needs a home, and
  moving is costly), and supply is inelastic in the short run (new homes take years). So a
  small rise in demand pushes rents up a lot, and sitting tenants have little bargaining
  power. Rents also resist falling: landlords can leave a flat empty instead of cutting the
  rent, because holding costs are low and evictions in Italy are slow, so a "safe" tenant at
  a high rent beats a risky one at a low rent. This fits the data: rents beat prices in every
  group of comuni (notebook 02, section 5.4).

## Scope warning

The evaluation is on 1–3 December. The core project still needs the ISTAT notebook,
the `affordability/` package and the Streamlit app, and those are graded criteria.
Suggested order:

1. Finish the OMI notebook (findings and README).
2. Do the ISTAT notebook and the package (the core).
3. **Then** add Part A of the Milan case study: A1 to A4 are about one day of work,
   because they reuse functions we already have. A5 needs the ISTAT boundaries.
4. Part B only if time allows.
