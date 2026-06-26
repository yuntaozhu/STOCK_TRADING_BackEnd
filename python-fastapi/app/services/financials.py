import requests
from app.core.mootdx_client import tdx_client
from app.core.limiter import em_get
from app.services.base import clean_code

class FinancialsService:
    @staticmethod
    def get_mootdx_finance(code: str) -> dict:
        """
        Retrieves financial snapshots including capital stock, EPS, ROE, book values, reserves etc.
        """
        cleaned = clean_code(code)
        try:
            client = tdx_client()
            fin = client.finance(symbol=cleaned)
            if fin is not None:
                # pandas series or dictionary
                if hasattr(fin, "to_dict"):
                    return fin.to_dict()
                return dict(fin)
        except Exception as e:
            # Let it fail gracefully
            pass
        return {}

    @staticmethod
    def get_mootdx_f10(code: str, name: str) -> str:
        """
        Retrieves company F10 reports (e.g. 公司概况, 股东研究 etc.)
        """
        cleaned = clean_code(code)
        try:
            client = tdx_client()
            text = client.F10(symbol=cleaned, name=name)
            return text or ""
        except Exception:
            return ""

    @staticmethod
    def get_eastmoney_stock_info(code: str) -> dict:
        """
        Retrieves individual stock primary info like industry classification, listing date, capital etc.
        """
        cleaned = clean_code(code)
        market_code = 1 if cleaned.startswith("6") else 0
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "fltt": "2", "invt": "2",
            "fields": "f57,f58,f84,f85,f127,f116,f117,f189,f43",
            "secid": f"{market_code}.{cleaned}",
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = em_get(url, params=params, headers=headers, timeout=10)
            d = r.json().get("data", {}) or {}
            return {
                "code": d.get("f57", ""),
                "name": d.get("f58", ""),
                "industry": d.get("f127", ""),
                "total_shares": d.get("f84", 0),
                "float_shares": d.get("f85", 0),
                "mcap": d.get("f116", 0),
                "float_mcap": d.get("f117", 0),
                "list_date": str(d.get("f189", "")),
                "price": d.get("f43", 0.0),
            }
        except Exception as e:
            return {}

    @staticmethod
    def get_sina_financial_report(code: str, report_type: str = "lrb", num: int = 8) -> list[dict]:
        """
        Retrieves Sina balance sheet (fzb), income statement (lrb), or cash flow (llb).
        """
        cleaned = clean_code(code)
        prefix = "sh" if cleaned.startswith("6") else "sz"
        paper_code = f"{prefix}{cleaned}"
        url = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
        params = {
            "paperCode": paper_code,
            "source": report_type,
            "type": "0",
            "page": "1",
            "num": str(num),
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=15)
            report_list = r.json().get("result", {}).get("data", {}).get("report_list", {}) or {}
            
            rows = []
            for period in sorted(report_list.keys(), reverse=True)[:num]:
                obj = report_list[period]
                rec = {"报告期": f"{period[:4]}-{period[4:6]}-{period[6:8]}"}
                for it in obj.get("data", []) or []:
                    title = it.get("item_title", "")
                    if not title or it.get("item_value") is None:
                        continue
                    rec[title] = it.get("item_value")
                    tongbi = it.get("item_tongbi")
                    if tongbi not in (None, ""):
                        rec[title + "_同比"] = tongbi
                rows.append(rec)
            return rows
        except Exception:
            return []
