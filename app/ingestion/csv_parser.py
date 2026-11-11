import io
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
from app.ingestion.column_mapper import ColumnMapper
from app.ingestion.csv_validator import CSVValidator
from app.database.models import TransactionModel
from app.core.exceptions import CSVValidationException
from app.core.logging import logger


class CSVParser:
    @staticmethod
    def parse(file_content: bytes, session_id: str, custom_mapping: Dict[str, str] = None) -> Tuple[List[TransactionModel], Dict[str, Any]]:
        CSVValidator.validate_file_size(file_content)

        # Detect encoding
        df = None
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                break
            except Exception:
                continue

        if df is None:
            raise CSVValidationException("Failed to decode CSV file with supported encodings (UTF-8, Latin-1).")

        # Strip whitespace from headers
        df.columns = [str(c).strip() for c in df.columns]

        # Column mapping
        detected_mapping = ColumnMapper.detect_columns(list(df.columns))
        if custom_mapping:
            for k, v in custom_mapping.items():
                if v and v in df.columns:
                    detected_mapping[k] = v

        is_valid, errors = CSVValidator.validate_dataframe(df, detected_mapping)
        if not is_valid:
            raise CSVValidationException("; ".join(errors))

        date_col = detected_mapping["date"]
        amount_col = detected_mapping["amount"]
        merchant_col = detected_mapping["merchant"] or detected_mapping["description"]
        type_col = detected_mapping["type"]
        category_col = detected_mapping["category"]
        desc_col = detected_mapping["description"]

        # Drop rows where essential columns are NaN
        df = df.dropna(subset=[date_col, amount_col])

        # Clean Amount
        def clean_amount(val):
            if pd.isna(val):
                return 0.0
            if isinstance(val, (int, float)):
                return float(abs(val))
            # Remove currency symbols (₹, $, commas, whitespace)
            clean_str = re.sub(r"[^\d.-]", "", str(val))
            try:
                return float(abs(float(clean_str)))
            except ValueError:
                return 0.0

        df["_parsed_amount"] = df[amount_col].apply(clean_amount)

        # Parse Dates
        df["_parsed_date"] = pd.to_datetime(df[date_col], errors="coerce")
        # Drop rows where date could not be parsed
        df = df.dropna(subset=["_parsed_date"])

        # Determine transaction type (DEBIT or CREDIT)
        def determine_type(row):
            if type_col and type_col in row and pd.notna(row[type_col]):
                raw_type = str(row[type_col]).strip().upper()
                if "CR" in raw_type or "INCOME" in raw_type or "DEPOSIT" in raw_type:
                    return "CREDIT"
                return "DEBIT"
            
            # Check if amount column or merchant indicates salary/credit
            merchant_text = str(row.get(merchant_col, "")).lower()
            if "salary" in merchant_text or "refund" in merchant_text or "cashback" in merchant_text:
                return "CREDIT"
            return "DEBIT"

        df["_parsed_type"] = df.apply(determine_type, axis=1)

        # Build records
        records: List[TransactionModel] = []
        canonical_cols = {date_col, amount_col, merchant_col, type_col, category_col, desc_col, "_parsed_amount", "_parsed_date", "_parsed_type"}

        for _, row in df.iterrows():
            m_val = str(row.get(merchant_col, "Unknown")).strip()
            d_val = str(row.get(desc_col, "")).strip() if desc_col else ""
            
            # Category: use existing if valid, otherwise rule-based categorization
            if category_col and pd.notna(row.get(category_col)) and str(row.get(category_col)).strip():
                cat = str(row[category_col]).strip()
            else:
                cat = ColumnMapper.categorize_merchant(m_val, d_val, row["_parsed_type"])

            # Extra data
            extra = {}
            for col in df.columns:
                if col not in canonical_cols and pd.notna(row[col]):
                    extra[col] = str(row[col])

            records.append(
                TransactionModel(
                    session_id=session_id,
                    transaction_date=row["_parsed_date"].to_pydatetime(),
                    merchant=m_val if m_val else "Unknown",
                    category=cat,
                    amount=row["_parsed_amount"],
                    type=row["_parsed_type"],
                    description=d_val if d_val else None,
                    extra_data=extra
                )
            )

        summary = {
            "total_records": len(records),
            "debit_count": sum(1 for r in records if r.type == "DEBIT"),
            "credit_count": sum(1 for r in records if r.type == "CREDIT"),
            "columns_detected": list(df.columns),
            "mapping": detected_mapping,
            "date_range_start": df["_parsed_date"].min().strftime("%Y-%m-%d") if not df.empty else None,
            "date_range_end": df["_parsed_date"].max().strftime("%Y-%m-%d") if not df.empty else None,
        }

        return records, summary
