"""Helpers shared by the ``io_*`` modules."""

from pathlib import Path

import requests

from .config import PROJECT_DIR, REQUEST_HEADERS, REQUEST_TIMEOUT
from .errors import DataLoadError


def short_path(path):
    """
    Return a path relative to the project folder, for messages.

    Messages never show the full path, which would include the user's home folder.

    Parameters
    ----------
    path : pathlib.Path
        Any path.

    Returns
    -------
    str
        The path relative to the project folder, or just the file name if the
        path is outside the project.
    """
    path = Path(path)
    try:
        return str(path.resolve().relative_to(PROJECT_DIR))
    except ValueError:
        return path.name


def download(url, path, force=False):
    """
    Download a file once; later calls use the copy on disk (a cache).

    Parameters
    ----------
    url : str
        Where to download from.
    path : pathlib.Path
        Where to save the file. Missing folders are created.
    force : bool, optional
        If True, download again even if the file exists.

    Returns
    -------
    pathlib.Path
        The path of the file on disk.

    Raises
    ------
    DataLoadError
        If the server cannot be reached or answers with an error (404, 500, ...).
        Nothing is saved in that case, so no broken file stays in the cache.
    """
    path = Path(path)
    if path.exists() and not force:
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=REQUEST_HEADERS)
        response.raise_for_status()                 # 404, 500, ... become an exception
    except requests.RequestException as err:
        # "from err" keeps the original error attached, for debugging
        raise DataLoadError(
            f"Could not download {short_path(path)} from {url}: {err}. "
            "Check your internet connection, or download the file by hand into "
            f"{short_path(path.parent)}/."
        ) from err

    path.write_bytes(response.content)
    return path


def require_file(path, hint):
    """
    Check that a file exists, with a helpful message if it does not.

    Parameters
    ----------
    path : pathlib.Path
        The file that must exist.
    hint : str
        What the user should do to get it.

    Returns
    -------
    pathlib.Path
        The same path, so the call can be used inline.

    Raises
    ------
    DataLoadError
        If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise DataLoadError(f"{short_path(path)} not found. {hint}")
    return path
