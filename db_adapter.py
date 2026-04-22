import os
import re
import glob
import sqlite3
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EXTRACTED_DIR = os.path.join(DATA_DIR, "extracted")
CSV_SOURCE = os.path.join(os.path.dirname(__file__), "VISIPILOT veille Food Fraud .csv")
DB_PATH = os.path.join(DATA_DIR, "database.sqlite")

SCHEMA_REPORTS = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL,
    report_year INTEGER,
    report_month INTEGER,
    file_path TEXT,
    total_suspicions INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0.0,
    extraction_method TEXT DEFAULT '',
    date_added TEXT
)
"""

SCHEMA_SUSPICIONS = """
CREATE TABLE IF NOT EXISTS suspicions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER,
    source_id TEXT,
    classification TEXT DEFAULT '',
    product_category TEXT,
    commodity TEXT,
    issue TEXT,
    origin TEXT,
    notified_by TEXT DEFAULT '',
    fraud_type TEXT,
    fraud_category TEXT DEFAULT '',
    link_source TEXT DEFAULT '',
    FOREIGN KEY (report_id) REFERENCES reports(id)
)
"""

SCHEMA_EXTRACTION_LOGS = """
CREATE TABLE IF NOT EXISTS extraction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT,
    method TEXT,
    extracted_count INTEGER DEFAULT 0,
    announced_count INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0.0,
    timestamp TEXT
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_reports_ym ON reports(report_year, report_month)",
    "CREATE INDEX IF NOT EXISTS idx_suspicions_rid ON suspicions(report_id)",
    "CREATE INDEX IF NOT EXISTS idx_suspicions_cat ON suspicions(product_category)",
    "CREATE INDEX IF NOT EXISTS idx_suspicions_ft ON suspicions(fraud_type)",
    "CREATE INDEX IF NOT EXISTS idx_suspicions_origin ON suspicions(origin)",
]

MONTH_FR_TO_NUM = {
    "janv": 1,
    "févr": 2,
    "mars": 3,
    "avr": 4,
    "mai": 5,
    "juin": 6,
    "juil": 7,
    "août": 8,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "déc": 12,
    "janvier": 1,
    "février": 2,
    "avril": 4,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}


