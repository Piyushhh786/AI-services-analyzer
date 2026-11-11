from typing import List, Dict, Any
from app.database.models import TransactionModel
from app.database.repository import repository
from app.core.logging import logger


class DataLoader:
    @staticmethod
    def load(records: List[TransactionModel]) -> int:
        if not records:
            return 0
        inserted_count = repository.insert_transactions(records)
        logger.info(f"Loaded {inserted_count} transaction records into database.")
        return inserted_count
