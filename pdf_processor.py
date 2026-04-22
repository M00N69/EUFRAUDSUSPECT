import os
import re
import logging
import tempfile
from datetime import datetime

import pandas as pd
import pdfplumber
import PyPDF2
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en"

EU_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 5,
    "join_tolerance": 5,
    "edge_min_length": 20,
    "min_words_vertical": 1,
    "min_words_horizontal": 1,
}

FRAUD_SECTION_PATTERNS = [
    (r"1\.?\s*PRODUCT\s+TAMPERING", "Product tampering"),
    (r"2\.?\s*RECORD\s+TAMPERING", "Record tampering"),
    (r"3\.?\s*OTHER\s+NON-COMPLIANCES", "Other non-compliances"),
]

EXPECTED_HEADERS = [
    "CLASSIFICATION",
    "PRODUCT CATEGORY",
    "COMMODITY",
    "ISSUE",
    "ORIGIN",
    "NOTIFIED BY",
]


def _detect_fraud_type(
    text: str, current: str | None = None
) -> tuple[str | None, bool]:
    for pattern, fraud_type in FRAUD_SECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return fraud_type, True
    for keyword, fraud_type in [
        ("PRODUCT TAMPERING", "Product tampering"),
        ("RECORD TAMPERING", "Record tampering"),
        ("OTHER NON-COMPLIANCES", "Other non-compliances"),
    ]:
        if keyword in text.upper():
            return fraud_type, True
    return current, False


def _match_headers(header_row: list) -> dict[str, int]:
    indices = {}
    for i, cell in enumerate(header_row):
        if not cell:
            continue
        cell_str = str(cell).strip().upper()
        for expected in EXPECTED_HEADERS:
            if expected in cell_str or cell_str in expected:
                indices[expected] = i
                break
    return indices


def _extract_total_suspicions(pdf_path: str) -> int:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(min(3, len(pdf.pages))):
                text = pdf.pages[page_num].extract_text() or ""
                match = re.search(
                    r"THIS MONTH (\d+) SUSPICIONS WERE RETRIEVED", text, re.IGNORECASE
                )
                if match:
                    return int(match.group(1))
    except Exception as e:
        logger.warning("Extraction total suspicions echouee: %s", e)
    return 0


def _extract_date_from_pdf(pdf_path: str) -> str | None:
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            if not reader.pages:
                return None
            text = reader.pages[0].extract_text() or ""
            months = [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]
            for month in months:
                match = re.search(f"{month}\\s+(\\d{{4}})", text)
                if match:
                    return f"{match.group(1)}-{months.index(month) + 1:02d}"
    except Exception as e:
        logger.warning("Extraction date PDF echouee: %s", e)
    return None


def _extract_report_date(filename: str, pdf_path: str, full_url: str) -> str:
    if "?filename=" in full_url:
        fname = full_url.split("?filename=")[-1]
    else:
        fname = filename
    match = re.search(r"report[_-](\d{4})(\d{2})\.pdf", fname, re.IGNORECASE)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r"(\d{4})[_-](\d{2})\.pdf", fname, re.IGNORECASE)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    date = _extract_date_from_pdf(pdf_path)
    if date:
        return date
    match = re.search(r"(\d{4})(\d{2})\.pdf", fname)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    now = datetime.now()
    logger.warning("Date non extractible, utilisation date actuelle")
    return f"{now.year}-{now.month:02d}"


