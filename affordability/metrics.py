"""
Affordability measures: years of pay, mortgage burden, rental yield, real changes.

Moved from notebooks 02 and 03. Every function works on single numbers and on whole
columns (pandas Series or numpy arrays), so the same code computes Milan alone or
all 7,900 comuni at once.
"""

import numpy as np
import pandas as pd

from .config import (DISTANCE_BANDS_KM, DISTANCE_LABELS, FLAT_SIZE_M2, LOAN_TO_VALUE,
                     MORTGAGE_LIMIT_PCT, MORTGAGE_YEARS)


def years_of_pay(price_m2, yearly_pay, size_m2=FLAT_SIZE_M2):
    """
    How many years of gross pay a flat costs (price-to-income ratio).

    It is a ratio of euros to euros per year, so inflation cancels out and two years
    can be compared without deflating.

    Parameters
    ----------
    price_m2 : float or array-like
        Price in €/m².
    yearly_pay : float or array-like
        Gross income or wage, € per year.
    size_m2 : float, optional
        Size of the flat.

    Returns
    -------
    float or array-like
        Years of pay.
    """
    return price_m2 * size_m2 / yearly_pay


def mortgage_payment(principal, annual_rate_pct, years=MORTGAGE_YEARS):
    """
    Monthly payment of a fixed-rate mortgage (annuity formula).

    Parameters
    ----------
    principal : float or numpy.ndarray
        Amount borrowed, in euro.
    annual_rate_pct : float or numpy.ndarray
        Yearly interest rate in percent, e.g. ``3.5``.
    years : int, optional
        Length of the mortgage.

    Returns
    -------
    float or numpy.ndarray
        Monthly payment in euro (``principal / months`` when the rate is 0).
    """
    r = np.asarray(annual_rate_pct, dtype=float) / 100 / 12     # monthly rate
    n = years * 12
    # np.where computes both branches, so silence the 0/0 warning of the zero-rate case
    with np.errstate(divide="ignore", invalid="ignore"):
        payment = principal * r / (1 - (1 + r) ** -n)
    result = np.where(r == 0, principal / n, payment)
    return float(result) if result.ndim == 0 else result


def mortgage_share(price_m2, annual_rate_pct, yearly_wage, size_m2=FLAT_SIZE_M2,
                   loan_to_value=LOAN_TO_VALUE, years=MORTGAGE_YEARS):
    """
    Monthly mortgage payment as a percentage of the monthly gross wage.

    Banks usually lend if the payment is at most about a third of net pay.

    Parameters
    ----------
    price_m2 : float or array-like
        Price in €/m².
    annual_rate_pct : float or array-like
        Mortgage rate, % per year.
    yearly_wage : float or array-like
        Gross wage, € per year.
    size_m2, loan_to_value, years : optional
        The typical flat and mortgage (see ``config.py``).

    Returns
    -------
    float or array-like
        Percent of the monthly wage, e.g. ``35.0``.
    """
    loan = np.asarray(price_m2, dtype=float) * size_m2 * loan_to_value
    payment = mortgage_payment(loan, annual_rate_pct, years)
    return payment / (np.asarray(yearly_wage, dtype=float) / 12) * 100


def rental_yield(rent_m2_month, price_m2):
    """
    Gross rental yield: one year of rent divided by the price (0.05 = 5%).

    Parameters
    ----------
    rent_m2_month : float or array-like
        Rent in €/m² per month.
    price_m2 : float or array-like
        Price in €/m².

    Returns
    -------
    float or array-like
        The yield as a fraction. Its inverse is the price-to-rent ratio
        (years of rent that buy the home).
    """
    return rent_m2_month * 12 / price_m2


def real_change(nominal_change, inflation):
    """
    Turn a nominal change into a real one (in today's purchasing power).

    ``(1 + nominal) / (1 + inflation) - 1``: e.g. -5% nominal with 22.4% inflation
    is about -22.4% real. Simply subtracting (-5 - 22.4) would be slightly wrong.

    Parameters
    ----------
    nominal_change : float or array-like
        As a fraction, e.g. ``-0.05``.
    inflation : float
        As a fraction, e.g. ``0.224``.

    Returns
    -------
    float or array-like
        The real change, as a fraction.
    """
    return (1 + nominal_change) / (1 + inflation) - 1


def weighted_median(values, weights):
    """
    Median where each value counts as many times as its weight.

    With taxpayers as weights it answers "how many years does the TYPICAL PERSON
    need?" instead of "the typical comune" (where a village counts like Milan).

    Parameters
    ----------
    values, weights : array-like
        For example years of income per comune, and taxpayers per comune.

    Returns
    -------
    float
        The value below which half of the total weight lies (NaN if no values).
    """
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    keep = ~np.isnan(values) & ~np.isnan(weights)
    values, weights = values[keep], weights[keep]
    if len(values) == 0:
        return np.nan
    order = np.argsort(values)
    cumulative = np.cumsum(weights[order])
    return float(values[order][np.searchsorted(cumulative, cumulative[-1] / 2)])


