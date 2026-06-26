import requests
from app.core.limiter import em_get, eastmoney_datacenter
from app.services.base import clean_code

class CapitalService:
    @staticmethod
    def get_margin_trading(code: str, page_size: int = 30) -> list[dict]:
        """
        Retrieves historical margin trading, buying and short selling details.
        """
        cleaned = clean_code(code)
        data = eastmoney_datacenter(
            "RPTA_WEB_RZRQ_GGMX",
            filter_str=f'(SCODE="{cleaned}")',
            page_size=page_size,
            sort_columns="DATE", sort_types="-1",
        )
        rows = []
        for row in data:
            rows.append({
                "date": str(row.get("DATE", ""))[:10],
                "rzye": row.get("RZYE", 0.0),       # Margin balance (RMB)
                "rzmre": row.get("RZMRE", 0.0),     # Margin buy amount
                "rzche": row.get("RZCHE", 0.0),     # Margin repayment amount
                "rqye": row.get("RQYE", 0.0),       # Short balance (RMB)
                "rqmcl": row.get("RQMCL", 0.0),     # Short sell volume
                "rqchl": row.get("RQCHL", 0.0),     # Short repayment volume
                "rzrqye": row.get("RZRQYE", 0.0),   # Combined margin and short balance
            })
        return rows

    @staticmethod
    def get_block_trade(code: str, page_size: int = 20) -> list[dict]:
        """
        Retrieves institutional/major block trade transaction history.
        """
        cleaned = clean_code(code)
        data = eastmoney_datacenter(
            "RPT_DATA_BLOCKTRADE",
            filter_str=f'(SECURITY_CODE="{cleaned}")',
            page_size=page_size,
            sort_columns="TRADE_DATE", sort_types="-1",
        )
        rows = []
        for row in data:
            close = row.get("CLOSE_PRICE") or 0.0
            deal_price = row.get("DEAL_PRICE") or 0.0
            premium = ((deal_price / close - 1) * 100) if close else 0.0
            rows.append({
                "date": str(row.get("TRADE_DATE", ""))[:10],
                "price": deal_price,
                "close": close,
                "premium_pct": round(premium, 2),
                "vol": row.get("DEAL_VOLUME", 0),
                "amount": row.get("DEAL_AMT", 0.0),
                "buyer": row.get("BUYER_NAME", ""),
                "seller": row.get("SELLER_NAME", ""),
            })
        return rows

    @staticmethod
    def get_holder_num_change(code: str, page_size: int = 10) -> list[dict]:
        """
        Retrieves shareholders concentration trends and sequential percentage changes.
        """
        cleaned = clean_code(code)
        data = eastmoney_datacenter(
            "RPT_HOLDERNUMLATEST",
            filter_str=f'(SECURITY_CODE="{cleaned}")',
            page_size=page_size,
            sort_columns="END_DATE", sort_types="-1",
        )
        rows = []
        for row in data:
            rows.append({
                "date": str(row.get("END_DATE", ""))[:10],
                "holder_num": row.get("HOLDER_NUM", 0),
                "change_num": row.get("HOLDER_NUM_CHANGE", 0),
                "change_ratio": row.get("HOLDER_NUM_RATIO", 0.0),  # Sequential change ratio (%)
                "avg_shares": row.get("AVG_FREE_SHARES", 0.0),     # Avg shares per household
            })
        return rows

    @staticmethod
    def get_dividend_history(code: str, page_size: int = 20) -> list[dict]:
        """
        Retrieves historical dividend payout records and stock splits/capital bonus schemes.
        """
        cleaned = clean_code(code)
        data = eastmoney_datacenter(
            "RPT_SHAREBONUS_DET",
            filter_str=f'(SECURITY_CODE="{cleaned}")',
            page_size=page_size,
            sort_columns="EX_DIVIDEND_DATE", sort_types="-1",
        )
        rows = []
        for row in data:
            rows.append({
                "date": str(row.get("EX_DIVIDEND_DATE", ""))[:10],
                "bonus_rmb": row.get("PRETAX_BONUS_RMB", 0.0),    # Dividend per share (Pre-tax)
                "transfer_ratio": row.get("TRANSFER_RATIO", 0.0),  # Increase ratio (Shares per 10)
                "bonus_ratio": row.get("BONUS_RATIO", 0.0),        # Gift ratio (Shares per 10)
                "plan": row.get("ASSIGN_PROGRESS", ""),            # Status (approved, proposal etc)
            })
        return rows

    @staticmethod
    def get_stock_fund_flow_120d(code: str) -> list[dict]:
        """
        Retrieves historical 120-day capital flow data for a stock.
        """
        cleaned = clean_code(code)
        market_code = 1 if cleaned.startswith("6") else 0
        url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        params = {
            "secid": f"{market_code}.{cleaned}",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "lmt": "120",
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/",
        }
        try:
            r = em_get(url, params=params, headers=headers, timeout=15)
            d = r.json()
            klines = d.get("data", {}).get("klines", []) or []
            rows = []
            for line in klines:
                parts = line.split(",")
                if len(parts) >= 7:
                    rows.append({
                        "date": parts[0],
                        "main_net": float(parts[1]) if parts[1] != "-" else 0.0,
                        "small_net": float(parts[2]) if parts[2] != "-" else 0.0,
                        "mid_net": float(parts[3]) if parts[3] != "-" else 0.0,
                        "large_net": float(parts[4]) if parts[4] != "-" else 0.0,
                        "super_net": float(parts[5]) if parts[5] != "-" else 0.0,
                    })
            return rows
        except Exception as e:
            return []
