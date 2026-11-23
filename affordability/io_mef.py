"""
Load the MEF incomes per comune (IRPEF tax returns, one CSV per tax year).

Moved from notebook 01. Quirks of the files, handled here:

- separator ``;``, encoding latin-1, an empty extra column (every line ends with ``;``);
- the ISTAT code must stay text, or the leading zero is lost (``015146`` = Milan);
- ``NA`` is Napoli's province, not a missing value;
- column names differ between years ("- Ammontare" vs "- Ammontare in euro", double spaces);
- the last row has code ``0`` (taxpayers not assigned to a comune).
"""

import zipfile

import pandas as pd

from .config import INCOME_YEARS, MEF_DIR, MEF_URL_TEMPLATE
from .errors import DataLoadError
from .io_common import download, require_file, short_path

CODE_COL = "Codice Istat Comune"
NAME_COL = "Denominazione Comune"
PROVINCE_COL = "Sigla Provincia"
YEAR_COL = "Anno di imposta"
TAXPAYERS_COL = "Numero contribuenti"


def mef_csv_path(year, folder=MEF_DIR):
    """Return the path of the MEF CSV of one tax year, e.g. ``data/raw/mef/mef_income_2024.csv``."""
    return folder / f"mef_income_{year}.csv"


def download_mef(year, folder=MEF_DIR, force=False):
    """
    Download the MEF ZIP of one tax year and extract its CSV (once).

    Parameters
    ----------
    year : int
        Tax year, e.g. 2024.
    folder : pathlib.Path, optional
        Where to save the files.
    force : bool, optional
        If True, download again even if the CSV exists.

    Returns
    -------
    pathlib.Path
        Path of the CSV, named ``mef_income_<year>.csv``.

    Raises
    ------
    DataLoadError
        If the download fails or the ZIP does not contain exactly one CSV.
    """
    csv_path = mef_csv_path(year, folder)
    if csv_path.exists() and not force:
        return csv_path

    zip_path = download(MEF_URL_TEMPLATE.format(year=year), folder / f"mef_{year}.zip", force=force)
    with zipfile.ZipFile(zip_path) as z:
        csv_files = [name for name in z.namelist() if name.lower().endswith(".csv")]
        if len(csv_files) != 1:
            raise DataLoadError(
                f"Expected one CSV in {short_path(zip_path)}, found {csv_files}"
            )
        csv_path.write_bytes(z.read(csv_files[0]))
    return csv_path


def clean_mef_columns(df):
    """
    Give the MEF columns the same names in every year and drop empty columns.

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF income table as read from the CSV.

    Returns
    -------
    pandas.DataFrame
        A copy with harmonised column names and without all-empty columns.
    """
    df = df.copy()
    # " ".join(name.split()) removes leading/trailing spaces and double spaces
    df.columns = [" ".join(col.split()) for col in df.columns]
    df.columns = [
        col.replace("- Ammontare in euro", "- Ammontare")
           .replace("minore o uguale a zero", "minore di zero")
        for col in df.columns
    ]
    return df.dropna(axis=1, how="all")       # the empty column after the last ";"


def load_mef(year, folder=MEF_DIR):
    """
    Load and clean the MEF incomes of one tax year.

    Parameters
    ----------
    year : int
        Tax year, e.g. 2024.
    folder : pathlib.Path, optional
        Folder with ``mef_income_<year>.csv``.

    Returns
    -------
    pandas.DataFrame
        One row per comune: the ISTAT code as 6-character text, harmonised column
        names, and a ``year`` column.

    Raises
    ------
    DataLoadError
        If the file is missing, or does not contain the expected year and columns.
    """
    path = require_file(
        mef_csv_path(year, folder),
        f"Run download_mef({year}) first.",
    )
    df = pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        dtype={CODE_COL: str},        # keep the leading zero of the ISTAT code
        keep_default_na=False,        # "NA" is Napoli's province, not a missing value
        na_values=[""],               # only an empty cell is missing
    )
    missing = {CODE_COL, NAME_COL, YEAR_COL, TAXPAYERS_COL} - set(df.columns)
    if missing:
        raise DataLoadError(f"{short_path(path)} has no column(s) {sorted(missing)}")
    if not (df[YEAR_COL] == year).all():
        raise DataLoadError(f"{short_path(path)} does not contain only tax year {year}")

    df = clean_mef_columns(df)
    # Real comuni have a 6-digit code; this drops the final "0" row
    df = df[df[CODE_COL].str.fullmatch(r"\d{6}")].copy()
    df["year"] = year
    return df.reset_index(drop=True)


def load_all_mef(years=INCOME_YEARS, folder=MEF_DIR):
    """
    Download (if needed) and load several tax years.

    Parameters
    ----------
    years : list of int, optional
        Tax years to load.
    folder : pathlib.Path, optional
        Folder of the MEF files.

    Returns
    -------
    dict
        ``{year: DataFrame}``.
    """
    result = {}
    for year in years:
        download_mef(year, folder)
        result[year] = load_mef(year, folder)
    return result


def find_mef_column(df, keyword, kind):
    """
    Find the MEF column that contains a keyword and ends with a given kind.

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF table after ``clean_mef_columns``.
    keyword : str
        Text in the column name, e.g. ``"lavoro dipendente"``.
    kind : str
        ``"Frequenza"`` (number of taxpayers) or ``"Ammontare"`` (euros).

    Returns
    -------
    str
        The full column name.

    Raises
    ------
    KeyError
        If no column, or more than one, matches.
    """
    matches = [col for col in df.columns if keyword in col and col.endswith(f"- {kind}")]
    if len(matches) != 1:
        raise KeyError(f"Expected 1 column for '{keyword}' / {kind}, found {matches}")
    return matches[0]
