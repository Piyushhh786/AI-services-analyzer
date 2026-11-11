import re
from typing import Dict, Optional, Tuple, List

# Standard categories based on problem statement
CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Bills",
    "Entertainment",
    "Healthcare",
    "Fitness",
    "Salary",
    "Investment",
    "Others"
]

# Rule-based merchant mapping patterns
MERCHANT_RULES = {
    "Food": [
        "swiggy", "zomato", "mcdonald", "kfc", "domino", "starbucks", "chai point",
        "cafe", "restaurant", "burger", "pizza", "dine", "eats", "subway", "barbeque",
        "biryani", "bakery", "sweet"
    ],
    "Travel": [
        "uber", "ola", "rapido", "irctc", "makemytrip", "goibibo", "fastag", "metro",
        "fuel", "petrol", "diesel", "shell", "hpcl", "bpcl", "ioc", "indigo", "air india",
        "flight", "toll", "redbus", "cleartrip"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "meesho", "nykaa", "ajio", "tata cliq",
        "blinkit", "zepto", "instamart", "bigbasket", "dmart", "reliance retail", "croma"
    ],
    "Bills": [
        "airtel", "jio", "vi", "vodafone", "credit card", "bill", "electricity", "bescom",
        "tneb", "uppcl", "gas", "water", "recharge", "broadband", "rent", "maintenance", "tata play"
    ],
    "Entertainment": [
        "netflix", "spotify", "bookmyshow", "hotstar", "disney", "prime video",
        "youtube", "cinema", "pvr", "inox", "apple music", "steam", "playstation"
    ],
    "Healthcare": [
        "apollo", "1mg", "pharmeasy", "pharmacy", "hospital", "clinic", "dr.",
        "lab", "diagnostic", "medplus", "netmeds"
    ],
    "Fitness": [
        "cult", "cult fit", "cult.fit", "gym", "fitness", "gold gym", "anytime fitness"
    ],
    "Salary": [
        "salary", "payroll", "stipend", "wages", "bonus"
    ]
}


class ColumnMapper:
    DATE_ALIASES = ["date", "txn_date", "txndate", "transaction_date", "trans_date", "timestamp", "time"]
    MERCHANT_ALIASES = ["merchant", "payee", "beneficiary", "narration", "description", "party", "receiver", "to", "vendor"]
    AMOUNT_ALIASES = ["amount", "txn_amount", "amt", "value", "inr", "debit_amount", "transaction_amount"]
    TYPE_ALIASES = ["type", "txn_type", "cr_dr", "d_c", "credit_debit", "transaction_type"]
    CATEGORY_ALIASES = ["category", "cat", "genre", "expense_type"]
    DESCRIPTION_ALIASES = ["description", "remarks", "memo", "notes", "detail"]

    @classmethod
    def detect_columns(cls, columns: List[str]) -> Dict[str, Optional[str]]:
        normalized = {c.strip().lower().replace(" ", "_").replace("-", "_"): c for c in columns}
        mapping = {
            "date": None,
            "merchant": None,
            "amount": None,
            "type": None,
            "category": None,
            "description": None,
        }

        for norm, original in normalized.items():
            if not mapping["date"] and any(alias in norm for alias in cls.DATE_ALIASES):
                mapping["date"] = original
            elif not mapping["amount"] and any(alias in norm for alias in cls.AMOUNT_ALIASES):
                mapping["amount"] = original
            elif not mapping["type"] and any(alias in norm for alias in cls.TYPE_ALIASES):
                mapping["type"] = original
            elif not mapping["category"] and any(alias in norm for alias in cls.CATEGORY_ALIASES):
                mapping["category"] = original
            elif not mapping["merchant"] and any(alias in norm for alias in cls.MERCHANT_ALIASES):
                mapping["merchant"] = original
            elif not mapping["description"] and any(alias in norm for alias in cls.DESCRIPTION_ALIASES):
                mapping["description"] = original

        # Fallbacks if merchant wasn't identified
        if not mapping["merchant"] and mapping["description"]:
            mapping["merchant"] = mapping["description"]

        return mapping

    @classmethod
    def categorize_merchant(cls, merchant_name: str, description: Optional[str] = "", tx_type: str = "DEBIT") -> str:
        text = f"{merchant_name or ''} {description or ''}".lower()

        if tx_type == "CREDIT" and any(k in text for k in ["salary", "payroll", "stipend", "bonus"]):
            return "Salary"

        for category, keywords in MERCHANT_RULES.items():
            for kw in keywords:
                if kw in text:
                    return category

        if tx_type == "CREDIT":
            return "Income"

        return "Others"