def _clean_value(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\*+$", "", text.strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_data_from_pdf(pdf_path: str) -> dict:
    extracted_data = {"total_suspicions": 0, "suspicions": [], "method": "pdfplumber"}
    total_announced = _extract_total_suspicions(pdf_path)
    extracted_data["total_suspicions"] = total_announced

    current_fraud_type = None
    current_classification = None
    last_values = {}
    suspicions = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            start_page = 2
            for page_num in range(start_page, len(pdf.pages)):
                page = pdf.pages[page_num]
                text = page.extract_text() or ""

                detected, changed = _detect_fraud_type(text, current_fraud_type)
                if changed:
                    current_fraud_type = detected
                    last_values = {}
                    current_classification = None

                tables = page.extract_tables(table_settings=EU_TABLE_SETTINGS)
                if not tables:
                    tables = page.extract_tables()

                for table in tables:
                    if not table or len(table) <= 1:
                        continue

                    header_row = table[0]
                    header_indices = _match_headers(header_row)

                    if len(header_indices) < 3:
                        continue

                    for row in table[1:]:
                        if not row or all(
                            not cell or (isinstance(cell, str) and cell.strip() == "")
                            for cell in row
                        ):
                            continue

                        for i, cell in enumerate(row):
                            if cell and isinstance(cell, str) and cell.strip():
                                last_values[i] = cell.strip()

                        if "CLASSIFICATION" in header_indices:
                            idx = header_indices["CLASSIFICATION"]
                            if (
                                idx < len(row)
                                and row[idx]
                                and isinstance(row[idx], str)
                                and row[idx].strip()
                            ):
                                current_classification = row[idx].strip()
                            else:
                                val = last_values.get(idx, "")
                                if val:
                                    current_classification = val

                        suspicion = {
                            "fraud_type": current_fraud_type or "",
                            "classification": current_classification or "",
                            "product_category": "",
                            "commodity": "",
                            "issue": "",
                            "origin": "",
                            "notified_by": "",
                        }

                        for field, header in [
                            ("product_category", "PRODUCT CATEGORY"),
                            ("commodity", "COMMODITY"),
                            ("issue", "ISSUE"),
                            ("origin", "ORIGIN"),
                            ("notified_by", "NOTIFIED BY"),
                        ]:
                            if header in header_indices:
                                idx = header_indices[header]
                                if (
                                    idx < len(row)
                                    and row[idx]
                                    and isinstance(row[idx], str)
                                    and row[idx].strip()
                                ):
                                    suspicion[field] = row[idx].strip()
                                elif field in ["product_category", "classification"]:
                                    suspicion[field] = last_values.get(idx, "")

                        essential = ["product_category", "commodity", "issue"]
                        if all(suspicion[f] == "" for f in essential):
                            continue

                        for key in suspicion:
                            suspicion[key] = _clean_value(suspicion[key])

                        suspicions.append(suspicion)

    except Exception as e:
        logger.error("Erreur extraction PDF: %s", e)

    extracted_data["suspicions"] = suspicions
    if total_announced > 0 and len(suspicions) > 0:
        extracted_data["confidence_score"] = min(len(suspicions) / total_announced, 1.5)
        if abs(len(suspicions) - total_announced) > total_announced * 0.2:
            logger.warning(
                "Ecart extraction: %d extraites vs %d annoncees",
                len(suspicions),
                total_announced,
            )
    else:
        extracted_data["confidence_score"] = 0.5

    return extracted_data


def download_latest_report(save_dir: str | None = None) -> tuple[str | None, str]:
    if save_dir is None:
        save_dir = os.path.join(os.path.dirname(__file__), "data", "pdf_reports")
    os.makedirs(save_dir, exist_ok=True)

    try:
        response = requests.get(BASE_URL, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        pdf_links = []
        pattern = re.compile(r"report.*\d{4}.*\.pdf", re.IGNORECASE)
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if pattern.search(href) and href.endswith(".pdf"):
                pdf_links.append(href)

        if not pdf_links:
            logger.error("Aucun lien PDF trouve")
            return None, "Aucun lien PDF trouve"

        latest_pdf_link = pdf_links[0]
        if latest_pdf_link.startswith("http"):
            full_url = latest_pdf_link
        elif latest_pdf_link.startswith("/"):
            domain = re.match(r"(https?://[^/]+)", BASE_URL).group(1)
            full_url = domain + latest_pdf_link
        else:
            full_url = BASE_URL.rstrip("/") + "/" + latest_pdf_link

        if "?filename=" in full_url:
            filename = full_url.split("?filename=")[-1]
        else:
            filename = os.path.basename(full_url)

        local_path = os.path.join(save_dir, filename)

        pdf_response = requests.get(full_url, stream=True, timeout=60)
        pdf_response.raise_for_status()

        with open(local_path, "wb") as f:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                f.write(chunk)

        report_date = _extract_report_date(filename, local_path, full_url)
        logger.info("PDF telecharge: %s (date: %s)", filename, report_date)
        return local_path, report_date

    except Exception as e:
        logger.error("Erreur telechargement: %s", e)
        return None, str(e)


def check_for_new_report(data_manager) -> bool:
    latest_year, latest_month = data_manager.get_latest_report_date()
    pdf_path, report_date = download_latest_report()
    if not pdf_path:
        return False

    try:
        date_obj = datetime.strptime(report_date, "%Y-%m")
        year, month = date_obj.year, date_obj.month
    except ValueError:
        logger.error("Format date invalide: %s", report_date)
        return False

    if latest_year is not None and latest_month is not None:
        if year < latest_year or (year == latest_year and month <= latest_month):
            return False

    extracted_data = extract_data_from_pdf(pdf_path)
    confidence = extracted_data.get("confidence_score", 0.5)
    method = extracted_data.get("method", "pdfplumber")

    return data_manager.add_report_data(
        report_date,
        pdf_path,
        extracted_data,
        confidence_score=confidence,
        extraction_method=method,
    )


def force_download_latest_report(data_manager) -> bool:
    pdf_path, report_date = download_latest_report()
    if not pdf_path:
        return False
    extracted_data = extract_data_from_pdf(pdf_path)
    confidence = extracted_data.get("confidence_score", 0.5)
    method = extracted_data.get("method", "pdfplumber")
    return data_manager.add_report_data(
        report_date,
        pdf_path,
        extracted_data,
        confidence_score=confidence,
        extraction_method=method,
    )
