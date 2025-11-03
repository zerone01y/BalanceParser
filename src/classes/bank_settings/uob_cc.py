import re

import pandas as pd

from bsutils.logger import logger
from const import DATE_FORMATTER
from .base import BankSettings


class UOB_CC(BankSettings):
    PAGE_FILTER_REGEX = "Transaction Amount"
    TITLE_REGEX = r"([A-Z\' ]+(?:CARD|VISA))\n((?:\d{4}-){3}\d+)\s*[A-Z ]+\n"
    DATE_REGEX = r"Statement Date\s*(\d+)\s*([A-Z]+)\s*(\d+)"

    def __init__(self):
        super().__init__()
        self._reader_options = {
            "columns": ["98,144,468"],
            "flavor": "stream",
            "edge_tol": 100,
            "row_tol": 5,
        }

    def reader_options(self, page=None):
        if page and page > 1:
            return super().reader_options(page)
        temp_option = self._reader_options.copy()
        temp_option.update(columns=None)
        return temp_option

    def extract_titles(self, p):
        find = re.findall(self.TITLE_REGEX, p)
        find_abbv = []
        for f in find:
            card = "".join(i[0] for i in f[0].split(" "))
            num = f[1][-4:]
            find_abbv.append(f"{card}_{num}")
        return find_abbv

    def is_table_end(self, df):
        subtotal_mask = df.iloc[:, 2].str.fullmatch("SUB TOTAL")
        sub_total = 0
        if subtotal_mask.any():
            sub_total = df.loc[subtotal_mask, 3].iloc[0].replace(",", "")
        return (subtotal_mask.any(), sub_total)

    def header_locator(self, df):
        return (df.iloc[:, 0] == "Post") & (df.iloc[:, 1] == "Trans")

    def row_filter(self, df):
        if not len(df.columns):
            return df
        m1 = df[2].str.contains(r"(?:PREVIOUS BALANCE|TOTAL BALANCE)")
        if m1.any():
            summary = df[m1].to_string(header=False, index=False)
            logger.info(f"Summary rows retained before filtering:\n{summary}")

        mask = df[2].str.contains(
            r"(?:PREVIOUS BALANCE|SUB TOTAL|TOTAL BALANCE FOR|Description of Transaction)"
        ) | (df[2] == "")
        return df.loc[~mask]

    def process(self, df, date):
        if len(df.columns) < 4 or len(df) <= 1:
            return pd.DataFrame(columns=["Date", "Payee", "Memo", "Outflow", "Inflow"])

        df = df.replace("", None).dropna(how="all", axis=1)
        df.columns = range(0, len(df.columns))
        df = df.reset_index()

        statement_date = pd.Timestamp(date)
        raw_dates = pd.to_datetime(
            df[1].str.replace("$", f" {statement_date.year}", regex=True),
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
        if df.loc[~mask][[1, 3]].any(axis=1).any():
            rm_entries = df[~mask][df[~mask][[1, 3]].any(axis=1)]
            df = df.drop(rm_entries.index)
            removed = (
                rm_entries.iloc[:, 1:-1]
                .to_string(index=False, header=False)
                .replace("\n", "; ")
                .strip()
            )
            logger.warning(
                f"Dropping rows that contain amounts but lack transaction dates: {removed}"
            )

        df = df.dropna(subset=["id"])
        df["id"] = df["id"].astype("int64")

        description = (
            df.groupby("id")[2]
            .apply(lambda x: x.str.cat(sep="\n").strip("\n"))
            .str.split("\n", expand=True)
        )

        df = df.groupby("id").sum()
        df["Payee"] = description.pop(0)
        df["Memo"] = (
            (df[0] + " - " + description.fillna("").agg(" - ".join, axis=1))
            .str.replace(r"\s*\- Ref No\. : \d+", "", regex=True)
            .str.strip(" -")
        )

        df[3] = df[3].astype(str).str.replace(",", "")

        mask = df[3].str.endswith("CR")
        df["Inflow"] = ""
        if mask.any():
            df.loc[mask, "Inflow"] = df.loc[mask, 3].astype(str).str.strip("CR")
            df.loc[mask, 3] = 0

        return df.rename(columns={0: "Date", 3: "Outflow"})