def add_affordability(panel, rates_by_year):
    """
    Add every affordability column to the panel (one row per comune and year).

    Parameters
    ----------
    panel : pandas.DataFrame
        Output of ``cleaning.build_panel``.
    rates_by_year : pandas.Series
        Average mortgage rate (%) per year, e.g. ``io_ecb.yearly_average(rates)``.

    Returns
    -------
    pandas.DataFrame
        A copy with ``flat_price``, ``years_income``, ``years_wage``, ``worker_gap``,
        ``rate_pct``,
        ``mortgage_share_pct``, ``rental_yield_pct`` and ``rent_share_pct``.
    """
    panel = panel.copy()
    panel["flat_price"] = panel["buy_m2"] * FLAT_SIZE_M2
    panel["years_income"] = years_of_pay(panel["buy_m2"], panel["mean_income"])
    panel["years_wage"] = years_of_pay(panel["buy_m2"], panel["mean_wage"])
    # Worker gap: how many times harder it is for an employee than the average suggests
    panel["worker_gap"] = panel["years_wage"] / panel["years_income"]
    panel["rate_pct"] = panel["year"].map(rates_by_year)
    panel["mortgage_share_pct"] = mortgage_share(panel["buy_m2"], panel["rate_pct"],
                                                 panel["mean_wage"])
    panel["rental_yield_pct"] = rental_yield(panel["rent_m2"], panel["buy_m2"]) * 100
    panel["rent_share_pct"] = rent_share(panel["rent_m2"], panel["mean_wage"])
    return panel


def summary_by_year(panel, min_taxpayers=0):
    """
    The headline numbers of each year.

    Parameters
    ----------
    panel : pandas.DataFrame
        Output of ``add_affordability``.
    min_taxpayers : int, optional
        Skip smaller comuni.

    Returns
    -------
    pandas.DataFrame
        One row per year: number of comuni, median years of wage per comune and per
        person, share of comuni above 10 years, median mortgage share.
    """
    data = panel[panel["taxpayers"] >= min_taxpayers]
    rows = {}
    for year, group in data.groupby("year"):
        rows[year] = {
            "comuni": len(group),
            "years_wage_median_comune": group["years_wage"].median(),
            "years_wage_median_person": weighted_median(group["years_wage"], group["taxpayers"]),
            "share_above_10_years": (group["years_wage"] > 10).mean(),
            "mortgage_share_median_pct": group["mortgage_share_pct"].median(),
        }
    return pd.DataFrame(rows).T


def rent_share(rent_m2_month, yearly_wage, size_m2=FLAT_SIZE_M2):
    """
    Monthly rent of the flat as a percentage of the monthly gross wage.

    Parameters
    ----------
    rent_m2_month : float or array-like
        Rent in €/m² per month.
    yearly_wage : float or array-like
        Gross wage, € per year.
    size_m2 : float, optional
        Size of the flat.

    Returns
    -------
    float or array-like
        Percent of the monthly wage.
    """
    return rent_m2_month * size_m2 / (yearly_wage / 12) * 100


def salary_needed(price_m2, annual_rate_pct, limit_pct=MORTGAGE_LIMIT_PCT,
                  size_m2=FLAT_SIZE_M2, loan_to_value=LOAN_TO_VALUE, years=MORTGAGE_YEARS):
    """
    The gross yearly salary at which the mortgage payment is exactly ``limit_pct``.

    The reverse of ``mortgage_share``: a salary is easier to read than a percentage.

    Parameters
    ----------
    price_m2 : float or array-like
        Price in €/m².
    annual_rate_pct : float or array-like
        Mortgage rate, % per year.
    limit_pct : float, optional
        Highest payment as a percentage of the monthly salary.
    size_m2, loan_to_value, years : optional
        The typical flat and mortgage.

    Returns
    -------
    float or array-like
        Gross salary, € per year.
    """
    loan = np.asarray(price_m2, dtype=float) * size_m2 * loan_to_value
    payment = mortgage_payment(loan, annual_rate_pct, years)
    return payment * 12 / (limit_pct / 100)


def down_payment(price_m2, size_m2=FLAT_SIZE_M2, loan_to_value=LOAN_TO_VALUE):
    """
    The part of the price the bank does not lend (notary and taxes not included).

    Parameters
    ----------
    price_m2 : float or array-like
        Price in €/m².
    size_m2, loan_to_value : optional
        The typical flat and mortgage.

    Returns
    -------
    float or array-like
        Euros.
    """
    return price_m2 * size_m2 * (1 - loan_to_value)


