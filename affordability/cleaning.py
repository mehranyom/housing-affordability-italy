"""
Turn the raw tables of the ``io_*`` modules into clean tables, one row per comune.

Moved from notebooks 01, 02 and 03. The steps, in the order the pipeline runs them:

1. ``fix_omi_codes``     OMI comune codes -> 6-digit ISTAT codes (checked on the ISTAT list)
2. ``clean_omi_values``  one row per OMI zone: ordinary homes, normal condition, numbers
3. ``comune_prices``     one row per comune and year: median price and rent of the zones
4. ``zone_changes`` and ``comune_changes``   2014 -> 2024 change, comparing the SAME zones
5. ``income_table``      one row per comune and year: taxpayers, mean income, mean wage
6. ``build_panel``       prices + incomes + ISTAT attributes, one row per comune and year
"""

import re
import unicodedata

import numpy as np
import pandas as pd

from . import inequality
from .config import OMI_CONDITION, OMI_PROPERTY_TYPE
from .io_mef import CODE_COL as MEF_CODE_COL
from .io_mef import NAME_COL as MEF_NAME_COL
from .io_mef import PROVINCE_COL as MEF_PROVINCE_COL
from .io_mef import TAXPAYERS_COL, find_mef_column
from .io_omi import (CODE_COL, FASCIA_COL, NAME_COL, PRICE_COLS, PROVINCE_COL,
                     REGION_COL, STATE_COL, TYPE_COL, ZONE_COL)

# MEF columns used for the incomes (names after ``io_mef.clean_mef_columns``)
INCOME_TOTAL = "Reddito imponibile - Ammontare"
INCOME_COUNT = "Reddito imponibile - Frequenza"
WAGE_TOTAL = "Reddito da lavoro dipendente e assimilati - Ammontare"
WAGE_COUNT = "Reddito da lavoro dipendente e assimilati - Frequenza"
# Pieces of the MEF column names for the local economy (research question 3)
PENSION_KEY = "Reddito da pensione"
PROPERTY_KEY = "Reddito da fabbricati"
HIGH_INCOME_KEYS = ["da 75000 a 120000", "oltre 120000"]


