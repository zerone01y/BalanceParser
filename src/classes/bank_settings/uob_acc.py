import re

import pandas as pd

from bsutils.logger import logger
from const import DATE_FORMATTER
from .base import BankSettings


class UOB_ACC(BankSettings):
    TITLE_REGEX = r"\n(.+Account)\s+([\d+-]+)\s*\n"
    DATE_REGEX = r"Period:.+to\s*(\d+)\s*([A-z]+)\s*(\d+)"

    def __init__(self):
        super().__init__()
        self._reader_options = {
            "columns": ["116,320,399, 475"],
            "flavor": "stream",
            "edge_tol": 300,
            "row_tol": 5,
        }

    def page_filter(self, p):
        return "Account Transaction Details" in p or "Statement of Account" in p

    def is_table_end(self, df):
        mask = df.iloc[:, 1].str.fullmatch("Total")
        if mask.any():
            total = df.loc[mask, 4].iloc[0].replace(",", "")
            return (True, total)
        return (False, 0)

    def header_locator(self, df):
        return (df.iloc[:, 0] == "Date") & (df.iloc[:, 1] == "Description")

    def row_filter(self, df):
        if not len(df.columns):
            return df
        mask = df[1].str.contains(r"(?:BALANCE B/F|Total)") | (df[1] == "")
        return df.loc[~mask]

    def process(self, df, date):
        if (len(df.columns) < 4) or (len(df) <= 1):
            return pd.DataFrame(columns=["Date", "Payee", "Memo", "Outflow", "Inflow"])

        df = df.reset_index()

        statement_date = pd.Timestamp(date)
        raw_dates = pd.to_datetime(
            df[0].str.replace("$", f" {statement_date.year}", regex=True),
            format="%d %b %Y",
            errors="coerce",
        )
        mask = raw_dates.notna()
        adjusted_dates = raw_dates.mask(
            raw_dates > statement_date, raw_dates - pd.DateOffset(years=1)
        )
        df.loc[:, 0] = adjusted_dates.dt.strftime(DATE_FORMATTER)
        df.loc[~mask, 0] = None
        df["id"] = df["index"]
        df.loc[~mask, "id"] = pd.NA
        df["id"] = df["id"].astype("Int64").ffill()
        if df.loc[~mask][[2, 3, 4]].any(axis=1).any():
            rm_entries = df[~mask][df[~mask][[2, 3, 4]].any(axis=1)]
            df = df.drop(rm_entries.index)
            removed = (
                rm_entries.iloc[:, 1:-1]
                .to_string(index=False, header=False)
                .replace("\n", "; ")
                .strip()
            )
            logger.warning(
                f"Dropping rows without dates that still contain values: {removed}"
            )

        df = df.dropna(subset=["id"])
        df["id"] = df["id"].astype("int64")

        description = (
            df.groupby("id")[1]
            .apply(lambda x: x.str.cat(sep="\n").strip("\n"))
            .str.split("\n", expand=True)
        )
        df = df.groupby("id").sum()
        if df.empty:
            return pd.DataFrame(columns=["Date", "Payee", "Memo", "Outflow", "Inflow"])
        if 2 in description.columns:
            fallback = description.ffill(axis=1)[2]
            payee = description[2].fillna(fallback).fillna("")
            description = description.drop(columns=2)
            df["Payee"] = payee
        else:
            df["Payee"] = ""
        df["Memo"] = description.fillna("").agg(" - ".join, axis=1).str.strip(" -")
        return df.rename(columns={0: "Date", 2: "Outflow", 3: "Inflow"})
