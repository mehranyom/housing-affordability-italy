"""
Load the OMI house prices and rents (Agenzia delle Entrate).

Moved from notebook 02. The files cannot be downloaded by code (SPID login): the user
puts one ZIP per semester in ``data/raw/omi/`` (see README). Quirks handled here:

- a title line above the header, separator ``;`` and an empty extra column;
- everything is read as text: the codes keep their zeros and ``NA`` stays Napoli;
- the semester (e.g. ``20242``) is read from the file name.

Numbers (decimal comma), codes and filters are cleaned later, in ``cleaning.py``.
"""

import re
import zipfile

import pandas as pd

from .config import OMI_DIR
from .errors import DataLoadError
from .io_common import short_path

# Columns the rest of the project relies on
CODE_COL = "Comune_ISTAT"
NAME_COL = "Comune_descrizione"
PROVINCE_COL = "Prov"
REGION_COL = "Regione"
FASCIA_COL = "Fascia"
ZONE_COL = "Zona"
TYPE_COL = "Descr_Tipologia"
STATE_COL = "Stato"
PRICE_COLS = ["Compr_min", "Compr_max", "Loc_min", "Loc_max"]
VALORI_COLUMNS = [CODE_COL, NAME_COL, PROVINCE_COL, REGION_COL, FASCIA_COL,
                  ZONE_COL, TYPE_COL, STATE_COL] + PRICE_COLS

SPID_HINT = (
    "OMI files must be downloaded by hand with SPID: see 'How to download the OMI "
    "data' in the README, and put the ZIPs in data/raw/omi/."
)


def extract_omi_zips(folder=OMI_DIR):
    """
    Extract every OMI ZIP into its own folder (once).

    Parameters
    ----------
    folder : pathlib.Path, optional
        Folder with the ZIPs, e.g. ``omi_2024_2.zip``.

    Returns
    -------
    list of pathlib.Path
        The extracted folders.
    """
    extracted = []
    for zip_path in sorted(folder.glob("*.zip")):
        target = folder / zip_path.stem              # same name as the ZIP, without .zip
        if not target.exists():
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(target)
        extracted.append(target)
    return extracted


def find_semester(filename):
    """
    Read the semester from an OMI file name.

    Parameters
    ----------
    filename : str
        For example ``"QI_1234_1_20242_VALORI.csv"``.

    Returns
    -------
    str or None
        ``"2024_2"`` for the example above, or None if no semester is found.
    """
    # (20\d\d) = a year 2000-2099, ([12]) = semester 1 or 2, then no other digit
    match = re.search(r"(20\d\d)([12])(?:\D|$)", filename)
    return f"{match.group(1)}_{match.group(2)}" if match else None


def find_omi_files(folder=OMI_DIR):
    """
    Find the VALORI and ZONE CSV of every semester.

    Parameters
    ----------
    folder : pathlib.Path, optional
        The OMI folder (ZIPs are extracted first).

    Returns
    -------
    dict
        ``{"2024_2": {"VALORI": path, "ZONE": path}, ...}``

    Raises
    ------
    DataLoadError
        If no OMI file is found.
    """
    extract_omi_zips(folder)
    files = {}
    for path in sorted(folder.rglob("*.csv")):
        name = path.name.upper()
        kind = "VALORI" if "VALORI" in name else "ZONE" if "ZONE" in name else None
        semester = find_semester(path.name)
        if kind and semester:
            files.setdefault(semester, {})[kind] = path
    if not files:
        raise DataLoadError(f"No OMI files in {short_path(folder)}. {SPID_HINT}")
    return files


def find_header_row(path, marker="Zona", max_lines=10):
    """
    Find the line where the column names are (OMI puts a title line above them).

    Parameters
    ----------
    path : pathlib.Path
        The CSV file.
    marker : str, optional
        A column name that appears in the header line.
    max_lines : int, optional
        How many lines to look at.

    Returns
    -------
    int
        The 0-based number of the header line (use it as ``skiprows``).

    Raises
    ------
    DataLoadError
        If the marker is not found in the first ``max_lines`` lines.
    """
    with open(path, encoding="latin-1") as f:
        for number, line in enumerate(f):
            if number >= max_lines:
                break
            if marker in line.split(";"):
                return number
    raise DataLoadError(
        f"No header with '{marker}' in the first {max_lines} lines of {short_path(path)}: "
        "is it an OMI file?"
    )


def read_omi_csv(path):
    """
    Read one OMI CSV (VALORI or ZONE) with every column as text.

    Parameters
    ----------
    path : pathlib.Path
        The CSV file.

    Returns
    -------
    pandas.DataFrame
        All columns as text, stripped column names, no empty columns.
    """
    df = pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        skiprows=find_header_row(path),
        dtype=str,                 # read everything as text: codes keep their zeros
        keep_default_na=False,     # "NA" (Napoli) stays text
        na_values=[""],
    )
    df.columns = [col.strip() for col in df.columns]
    return df.dropna(axis=1, how="all")   # the empty column made by the final ";"


def load_omi(semester, kind="VALORI", folder=OMI_DIR):
    """
    Load the raw OMI table of one semester.

    Parameters
    ----------
    semester : str
        For example ``"2024_2"``.
    kind : {"VALORI", "ZONE"}, optional
        Prices (VALORI) or zone descriptions (ZONE).
    folder : pathlib.Path, optional
        The OMI folder.

    Returns
    -------
    pandas.DataFrame
        The raw table (all text) with an extra ``semester`` column.

    Raises
    ------
    DataLoadError
        If the semester or the file kind is missing, or VALORI lacks a needed column.
    """
    files = find_omi_files(folder)
    if semester not in files or kind not in files[semester]:
        found = {sem: sorted(kinds) for sem, kinds in files.items()}
        raise DataLoadError(f"No OMI {kind} file for {semester}; found {found}. {SPID_HINT}")

    path = files[semester][kind]
    df = read_omi_csv(path)
    if kind == "VALORI":
        missing = set(VALORI_COLUMNS) - set(df.columns)
        if missing:
            raise DataLoadError(f"{short_path(path)} has no column(s) {sorted(missing)}")
    df["semester"] = semester
    return df
