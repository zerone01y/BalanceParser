import camelot
from pypdf import PdfReader
from pathlib import Path
import matplotlib.pyplot as plt
from bsutils.logger import logger
from datetime import datetime
import pandas as pd
from classes.statement_tables import StatementTables
from classes.statement_settings import *
from config import load_active_config
import re

_APP_CONFIG = load_active_config()


def read_statement(file, statement_reader=None):
    logger.info(f"Reading statement: {file}")
    reader = PdfReader(file)
    page = 0
    current_table = None
    date = datetime.today()
    statement_date = None
    processed_table_titles = []
    while page < len(reader.pages):
        page += 1
        page_content = reader.pages[page - 1].extract_text()
        if statement_reader is None:
            statement_reader = auto_assign_reader(page_content)
            if statement_reader is None:
                logger.error(
                    "No statement reader matched this document; skipping file."
                )
                return
        if not statement_reader.page_filter(page_content):
            logger.debug(f"Skipping page {page} after filtering")
            continue
        logger.debug(f"Processing page {page}")
        if statement_date is None:
            statement_date = statement_reader.extract_date(page_content)
        # 读取表格
        tables = try_read_pdf_table(file, page, statement_reader)
        if not tables:
            continue
        for table in tables:
            df = table.df

            if statement_date:
                date = statement_date
            table_title_list = statement_reader.extract_titles(page_content)
            table_header_mask = statement_reader.header_locator(df)
            number_of_tables, table_header_index = get_table_count_and_index(
                df, table_header_mask, current_table, table_title_list
            )
            for tc in range(number_of_tables):
                current_table, current_df = handle_table_detection(
                    current_table,
                    table_title_list,
                    df,
                    table_header_mask,
                    table_header_index,
                    tc,
                    date,
                )
                if current_table is not None:
                    (
                        current_table.is_complete,
                        current_table.balance,
                    ) = statement_reader.is_table_end(current_df)
                    current_df = statement_reader.row_filter(current_df)
                    current_df = statement_reader.process(current_df, date)
                    current_table.append(current_df)
                    if current_table.is_complete == 1:
                        if (
                            current_table.account != "Unknown"
                            and len(current_table) > 0
                        ):
                            processed_table_titles.append(current_table.account)
                        current_table.output()
                        current_table = None
    archive_file(file, statement_reader, processed_table_titles, date)


def auto_assign_reader(page_content):
    page_content = page_content.replace(" ", "")
    for patterns, reader_cls in SETTING_DICT:
        if all(re.findall(pattern, page_content) for pattern in patterns):
            reader = reader_cls()
            logger.debug(
                f"Automatically selected reader '{reader.__class__.__name__}'."
            )
            return reader
    logger.debug("No reader matched the page content automatically.")
    return None


def try_read_pdf_table(file, page, statement_reader):
    try:
        tables = camelot.read_pdf(
            str(file), pages=str(page), **statement_reader.reader_options(page)
        )
        return tables
    except Exception as e:
        logger.warning(
            f"Camelot failed to parse tables on page {page}: {e}; continuing."
        )
        return None


def get_table_count_and_index(df, table_header_mask, current_table, table_title_list):
    if isinstance(table_header_mask, (pd.DataFrame, pd.Series)):
        number_of_tables = table_header_mask.sum()
        table_header_index = df[table_header_mask].index
    else:
        number_of_tables = max(bool(current_table) + len(table_title_list), 1)
        table_header_index = None
    return number_of_tables, table_header_index


def handle_table_detection(
    current_table, table_title_list, df, table_header_mask, table_header_index, tc, date
):
    # 新表格检测
    if current_table is None:
        if len(table_title_list):
            logger.debug("Detected start of a new table")
            account = table_title_list.pop(0)
            logger.success(f"Processing account table: {account}")
            current_table = StatementTables(account=account, date=date)
        else:
            logger.debug("Starting unnamed table capture")
            account = "Unknown"
            logger.info(f"Processing table with placeholder account '{account}'")
            current_table = StatementTables(account=account, date=date)
    # 已有表格，选择表格数据
    if current_table is not None and isinstance(
        table_header_mask, (pd.DataFrame, pd.Series)
    ):
        if tc == len(table_header_index) - 1:  # 最后一个表
            current_df = df.loc[table_header_index[tc] :]
        else:
            current_df = df.loc[table_header_index[tc] : table_header_index[tc + 1] - 1]
    else:
        current_df = df
    return current_table, current_df


def archive_file(file, statement_reader, processed_table_titles, date):
    # 归档文件
    try:
        archive_dir = _APP_CONFIG.pdf_dir
        if archive_dir is not None:
            account = (
                processed_table_titles[0] if len(processed_table_titles) else "Unknown"
            )
            target_name = f"{type(statement_reader).__name__}_{account}_{date.strftime('%Y%m')}.pdf"
            file.rename(archive_dir / target_name)
            logger.info(f"PDF file is archived as: {target_name}")
    except Exception as e:
        logger.warning(f"Failed to archive processed file: {e}")


def visualize_statement(file, pages, **kwargs):
    import matplotlib.pyplot as plt

    tables = camelot.read_pdf(
        str(file), flavor="stream", row_tol=5, pages=str(pages), **kwargs
    )
    camelot.plot(tables[0], kind="contour").show()
    plt.show()
    return tables[0]