def _init_db(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(SCHEMA_REPORTS)
    c.execute(SCHEMA_SUSPICIONS)
    c.execute(SCHEMA_EXTRACTION_LOGS)
    for idx in INDEXES:
        c.execute(idx)
    conn.commit()
    conn.close()
    logger.info("Base de données initialisée: %s", db_path)


def _parse_csv_month(mois_str: str) -> int:
    if not mois_str or not isinstance(mois_str, str):
        return 1
    cleaned = mois_str.strip().lower().rstrip(".")
    return MONTH_FR_TO_NUM.get(cleaned, 1)


def _load_csv_source(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        logger.warning("CSV source introuvable: %s", csv_path)
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="latin-1")
    except Exception:
        try:
            df = pd.read_csv(csv_path, sep=",", encoding="utf-8-sig")
        except Exception as e:
            logger.error("Impossible de lire le CSV source: %s", e)
            return pd.DataFrame()

    COL_PATTERNS = {
        r"^ID$": "source_id",
        r"Ann": "year",
        r"Mois": "month_str",
        r"Date": "date_raw",
        r"Pays": "origin",
        r"CATPROD": "product_category",
        r"Produit": "commodity",
        r"CATFRAU": "fraud_type",
        r"OBJETFRAU": "issue",
        r"LINKSOURCE": "link_source",
    }
    actual_rename = {}
    for col in df.columns:
        cleaned_col = col.strip().lstrip("\ufeff")
        for pattern, target in COL_PATTERNS.items():
            if re.match(pattern, cleaned_col, re.IGNORECASE):
                actual_rename[col] = target
                break
    df = df.rename(columns=actual_rename)

    drop_cols = [c for c in df.columns if c.startswith("Unnamed")]
    df = df.drop(columns=drop_cols, errors="ignore")

    if "date_raw" in df.columns:
        df["_parsed_year"] = pd.to_datetime(
            df["date_raw"], format="%d/%m/%Y", errors="coerce"
        ).dt.year
        df["_parsed_month"] = pd.to_datetime(
            df["date_raw"], format="%d/%m/%Y", errors="coerce"
        ).dt.month

    if "_parsed_year" in df.columns and df["_parsed_year"].notna().any():
        df["report_year"] = df["_parsed_year"].astype("Int64")
    elif "year" in df.columns:
        df["report_year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "_parsed_month" in df.columns and df["_parsed_month"].notna().any():
        df["report_month"] = df["_parsed_month"].astype("Int64")
    elif "month_str" in df.columns:
        df["report_month"] = df["month_str"].apply(_parse_csv_month)
    if "report_year" in df.columns and "report_month" in df.columns:
        df["report_date"] = df.apply(
            lambda r: (
                f"{int(r['report_year']):04d}-{int(r['report_month']):02d}"
                if pd.notna(r["report_year"])
                else ""
            ),
            axis=1,
        )

    if "source_id" not in df.columns:
        df["source_id"] = ""
    if "classification" not in df.columns:
        df["classification"] = ""
    if "notified_by" not in df.columns:
        df["notified_by"] = ""
    if "fraud_category" not in df.columns:
        df["fraud_category"] = df.get("fraud_type", "")

    required = [
        "source_id",
        "product_category",
        "commodity",
        "issue",
        "origin",
        "fraud_type",
        "report_date",
        "report_year",
        "report_month",
        "classification",
        "notified_by",
        "fraud_category",
        "link_source",
    ]
    for col in required:
        if col not in df.columns:
            df[col] = ""

    df = df[required].copy()
    df = df.dropna(subset=["product_category", "issue"], how="all")
    logger.info("CSV source chargé: %d lignes", len(df))
    return df


def _load_extracted_csvs(extracted_dir: str) -> pd.DataFrame:
    if not os.path.exists(extracted_dir):
        return pd.DataFrame()
    pattern = os.path.join(extracted_dir, "report_*.csv")
    csv_files = sorted(glob.glob(pattern))
    if not csv_files:
        return pd.DataFrame()
    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, encoding="utf-8")
            dfs.append(df)
        except Exception as e:
            logger.warning("Erreur lecture %s: %s", f, e)
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    logger.info(
        "CSV extraits chargés: %d lignes depuis %d fichiers",
        len(combined),
        len(csv_files),
    )
    return combined


def _rebuild_db_from_dataframes(db_path: str, *dataframes: pd.DataFrame) -> None:
    _init_db(db_path)
    conn = sqlite3.connect(db_path)
    all_dfs = [df for df in dataframes if not df.empty]
    if not all_dfs:
        conn.close()
        return
    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.dropna(subset=["product_category", "issue"], how="all")
    combined = combined.drop_duplicates(
        subset=["product_category", "commodity", "issue", "origin"],
        keep="last",
    )
    if "report_date" in combined.columns:
        for report_date in combined["report_date"].dropna().unique():
            report_data = combined[combined["report_date"] == report_date]
            try:
                year = int(float(str(report_data["report_year"].iloc[0])))
            except (ValueError, TypeError, IndexError):
                year = 0
            try:
                month = int(float(str(report_data["report_month"].iloc[0])))
            except (ValueError, TypeError, IndexError):
                month = 0
            c = conn.cursor()
            c.execute(
                "SELECT id FROM reports WHERE report_year = ? AND report_month = ?",
                (year, month),
            )
            existing = c.fetchone()
            if existing:
                report_id = existing[0]
            else:
                c.execute(
                    "INSERT INTO reports (report_date, report_year, report_month, total_suspicions, date_added) VALUES (?, ?, ?, ?, ?)",
                    (
                        report_date,
                        year,
                        month,
                        len(report_data),
                        datetime.now().isoformat(),
                    ),
                )
                report_id = c.lastrowid
            for _, row in report_data.iterrows():
                c.execute(
                    "INSERT INTO suspicions (report_id, source_id, classification, product_category, commodity, issue, origin, notified_by, fraud_type, fraud_category, link_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        report_id,
                        str(row.get("source_id", "")),
                        str(row.get("classification", "")),
                        str(row.get("product_category", "")),
                        str(row.get("commodity", "")),
                        str(row.get("issue", "")),
                        str(row.get("origin", "")),
                        str(row.get("notified_by", "")),
                        str(row.get("fraud_type", "")),
                        str(row.get("fraud_category", "")),
                        str(row.get("link_source", "")),
                    ),
                )
        conn.commit()
    conn.close()
    logger.info("Base reconstruite: %d entrées", len(combined))


