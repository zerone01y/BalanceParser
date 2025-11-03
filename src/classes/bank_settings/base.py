from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union
from datetime import timedelta

import pandas as pd

TableEnd = Tuple[bool, Optional[Union[str, float, int]]]
CamelotOptions = Dict[str, Any]
# Required schema for processed statement dataframes
StatementFrame = pd.DataFrame


class BankSettings:
    """
    Base class for bank-specific statement parsers.

    Subclasses translate Camelot dataframes into the normalised output used by
    BalanceParser. Every bank reader should implement the behaviour outlined
    below to keep the overall pipeline consistent.
    """

    PAGE_FILTER_REGEX = None

    TITLE_REGEX = None
    DATE_REGEX = None

    def __init__(self) -> None:
        """
        Store default keyword arguments passed to :func:`camelot.read_pdf`.

        Override this in subclasses when the reader requires specific Camelot
        options (column positions, tolerances, flavour, etc.).

        See https://camelot-py.readthedocs.io/en/master/api.html#camelot.read_pdf
        """
        self._reader_options = {
            "flavor": "stream",
        }

    def page_filter(self, p: str) -> bool:
        """
        Return ``True`` when the current PDF page should be processed.

        Override when a statement includes cover pages or extra summaries that
        must be skipped before table extraction begins.
        """
        if self.PAGE_FILTER_REGEX is not None:
            return self.PAGE_FILTER_REGEX in p
        return True

    def extract_titles(self, p: str) -> list:
        """
        Extract account identifiers for the tables found on the page.

        When subclasses define :data:`TITLE_REGEX`, the default implementation
        will apply that pattern. Most concrete readers override this method to
        build cleaner names (see :mod:`classes.bank_settings.dbs_acc`).
        """
        find = re.findall(self.TITLE_REGEX, p)
        return ["-".join(s) for s in find]

    def extract_date(self, p: str) -> Optional[datetime]:
        """
        Extract the statement date (if present) from the page text.

        The resulting date is used for naming archived statements and adjusting
        transaction years. Returning ``None`` tells the pipeline to fall back to
        other heuristics.
        """

        datestr = re.search(self.DATE_REGEX, p)
        if datestr:
            return pd.to_datetime(
                f"{datestr[1]}-{datestr[2]}-{datestr[3]}", format="%d-%b-%Y"
            )
        return None

    def reader_options(self, page: Optional[int] = None) -> CamelotOptions:
        """
        Provide the Camelot options for the current page.

        Most readers return the same configuration for every page; however,
        implementations can override this to adjust settings dynamically—for
        example, :mod:`classes.bank_settings.uob_cc` sets ``columns=None`` for
        the first page only.
        """
        return self._reader_options

    def is_table_end(self, df: pd.DataFrame) -> TableEnd:
        """
        Decide whether the current table is complete.

        Subclasses **must** return a tuple ``(finished, balance)``:

        - ``finished`` (bool): ``True`` when the current table has reached its
          end.
        - ``balance`` (str | float | int | None): closing balance extracted from
          the table, used to label the CSV; ``None`` if no balance is available.
        """
        raise NotImplementedError

    def row_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drop rows that are not part of the transaction details.

        Many readers remove running totals or empty spacer rows here. The base
        implementation returns the dataframe unchanged.
        """
        return df

    def header_locator(self, df: pd.DataFrame) -> Optional[pd.Series]:
        """
        Locate table headers within the Camelot dataframe.

        Subclasses should return one of:

        - ``None`` when the table starts from the first row (single-table page).
        - A boolean :class:`pandas.Series` aligned with ``df`` where ``True``
          marks rows that act as table headers, allowing the pipeline to split
          multiple tables from the same page.
        """
        return None

    def process(self, df: pd.DataFrame, date: datetime) -> StatementFrame:
        """
        Convert the cleaned dataframe into the standard output schema.

        Expectations for subclasses:
            * Format the `Date` column as ``"%d/%m/%Y"``.
            * Populate `Payee`, `Memo`, `Outflow`, and `Inflow`.
            * Return an empty dataframe with these columns if no transactions are
              detected.
        """
        return df
