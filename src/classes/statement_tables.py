import pandas as pd
from bsutils.logger import logger
from datetime import datetime

from const import DATE_FORMATTER
from config import load_active_config


class StatementTables(list):
    def __init__(self, *args, account="", date=datetime.today()):
        super().__init__(*args)
        self.account = account
        self.date = date
        self.is_complete = False
        self.balance = 0

    def set_account(self, account):
        self.account = account

    def output(self):
        if self.is_complete:
            statement = (pd.concat(self, axis=0))[
                ["Date", "Payee", "Memo", "Outflow", "Inflow"]
            ]
            if len(statement) <= 0:
                logger.info(
                    "Skipping CSV export because no transaction rows were extracted."
                )
                return
            Date = pd.to_datetime(
                statement.Date, errors="coerce", format=DATE_FORMATTER
            )

            periods = (
                Date.min().strftime("%d%b%Y") + "-" + Date.max().strftime("%d%b%Y")
            )
            logger.success(f"\tStatement period: {periods}")
            filename = f"{self.account}_{periods}".replace(" ", "_")
            if self.balance:
                filename += f"_balance={self.balance}.csv"
            csv_dir = load_active_config().csv_dir
            filename = (csv_dir / filename).with_suffix(".csv")
            statement.to_csv(filename, index=False)
            logger.success(f"Exported CSV to {filename}\n" + "=" * 80)
            return filename
        else:
            return
