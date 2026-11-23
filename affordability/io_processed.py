"""
Read the final tables made by ``scripts/build_dataset.py``.

The analysis notebook and the Streamlit app start here, not from the raw data.
"""

import pandas as pd

from .config import CHANGES_FILE, PANEL_FILE
from .io_common import require_file

BUILD_HINT = "Run 'python scripts/build_dataset.py' from the project folder first."


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
    return pd.read_csv(require_file(path, BUILD_HINT), dtype={"istat_code": str})


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
    return pd.read_csv(require_file(path, BUILD_HINT), dtype={"istat_code": str})