def down_payment_years(price_m2, yearly_wage, size_m2=FLAT_SIZE_M2,
                       loan_to_value=LOAN_TO_VALUE):
    """
    The down payment in years of gross wage.

    Parameters
    ----------
    price_m2 : float or array-like
        Price in €/m².
    yearly_wage : float or array-like
        Gross wage, € per year.
    size_m2, loan_to_value : optional
        The typical flat and mortgage.

    Returns
    -------
    float or array-like
        Years of gross wage.
    """
    return down_payment(price_m2, size_m2, loan_to_value) / yearly_wage


def mortgage_steps(before, after, size_m2=FLAT_SIZE_M2):
    """
    How the mortgage share moved from one year to the next, one cause at a time.

    The changes are applied in a fixed order (price, then rate, then wage), so each
    step shows what that cause added ON TOP of the previous ones. Another order
    would give slightly different steps, with the same start and end.

    Parameters
    ----------
    before, after : pandas.Series
        One panel row each, with ``buy_m2``, ``rate_pct`` and ``mean_wage``.
    size_m2 : float, optional
        Size of the flat.

    Returns
    -------
    pandas.Series
        Mortgage share (%) at ``start``, ``+ price``, ``+ rate``, ``+ wage`` (= end).
    """
    def share(price, rate, wage):
        return float(mortgage_share(price, rate, wage, size_m2=size_m2))

    return pd.Series({
        "start": share(before["buy_m2"], before["rate_pct"], before["mean_wage"]),
        "+ price": share(after["buy_m2"], before["rate_pct"], before["mean_wage"]),
        "+ rate": share(after["buy_m2"], after["rate_pct"], before["mean_wage"]),
        "+ wage": share(after["buy_m2"], after["rate_pct"], after["mean_wage"]),
    })


def distance_from(geo, code):
    """
    Distance (km) of every comune from one comune, between their centroids.

    Parameters
    ----------
    geo : geopandas.GeoDataFrame
        Output of ``io_geo.load_boundaries`` (metric coordinates, EPSG:32632).
    code : str
        ISTAT code of the comune to measure from, e.g. ``"015146"`` (Milan).

    Returns
    -------
    pandas.Series
        Index = ``istat_code``, values = km.
    """
    centroids = np.column_stack([geo.geometry.centroid.x, geo.geometry.centroid.y])
    origin = centroids[(geo["istat_code"] == code).to_numpy()][0]
    km = np.hypot(*(centroids - origin).T) / 1000       # vectorised Pythagoras
    return pd.Series(km, index=geo["istat_code"].to_numpy())


def distance_band(km):
    """
    Put distances into the bands of ``config.DISTANCE_BANDS_KM`` (Milan, < 15 km...).

    Parameters
    ----------
    km : pandas.Series
        Distances in km.

    Returns
    -------
    pandas.Series
        Ordered categories with the labels of ``config.DISTANCE_LABELS``.
    """
    return pd.cut(km, bins=[-1] + DISTANCE_BANDS_KM, labels=DISTANCE_LABELS)


def headline_numbers(panel, changes, min_taxpayers=0):
    """
    The numbers the story is built on, computed (never typed by hand).

    "Typical person" = median weighted by taxpayers.

    Parameters
    ----------
    panel : pandas.DataFrame
        One row per comune and year (``add_affordability`` columns).
    changes : pandas.DataFrame
        One row per comune, with ``buy_change_pct``, ``wage_change_pct``,
        ``rent_change_pct``, ``buy_change_real_pct`` and ``taxpayers``.
    min_taxpayers : int, optional
        Skip smaller comuni.

    Returns
    -------
    dict
        ``years_wage``, ``mortgage_share``, ``rent_share``, ``rental_yield``
        (each a dict year -> value), and ``price_change``, ``wage_change``,
        ``rent_change``, ``real_price_change``, ``share_comuni_outran``,
        ``share_people_outran``.
    """
    data = panel[panel["taxpayers"] >= min_taxpayers]
    result = {}
    for name, column in [("years_wage", "years_wage"), ("mortgage_share", "mortgage_share_pct"),
                         ("rent_share", "rent_share_pct"),
                         ("rental_yield", "rental_yield_pct")]:
        result[name] = {year: weighted_median(group[column], group["taxpayers"])
                        for year, group in data.groupby("year")}

    moved = changes[(changes["taxpayers"] >= min_taxpayers)].dropna(
        subset=["buy_change_pct", "wage_change_pct"])
    weights = moved["taxpayers"]
    for name, column in [("price_change", "buy_change_pct"), ("wage_change", "wage_change_pct"),
                         ("rent_change", "rent_change_pct"),
                         ("real_price_change", "buy_change_real_pct")]:
        result[name] = weighted_median(moved[column], weights)
    outran = moved["buy_change_pct"] > moved["wage_change_pct"]
    result["share_comuni_outran"] = outran.mean()
    result["share_people_outran"] = weights[outran].sum() / weights.sum()
    return result