# ---------------------------------------------------------------------------
# 1. OMI codes
# ---------------------------------------------------------------------------
def normalize_name(name):
    """
    Make a comune name comparable: upper case, no accents, only letters and digits.

    Parameters
    ----------
    name : str
        For example ``"Cortina d'Ampezzo"``.

    Returns
    -------
    str
        For example ``"CORTINADAMPEZZO"``.
    """
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def fix_omi_codes(omi, comuni, code_col=CODE_COL, prov_col=PROVINCE_COL, name_col=NAME_COL):
    """
    Turn the OMI comune codes into 6-digit ISTAT codes, checked against the ISTAT list.

    OMI writes "region number + ISTAT code", but the code is not always today's:

    - for some new comuni (born from mergers) the leading zeros or the region are lost;
    - comuni that moved to a newer province keep their OLD code and province in OMI,
      e.g. Agrate Brianza is "3015003", MI, while ISTAT says 108001, MB (Monza and
      Brianza became a province in 2009).

    So, for each comune, we try in order:

    1. every reading of the digits (no prefix, 1-digit or 2-digit region prefix) that
       exists in the ISTAT list **in the same province**;
    2. the name, in the same province;
    3. the name anywhere in Italy, if no other comune has that name.

    Parameters
    ----------
    omi : pandas.DataFrame
        OMI rows, with the code, province and name columns.
    comuni : pandas.DataFrame
        ISTAT list with columns ``istat_code``, ``name``, ``province``
        (as returned by ``io_geo.load_comuni_list``).

    Returns
    -------
    pandas.Series
        6-digit codes aligned with ``omi`` (NaN where nothing matched: mostly comuni
        that have since been merged into a new one).
    """
    # --- STEP 1: Build the 3 cheat sheets from the official ISTAT table ---

    # Cheat sheet 1: Set of all real (code, province) pairs for fast lookup
    valid = set(zip(comuni["istat_code"], comuni["province"]))

    # Add a temporary "key" column with cleaned names (uppercase, no accents/spaces)
    names = comuni.assign(key=comuni["name"].map(normalize_name))

    # Cheat sheet 2: Dict mapping (clean_name, province) -> istat_code
    by_name = dict(zip(zip(names["key"], names["province"]), names["istat_code"]))

    # Drop ALL towns whose name appears more than once in Italy (e.g., both "Livo"s)
    unique = names.drop_duplicates("key", keep=False)

    # Cheat sheet 3: Dict mapping clean_name -> istat_code (only for unique names)
    by_name_only = dict(zip(unique["key"], unique["istat_code"]))

    # --- STEP 2: Define the 3-step fallback game for ONE single town ---
    def resolve(raw, prov, name):
        # Keep only digits from the raw OMI code (or "" if it's missing/NaN)
        digits = re.sub(r"\D", "", raw) if isinstance(raw, str) else ""

        # Try dropping 0, 1, or 2 leading digits (region prefix) and pad to 6 digits
        candidates = {digits[k:].zfill(6) for k in range(3) if 0 < len(digits) - k <= 6}

        # Check which candidates actually exist in ISTAT for this province
        matches = [c for c in candidates if (c, prov) in valid]

        # TRY 1: If exactly one candidate matched, we're done
        if len(matches) == 1:
            return matches[0]

        # Clean the OMI town name for name-based matching
        key = normalize_name(name)

        # TRY 2: Look up (name, province). If not found, TRY 3: look up name alone.
        # If neither is found, returns None (which becomes NaN in pandas).
        return by_name.get((key, prov), by_name_only.get(key))

    # --- STEP 3: Run resolve() once per unique town, then copy back to all rows ---

    # Get a small table of unique (code, province, name) combinations
    keys = omi[[code_col, prov_col, name_col]].drop_duplicates()

    # Run resolve() on each unique combination and store the answer in "istat_code"
    keys["istat_code"] = [resolve(*row) for row in keys.itertuples(index=False)]

    # Merge the answers back onto every row of the original OMI table
    fixed = omi[[code_col, prov_col, name_col]].merge(
        keys, on=[code_col, prov_col, name_col], how="left", validate="many_to_one"
    )

    # Return just the istat_code column, restoring omi's original row index
    return fixed["istat_code"].set_axis(omi.index)


def parse_omi_code(codes):
    """
    The simple reading of an OMI code: the last 6 digits.

    Used for comuni that no longer exist in the ISTAT list (merged since): their old
    code still matches the MEF file of the same year.

    Parameters
    ----------
    codes : pandas.Series
        OMI codes, e.g. ``"1006006"``.

    Returns
    -------
    pandas.Series
        For example ``"006006"``; NaN if there are no digits or the code is all zeros.
    """
    parsed = codes.str.replace(r"\D", "", regex=True).str[-6:].str.zfill(6)
    return parsed.where(parsed.str.strip("0") != "")


# ---------------------------------------------------------------------------
# 2-4. OMI prices
# ---------------------------------------------------------------------------
def to_number(text):
    """
    Convert OMI text numbers (decimal comma) to floats; 0 or less becomes NaN.

    A price of 0 means "no quotation" (e.g. the earthquake zones of Norcia), not a
    free house.

    Parameters
    ----------
    text : pandas.Series
        Text such as ``"1500"`` or ``"8,5"``.

    Returns
    -------
    pandas.Series
        Floats, NaN where the value is missing, not a number, or not positive.
    """
    numbers = pd.to_numeric(text.str.replace(",", ".", regex=False), errors="coerce")
    return numbers.where(numbers > 0)


