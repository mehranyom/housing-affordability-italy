"""Custom exceptions of the project."""


class DataLoadError(Exception):
    """
    A data file is missing, cannot be downloaded or does not look as expected.

    Raised by the ``io_*`` modules with a message that says what went wrong and
    what to do. The caller (a notebook, a script or the Streamlit app) can catch
    this one type of error and show the message, instead of a long traceback.
    """
