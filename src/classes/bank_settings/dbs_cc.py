import re
from datetime import datetime

import pandas as pd

from const import DATE_FORMATTER
from .base import BankSettings


class DBS_CC(BankSettings):
    TITLE_REGEX = r"CARD NO.: ([\d ]+)\n"

    def __init__(self):
        super().__init__()
        self._reader_options = {
            "columns": ["95,495"],
            "flavor": "stream",
            "edge_tol": 300,
            "row_tol": 5,
        }

    def is_table_end(self, df):
        return (df.iloc[:, 1].str.startswith("TOTAL").any(), 0)

    def header_locator(self, df):
        return None

    def process(self, df, date):
        today_year = datetime.today().year
        Date = pd.to_datetime(
            df[0].str.replace("$", f" {today_year}", regex=True),
            format="%d %b %Y",
            errors="coerce",
        ).dt.strftime(DATE_FORMATTER)

        df[0] = Date
        df = df.loc[~Date.isna()].copy()
        if df.empty:
            return pd.DataFrame(columns=["Date", "Payee", "Memo", "Outflow", "Inflow"])

        mask = df[2].fillna("").str.endswith("CR")
        df["Inflow"] = ""
        if mask.any():
            inflow_values = (
                df.loc[mask, 2]
                .astype(str)
                .str.replace("CR", "", regex=False)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            df.loc[mask, "Inflow"] = inflow_values
            df.loc[mask, 2] = 0
        df["Memo"] = ""
        return df.rename(columns={0: "Date", 2: "Outflow", 1: "Payee"})
