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
7. Unzip the files into `data/raw/omi/`.

### Notes on the MEF income data

Findings from the exploration notebook
([`notebooks/01_data_exploration.ipynb`](notebooks/01_data_exploration.ipynb)):

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
  is not affected by inflation.
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
│   ├── raw/                        # downloaded files: mef/, omi/, istat/
│   └── processed/                  # the final merged table
├── notebooks/
│   └── 01_data_exploration.ipynb   # first look at the raw data
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
