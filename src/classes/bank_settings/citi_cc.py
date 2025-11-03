import re

import pandas as pd

from const import DATE_FORMATTER
from .base import BankSettings, timedelta


class CITI_CC(BankSettings):
    TITLE_REGEX = r"\n(CITI.+CARD)(\d+)-\w+"
    DATE_REGEX = r"Date:(.+\d+,\d{4})"

    def __init__(self):
        super().__init__()
        self._reader_options = {
            "columns": ["105,500"],
            "flavor": "stream",
            "row_tol": 5,
        }

    @staticmethod
    def page_filter(p):
        return (
            "CARD" in p and "Detailedtransactionscanbefoundonthefollowingpages" not in p
        )

    def extract_titles(self, p):
        find = re.findall(self.TITLE_REGEX, p)
        return [
            ("-".join(s)).replace("CITIREWARDSWORLD", "CR").replace("MASTERCARD", "MC")
            for s in find
        ]

    def extract_date(self, p):
        datestr = re.search(self.DATE_REGEX, p)
        if datestr:
            date = pd.to_datetime(datestr[1], format="%B%d,%Y")
            return date - timedelta(weeks=4)
        return None

    def is_table_end(self, df):
        mask = df.iloc[:, 1].str.startswith("GRAND TOTAL")
        if mask.any():
            total = df.loc[mask, 2].iloc[0].replace(",", "")
            return (True, total)
        return (False, 0)

    def header_locator(self, df):
        return (df.iloc[:, 0] == "DATE") & (df.iloc[:, 1] == "Description".upper())

    def row_filter(self, df):
        if not len(df.columns):
            return df
        mask = df[1].str.contains(
            r"(?:SUB-TOTAL|TRANSACTIONS FOR CITI|BALANCE PREVIOUS STATEMENT)"
        )
        return df.loc[~mask]

    def process(self, df, date):
        if len(df.columns) < 3 or len(df) <= 1:
            return df
        df = df.reset_index()
        Date = pd.to_datetime(
            df[0].str.replace("$", f" {date.year}", regex=True),
            format="%d %b %Y",
            errors="coerce",
        ).apply(lambda x: x.replace(year=date.year - 1) if x > date else x)

        df.loc[:, 0] = Date.dt.strftime(DATE_FORMATTER)
        df = df.loc[~Date.isna()]

        mask = df[2].str.endswith(")")
        df["Inflow"] = ""
        df.loc[mask, "Inflow"] = df.loc[mask, 2].str.strip("()")
        df.loc[mask, 2] = "0"

        df["Memo"] = ""
        cleaned_words = ["AMAZE*", "PAYALL"]
        for word in cleaned_words:
            word_mask = df[1].str.startswith(word)
            df.loc[word_mask, 1] = (
                df.loc[word_mask, 1].str.replace(word, "").str.strip(" -")
            )
            df.loc[word_mask, "Memo"] = word

        return df.rename(columns={0: "Date", 1: "Payee", 2: "Outflow"})
