# 🏠 How many years of salary to buy a home?

**Housing affordability across Italian municipalities**

This project measures, for every Italian comune, how many years of income it takes
to buy a typical flat, how this changed between 2014 and 2024, and **whether homes
are priced for the people who work there**. It compares house prices with the
incomes of all taxpayers and, separately, with the wages of employees.

> 🚧 **Work in progress.** This is a course project for *Coding for Data Science and
> Data Management* (Università degli Studi di Milano, 2026/27). Sections marked
> *(planned)* are not implemented yet.

## Research questions

1. **Price-to-income:** how many years of average income are needed to buy a 70 m²
   flat in each comune?
2. **Change over time:** where did house prices grow faster than incomes between
   2014 and 2024?
3. **Worker affordability gap:** how much less affordable is housing for employees
   than the average income suggests, and is the gap linked to the local economy
   (share of pensioners, property owners, high earners)?
4. **Mortgage and rent:** what share of a monthly salary goes to a mortgage
   instalment or to rent? *(planned)*

## Data sources

| Source | Publisher | What it contains | Years | How it is obtained |
|--------|-----------|------------------|-------|--------------------|
| [Redditi e principali variabili IRPEF su base comunale](https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?search_class%5B0%5D=cCOMUNE&opendata=yes) | MEF (Ministry of Economy and Finance) | Taxpayers and declared income per comune, by type of income and by income bracket | tax years 2014 and 2024 | **Automatic** download by the code (ZIP → CSV). Licence CC-BY 4.0 |
| Quotazioni immobiliari OMI | Agenzia delle Entrate (OMI) | Minimum and maximum price (€/m²) and rent (€/m²/month) per zone, property type and condition | 2014 H2 and 2024 H2 | **Manual** download with SPID (see below) |
| [Elenco comuni italiani](https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx) | ISTAT | Official code, name, province, region and macro-area of every comune | current list | **Automatic** download (XLSX) |
| [Confini amministrativi, versione generalizzata](https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2025/Limiti01012025_g.zip) | ISTAT | Boundaries (polygons) of every comune, as of 1 January 2025 | 2025 | **Automatic** download (ZIP → shapefile) |
| [Cost of borrowing for house purchase, Italy](https://data.ecb.europa.eu/) (series `MIR.M.IT.B.A2C.AM.R.A.2250.EUR.N`) | ECB (European Central Bank) | Average interest rate on new mortgages in Italy, monthly | 2010 to today | **Automatic** download through the ECB Data Portal **API** (CSV) |
| [HICP, overall index, Italy](https://data.ecb.europa.eu/) (series `ICP.M.IT.N.000000.4.INX`) | ECB (Eurostat data) | Harmonised consumer price index, monthly (2015 = 100), used to measure inflation | 2014 to today | **Automatic** download through the ECB Data Portal **API** (CSV) |

All sources are joined through the **6-digit ISTAT municipal code**
(e.g. `015146` = Milano), always handled as text so that the leading zero is kept.

### How to download the OMI data (SPID required)

The OMI data cannot be downloaded by code because it requires a personal login.

1. Go to [agenziaentrate.gov.it](https://www.agenziaentrate.gov.it) and log in to the
   *Area riservata* with SPID (or CIE/CNS).
2. Open **Servizi → Forniture dati OMI → Quotazioni immobiliari**.
3. Choose **Territorio nazionale**, then the semester: **2024, 2° semestre**.
4. Do **not** tick *Perimetri di Zona OMI* (zone shapes, not needed).
5. Submit the request and repeat it for **2014, 2° semestre**.
6. The requests appear in *My Requests* with state **Inserted**. After processing
   (usually a few hours) the state becomes **Available** and a download link appears.
   ⚠️ Each request can be downloaded **only once** and expires 7 days after processing.
7. Rename the downloaded ZIPs to `omi_2014_2.zip` and `omi_2024_2.zip` (the original
   names contain your codice fiscale) and put them in `data/raw/omi/`. The
   notebook extracts them automatically.

### Notes on the MEF income data

Findings from the exploration notebook
([`notebooks/01_explore_mef.ipynb`](notebooks/01_explore_mef.ipynb)):

- **One row = one comune in one tax year.** 8,049 comuni in 2014, 7,897 in 2024:
  152 fewer, because small comuni merged in the meantime. Their codes are harmonised
  to the 2025 codes *(planned, Week 3)*.
- The year used is the **tax year** (*anno d'imposta*): "2025 a.i. 2024" contains
  incomes earned in 2024.
- Most variables come in pairs: **Frequenza** = number of taxpayers with that income,
  **Ammontare** = total euros. Their ratio is the average per person.
- **Income measure:** average **taxable income** (`Reddito imponibile` Ammontare /
  Frequenza). It is available in both years with no missing values. The total
  *reddito complessivo* exists only in the 2024 file.
- **Missing values (NaN)** in the other columns mean that MEF hid the value because
  very few taxpayers fall in that category (privacy), mostly in small comuni.
- **Format differences between years**, handled by `clean_mef_columns()`:
  - 2024 column names end with `- Ammontare in euro`, 2014 ones with `- Ammontare`;
  - some names contain double or trailing spaces;
  - the lowest bracket changed from *minore di zero* (< 0, 2014) to
    *minore o uguale a zero* (≤ 0, 2024);
  - the 2024 CSV ends every line with `;`, which creates an extra, empty column.
- **Napoli and "NA":** the province code of Napoli is `NA`, which pandas reads as a
  missing value by default. The files are read with
  `keep_default_na=False, na_values=[""]`.
- **Names** are written in uppercase ASCII with an apostrophe in place of the accent
  (`CAVAGLIA'` = Cavaglià). Official names are taken from the ISTAT list instead.
- Files are read with `sep=";"` and `encoding="latin-1"`.
- The **last row of the 2024 file** has code `0` and all fields set to 0: it contains
  taxpayers not assigned to any comune. Only rows with a 6-digit ISTAT code are kept.
- **Mappano** (`001316`) was created in 2013 but became operational only in 2017:
  its 2014 row covers only 12 taxpayers (5,460 in 2024), so it is excluded from the
  2014 → 2024 comparisons.
- **Building income** (*reddito da fabbricati*) mostly measures **home ownership**
  (the cadastral income of the main home is declared and then deducted), not rents:
  most rents are taxed with the flat *cedolare secca* outside IRPEF. Its share of
  income fell in almost every comune between 2014 and 2024, a national effect of
  tax rules and frozen cadastral values.
- **Self-employed and business income** roughly halved between 2014 and 2024 because
  the flat-tax regime (*regime forfettario*) was extended, which moved that income
  out of IRPEF. This is why the **employee wage** is used as the main income measure
  for affordability.

### Notes on the OMI price data

Findings from [`notebooks/02_explore_omi.ipynb`](notebooks/02_explore_omi.ipynb):

- Each semester comes as one ZIP with two CSV files, e.g. `QI_<request>_1_20242_VALORI.csv`
  and `..._ZONE.csv` (`20242` = 2024, 2nd semester). The notebook reads the semester
  from the file name.
- **VALORI** (prices): one row = one **zone** of a comune × one **property type**
  (*Abitazioni civili*, *Box*, *Negozi*, ...) × one **condition** (*NORMALE*, *OTTIMO*,
  *SCADENTE*). About 160,000 rows per semester. Prices to buy (`Compr_min`, `Compr_max`,
  €/m²) and to rent (`Loc_min`, `Loc_max`, €/m² per month).
- **ZONE**: one row = one zone, with its description (`Zona_Descr`) and position
  (`Fascia`: B centre, C semi-centre, D periphery, E suburban, R rural). About 27,000 zones.
- **File format:** the first line is a title ("Quotazioni Immobiliari : Valori di Mercato -
  Semestre 2014/2 ..."), the header is on the second line, the separator is `;` and every
  line ends with `;` (an extra, empty column). The header line is found automatically.
- **Decimal comma** in rents (`3,6` = 3.6 €/m²): converted when cleaning.
- **ISTAT code with a region prefix:** `Comune_ISTAT` is `1006003` = region `1` (Piemonte)
  + `006003` (Alessandria). It has 7 or 8 digits, so the **last 6 digits** are kept to
  match MEF and ISTAT.
- **Broken codes for merged comuni:** about 250 rows (some 15 comuni, mostly born from
  mergers, e.g. Piadena Drizzona, Vermezzo con Zelo, Val di Chy) have codes of 5 or 6
  digits: the region prefix is there but the leading zeros are lost (`319116` = region 3
  + `019116`), or the prefix is missing (`38028` = `038028`). One row (Ordona) has no code.
  Taking the last 6 digits would give wrong codes, some of which could exist in **another
  province** (a silent wrong match). Fix: try every reading of the digits and keep the one
  that exists in the ISTAT list **in the same province**; if none does, match on
  province + name.
- **Zone maps change over time.** OMI sometimes redraws its zones: 10% of comuni have a
  different number of zones in 2014 and 2024 (Turin 41 → 47, Venice 14 → 32). Comparing
  the "median of the zones" of two different maps mixes a price change with a map change.
  So **changes over time are computed zone by zone** (same comune + same zone code in both
  years), then the median per comune. This matters a lot for some cities (Turin −8.2% with
  all zones, −0.5% with the same zones; Venice −16.5% vs −4.7%) and little for others
  (Bologna +5.8% both ways). Caveat: a zone code kept by OMI may cover a slightly
  different area after a revision.
- **Prices 2014 → 2024 (same zones):** the median comune fell by about 5% in **nominal**
  terms (−5.2%, weighted by taxpayers), i.e. about −21% in **real** terms after ~20%
  inflation. With all zones, prices rose in only 22% of comuni, home to 28% of taxpayers. Milan is the
  big exception (+42%); Rome (−12%), Genoa (−19%) and Palermo (−8%) fell. This matches the
  known Italian pattern (prices fell after the 2008 and 2011–12 crises until about 2019 and
  recovered mainly in a few cities), but OMI values are conservative estimates that react
  slowly, not transaction prices, so recent rises may be understated.
- **Price 0 = no quotation.** In the zones hit by the 2016 Central Italy earthquake
  (Norcia, Cascia, Arquata del Tronto, Preci, ...) OMI publishes 0 €/m². Zeros are treated
  as missing values.
- **Sticky quotations:** OMI does not revise every zone every semester; in many small
  comuni the 2024 price is exactly the 2014 one. Changes over time are more reliable for
  larger comuni.
- **Names** use a backtick instead of the apostrophe (``CORTINA D`AMPEZZO``) and have
  some typos (`FORTE DE MARMI`): official names are taken from the ISTAT list.
- **Filter:** only *Abitazioni civili* in *NORMALE* condition, so the same kind of property
  is compared everywhere. Price of a zone = (min + max) / 2; price of a comune = **median**
  of its zones.
- **Centre vs periphery: a Simpson's paradox.** Across all of Italy, the median centre
  zone (B, 895 €/m²) looks *cheaper* than semi-centre (C, 1,325) and periphery (D, 1,085)
  zones (ordinary homes, normal condition, 2024 H2). This is a composition effect: 99% of
  comuni have a B zone, including thousands of cheap villages, while only 10% have a C zone
  and 33% a D zone (mostly bigger, more expensive towns). Comparing each zone with the centre
  of **its own comune** gives the expected order: the median comune prices C at 94% of its
  centre, D at 93%, E at 95% and R (rural) at 83%. E being slightly above D fits seaside and
  lake towns, where the "suburban" zone is often the waterfront. Lesson: compare prices
  *within* comuni, or weight them, before drawing conclusions.

### Notes on the ISTAT and ECB data

Findings from [`notebooks/03_explore_istat.ipynb`](notebooks/03_explore_istat.ipynb)
*(counts to be filled in after running on the real data)*:

- **ISTAT list:** the Excel column names are long and some contain line breaks, so the
  notebook finds each column by a piece of its name. Codes are read as text (`dtype=str`).
  It gives proper names (with accents and apostrophes) and the **macro-area**
  (Nord-ovest, Nord-est, Centro, Sud, Isole).
- **Code matching and mergers (*fusioni*):** Italy had about 8,050 comuni in 2014 and about
  7,900 in 2025. Merged comuni get a new code and the old codes disappear, so some 2014
  codes are not in the 2025 list. Decision: compare 2014 and 2024 only for comuni with the
  same code in both years (plus the ±50% size filter).
- **Boundaries:** shapefile `Com01012025_g_WGS84.shp`, join column `PRO_COM_T` (code as
  text). The coordinate system is **EPSG:32632** (UTM 32N), in **metres**, so distances
  are measured directly. Distances from Milan use comune centroids and a
  `scipy.spatial.cKDTree`.
- **Mortgage rate (ECB):** the composite cost of borrowing on new home loans in Italy.
  Yearly averages are used for 2014 and 2024. The decade had record-low rates around
  2020–2021, followed by a sharp rise in 2022–2023.
- **Inflation (ECB, HICP):** used in the OMI notebook to turn the 2014→2024 price change
  into a **real** change (the first version used an approximate 20%). Inflation = average
  index of 2024 / average index of 2014 − 1, with yearly averages to match the MEF tax
  years. The API URL is `.../service/data/<dataset>/<series key>`: the dataset (`ICP`,
  `MIR`) is separated from the key by a slash, otherwise the server answers *400 Bad Request*.
- **Mortgage payment:** annuity formula with 80% loan-to-value over 25 years, vectorised in
  numpy, with a special case for a zero rate. MEF wages are **gross**, while banks use
  **net** income, so the burden shown is a lower bound.

## Method

### Main measures *(planned)*

| Measure | Formula | Meaning |
|---------|---------|---------|
| Price-to-income ratio | (price per m² × 70) / average taxable income | Years of income needed to buy a 70 m² flat |
| Price-to-wage ratio | (price per m² × 70) / average employee wage | The same, for a salaried worker |
| Worker affordability gap | price-to-wage / price-to-income | How much worse it is for employees than the average suggests |
| Mortgage payment share | monthly instalment on 80% of the price, 25 years / monthly wage | Above 30–35% is considered unaffordable by banks |
| Price vs income growth | compound yearly growth 2014 → 2024 | Where homes became harder to buy |
| Rent burden | (rent per m² × 70 × 12) / income | Share of income spent on rent |

### Key choices

| Choice | Decision | Why |
|--------|----------|-----|
| Price of a comune | Median of the OMI zone midpoints ((min + max) / 2) | The mean would be pulled up by a few luxury central zones |
| Property type | *Abitazioni civili* in *NORMALE* condition | Ordinary homes, not luxury or run-down properties |
| Flat size | 70 m² (adjustable in the app) | A typical flat for a small family |
| Income | Average taxable income per taxpayer; average employee wage as a second measure | Complete in both years; the wage matches "years of salary" |
| Statistics | Spearman correlation, Kruskal-Wallis test | The data is skewed, so non-parametric methods fit better |
| Small comuni | Rankings only for comuni with at least 1,000 taxpayers | Averages of tiny villages are unstable |

### Limitations

- MEF incomes are **declared** incomes: tax evasion and flat-tax self-employed workers
  (*regime forfettario*) are not fully included, so some areas look poorer than they are.
- Incomes are per **taxpayer**, not per household.
- People are counted where they **live**, not where they work (commuters).
- OMI gives **price ranges** for zones, not actual sale prices.
- All values are **nominal** euros. Comparing prices and incomes of the same year
  is not affected by inflation; changes over time are also shown in **real** terms,
  deflated with the HICP.
- Results describe **comuni**, not individual people, and correlations do not
  imply causation.

## Libraries

| Library | Used for |
|---------|----------|
| `requests` | downloading the MEF and ISTAT files |
| `pandas` | loading, cleaning, merging and reshaping the tables |
| `numpy` | vectorised calculations (ratios, mortgage formula, growth rates) |
| `scipy` | statistical tests and correlations |
| `matplotlib`, `seaborn` | charts |
| `geopandas` | reading the boundaries and drawing maps |
| `openpyxl` | reading the ISTAT Excel file |
| `streamlit` | the interactive web app *(planned)* |
| `jupyterlab` | the notebooks |

Exact versions are listed in [`requirements.txt`](requirements.txt).

## Setup

1. Clone the repository and enter the folder:

   ```bash
   git clone https://github.com/<your-user>/housing-affordability-italy.git
   cd housing-affordability-italy
   ```

2. Create a virtual environment and install the dependencies (Python 3.11 or newer):

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # on Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Download the OMI files as described in
   [How to download the OMI data](#how-to-download-the-omi-data-spid-required)
   and put them in `data/raw/omi/`. The other sources are downloaded automatically.

## Run

*(planned)*

```bash
python scripts/build_dataset.py      # download, clean and merge the data
streamlit run app.py                 # start the web app
jupyter lab                          # open the notebooks
```

## Project structure

```
housing-affordability-italy/
├── affordability/                  # the Python package (no Streamlit code here)
│   └── __init__.py
├── data/                           # not committed (see .gitignore)
│   ├── raw/                        # downloaded files: mef/, omi/, istat/, ecb/
│   └── processed/                  # the final merged table
├── notebooks/
│   ├── 01_explore_mef.ipynb   # exploration of the MEF income data
│   ├── 02_explore_omi.ipynb   # exploration of the OMI house prices
│   └── 03_explore_istat.ipynb # ISTAT list and boundaries, code matching, maps, ECB mortgage rates
├── pages/                          # Streamlit pages (planned)
├── scripts/                        # pipeline scripts (planned)
├── .gitignore
├── requirements.txt
└── README.md
```

## Data licence and attribution

MEF income data: © Ministero dell'Economia e delle Finanze, licence CC-BY 4.0.
OMI data: © Agenzia delle Entrate – Osservatorio del Mercato Immobiliare.
ISTAT data: © Istituto Nazionale di Statistica, licence CC-BY 4.0.
Mortgage rates: © European Central Bank, ECB Data Portal (free reuse with source attribution).
