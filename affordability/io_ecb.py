"""
Load monthly series from the ECB Data Portal API: mortgage rates and inflation.

Moved from notebooks 02 and 03. The API URL is
``https://data-api.ecb.europa.eu/service/data/<dataset>/<series key>``: the dataset
and the key are separated by a slash (otherwise the server answers 400 Bad Request).
"""

import pandas as pd

from .config import ECB_API_URL, ECB_DIR, ECB_START_PERIOD, HICP_SERIES, MORTGAGE_SERIES
from .errors import DataLoadError
from .io_common import download, short_path


def ecb_url(dataset, key, start=ECB_START_PERIOD):
    """Return the API URL of one ECB series, as CSV, from ``start`` (``"YYYY-MM"``)."""
    return ECB_API_URL.format(dataset=dataset, key=key) + f"?format=csvdata&startPeriod={start}"


def load_ecb_series(dataset, key, filename, folder=ECB_DIR, force=False):
    """
    Download (once) and load one monthly ECB series.

    Parameters
    ----------
    dataset : str
        ECB dataset, e.g. ``"MIR"`` (bank interest rates) or ``"ICP"`` (consumer prices).
    key : str
        Series key inside the dataset.
    filename : str
        Name of the cached CSV in ``folder``.
    folder : pathlib.Path, optional
        Where the CSV is saved.
    force : bool, optional
        If True, download again (to get the newest months).

    Returns
    -------
    pandas.DataFrame
        Columns ``date`` (first day of the month) and ``value``, sorted by date.

    Raises
    ------
    DataLoadError
        If the download fails or the file has no ``TIME_PERIOD``/``OBS_VALUE`` columns.
    """
    path = download(ecb_url(dataset, key), folder / filename, force=force)
    raw = pd.read_csv(path)
    if not {"TIME_PERIOD", "OBS_VALUE"} <= set(raw.columns):
        raise DataLoadError(
            f"{short_path(path)} is not an ECB series file: delete it and download again."
        )
    series = pd.DataFrame({
        "date": pd.to_datetime(raw["TIME_PERIOD"], format="%Y-%m"),
        "value": pd.to_numeric(raw["OBS_VALUE"], errors="coerce"),
    })
    return series.dropna().sort_values("date").reset_index(drop=True)


def load_mortgage_rates(folder=ECB_DIR):
    """
    Average interest rate on new mortgages in Italy, monthly, in % per year.

    Returns
    -------
    pandas.DataFrame
        Columns ``date`` and ``value``.
    """
    dataset, key = MORTGAGE_SERIES
    return load_ecb_series(dataset, key, "mortgage_rate_it.csv", folder)


def load_hicp(folder=ECB_DIR):
    """
    Harmonised consumer price index for Italy, monthly (2015 = 100).

    Returns
    -------
    pandas.DataFrame
        Columns ``date`` and ``value``.
    """
    dataset, key = HICP_SERIES
    return load_ecb_series(dataset, key, "hicp_it.csv", folder)


def yearly_average(series):
    """
    Average of a monthly series for each calendar year.

    Parameters
    ----------
    series : pandas.DataFrame
        Columns ``date`` and ``value``, as returned by ``load_ecb_series``.

    Returns
    -------
    pandas.Series
        Index = year, values = yearly average.
    """
    return series.groupby(series["date"].dt.year)["value"].mean()


def inflation_between(start_year, end_year, hicp=None):
    """
    Inflation between two years, from yearly averages of the HICP.

    Parameters
    ----------
    start_year, end_year : int
        For example 2014 and 2024.
    hicp : pandas.DataFrame, optional
        The HICP series; loaded with ``load_hicp`` if not given.

    Returns
    -------
    float
        For example 0.224 for +22.4%.

    Raises
    ------
    DataLoadError
        If one of the years is not in the series.
    """
    yearly = yearly_average(load_hicp() if hicp is None else hicp)
    missing = [year for year in (start_year, end_year) if year not in yearly.index]
    if missing:
        raise DataLoadError(f"No HICP data for {missing}")
    return yearly.loc[end_year] / yearly.loc[start_year] - 1