def clean_omi_values(valori, comuni):
    """
    Turn a raw OMI VALORI table into clean numbers for ordinary homes.

    Parameters
    ----------
    valori : pandas.DataFrame
        A VALORI table as returned by ``io_omi.load_omi`` (with a ``semester`` column).
    comuni : pandas.DataFrame
        The ISTAT list, used by ``fix_omi_codes``.

    Returns
    -------
    pandas.DataFrame
        One row per zone, only ``OMI_PROPERTY_TYPE`` in ``OMI_CONDITION``, with
        ``istat_code`` (6-character text), ``in_istat_2025`` (False for comuni merged
        since, which keep their old code), numeric price columns,
        the zone midpoints ``buy_mid`` (€/m²) and ``rent_mid`` (€/m² per month),
        ``semester`` and ``year``.
    """
    homes = valori[
        (valori[TYPE_COL].str.strip() == OMI_PROPERTY_TYPE)
        & (valori[STATE_COL].str.strip().str.upper() == OMI_CONDITION)
    ].copy()
    for col in PRICE_COLS:
        homes[col] = to_number(homes[col])

    checked = fix_omi_codes(homes, comuni)
    # in_istat_2025 = False: an old comune, merged since. Its old code is kept so it
    # can still meet the MEF incomes of the same year.
    homes["in_istat_2025"] = checked.notna()
    homes["istat_code"] = checked.fillna(parse_omi_code(homes[CODE_COL]))
    homes["buy_mid"] = (homes["Compr_min"] + homes["Compr_max"]) / 2
    homes["rent_mid"] = (homes["Loc_min"] + homes["Loc_max"]) / 2
    homes["year"] = homes["semester"].str[:4].astype(int)
    return homes.reset_index(drop=True)


def comune_prices(homes):
    """
    One row per comune and year, with the median zone price and rent.

    The median of the zones is not weighted: OMI does not say how many homes are
    in each zone (see the README, "Comune price").

    Parameters
    ----------
    homes : pandas.DataFrame
        Output of ``clean_omi_values`` (one row per zone).

    Returns
    -------
    pandas.DataFrame
        Columns ``istat_code``, ``year``, ``semester``, ``comune``, ``omi_region``,
        ``n_zones``, ``buy_m2`` (median €/m²), ``rent_m2`` (median €/m² per month).
    """
    return (
        homes.dropna(subset=["istat_code"])
        .groupby(["istat_code", "year"], as_index=False)
        .agg(
            semester=("semester", "first"),
            comune=(NAME_COL, "first"),
            omi_region=(REGION_COL, "first"),
            n_zones=(ZONE_COL, "nunique"),
            buy_m2=("buy_mid", "median"),
            rent_m2=("rent_mid", "median"),
        )
    )


def zone_changes(homes, start_year, end_year):
    """
    Change of price and rent of each zone that exists in both years.

    Zone maps are redrawn between years (about 10% of comuni), so comparing the
    median of ALL zones mixes a price change with a map change. Here a zone is
    compared only with itself: same comune, same zone code.

    Parameters
    ----------
    homes : pandas.DataFrame
        Output of ``clean_omi_values`` for both years.
    start_year, end_year : int
        For example 2014 and 2024.

    Returns
    -------
    pandas.DataFrame
        One row per (``istat_code``, zone) with ``buy_start``, ``buy_end``,
        ``rent_start``, ``rent_end``, ``buy_change_pct`` and ``rent_change_pct``.
    """
# Columns that uniquely identify a single OMI zone: (comune, zone code)
    keys = ["istat_code", ZONE_COL]

    # Drop any rows that are missing an ISTAT code
    zones = homes.dropna(subset=["istat_code"])

    # Collapse repeated zone codes (e.g., from multiple cadastral sections in the same comune)
    # into one row per (year, comune, zone) using the median buy/rent price.
    # **{FASCIA_COL: ...} unpacks into Fascia=("Fascia", "first") so the column name is "Fascia".
    per_zone = zones.groupby(["year"] + keys).agg(
        buy_mid=("buy_mid", "median"),
        rent_mid=("rent_mid", "median"),
        **{FASCIA_COL: (FASCIA_COL, "first")},
    ).reset_index()

    # Slice the start year (e.g., 2014), index by (istat_code, Zona), and keep prices + Fascia
    start = per_zone[per_zone["year"] == start_year].set_index(keys)[["buy_mid", "rent_mid", FASCIA_COL]]

    # Slice the end year (e.g., 2024), index by (istat_code, Zona), and keep only prices
    end = per_zone[per_zone["year"] == end_year].set_index(keys)[["buy_mid", "rent_mid"]]

    # Match each zone in start_year with the exact same zone in end_year.
    # how="inner" drops zones that don't exist in both years; validate="one_to_one" ensures no duplicates.
    both = start.join(end, how="inner", lsuffix="_start", rsuffix="_end", validate="one_to_one")

    # Shorten the suffixed column names (e.g., buy_mid_start -> buy_start)
    both = both.rename(columns={
        "buy_mid_start": "buy_start", "buy_mid_end": "buy_end",
        "rent_mid_start": "rent_start", "rent_mid_end": "rent_end",
    })

    # Compute the percentage change from start_year to end_year for buy price and rent
    both["buy_change_pct"] = (both["buy_end"] / both["buy_start"] - 1) * 100
    both["rent_change_pct"] = (both["rent_end"] / both["rent_start"] - 1) * 100

    # Turn (istat_code, Zona) back from index labels into regular columns and return
    return both.reset_index()


