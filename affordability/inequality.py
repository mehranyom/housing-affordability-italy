"""
Who the taxpayers are, and how unequal their incomes are (MEF brackets and types).

Moved from notebook 01. The MEF gives, for each comune, how many taxpayers fall in
each bracket of total income and how many euros they declare. From these:

- ``gini_from_brackets``: the Gini coefficient (0 = everybody earns the same,
  1 = one person earns everything), from the Lorenz curve of the brackets;
- ``income_mix``: the share of taxpayers with each type of income (employees,
  pensioners, self-employed...).

Brackets hide the inequality inside each bracket, so this Gini is a lower bound.
"""

import numpy as np
import pandas as pd

from .io_mef import TAXPAYERS_COL, find_mef_column

# Short labels -> a piece of text that appears in exactly one MEF column name
INCOME_TYPES = {
    "Employees": "lavoro dipendente",
    "Pensioners": "pensione",
    "Owners of buildings": "fabbricati",
    "Self-employed": "lavoro autonomo",
    "Business (ordinary)": "contabilita' ordinaria",
    "Business (simplified)": "contabilita' semplificata",
    "Partnerships": "partecipazione",
}

# Brackets of total income, in increasing order. The negative bracket is left out:
# a Lorenz curve needs incomes >= 0.
INCOME_BRACKETS = {
    "0-10k": "da 0 a 10000",
    "10-15k": "da 10000 a 15000",
    "15-26k": "da 15000 a 26000",
    "26-55k": "da 26000 a 55000",
    "55-75k": "da 55000 a 75000",
    "75-120k": "da 75000 a 120000",
    "> 120k": "oltre 120000",
}