class DataManager:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        self.csv_source = CSV_SOURCE
        self.extracted_dir = EXTRACTED_DIR
        self._data: pd.DataFrame | None = None
        self._ensure_and_load()

    def _ensure_and_load(self) -> None:
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
                logger.info("Ancienne base supprimee, reconstruction propre")
            except Exception:
                pass

        csv_df = _load_csv_source(self.csv_source)
        extracted_df = _load_extracted_csvs(self.extracted_dir)
        _rebuild_db_from_dataframes(self.db_path, csv_df, extracted_df)

        self._load_data()

    def _load_data(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            query = """
            SELECT s.*, r.report_date as date, r.report_year as year,
                   r.report_month as month, r.total_suspicions
            FROM suspicions s
            JOIN reports r ON s.report_id = r.id
            """
            self._data = pd.read_sql(query, conn)
        except Exception as e:
            logger.error("Erreur chargement données: %s", e)
            self._data = pd.DataFrame()
        finally:
            conn.close()

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None or self._data.empty:
            self._ensure_and_load()
        return self._data

    def reload(self) -> None:
        self._data = None
        self._ensure_and_load()

    def get_available_dates(self) -> list[str]:
        if self._data is None or self._data.empty or "date" not in self._data.columns:
            return []
        dates = sorted(d for d in self._data["date"].dropna().unique() if d)
        return dates

    def get_product_categories(self) -> list[str]:
        if (
            self._data is None
            or self._data.empty
            or "product_category" not in self._data.columns
        ):
            return []
        cats = [c for c in self._data["product_category"].dropna().unique() if c]
        return sorted(cats)

    def get_fraud_types(self) -> list[str]:
        if (
            self._data is None
            or self._data.empty
            or "fraud_type" not in self._data.columns
        ):
            return []
        types = [t for t in self._data["fraud_type"].dropna().unique() if t]
        return sorted(types)

    def get_origins(self) -> list[str]:
        if self._data is None or self._data.empty or "origin" not in self._data.columns:
            return []
        origins = [o for o in self._data["origin"].dropna().unique() if o]
        return sorted(origins)

    def filter_data(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        categories: list[str] | None = None,
        fraud_types: list[str] | None = None,
        origins: list[str] | None = None,
    ) -> pd.DataFrame:
        if self._data is None or self._data.empty:
            return pd.DataFrame()
        filtered = self._data.copy()
        if start_date and end_date and "date" in filtered.columns:
            filtered = filtered[
                (filtered["date"] >= start_date) & (filtered["date"] <= end_date)
            ]
        if categories and "product_category" in filtered.columns:
            filtered = filtered[filtered["product_category"].isin(categories)]
        if fraud_types and "fraud_type" in filtered.columns:
            filtered = filtered[filtered["fraud_type"].isin(fraud_types)]
        if origins and "origin" in filtered.columns:
            filtered = filtered[filtered["origin"].isin(origins)]
        return filtered

    def add_report_data(
        self,
        report_date: str,
        file_path: str,
        extracted_data: dict,
        confidence_score: float = 0.0,
        extraction_method: str = "pdfplumber",
    ) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            date_obj = datetime.strptime(report_date, "%Y-%m")
            year, month = date_obj.year, date_obj.month

            c.execute(
                "SELECT id FROM reports WHERE report_year = ? AND report_month = ?",
                (year, month),
            )
            existing = c.fetchone()

            suspicions = extracted_data.get("suspicions", [])
            valid_suspicions = [
                s
                for s in suspicions
                if s.get("product_category", "").strip() and s.get("issue", "").strip()
            ]

            if existing:
                report_id = existing[0]
                c.execute(
                    "UPDATE reports SET file_path=?, total_suspicions=?, confidence_score=?, extraction_method=?, date_added=? WHERE id=?",
                    (
                        file_path,
                        len(valid_suspicions),
                        confidence_score,
                        extraction_method,
                        datetime.now().isoformat(),
                        report_id,
                    ),
                )
                c.execute("DELETE FROM suspicions WHERE report_id = ?", (report_id,))
            else:
                c.execute(
                    "INSERT INTO reports (report_date, report_year, report_month, file_path, total_suspicions, confidence_score, extraction_method, date_added) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        report_date,
                        year,
                        month,
                        file_path,
                        len(valid_suspicions),
                        confidence_score,
                        extraction_method,
                        datetime.now().isoformat(),
                    ),
                )
                report_id = c.lastrowid

            for susp in valid_suspicions:
                c.execute(
                    "INSERT INTO suspicions (report_id, source_id, classification, product_category, commodity, issue, origin, notified_by, fraud_type, fraud_category, link_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        report_id,
                        susp.get("source_id", ""),
                        susp.get("classification", ""),
                        susp.get("product_category", ""),
                        susp.get("commodity", ""),
                        susp.get("issue", ""),
                        susp.get("origin", ""),
                        susp.get("notified_by", ""),
                        susp.get("fraud_type", ""),
                        susp.get("fraud_category", susp.get("fraud_type", "")),
                        susp.get("link_source", ""),
                    ),
                )

            c.execute(
                "INSERT INTO extraction_logs (report_date, method, extracted_count, announced_count, confidence_score, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    report_date,
                    extraction_method,
                    len(valid_suspicions),
                    extracted_data.get("total_suspicions", 0),
                    confidence_score,
                    datetime.now().isoformat(),
                ),
            )

            csv_path = os.path.join(self.extracted_dir, f"report_{report_date}.csv")
            os.makedirs(self.extracted_dir, exist_ok=True)
            pd.DataFrame(valid_suspicions).to_csv(
                csv_path, index=False, encoding="utf-8"
            )

            conn.commit()
            logger.info(
                "Rapport %s ajouté: %d suspicions (confiance: %.1f%%)",
                report_date,
                len(valid_suspicions),
                confidence_score * 100,
            )
        except Exception as e:
            conn.rollback()
            logger.error("Erreur ajout rapport: %s", e)
            return False
        finally:
            conn.close()

        self._load_data()
        return True

    def check_report_exists(self, year: int, month: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM reports WHERE report_year = ? AND report_month = ?",
            (year, month),
        )
        count = c.fetchone()[0]
        conn.close()
        return count > 0

    def get_latest_report_date(self) -> tuple[int | None, int | None]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "SELECT report_year, report_month FROM reports ORDER BY report_year DESC, report_month DESC LIMIT 1"
        )
        result = c.fetchone()
        conn.close()
        if result:
            return result[0], result[1]
        return None, None

    def get_extraction_logs(self) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        try:
            return pd.read_sql(
                "SELECT * FROM extraction_logs ORDER BY timestamp DESC", conn
            )
        except Exception:
            return pd.DataFrame()
        finally:
            conn.close()

    def reset_database(self) -> bool:
        if os.path.exists(self.db_path):
            try:
                os.rename(self.db_path, self.db_path + ".backup")
            except Exception:
                os.remove(self.db_path)
        self._data = pd.DataFrame()
        csv_df = _load_csv_source(self.csv_source)
        extracted_df = _load_extracted_csvs(self.extracted_dir)
        _rebuild_db_from_dataframes(self.db_path, csv_df, extracted_df)
        self._load_data()
        return True
