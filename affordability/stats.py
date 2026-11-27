"""
Statistical tests used in the analysis (scipy), each returning a small dict.

Moved from notebook 02. A dict instead of printing means the same function feeds a
notebook printout, a README number and a Streamlit label.
"""

import numpy as np
import pandas as pd
from scipy import stats


def elasticity(wage, price):
    """
    Elasticity of price to wage: slope of log(price) on log(wage).

    1 means prices rise in proportion to wages; above 1, richer places are also
    relatively more expensive.

    Parameters
    ----------
    wage, price : array-like
        Positive values, one per comune.

    Returns
    -------
    dict
        ``slope``, ``ci_low``, ``ci_high`` (95% confidence interval), ``r2``, ``n``.
    """
    wage, price = np.asarray(wage, dtype=float), np.asarray(price, dtype=float)
    keep = (wage > 0) & (price > 0)
    fit = stats.linregress(np.log(wage[keep]), np.log(price[keep]))
    margin = 1.96 * fit.stderr                    # normal approximation, fine for n > 100
    return {"slope": fit.slope, "ci_low": fit.slope - margin, "ci_high": fit.slope + margin,
            "r2": fit.rvalue ** 2, "n": int(keep.sum())}


def spearman(x, y):
    """
    Spearman rank correlation (robust to extreme values, no straight line assumed).

    Parameters
    ----------
    x, y : array-like
        Paired values, e.g. price change and rent change per comune.

    Returns
    -------
    dict
        ``rho``, ``p_value``, ``n``.
    """
    data = pd.DataFrame({"x": x, "y": y}).dropna()
    result = stats.spearmanr(data["x"], data["y"])
    return {"rho": result.statistic, "p_value": result.pvalue, "n": len(data)}


def paired_change_test(before, after):
    """
    Did a value change for the same comuni? Wilcoxon signed-rank test.

    Used for "years of wage in 2014 vs 2024, same comuni". It does not assume a
    normal distribution, which years of wage do not follow (long right tail).

    Parameters
    ----------
    before, after : array-like
        Paired values (same comuni, same order).

    Returns
    -------
    dict
        ``median_before``, ``median_after``, ``median_difference``, ``p_value``, ``n``.
    """
    data = pd.DataFrame({"before": before, "after": after}).dropna()
    result = stats.wilcoxon(data["after"], data["before"])
    return {"median_before": data["before"].median(), "median_after": data["after"].median(),
            "median_difference": (data["after"] - data["before"]).median(),
            "p_value": result.pvalue, "n": len(data)}


def group_difference(df, value, group):
    """
    Do groups (e.g. macro-areas) differ? Kruskal-Wallis test on the medians.

    Parameters
    ----------
    df : pandas.DataFrame
        The data.
    value : str
        Column to compare, e.g. ``"years_wage"``.
    group : str
        Column with the groups, e.g. ``"macro_area"``.

    Returns
    -------
    dict
        ``h``, ``p_value`` and ``medians`` (a Series, one value per group).
    """
    data = df.dropna(subset=[value, group])
    samples = [g[value].to_numpy() for _, g in data.groupby(group)]
    result = stats.kruskal(*samples)
    return {"h": result.statistic, "p_value": result.pvalue,
            "medians": data.groupby(group)[value].median().sort_values()}


def quintile_medians(df, by, columns, q=5):
    """
    Split the rows into ``q`` equal groups by one column; median of others per group.

    Used for "rent change in each fifth of comuni, from the biggest price fall to
    the biggest rise".

    Parameters
    ----------
    df : pandas.DataFrame
        The data.
    by : str
        Column that defines the groups.
    columns : list of str
        Columns to summarise.
    q : int, optional
        Number of groups.

    Returns
    -------
    pandas.DataFrame
        One row per group (index = the interval of ``by``) with ``count`` and medians.
    """
    groups = pd.qcut(df[by], q=q, duplicates="drop")
    table = df.groupby(groups, observed=True)[columns].median()
    table.insert(0, "count", df.groupby(groups, observed=True).size())
    return table
