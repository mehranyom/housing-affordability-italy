"""
Project settings: folders, download links and the constants of the analysis.

Everything that could change (a year, a URL, the size of the "typical flat") lives
here, so the rest of the code never repeats a hard-coded value.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------
# Path(__file__) is this file; .parent is the package folder (affordability/),
# .parent.parent is the project folder. Built this way, the paths work no matter
# where Python is started from (notebooks/, the project folder, Streamlit, ...).
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

MEF_DIR = RAW_DIR / "mef"
OMI_DIR = RAW_DIR / "omi"
ISTAT_DIR = RAW_DIR / "istat"
ECB_DIR = RAW_DIR / "ecb"

# Output of scripts/build_dataset.py, read by the analysis notebook and the app
PANEL_FILE = PROCESSED_DIR / "comuni_panel.csv"        # one row per comune and year
CHANGES_FILE = PROCESSED_DIR / "comuni_changes.csv"    # one row per comune, 2014 -> 2024
ZONES_FILE = PROCESSED_DIR / "omi_zones.csv"           # one row per OMI zone and year
INCOME_MIX_FILE = PROCESSED_DIR / "income_mix.csv"     # Italy: taxpayers by income type
RATES_FILE = PROCESSED_DIR / "mortgage_rates.csv"      # Italy: mortgage rate, monthly

# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 120                        # seconds before a download gives up
# Some public servers refuse requests without a browser-like User-Agent
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}

# MEF: incomes per comune. Only the year changes in the link.
MEF_URL_TEMPLATE = (
    "https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/"
    "Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_{year}.zip?d=1615465800"
)
INCOME_YEARS = [2014, 2024]                  # tax years (anno d'imposta)

# OMI: house prices. Downloaded by hand with SPID (see README), one ZIP per semester,
# renamed to omi_<year>_<semester>.zip
OMI_SEMESTERS = ["2014_2", "2024_2"]

# ISTAT: official list of comuni and their boundaries (1 January 2025)
ISTAT_COMUNI_URL = (
    "https://www.istat.it/storage/codici-unita-amministrative/"
    "Elenco-comuni-italiani.xlsx"
)
ISTAT_BOUNDARIES_URL = (
    "https://www.istat.it/storage/cartografia/confini_amministrativi/"
    "generalizzati/2025/Limiti01012025_g.zip"
)

# ECB Data Portal API: .../service/data/<dataset>/<series key>
ECB_API_URL = "https://data-api.ecb.europa.eu/service/data/{dataset}/{key}"
# Cost of borrowing for house purchase, Italy, new loans, monthly (%)
MORTGAGE_SERIES = ("MIR", "M.IT.B.A2C.AM.R.A.2250.EUR.N")
# Harmonised consumer price index, Italy, all items, monthly (2015 = 100)
HICP_SERIES = ("ICP", "M.IT.N.000000.4.INX")
ECB_START_PERIOD = "2010-01"

# ---------------------------------------------------------------------------
# Analysis choices (see "Key choices" in the README)
# ---------------------------------------------------------------------------
FLAT_SIZE_M2 = 70              # the "typical flat"
LOAN_TO_VALUE = 0.80           # share of the price a bank lends
MORTGAGE_YEARS = 25            # length of the mortgage
MIN_TAXPAYERS = 1000           # rankings only for comuni with at least this many taxpayers
OMI_PROPERTY_TYPE = "Abitazioni civili"
OMI_CONDITION = "NORMALE"
MILAN_CODE = "015146"
MORTGAGE_LIMIT_PCT = 33        # highest payment / monthly wage a bank usually accepts

# The ten largest cities (ISTAT codes), for labels and comparisons
BIG_CITIES = {
    "015146": "Milano", "058091": "Roma", "063049": "Napoli", "001272": "Torino",
    "082053": "Palermo", "010025": "Genova", "037006": "Bologna", "048017": "Firenze",
    "072006": "Bari", "027042": "Venezia",
}
# Distance bands from Milan, in km (the upper edge of each band)
DISTANCE_BANDS_KM = [0.001, 15, 30, 50, 100, 2000]
DISTANCE_LABELS = ["Milan", "< 15 km", "15-30 km", "30-50 km", "50-100 km", "> 100 km"]