def category_table(df, categories):
    """
    Number of taxpayers and euros for each category, summed over the rows of ``df``.

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF income table (all comuni, or just one row).
    categories : dict
        Mapping ``label -> keyword``, e.g. ``INCOME_TYPES``.

    Returns
    -------
    pandas.DataFrame
        Index = labels; columns ``taxpayers`` and ``amount``. Hidden values (NaN)
        count as 0.
    """
    rows = {}
    for label, keyword in categories.items():
        rows[label] = {
            "taxpayers": df[find_mef_column(df, keyword, "Frequenza")].fillna(0).sum(),
            "amount": df[find_mef_column(df, keyword, "Ammontare")].fillna(0).sum(),
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def income_mix(df):
    """
    Share of taxpayers with each type of income, and share of income from it.

    One person can have more than one type (a pension AND a rented flat), so the
    shares of taxpayers do not add up to 100%.

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF table (all comuni, or a subset).

    Returns
    -------
    pandas.DataFrame
        Index = income types; columns ``pct_taxpayers`` and ``pct_income``.
    """
    table = category_table(df, INCOME_TYPES)
    return pd.DataFrame({
        "pct_taxpayers": table["taxpayers"] / df[TAXPAYERS_COL].sum() * 100,
        "pct_income": table["amount"] / table["amount"].sum() * 100,
    })


def bracket_matrix(df, kind):
    """
    The bracket values of every row in one 2-D numpy array.

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF table.
    kind : str
        ``"Frequenza"`` (taxpayers) or ``"Ammontare"`` (euros).

    Returns
    -------
    numpy.ndarray
        Shape (rows, brackets), brackets in increasing order, NaN counted as 0.
    """
    columns = [find_mef_column(df, keyword, kind) for keyword in INCOME_BRACKETS.values()]
    return df[columns].fillna(0).to_numpy(dtype=float)


def lorenz_points(freq, amount):
    """
    Cumulative shares of taxpayers (x) and of income (y), starting from 0.

    Parameters
    ----------
    freq, amount : numpy.ndarray
        Arrays of shape (rows, brackets), as from ``bracket_matrix``.

    Returns
    -------
    tuple of numpy.ndarray
        ``(x, y)``, each of shape (rows, brackets + 1).
    """
    freq = np.atleast_2d(np.asarray(freq, dtype=float))
    amount = np.atleast_2d(np.asarray(amount, dtype=float))
    # keepdims=True keeps the shape (rows, 1), so each row is divided by its own total
    with np.errstate(divide="ignore", invalid="ignore"):
        pop_share = freq / freq.sum(axis=1, keepdims=True)
        income_share = amount / amount.sum(axis=1, keepdims=True)
    zeros = np.zeros((freq.shape[0], 1))
    x = np.hstack([zeros, np.cumsum(pop_share, axis=1)])
    y = np.hstack([zeros, np.cumsum(income_share, axis=1)])
    return x, y


def gini_from_lorenz(x, y):
    """
    Gini coefficient from Lorenz points: 1 minus twice the area under the curve.

    Parameters
    ----------
    x, y : numpy.ndarray
        Output of ``lorenz_points``.

    Returns
    -------
    numpy.ndarray
        One value per row (the trapezoid rule: sum of (x_k - x_k-1)(y_k + y_k-1)).
    """
    return 1 - np.sum(np.diff(x, axis=1) * (y[:, 1:] + y[:, :-1]), axis=1)


def gini_from_brackets(df):
    """
    Gini coefficient of income for every row (comune) of a MEF table.

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF table.

    Returns
    -------
    pandas.Series
        One value between 0 and 1 per row of ``df``.
    """
    x, y = lorenz_points(bracket_matrix(df, "Frequenza"), bracket_matrix(df, "Ammontare"))
    return pd.Series(gini_from_lorenz(x, y), index=df.index)


def share_below(df, limit_label="26-55k"):
    """
    Share of taxpayers in the brackets below a given one (e.g. below 26,000 €).

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF table.
    limit_label : str, optional
        The first bracket NOT counted.

    Returns
    -------
    pandas.Series
        A share between 0 and 1 per row.
    """
    freq = bracket_matrix(df, "Frequenza")
    below = list(INCOME_BRACKETS).index(limit_label)
    return pd.Series(freq[:, :below].sum(axis=1) / freq.sum(axis=1), index=df.index)


def bracket_columns(df):
    """
    The bracket counts and euros as short columns, to save with the panel.

    The app draws a Lorenz curve for any comune from these columns.

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF table.

    Returns
    -------
    pandas.DataFrame
        Columns ``freq_<label>`` and ``amount_<label>`` for every bracket.
    """
    freq = bracket_matrix(df, "Frequenza")
    amount = bracket_matrix(df, "Ammontare")
    columns = {}
    for i, label in enumerate(INCOME_BRACKETS):
        columns[f"freq_{label}"] = freq[:, i]
        columns[f"amount_{label}"] = amount[:, i]
    return pd.DataFrame(columns, index=df.index)


def lorenz_from_panel(rows):
    """
    Lorenz points of the sum of some panel rows (one comune, or all of Italy).

    Parameters
    ----------
    rows : pandas.DataFrame
        Panel rows with the ``freq_*`` and ``amount_*`` columns.

    Returns
    -------
    tuple
        ``(x, y, gini)`` with x and y as 1-D arrays.
    """
    freq = rows[[f"freq_{label}" for label in INCOME_BRACKETS]].sum().to_numpy()
    amount = rows[[f"amount_{label}" for label in INCOME_BRACKETS]].sum().to_numpy()
    x, y = lorenz_points(freq, amount)
    return x[0], y[0], float(gini_from_lorenz(x, y)[0])


def type_columns(df):
    """
    The taxpayers and euros of every type of income as short columns, to save with the panel.

    The app draws "who earns what" for any comune from these columns.

    Parameters
    ----------
    df : pandas.DataFrame
        A MEF table.

    Returns
    -------
    pandas.DataFrame
        Columns ``freq_type_<label>`` and ``amount_type_<label>`` for every income type.
    """
    columns = {}
    for label, keyword in INCOME_TYPES.items():
        columns[f"freq_type_{label}"] = df[find_mef_column(df, keyword, "Frequenza")].fillna(0)
        columns[f"amount_type_{label}"] = df[find_mef_column(df, keyword, "Ammontare")].fillna(0)
    return pd.DataFrame(columns, index=df.index)


def types_from_panel(rows):
    """
    Who earns what, for the sum of some panel rows (one comune, or all of Italy).

    Moved from notebook 01 (``plot_income_types``).

    Parameters
    ----------
    rows : pandas.DataFrame
        Panel rows with ``taxpayers`` and the ``freq_type_*`` / ``amount_type_*`` columns.

    Returns
    -------
    pandas.DataFrame
        Index = income types; ``pct_taxpayers`` (share of taxpayers with that income) and
        ``avg_income`` (euros per person who has it; NaN if nobody has it).
    """
    freq = pd.Series({label: rows[f"freq_type_{label}"].sum() for label in INCOME_TYPES})
    amount = pd.Series({label: rows[f"amount_type_{label}"].sum() for label in INCOME_TYPES})
    return pd.DataFrame({
        "pct_taxpayers": freq / rows["taxpayers"].sum() * 100,
        "avg_income": amount / freq.replace(0, np.nan),
    })


def brackets_from_panel(rows):
    """
    Share of taxpayers in each income bracket, for the sum of some panel rows.

    Moved from notebook 01 (``plot_income_brackets``).

    Parameters
    ----------
    rows : pandas.DataFrame
        Panel rows with the ``freq_*`` bracket columns.

    Returns
    -------
    pandas.Series
        Index = bracket labels (increasing), values in % (they add up to 100).
    """
    freq = pd.Series({label: rows[f"freq_{label}"].sum() for label in INCOME_BRACKETS})
    return freq / freq.sum() * 100
