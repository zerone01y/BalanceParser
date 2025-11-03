import re

import pandas as pd

from bsutils.logger import logger
from const import DATE_FORMATTER
from .base import BankSettings


class DBS_ACC(BankSettings):
    PAGE_FILTER_REGEX = r"Transaction Details"
    TITLE_REGEX = r"\n(.+Account)\s+Account No. ([\d+-]+)"
    DATE_REGEX = r"Transaction Details as of\s*(\d+)\s*([A-z]+)\s*(\d+)"

    def __init__(self):
        super().__init__()
        self._reader_options = {
            "columns": ["105,333,405,480"],
            "flavor": "stream",
            "edge_tol": 300,
            "row_tol": 5,
        }

    def is_table_end(self, df):
        crcid = df[df[0].str.contains("CURRENCY:")].index
        mask = df.iloc[:, 1].str.startswith("Total Balance")
        if mask.any():
            return True, df.loc[mask, 4].iloc[0].replace(",", "")
        return ((len(crcid) and df.loc[crcid[0], 0] != "CURRENCY: SINGAPORE DOLLAR"), 0)

    def header_locator(self, df):
        return (df.iloc[:, 0] == "Date") & (df.iloc[:, 1] == "Description")

    def row_filter(self, df):
        if not len(df.columns):
            return df
        crcid = df[df[0].str.contains("CURRENCY:")].index
        if len(crcid) and df.loc[crcid[0], 0] != "CURRENCY: SINGAPORE DOLLAR":
            return pd.DataFrame(index=df.index)
        mask = df[1].str.contains(
            r"(?:Balance Brought Forward|Balance Carried Forward)"
        )
        if mask.any():
            summary = (
                df.loc[mask, [1, 4]]
                .to_string(index=False, header=False)
                .replace("\n", "; ")
                .strip()
            )
            logger.success(f"\tBalance summary rows retained: {summary}")
        return df.loc[~mask]

    def process(self, df, date):
        if len(df.columns) < 4 or len(df) <= 1:
            return pd.DataFrame(columns=["Date", "Payee", "Memo", "Outflow", "Inflow"])
        df = df.reset_index()
        Date = pd.to_datetime(df[0], errors="coerce", format=DATE_FORMATTER)
        mask = ~Date.isna()
        id_series = df["index"].where(mask)
        df["id"] = id_series.ffill().astype("Int64")
        if df.loc[~mask][[2, 3, 4]].any(axis=1).any():
            rm_entries = df[~mask][df[~mask][[2, 3, 4]].any(axis=1)]
            df = df.drop(rm_entries.index)
            if len(df) <= 1:
                return pd.DataFrame(
                    columns=["Date", "Payee", "Memo", "Outflow", "Inflow"]
                )
        description = (
            df.groupby("id")[1]
            .apply(lambda x: x.str.cat(sep="\n").strip("\n"))
            .str.split("\n", expand=True)
        )
        mask = description[1].str.startswith("VALUE DATE", na=False)
        description[1].loc[mask] = None
        description[1] = description[1].fillna(description[0]).infer_objects(copy=False)
        mask = description[1].str.endswith(":", na=False)
        if description.shape[1] > 2:
            description.loc[mask, 1] = description.loc[mask, 1].str.cat(
                description.loc[mask, 2], na_rep="", sep=" "
            )
            description.loc[mask, 2] = None
        df = df.groupby("id").sum()
        df["Payee"] = description.pop(1)
        df["Memo"] = description.fillna("").agg(" - ".join, axis=1).str.strip(" -")
        return df.rename(columns={0: "Date", 2: "Outflow", 3: "Inflow"})
