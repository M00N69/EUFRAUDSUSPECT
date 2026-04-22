#!/usr/bin/env python3
"""Script de mise à jour des données — appelé par GitHub Actions ou manuellement."""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_processor import download_latest_report, extract_data_from_pdf
from db_adapter import DataManager


def main():
    logger.info("Début de la mise à jour des données")
    dm = DataManager()
    latest_year, latest_month = dm.get_latest_report_date()
    logger.info("Dernier rapport en base: %s-%s", latest_year, latest_month)

    pdf_path, report_date = download_latest_report()
    if not pdf_path:
        logger.error("Échec du téléchargement: %s", report_date)
        sys.exit(1)

    logger.info("PDF téléchargé: %s (date: %s)", pdf_path, report_date)

    from datetime import datetime

    try:
        date_obj = datetime.strptime(report_date, "%Y-%m")
        year, month = date_obj.year, date_obj.month
    except ValueError:
        logger.error("Format de date invalide: %s", report_date)
        sys.exit(1)

    if latest_year is not None and latest_month is not None:
        if year < latest_year or (year == latest_year and month <= latest_month):
            logger.info("Rapport %s-%s déjà en base, rien à faire", year, month)
            return

    extracted_data = extract_data_from_pdf(pdf_path)
    confidence = extracted_data.get("confidence_score", 0.5)
    method = extracted_data.get("method", "pdfplumber")
    suspicions_count = len(extracted_data.get("suspicions", []))
    logger.info(
        "Extraction: %d suspicions (confiance: %.0f%%)",
        suspicions_count,
        confidence * 100,
    )

    success = dm.add_report_data(
        report_date,
        pdf_path,
        extracted_data,
        confidence_score=confidence,
        extraction_method=method,
    )

    if success:
        logger.info("Mise à jour réussie !")
    else:
        logger.error("Échec de la mise à jour")
        sys.exit(1)


if __name__ == "__main__":
    main()
