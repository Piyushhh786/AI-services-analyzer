import pandas as pd
from typing import Dict, List, Tuple
from app.core.exceptions import CSVValidationException
from app.core.config import settings


class CSVValidator:
    @staticmethod
    def validate_file_size(file_bytes: bytes):
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise CSVValidationException(f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.")
        if len(file_bytes) == 0:
            raise CSVValidationException("Uploaded file is empty.")

    @staticmethod
    def validate_dataframe(df: pd.DataFrame, mapping: Dict[str, str]) -> Tuple[bool, List[str]]:
        errors = []
        if df.empty:
            errors.append("CSV file has no data rows.")
            return False, errors

        # Essential columns: date, amount
        if not mapping.get("date") or mapping["date"] not in df.columns:
            errors.append("Could not locate a valid 'Date' column in the CSV.")

        if not mapping.get("amount") or mapping["amount"] not in df.columns:
            errors.append("Could not locate a valid 'Amount' column in the CSV.")

        if not mapping.get("merchant") and not mapping.get("description"):
            errors.append("Could not locate a 'Merchant' or 'Description' column.")

        return len(errors) == 0, errors
