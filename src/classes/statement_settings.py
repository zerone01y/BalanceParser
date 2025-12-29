from classes.bank_settings import (
    BankSettings,
    CITI_CC,
    DBS_ACC,
    DBS_CC,
    UOB_ACC,
    UOB_CC,
)

SETTING_DICT = (
    ((r"DBS[A-Z ]+CARD",), DBS_CC),
    ((r"(DBS[\w ]*Account|DBS[^\n]+POSB)",), DBS_ACC),
    (
        (
            "UOB",
            "StatementofAccount",
        ),
        UOB_ACC,
    ),
    (
        (
            "UOB",
            r"CreditCard\(s\)Statement",
        ),
        UOB_CC,
    ),
    (("CITI",), CITI_CC),
)

__all__ = [
    "BankSettings",
    "DBS_CC",
    "DBS_ACC",
    "UOB_ACC",
    "UOB_CC",
    "CITI_CC",
    "SETTING_DICT",
]
