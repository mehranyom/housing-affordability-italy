"""
Read the final tables made by ``scripts/build_dataset.py``.

The analysis notebook and the Streamlit app start here, not from the raw data.
"""

import pandas as pd

from .config import CHANGES_FILE, INCOME_MIX_FILE, PANEL_FILE, RATES_FILE, ZONES_FILE
from .io_common import require_file

BUILD_HINT = "Run 'python scripts/build_dataset.py' from the project folder first."


def read_table(path):
    """
    Read one processed CSV with the same text rules as the raw files.

    Parameters
    ----------
    path : pathlib.Path
        The CSV file.

    Returns
    -------
    pandas.DataFrame
        ``istat_code`` as text (``015146``, not ``15146``), and ``NA`` (Napoli's
        province) kept as text: only empty cells are missing.

    Raises
    ------
    DataLoadError
        If the file has not been built yet.
    """
    return pd.read_csv(
        require_file(path, BUILD_HINT),
        dtype={"istat_code": str},
        keep_default_na=False,
        na_values=[""],
    )


def load_panel(path=PANEL_FILE):
    """
    One row per comune and year, with prices, incomes and affordability measures.

    Returns
    -------
    pandas.DataFrame
        ``istat_code`` is read as text (``015146``, not ``15146``).

    Raises
    ------
    DataLoadError
        If the file has not been built yet.
    """
    return read_table(path)


def load_changes(path=CHANGES_FILE):
    """
    One row per comune: change of price and rent 2014 -> 2024 (same zones).

    Returns
    -------
    pandas.DataFrame
        ``istat_code`` is read as text.

    Raises
    ------
    DataLoadError
        If the file has not been built yet.
    """
    return read_table(path)


def load_zones(path=ZONES_FILE):
    """
    One row per OMI zone and year (ordinary homes): ``fascia``, ``buy_mid``, ``rent_mid``.

    Raises
    ------
    DataLoadError
        If the file has not been built yet.
    """
    return read_table(path)


def load_income_mix(path=INCOME_MIX_FILE):
    """
    Italy: share of taxpayers and of income by type of income, per year.

    Raises
    ------
    DataLoadError
        If the file has not been built yet.
    """
    return pd.read_csv(require_file(path, BUILD_HINT))



def load_rates(path=RATES_FILE):
    """
    Italy: average rate on new mortgages, one row per month.

    Returns
    -------
    pandas.DataFrame
        Columns ``date`` (a datetime) and ``rate_pct`` (% per year).

    Raises
    ------
    DataLoadError
        If the file has not been built yet.
    """
    return pd.read_csv(require_file(path, BUILD_HINT), parse_dates=["date"])
