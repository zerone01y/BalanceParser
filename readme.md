# BalanceParser

**BalanceParser** is a command-line–only batch processor for bank statements. Point it at a directory of PDFs and it will convert recognised statements into YNAB/Actual-ready CSVs while archiving the source files for traceability. 

## What It Does
- Reads Bank Statements in PDF with [Camelot](https://camelot-py.readthedocs.io/) and auto-detects Singapore Bank Statements, including DBS, UOB, and Citi layouts. 
- Cleans and normalises transaction rows (Date, Payee, Memo, Outflow, Inflow).
- Saves CSVs to `BankStatement/` and renames the source PDFs for easy traceability. Set the PDF path to `None` in the config if you want to skip archiving.
- Requires text-based PDFs; scanned/image-only statements need OCR before parsing.


BalanceParser in action: 

```bash
> balanceparser parse "~/Downloads" "Statement.pdf"

SUCCESS | Processing account table: PPV_6666
SUCCESS |       Statement period: 27Apr2025-30May2025
SUCCESS | Exported CSV to /Users/balanceparser/BankStatement/PPV_6699_27Apr2025-30May2025_balance=666.6.csv
================================================================================
SUCCESS | Processing account table: CRMC-54xxxx1234
SUCCESS |       Statement period: 18Oct2024-14Oct2025
SUCCESS | Exported CSV to /Users/balanceparser/BankStatement/CRMC-54xxxx1234_18Oct2024-14Oct2025_balance=666.6.csv
================================================================================
```

Every exported CSV is encoded in UTF-8 with a header row that matches the YNAB/Actual import format. Typical output looks like:

| Date       | Payee                          | Memo | Outflow | Inflow |
|------------|--------------------------------|------|---------|--------|
| 23/08/2025 | PAYMENT - DBS INTERNET/WIRELESS |      | 0       | 500.0  |
| 26/07/2025 | AGODA.COM HOTEL ROUT            |      | 0       | 200.0 |
| 10/08/2025 | BUS/MRT 123456789               |      | 2.00    |        |
| 11/08/2025 | BUS/MRT 987654321               |      | 3.00    |        |

## Before You Start
- Python 3.9–3.12.
- Ghostscript installed and on your PATH (see [Camelot requirement](https://camelot-py.readthedocs.io/en/master/user/install-deps.html)).

## Installation
1. Clone or download this repository to your machine (for example, `git clone <your fork url>`).
2. Change into the project directory:
   ```bash
   cd BalanceParser
   ```
3. Create/activate a virtual environment (optional but recommended).
4. Install the package and dependencies with **one** of the following:
   - pip (`-e` flag for editable install so CLI picks up local changes):

     ```bash
     pip install -e .
     ```

   - Poetry (installs in editable mode):

     ```bash
     poetry install
     ```

## Quick Start
1. Place your statement PDFs in a folder, e.g. `~/Downloads/`.
2. Run one of the following:

   ```bash
   balanceparser parse "~/Downloads/" "*Statement*.pdf"
   ```

   or, if you prefer the existing module entry point:
   ```bash
   python src/cli.py "~/Downloads/" "*Statement*.pdf"
   ```

   - Both forms accept the same arguments; the first is the directory to scan.
   - The second argument is optional. If you omit it, the default `*Statement*.pdf` pattern is used. Supply your own glob when your files follow a different naming scheme.
   - Append `--debug` if you want verbose logs and a `statement.log` file for troubleshooting.
3. By default, processed CSVs and archived PDFs are written to `BankStatement/`. To revise the path for processed CSVs and archived PDFs, use the following command to check:
```
balanceparser config -h
```

e.g. 

```
balanceparser config set --csv "My/path/to/csv/bankstatements" --pdf "My/path/to/pdf/archival".
```

## Supported Statements
- Singapore DBS credit cards
- Singapore DBS current/savings (POSB included)
- Singapore UOB accounts
- Singapore UOB credit cards
- Singapore Citi credit cards


## Statement Archiving & Configuration
To keep each run traceable, BalanceParser renames and moves the processed PDFs into the `BankStatement/` folder alongside the CSV export (e.g. `DBS_CC_Account_202501.pdf`). This preserves the original source documents without cluttering your working directory.


By default, both exported CSVs and archived PDFs are saved to `BankStatement/` in the current working directory. You can customise these locations with the configuration CLI:

```bash
# Show the active configuration (defaults if none saved yet)
python -m config show

# Update export/archival directories
python -m config set --csv "~/Documents/Statements/CSV" --pdf "~/Documents/Statements/PDF"

# Delete the stored config to fall back to defaults
python -m config delete
```

Note that by setting python pdf path to None, the pdf files will not be renamed and archived.

Configuration is stored per user in the standard config directory for your platform (e.g. `%APPDATA%` on Windows, `~/Library/Application Support` on macOS, or `~/.config` on Linux).

## Extending Bank Support
BalanceParser’s bank-specific logic lives in subclasses of `BankSettings`. To add a new statement type:
1. Review the hooks provided by the base class in `src/classes/bank_settings/base.py` (methods such as `page_filter`, `extract_titles`, `row_filter`, and `process`). These outline the lifecycle for parsing a statement table.
2. Create a new subclass in `src/classes/bank_settings/` that implements the necessary overrides. Use existing classes (e.g. `src/classes/bank_settings/uob_cc.py`, `src/classes/bank_settings/dbs_acc.py`) as references.
3. Register the new class in `src/classes/statement_settings.py` by adding it to `SETTING_DICT` with identifying regex patterns so the auto-assignment can select it.
4. Drop any sample PDFs into a local test folder and run `balanceparser parse <localfolder>` to verify the behaviour.


## Tuning Camelot Extraction
If Camelot struggles to read a layout, visualise the table detection and tweak `reader_options`. Camelot’s [visual debugging guide](https://camelot-py.readthedocs.io/en/master/user/advanced.html#visual-debugging) shows how to plot contours and adjust parameters until the columns align correctly.