def comune_changes(zones):
    """
    One row per comune: median change of its matched zones.

    Parameters
    ----------
    zones : pandas.DataFrame
        Output of ``zone_changes``.

    Returns
    -------
    pandas.DataFrame
        Columns ``istat_code``, ``n_zones_matched``, ``buy_change_pct``,
        ``rent_change_pct`` and ``not_updated`` (True if OMI left both price and
        rent exactly unchanged in every matched zone: a stale quotation, not a market).
    """
    zones = zones.assign(
        not_updated=(zones["buy_change_pct"] == 0) & (zones["rent_change_pct"] == 0)
    )
    return zones.groupby("istat_code", as_index=False).agg(
        n_zones_matched=(ZONE_COL, "nunique"),
        buy_change_pct=("buy_change_pct", "median"),
        rent_change_pct=("rent_change_pct", "median"),
        not_updated=("not_updated", "all"),
    )


def zones_table(homes):
    """
    The zones to keep for the app: one row per zone, comune and year.

    Parameters
    ----------
    homes : pandas.DataFrame
        Output of ``clean_omi_values`` for every year.

    Returns
    -------
    pandas.DataFrame
        Columns ``istat_code``, ``year``, ``fascia``, ``zone``, ``buy_mid``,
        ``rent_mid`` (repeated zone codes of a comune averaged with the median).
    """
    return (homes.dropna(subset=["istat_code"])
            .groupby(["istat_code", "year", FASCIA_COL, ZONE_COL], as_index=False)
            .agg(buy_mid=("buy_mid", "median"), rent_mid=("rent_mid", "median"))
            .rename(columns={FASCIA_COL: "fascia", ZONE_COL: "zone"}))


def centre_premium(zones, year):
    """
    Ratio between the centre (fascia B) and periphery (fascia D) price per comune.

    Moved from notebook 02.

    Parameters
    ----------
    zones : pandas.DataFrame
        Output of ``zones_table``.
    year : int
        The year to use.

    Returns
    -------
    pandas.DataFrame
        One row per comune that has both B and D zones: ``istat_code``, ``centre``,
        ``periphery`` (median €/m²) and ``premium`` (centre / periphery).
    """
    data = zones[(zones["year"] == year) & zones["fascia"].isin(["B", "D"])]
    # pivot_table: one row per comune, one column per fascia, median price inside
    table = data.pivot_table(index="istat_code", columns="fascia", values="buy_mid",
                             aggfunc="median")
    table = table.reindex(columns=["B", "D"]).dropna()
    table = table.rename(columns={"B": "centre", "D": "periphery"})
    table["premium"] = table["centre"] / table["periphery"]
    return table.reset_index()


def property_type_coverage(valori):
    """
    Count the comuni that have OMI quotes for ordinary homes, low-cost homes, or both.

    Some comuni have only "Abitazioni di tipo economico" and no "Abitazioni civili":
    they drop out of the analysis, and this count says how many.

    Parameters
    ----------
    valori : pandas.DataFrame
        A raw VALORI table (one semester).

    Returns
    -------
    pandas.Series
        Number of comuni per case: ``"civili and economico"``, ``"only civili"``,
        ``"only economico"``, ``"neither"``.
    """
    types = valori.groupby(CODE_COL)[TYPE_COL].agg(set)
    civili = types.apply(lambda s: "Abitazioni civili" in s)
    economico = types.apply(lambda s: "Abitazioni di tipo economico" in s)
    case = np.select(
        [civili & economico, civili, economico],
        ["civili and economico", "only civili", "only economico"],
        default="neither",
    )
    return pd.Series(case).value_counts()


