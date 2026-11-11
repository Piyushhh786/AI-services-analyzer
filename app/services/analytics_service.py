from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.database.repository import repository
from app.utils.sql_helpers import format_currency_inr
from app.core.logging import logger


def _safe_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None)
    if isinstance(val, str):
        try:
            # Try ISO format
            clean_str = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            return dt.replace(tzinfo=None)
        except Exception:
            try:
                return datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    return datetime.strptime(val[:10], "%Y-%m-%d")
                except Exception:
                    return None
    return None


class AnalyticsService:
    @staticmethod
    def get_spending_analytics(
        session_id: str,
        time_range: Optional[str] = "all",
        category: Optional[str] = None,
        tx_type: Optional[str] = None,
        merchant_search: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates complete financial metrics, category breakdowns, merchant rankings,
        time trends, and executive insights based on the active filters.
        """
        # Fetch all records for the session
        raw_query = "SELECT * FROM transactions WHERE session_id = %s" if repository.db.is_postgres else "SELECT * FROM transactions WHERE session_id = ?"
        all_rows = repository.execute_read_query(session_id, raw_query, [session_id])

        if not all_rows:
            return {
                "summary": {
                    "total_income": 0.0,
                    "total_expense": 0.0,
                    "net_savings": 0.0,
                    "transaction_count": 0,
                    "debit_count": 0,
                    "credit_count": 0,
                    "avg_expense": 0.0,
                    "highest_expense": 0.0,
                    "highest_expense_merchant": "N/A"
                },
                "category_breakdown": [],
                "top_merchants": [],
                "most_frequent_merchant": None,
                "highest_spend_merchant": None,
                "spending_over_time": [],
                "recent_transactions": [],
                "insights": ["No transaction records found for this session."],
                "applied_filters": {
                    "time_range": time_range,
                    "category": category,
                    "type": tx_type,
                    "merchant_search": merchant_search
                },
                "statement_meta": {
                    "min_date": None,
                    "max_date": None,
                    "min_date_formatted": None,
                    "max_date_formatted": None,
                    "total_records": 0,
                    "filtered_records": 0,
                    "available_months": [],
                    "active_filter_label": "No Data",
                    "is_empty": True
                }
            }

        # Determine reference date for relative filters
        dates = [_safe_dt(r["transaction_date"]) for r in all_rows if _safe_dt(r["transaction_date"])]
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else datetime.utcnow()

        # Compute available statement months
        month_counts = {}
        for r in all_rows:
            d = _safe_dt(r.get("transaction_date"))
            if d:
                mk = d.strftime("%Y-%m")
                month_counts[mk] = month_counts.get(mk, 0) + 1

        available_months = []
        for mk in sorted(month_counts.keys(), reverse=True):
            try:
                m_obj = datetime.strptime(mk, "%Y-%m")
                m_label = m_obj.strftime("%B %Y")
            except Exception:
                m_label = mk
            available_months.append({
                "key": f"month:{mk}",
                "month": mk,
                "label": m_label,
                "count": month_counts[mk]
            })

        # Compute date cutoffs and human-readable label based on time_range
        cutoff_start = None
        cutoff_end = None
        exact_month_filter = None
        filter_label = "Full Statement Period"

        tr = (time_range or "all").lower().strip()
        now_dt = datetime.utcnow()

        if tr == "all":
            filter_label = "Full Statement Period"
        elif tr in ["now_7d", "real_7d", "today_7d"]:
            cutoff_start = now_dt - timedelta(days=7)
            filter_label = f"Real-Time: Last 7 Days from Today ({cutoff_start.strftime('%d %b %Y')} - {now_dt.strftime('%d %b %Y')})"
        elif tr in ["now_30d", "real_30d", "today_30d"]:
            cutoff_start = now_dt - timedelta(days=30)
            filter_label = f"Real-Time: Last 30 Days from Today ({cutoff_start.strftime('%d %b %Y')} - {now_dt.strftime('%d %b %Y')})"
        elif tr in ["7d", "statement_7d"]:
            cutoff_start = max_date - timedelta(days=7)
            cutoff_end = max_date.replace(hour=23, minute=59, second=59)
            filter_label = f"Statement: Last 7 Days ({cutoff_start.strftime('%d %b %Y')} - {max_date.strftime('%d %b %Y')})"
        elif tr in ["30d", "statement_30d"]:
            cutoff_start = max_date - timedelta(days=30)
            cutoff_end = max_date.replace(hour=23, minute=59, second=59)
            filter_label = f"Statement: Last 30 Days ({cutoff_start.strftime('%d %b %Y')} - {max_date.strftime('%d %b %Y')})"
        elif tr in ["last_month", "statement_month"]:
            if available_months:
                exact_month_filter = available_months[0]["month"]
                filter_label = f"Statement: Last Month ({available_months[0]['label']})"
            else:
                cutoff_start = max_date - timedelta(days=30)
                cutoff_end = max_date.replace(hour=23, minute=59, second=59)
                filter_label = f"Statement: Last 30 Days"
        elif tr.startswith("month:"):
            exact_month_filter = tr.replace("month:", "").strip()
            matching_m = next((m for m in available_months if m["month"] == exact_month_filter), None)
            filter_label = matching_m["label"] if matching_m else f"Month {exact_month_filter}"
        elif tr in ["90d", "3m"]:
            cutoff_start = max_date - timedelta(days=90)
            cutoff_end = max_date.replace(hour=23, minute=59, second=59)
            filter_label = f"Statement: Last 90 Days ({cutoff_start.strftime('%d %b %Y')} - {max_date.strftime('%d %b %Y')})"
        elif tr in ["180d", "6m"]:
            cutoff_start = max_date - timedelta(days=180)
            cutoff_end = max_date.replace(hour=23, minute=59, second=59)
            filter_label = f"Statement: Last 6 Months ({cutoff_start.strftime('%d %b %Y')} - {max_date.strftime('%d %b %Y')})"

        s_dt = _safe_dt(start_date) if start_date else None
        e_dt = _safe_dt(end_date) if end_date else None
        if e_dt:
            # include entire end day
            e_dt = e_dt.replace(hour=23, minute=59, second=59)

        # Filter in memory for maximum speed and flexibility
        filtered_rows = []
        for r in all_rows:
            dt = _safe_dt(r["transaction_date"])

            # Exact month filter (e.g. month:2024-06)
            if exact_month_filter and dt:
                if dt.strftime("%Y-%m") != exact_month_filter:
                    continue

            # Date range filtering
            if cutoff_start and dt and dt < cutoff_start:
                continue

            if cutoff_end and dt and dt > cutoff_end:
                continue

            if s_dt and dt and dt < s_dt:
                continue

            if e_dt and dt and dt > e_dt:
                continue

            # Category filtering
            if category and category.lower() != "all" and str(r.get("category", "")).lower() != category.lower():
                continue

            # Type filtering
            if tx_type and tx_type.upper() != "ALL" and str(r.get("type", "")).upper() != tx_type.upper():
                continue

            # Merchant search filtering
            if merchant_search and merchant_search.strip():
                ms = merchant_search.strip().lower()
                m_name = str(r.get("merchant", "")).lower()
                d_name = str(r.get("description", "")).lower() if r.get("description") else ""
                if ms not in m_name and ms not in d_name:
                    continue

            filtered_rows.append(r)

        # Calculate metrics
        total_income = sum(float(r["amount"]) for r in filtered_rows if r["type"] == "CREDIT")
        total_expense = sum(float(r["amount"]) for r in filtered_rows if r["type"] == "DEBIT")
        net_savings = total_income - total_expense
        debit_rows = [r for r in filtered_rows if r["type"] == "DEBIT"]
        debit_count = len(debit_rows)
        credit_count = sum(1 for r in filtered_rows if r["type"] == "CREDIT")
        avg_expense = (total_expense / debit_count) if debit_count > 0 else 0.0

        # Highest single expense
        highest_expense = 0.0
        highest_expense_merchant = "N/A"
        if debit_rows:
            sorted_by_amount = sorted(debit_rows, key=lambda x: float(x["amount"]), reverse=True)
            highest_expense = float(sorted_by_amount[0]["amount"])
            highest_expense_merchant = sorted_by_amount[0]["merchant"]

        # Category Breakdown (DEBITS only for expenditure breakdown)
        category_map = {}
        for r in debit_rows:
            cat = r["category"] or "Others"
            category_map[cat] = category_map.get(cat, 0.0) + float(r["amount"])

        category_breakdown = [
            {
                "category": cat,
                "amount": round(amt, 2),
                "percentage": round((amt / total_expense * 100), 1) if total_expense > 0 else 0.0
            }
            for cat, amt in sorted(category_map.items(), key=lambda x: x[1], reverse=True)
        ]

        # Merchant Analysis (DEBITS)
        merchant_spend = {}
        merchant_counts = {}
        for r in debit_rows:
            m = r["merchant"] or "Unknown"
            merchant_spend[m] = merchant_spend.get(m, 0.0) + float(r["amount"])
            merchant_counts[m] = merchant_counts.get(m, 0) + 1

        top_merchants = [
            {
                "merchant": m,
                "amount": round(merchant_spend[m], 2),
                "count": merchant_counts[m],
                "avg_per_txn": round(merchant_spend[m] / merchant_counts[m], 2)
            }
            for m in sorted(merchant_spend.keys(), key=lambda k: merchant_spend[k], reverse=True)[:10]
        ]

        most_frequent_merchant = None
        if merchant_counts:
            mf_name = max(merchant_counts.keys(), key=lambda k: merchant_counts[k])
            most_frequent_merchant = {
                "merchant": mf_name,
                "count": merchant_counts[mf_name],
                "total_spend": round(merchant_spend[mf_name], 2)
            }

        highest_spend_merchant = None
        if merchant_spend:
            hs_name = max(merchant_spend.keys(), key=lambda k: merchant_spend[k])
            highest_spend_merchant = {
                "merchant": hs_name,
                "total_spend": round(merchant_spend[hs_name], 2),
                "count": merchant_counts[hs_name]
            }

        # Spending Over Time (Daily / Monthly buckets)
        time_buckets = {}
        for r in filtered_rows:
            dt_str = str(r["transaction_date"])
            try:
                date_key = dt_str[:7] if time_range in ["180d", "6m", "all"] else dt_str[:10]
            except Exception:
                date_key = "Other"

            if date_key not in time_buckets:
                time_buckets[date_key] = {"date": date_key, "expense": 0.0, "income": 0.0}

            if r["type"] == "DEBIT":
                time_buckets[date_key]["expense"] += float(r["amount"])
            else:
                time_buckets[date_key]["income"] += float(r["amount"])

        spending_over_time = [
            {
                "date": k,
                "expense": round(v["expense"], 2),
                "income": round(v["income"], 2)
            }
            for k, v in sorted(time_buckets.items(), key=lambda x: x[0])
        ]

        # Executive AI Insights Generation
        insights = []
        if total_income > 0:
            savings_rate = round((net_savings / total_income) * 100, 1)
            insights.append(f"Net savings rate is {savings_rate}% ({format_currency_inr(net_savings)} saved from {format_currency_inr(total_income)} total income).")

        if category_breakdown:
            top_cat = category_breakdown[0]
            insights.append(f"Top expenditure category is **{top_cat['category']}**, accounting for {top_cat['percentage']}% ({format_currency_inr(top_cat['amount'])}) of total expenses.")
            if len(category_breakdown) > 1:
                second_cat = category_breakdown[1]
                ratio = round(top_cat["amount"] / second_cat["amount"], 1) if second_cat["amount"] > 0 else 1
                if ratio > 1.2:
                    insights.append(f"Spending on {top_cat['category']} is {ratio}x higher than on {second_cat['category']}.")

        if most_frequent_merchant:
            insights.append(f"**{most_frequent_merchant['merchant']}** was your most frequently used merchant ({most_frequent_merchant['count']} transactions).")

        if highest_expense > 0:
            insights.append(f"Single largest debit was {format_currency_inr(highest_expense)} at **{highest_expense_merchant}**.")

        # Weekend vs Weekday analysis
        weekend_spend = 0.0
        weekday_spend = 0.0
        for r in debit_rows:
            dt = _safe_dt(r.get("transaction_date"))
            if dt:
                if dt.weekday() >= 5:  # Saturday or Sunday
                    weekend_spend += float(r["amount"])
                else:
                    weekday_spend += float(r["amount"])

        if weekend_spend + weekday_spend > 0:
            wknd_pct = round((weekend_spend / (weekend_spend + weekday_spend)) * 100, 1)
            if wknd_pct > 35:
                insights.append(f"Weekend spending was elevated: {wknd_pct}% of debit volume occurred during Saturdays & Sundays.")

        if not filtered_rows:
            date_range_str = f"{min_date.strftime('%d %b %Y')} to {max_date.strftime('%d %b %Y')}" if (min_date and max_date) else "uploaded period"
            insights.append(
                f"No transactions found matching filter '{filter_label}'. Note: The uploaded statement covers {date_range_str} ({len(all_rows)} total transactions)."
            )

        # Recent transactions preview (latest 50)
        sorted_recent = sorted(filtered_rows, key=lambda x: str(x["transaction_date"]), reverse=True)[:50]
        recent_transactions = [
            {
                "id": r.get("id"),
                "date": str(r["transaction_date"])[:10],
                "merchant": r["merchant"],
                "category": r["category"],
                "amount": float(r["amount"]),
                "type": r["type"],
                "description": r.get("description")
            }
            for r in sorted_recent
        ]

        statement_meta = {
            "min_date": min_date.strftime("%Y-%m-%d") if min_date else None,
            "max_date": max_date.strftime("%Y-%m-%d") if max_date else None,
            "min_date_formatted": min_date.strftime("%d %b %Y") if min_date else None,
            "max_date_formatted": max_date.strftime("%d %b %Y") if max_date else None,
            "total_records": len(all_rows),
            "filtered_records": len(filtered_rows),
            "available_months": available_months,
            "active_filter_label": filter_label,
            "is_empty": len(filtered_rows) == 0,
        }

        return {
            "summary": {
                "total_income": round(total_income, 2),
                "total_expense": round(total_expense, 2),
                "net_savings": round(net_savings, 2),
                "transaction_count": len(filtered_rows),
                "debit_count": debit_count,
                "credit_count": credit_count,
                "avg_expense": round(avg_expense, 2),
                "highest_expense": round(highest_expense, 2),
                "highest_expense_merchant": highest_expense_merchant
            },
            "category_breakdown": category_breakdown,
            "top_merchants": top_merchants,
            "most_frequent_merchant": most_frequent_merchant,
            "highest_spend_merchant": highest_spend_merchant,
            "spending_over_time": spending_over_time,
            "recent_transactions": recent_transactions,
            "insights": insights,
            "applied_filters": {
                "time_range": time_range,
                "category": category,
                "type": tx_type,
                "merchant_search": merchant_search
            },
            "statement_meta": statement_meta
        }
