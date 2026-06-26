import requests
from datetime import datetime
from app.services.base import clean_code

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

class AnnouncementsService:
    _cninfo_orgid_map = {}

    @classmethod
    def _get_cninfo_orgid(cls, code: str) -> str:
        """
        Dynamically retrieves the official giant tide (cninfo) orgId mapping for the given ticker.
        Caches results in memory to boost lookup performance and reduce bandwidth.
        """
        if not cls._cninfo_orgid_map:
            try:
                r = requests.get("http://www.cninfo.com.cn/new/data/szse_stock.json",
                                 headers={"User-Agent": UA}, timeout=15)
                if r.status_code == 200:
                    stock_list = r.json().get("stockList", [])
                    cls._cninfo_orgid_map = {s["code"]: s["orgId"] for s in stock_list}
            except Exception as e:
                # Log warning in standard output
                print(f"[WARN] Failed to load cninfo orgId mappings: {e}")
                
        org = cls._cninfo_orgid_map.get(code)
        if org:
            return org
            
        # Fallback to hardcoded historical standards
        if code.startswith("6"):
            return f"gssh0{code}"
        elif code.startswith("8") or code.startswith("4"):
            return f"gsbj0{code}"
        return f"gssz0{code}"

    @staticmethod
    def _ts_to_date(ts) -> str:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
        return str(ts)[:10] if ts else ""

    @classmethod
    def get_cninfo_announcements(cls, code: str, page_size: int = 30) -> list[dict]:
        """
        Retrieves company regulatory disclosures and board announcements from Cninfo.
        """
        cleaned = clean_code(code)
        org_id = cls._get_cninfo_orgid(cleaned)
        
        url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
        payload = {
            "stock": f"{cleaned},{org_id}",
            "tabName": "fulltext",
            "pageSize": str(page_size),
            "pageNum": "1",
            "column": "",
            "category": "",
            "plate": "",
            "seDate": "",
            "searchkey": "",
            "secid": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        headers = {
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.cninfo.com.cn/new/disclosure",
            "Origin": "https://www.cninfo.com.cn",
        }
        try:
            r = requests.post(url, data=payload, headers=headers, timeout=15)
            r.raise_for_status()
            d = r.json()
            
            rows = []
            announcements = d.get("announcements", []) or []
            for item in announcements:
                rows.append({
                    "title": item.get("announcementTitle", ""),
                    "type": item.get("announcementTypeName", ""),
                    "date": cls._ts_to_date(item.get("announcementTime")),
                    "url": f"https://www.cninfo.com.cn/new/disclosure/detail?annoId={item.get('announcementId', '')}",
                })
            return rows
        except Exception:
            return []