# ---------------------------------------------------------------------------
# 5. MEF incomes
# ---------------------------------------------------------------------------
def income_table(mef):
    """
    One row per comune: taxpayers, mean income, mean wage and the local economy.

    Parameters
    ----------
    mef : pandas.DataFrame
        One tax year, as returned by ``io_mef.load_mef``.

    Returns
    -------
    pandas.DataFrame
        Columns ``istat_code``, ``year``, ``mef_name``, ``province``, ``taxpayers``,
        ``mean_income`` and ``mean_wage`` (euro per year, per person who has that
        income; a count of 0 gives NaN, not infinity), and three shares of the
        taxpayers: ``share_pensioners``, ``share_property_income`` (people with
        income from buildings: landlords and owners of second homes) and
        ``share_high_income`` (total income above 75,000 €); ``gini`` and
        ``share_below_26k`` from the income brackets; and the bracket columns
        ``freq_<bracket>`` / ``amount_<bracket>`` (for Lorenz curves in the app) and
        ``freq_type_<type>`` / ``amount_type_<type>`` (for "who earns what").
    """
    income_count = mef[INCOME_COUNT].replace(0, np.nan)
    wage_count = mef[WAGE_COUNT].replace(0, np.nan)
    taxpayers = mef[TAXPAYERS_COL].replace(0, np.nan)

    def share(keyword):
        """Taxpayers counted in the column with this keyword, as a share of all."""
        return mef[find_mef_column(mef, keyword, "Frequenza")].fillna(0) / taxpayers

    table = pd.DataFrame({
        "istat_code": mef[MEF_CODE_COL],
        "year": mef["year"],
        "mef_name": mef[MEF_NAME_COL],
        "province": mef[MEF_PROVINCE_COL],
        "taxpayers": mef[TAXPAYERS_COL],
        "mean_income": mef[INCOME_TOTAL] / income_count,
        "mean_wage": mef[WAGE_TOTAL] / wage_count,
        "share_pensioners": share(PENSION_KEY),
        "share_property_income": share(PROPERTY_KEY),
        "share_high_income": sum(share(key) for key in HIGH_INCOME_KEYS),
        "gini": inequality.gini_from_brackets(mef),
        "share_below_26k": inequality.share_below(mef, "26-55k"),
    })
    return pd.concat([table, inequality.bracket_columns(mef), inequality.type_columns(mef)],
                     axis=1)


# ---------------------------------------------------------------------------
# 6. Merge
# ---------------------------------------------------------------------------
def build_panel(prices, incomes, comuni):
    """
    Put prices, incomes and ISTAT attributes in one table: one row per comune and year.

    Parameters
    ----------
    prices : pandas.DataFrame
        Output of ``comune_prices``.
    incomes : pandas.DataFrame
        Output of ``income_table`` for every year, concatenated.
    comuni : pandas.DataFrame
        The ISTAT list (``io_geo.load_comuni_list``).

    Returns
    -------
    pandas.DataFrame
        Only comuni with both a price and an income in that year (inner merge),
        plus ``region``, ``macro_area`` and ``is_capital`` from ISTAT. For comuni
        that no longer exist in 2025 (merged away), region and macro-area come from
        the OMI region; ``is_capital`` stays NaN.
    """
    # validate: the merge stops with an error if a code appears twice on one side
    panel = prices.merge(incomes, on=["istat_code", "year"], how="inner", validate="one_to_one")
    attributes = comuni[["istat_code", "region", "macro_area", "is_capital"]]
    panel = panel.merge(attributes, on="istat_code", how="left", validate="many_to_one")
    # Old comuni (merged since) are not in the 2025 list: take the region from OMI and
    # the macro-area from the region. The names differ: OMI "TRENTINO-ALTO ADIGE",
    # ISTAT "Trentino-Alto Adige/Südtirol", so compare the part before "/", normalised.
    region_names = {normalize_name(r.split("/")[0]): r for r in comuni["region"].dropna().unique()}
    omi_key = panel["omi_region"].astype(str).str.split("/").str[0].map(normalize_name)
    panel["region"] = panel["region"].fillna(omi_key.map(region_names))
    area_of_region = comuni.drop_duplicates("region").set_index("region")["macro_area"]
    panel["macro_area"] = panel["macro_area"].fillna(panel["region"].map(area_of_region))
    return panel.sort_values(["year", "istat_code"]).reset_index(drop=True)
