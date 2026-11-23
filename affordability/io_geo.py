"""
Load the ISTAT geography: the official list of comuni and their boundaries.

Moved from notebook 03. The list is the "master list" that MEF and OMI codes are
checked against; the boundaries are used for maps and distances.
"""

import zipfile

import geopandas as gpd
import pandas as pd

from .config import ISTAT_BOUNDARIES_URL, ISTAT_COMUNI_URL, ISTAT_DIR
from .errors import DataLoadError
from .io_common import download, short_path

COMUNI_FILE = "Elenco-comuni-italiani.xlsx"
BOUNDARIES_ZIP = "Limiti01012025_g.zip"

# Our short name -> (piece of the ISTAT column name, piece that must NOT be in it)
ISTAT_COLUMNS = {
    "istat_code": ("comune formato alfanumerico", None),
    "name": ("denominazione in italiano", None),
    "province": ("sigla automobilistica", None),
    "region": ("denominazione regione", None),
    "macro_area": ("ripartizione geografica", "codice"),
    "is_capital": ("capoluogo", None),
}


def find_istat_column(df, text, exclude=None):
    """
    Find the one column whose name contains a piece of text.

    Line breaks, double spaces and upper/lower case in the names are ignored.

    Parameters
    ----------
    df : pandas.DataFrame
        The ISTAT table.
    text : str
        A piece of the column name, e.g. ``"alfanumerico"``.
    exclude : str, optional
        Skip columns that also contain this text.

    Returns
    -------
    str
        The full, original column name.

    Raises
    ------
    DataLoadError
        If no column, or more than one column, matches (the file format changed).
    """
    matches = []
    for col in df.columns:
        clean = " ".join(str(col).split()).lower()
        if text.lower() in clean and not (exclude and exclude.lower() in clean):
            matches.append(col)
    if len(matches) != 1:
        raise DataLoadError(
            f"Expected 1 column containing '{text}' in the ISTAT list, found {matches}"
        )
    return matches[0]


def load_comuni_list(folder=ISTAT_DIR):
    """
    Download (once) and load the ISTAT list of comuni.

    Parameters
    ----------
    folder : pathlib.Path, optional
        Where the Excel file is saved.

    Returns
    -------
    pandas.DataFrame
        One row per comune with columns ``istat_code`` (6-character text), ``name``,
        ``province``, ``region``, ``macro_area`` and ``is_capital`` (bool).

    Raises
    ------
    DataLoadError
        If the download fails or the file does not have the expected columns.
    """
    path = download(ISTAT_COMUNI_URL, folder / COMUNI_FILE)
    raw = pd.read_excel(
        path,
        dtype=str,                  # text: "001001" keeps its zeros
        keep_default_na=False,      # "NA" is Napoli's province, not a missing value
        na_values=[""],
    )

    columns = {short: find_istat_column(raw, text, exclude)
               for short, (text, exclude) in ISTAT_COLUMNS.items()}
    comuni = raw[list(columns.values())].copy()
    comuni.columns = list(columns.keys())
    comuni["istat_code"] = comuni["istat_code"].str.strip().str.zfill(6)
    comuni["is_capital"] = comuni["is_capital"].str.strip() == "1"

    if not comuni["istat_code"].is_unique:
        raise DataLoadError(f"Duplicate codes in {short_path(path)}")
    return comuni


def load_boundaries(folder=ISTAT_DIR):
    """
    Download (once) and load the boundaries of the comuni.

    Parameters
    ----------
    folder : pathlib.Path, optional
        Where the ZIP is saved and extracted.

    Returns
    -------
    geopandas.GeoDataFrame
        Columns ``istat_code`` (6-character text) and ``geometry``, in EPSG:32632
        (UTM zone 32N, coordinates in metres).

    Raises
    ------
    DataLoadError
        If the download fails or the shapefile of the comuni is not in the ZIP.
    """
    zip_path = download(ISTAT_BOUNDARIES_URL, folder / BOUNDARIES_ZIP)
    target = folder / zip_path.stem
    if not target.exists():
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(target)

    shapefiles = sorted(target.rglob("Com*_WGS84.shp"))
    if not shapefiles:
        raise DataLoadError(f"No comuni shapefile (Com*_WGS84.shp) in {short_path(target)}")

    geo = gpd.read_file(shapefiles[0])
    if "PRO_COM_T" not in geo.columns:
        raise DataLoadError(f"{short_path(shapefiles[0])} has no PRO_COM_T column")
    geo = geo.rename(columns={"PRO_COM_T": "istat_code"})[["istat_code", "geometry"]]
    geo["istat_code"] = geo["istat_code"].str.zfill(6)
    return geo
